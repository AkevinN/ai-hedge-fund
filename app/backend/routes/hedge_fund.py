from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import asyncio

from app.backend.database import get_db
from app.backend.models.schemas import ErrorResponse, HedgeFundRequest, BacktestRequest, BacktestDayResult, BacktestPerformanceMetrics
from app.backend.models.events import StartEvent, ProgressUpdateEvent, ErrorEvent, CompleteEvent
from app.backend.services.graph import create_graph, parse_hedge_fund_response, run_graph_async
from app.backend.services.portfolio import create_portfolio
from app.backend.services.backtest_service import BacktestService
from app.backend.services.api_key_service import ApiKeyService
from src.utils.progress import progress
from src.utils.analysts import get_agents_list

router = APIRouter(prefix="/hedge-fund")

@router.post(
    path="/run",
    responses={
        200: {"description": "Successful response with streaming updates"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def run(request_data: HedgeFundRequest, request: Request, db: Session = Depends(get_db)):
    try:
        # 如果未提供API keys，从数据库加载
        if not request_data.api_keys:
            api_key_service = ApiKeyService(db)
            request_data.api_keys = api_key_service.get_api_keys_dict()

        # 创建投资组合
        portfolio = create_portfolio(request_data.initial_cash, request_data.margin_requirement, request_data.tickers, request_data.portfolio_positions)

        # 使用React Flow图结构构建agent图
        graph = create_graph(
            graph_nodes=request_data.graph_nodes,
            graph_edges=request_data.graph_edges
        )
        graph = graph.compile()

        # 记录测试进度更新用于调试
        progress.update_status("system", None, "准备对冲基金运行")

        # 如果model_provider是枚举，转换为字符串
        model_provider = request_data.model_provider
        if hasattr(model_provider, "value"):
            model_provider = model_provider.value

        # 检测客户端断开连接的函数
        async def wait_for_disconnect():
            """等待客户端断开连接，发生时返回True"""
            try:
                while True:
                    message = await request.receive()
                    if message["type"] == "http.disconnect":
                        return True
            except Exception:
                return True

        # 设置流式响应
        async def event_generator():
            # 进度更新队列
            progress_queue = asyncio.Queue()
            run_task = None
            disconnect_task = None

            # 简单的处理器，将更新添加到队列
            def progress_handler(agent_name, ticker, status, analysis, timestamp):
                event = ProgressUpdateEvent(agent=agent_name, ticker=ticker, status=status, timestamp=timestamp, analysis=analysis)
                progress_queue.put_nowait(event)

            # 向进度跟踪器注册我们的处理器
            progress.register_handler(progress_handler)

            try:
                # 在后台任务中开始图执行
                run_task = asyncio.create_task(
                    run_graph_async(
                        graph=graph,
                        portfolio=portfolio,
                        tickers=request_data.tickers,
                        start_date=request_data.start_date,
                        end_date=request_data.end_date,
                        model_name=request_data.model_name,
                        model_provider=model_provider,
                        request=request_data,  # 传递完整请求以支持agent特定模型访问
                    )
                )

                # 启动断开连接检测任务
                disconnect_task = asyncio.create_task(wait_for_disconnect())

                # 发送初始消息
                yield StartEvent().to_sse()

                # 流式传输进度更新，直到run_task完成或客户端断开连接
                while not run_task.done():
                    # 检查客户端是否断开
                    if disconnect_task.done():
                        print("客户端已断开连接，正在取消对冲基金执行")
                        run_task.cancel()
                        try:
                            await run_task
                        except asyncio.CancelledError:
                            pass
                        return

                    # 获取进度更新或稍等
                    try:
                        event = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                        yield event.to_sse()
                    except asyncio.TimeoutError:
                        # 继续循环
                        pass

                # 获取最终结果
                try:
                    result = await run_task
                except asyncio.CancelledError:
                    print("任务已被取消")
                    return

                if not result or not result.get("messages"):
                    yield ErrorEvent(message="生成对冲基金决策失败").to_sse()
                    return

                # 发送最终结果
                final_data = CompleteEvent(
                    data={
                        "decisions": parse_hedge_fund_response(result.get("messages", [])[-1].content),
                        "analyst_signals": result.get("data", {}).get("analyst_signals", {}),
                        "current_prices": result.get("data", {}).get("current_prices", {}),
                    }
                )
                yield final_data.to_sse()

            except asyncio.CancelledError:
                print("事件生成器已取消")
                return
            finally:
                # 清理
                progress.unregister_handler(progress_handler)
                if run_task and not run_task.done():
                    run_task.cancel()
                    try:
                        await run_task
                    except asyncio.CancelledError:
                        pass
                if disconnect_task and not disconnect_task.done():
                    disconnect_task.cancel()

        # 返回流式响应
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时发生错误: {str(e)}")

@router.post(
    path="/backtest",
    responses={
        200: {"description": "Successful response with streaming backtest updates"},
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def backtest(request_data: BacktestRequest, request: Request, db: Session = Depends(get_db)):
    """在一段时间内运行连续回测，并进行流式更新"""
    try:
        # 如果未提供API keys，从数据库加载
        if not request_data.api_keys:
            api_key_service = ApiKeyService(db)
            request_data.api_keys = api_key_service.get_api_keys_dict()

        # 如果model_provider是枚举，转换为字符串
        model_provider = request_data.model_provider
        if hasattr(model_provider, "value"):
            model_provider = model_provider.value

        # 创建投资组合（与/run端点相同）
        portfolio = create_portfolio(
            request_data.initial_capital,
            request_data.margin_requirement,
            request_data.tickers,
            request_data.portfolio_positions
        )

        # 使用React Flow图结构构建agent图（与/run端点相同）
        graph = create_graph(graph_nodes=request_data.graph_nodes, graph_edges=request_data.graph_edges)
        graph = graph.compile()

        # 使用编译后的图创建回测服务
        backtest_service = BacktestService(
            graph=graph,
            portfolio=portfolio,
            tickers=request_data.tickers,
            start_date=request_data.start_date,
            end_date=request_data.end_date,
            initial_capital=request_data.initial_capital,
            model_name=request_data.model_name,
            model_provider=model_provider,
            request=request_data,  # 传递完整请求以支持agent特定模型访问
        )

        # 检测客户端断开连接的函数
        async def wait_for_disconnect():
            """等待客户端断开连接，发生时返回True"""
            try:
                while True:
                    message = await request.receive()
                    if message["type"] == "http.disconnect":
                        return True
            except Exception:
                return True

        # 设置流式响应
        async def event_generator():
            progress_queue = asyncio.Queue()
            backtest_task = None
            disconnect_task = None

            # 全局进度处理器，在回测期间捕获单个agent更新
            def progress_handler(agent_name, ticker, status, analysis, timestamp):
                event = ProgressUpdateEvent(agent=agent_name, ticker=ticker, status=status, timestamp=timestamp, analysis=analysis)
                progress_queue.put_nowait(event)

            # 进度回调，处理特定于回测的更新
            def progress_callback(update):
                if update["type"] == "progress":
                    event = ProgressUpdateEvent(
                        agent="backtest",
                        ticker=None,
                        status=f"Processing {update['current_date']} ({update['current_step']}/{update['total_dates']})",
                        timestamp=None,
                        analysis=None
                    )
                    progress_queue.put_nowait(event)
                elif update["type"] == "backtest_result":
                    # 将天结果转换为流式事件
                    backtest_result = BacktestDayResult(**update["data"])

                    # 将完整的天结果数据作为JSON发送到analysis字段
                    import json
                    analysis_data = json.dumps(update["data"])

                    event = ProgressUpdateEvent(
                        agent="backtest",
                        ticker=None,
                        status=f"完成 {backtest_result.date} - 投资组合: ${backtest_result.portfolio_value:,.2f}",
                        timestamp=None,
                        analysis=analysis_data
                    )
                    progress_queue.put_nowait(event)

            # 向进度跟踪器注册我们的处理器以捕获agent更新
            progress.register_handler(progress_handler)

            try:
                # 在后台任务中启动回测
                backtest_task = asyncio.create_task(
                    backtest_service.run_backtest_async(progress_callback=progress_callback)
                )

                # 启动断开连接检测任务
                disconnect_task = asyncio.create_task(wait_for_disconnect())

                # 发送初始消息
                yield StartEvent().to_sse()

                # 流式传输进度更新，直到backtest_task完成或客户端断开连接
                while not backtest_task.done():
                    # 检查客户端是否断开
                    if disconnect_task.done():
                        print("客户端已断开连接，正在取消回测执行")
                        backtest_task.cancel()
                        try:
                            await backtest_task
                        except asyncio.CancelledError:
                            pass
                        return

                    # 获取进度更新或稍等
                    try:
                        event = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                        yield event.to_sse()
                    except asyncio.TimeoutError:
                        # 继续循环
                        pass

                # 获取最终结果
                try:
                    result = await backtest_task
                except asyncio.CancelledError:
                    print("回测任务已被取消")
                    return

                if not result:
                    yield ErrorEvent(message="完成回测失败").to_sse()
                    return

                # 发送最终结果
                performance_metrics = BacktestPerformanceMetrics(**result["performance_metrics"])
                final_data = CompleteEvent(
                    data={
                        "performance_metrics": performance_metrics.model_dump(),
                        "final_portfolio": result["final_portfolio"],
                        "total_days": len(result["results"]),
                    }
                )
                yield final_data.to_sse()

            except asyncio.CancelledError:
                print("回测事件生成器已取消")
                return
            finally:
                # 清理
                progress.unregister_handler(progress_handler)
                if backtest_task and not backtest_task.done():
                    backtest_task.cancel()
                    try:
                        await backtest_task
                    except asyncio.CancelledError:
                        pass
                if disconnect_task and not disconnect_task.done():
                    disconnect_task.cancel()

        # 返回流式响应
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理回测请求时发生错误: {str(e)}")


@router.get(
    path="/agents",
    responses={
        200: {"description": "List of available agents"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_agents():
    """获取可用的agents列表"""
    try:
        return {"agents": get_agents_list()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索agents失败: {str(e)}")


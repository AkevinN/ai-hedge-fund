import sys

from colorama import Fore, Style

from src.main import run_hedge_fund
from src.backtesting.engine import BacktestEngine
from src.backtesting.types import PerformanceMetrics
from src.cli.input import (
    parse_cli_inputs,
)


def run_backtest(backtester: BacktestEngine) -> PerformanceMetrics | None:
    """运行回测，优雅处理 KeyboardInterrupt。"""
    try:
        performance_metrics = backtester.run_backtest()
        print(f"\n{Fore.GREEN}回测已成功完成！{Style.RESET_ALL}")
        return performance_metrics
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}回测已被用户中断{Style.RESET_ALL}")
        
        # 尝试显示已计算的任何部分结果
        try:
            portfolio_values = backtester.get_portfolio_values()
            if len(portfolio_values) > 1:
                print(f"{Fore.GREEN}部分结果可用{Style.RESET_ALL}")
                
                # 显示可用投资组合值的基本摘要
                first_value = portfolio_values[0]["Portfolio Value"]
                last_value = portfolio_values[-1]["Portfolio Value"]
                total_return = ((last_value - first_value) / first_value) * 100
                
                print(f"{Fore.CYAN}初始组合价值: ${first_value:,.2f}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}最终组合价值: ${last_value:,.2f}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}总收益率: {total_return:+.2f}%{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}无法生成部分结果: {str(e)}{Style.RESET_ALL}")
        
        sys.exit(0)


### 运行回测 #####
if __name__ == "__main__":
    inputs = parse_cli_inputs(
        description="运行回测模拟",
        require_tickers=False,
        default_months_back=1,
        include_graph_flag=False,
        include_reasoning_flag=False,
    )

    # 创建并运行回测引擎
    backtester = BacktestEngine(
        agent=run_hedge_fund,
        tickers=inputs.tickers,
        start_date=inputs.start_date,
        end_date=inputs.end_date,
        initial_capital=inputs.initial_cash,
        model_name=inputs.model_name,
        model_provider=inputs.model_provider,
        selected_analysts=inputs.selected_analysts,
        initial_margin_requirement=inputs.margin_requirement,
    )

    # 运行回测，优雅退出处理
    performance_metrics = run_backtest(backtester)

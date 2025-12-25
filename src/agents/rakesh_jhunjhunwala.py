from src.graph.state import AgentState, show_agent_reasoning
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
import json
from typing_extensions import Literal
from src.tools.api import get_financial_metrics, get_market_cap, search_line_items
from src.utils.llm import call_llm
from src.utils.progress import progress
from src.utils.api_key import get_api_key_from_state

class RakeshJhunjhunwalaSignal(BaseModel):
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: float
    reasoning: str

def rakesh_jhunjhunwala_agent(state: AgentState, agent_id: str = "rakesh_jhunjhunwala_agent"):
    """使用 Rakesh Jhunjhunwala 的投资原则和 LLM 推理分析股票。"""
    data = state["data"]
    end_date = data["end_date"]
    tickers = data["tickers"]
    api_key = get_api_key_from_state(state, "FINANCIAL_DATASETS_API_KEY")
    # 收集所有分析数据用于 LLM 推理
    analysis_data = {}
    jhunjhunwala_analysis = {}

    for ticker in tickers:

        # 核心数据
        progress.update_status(agent_id, ticker, "获取财务指标")
        metrics = get_financial_metrics(ticker, end_date, period="ttm", limit=5, api_key=api_key)

        progress.update_status(agent_id, ticker, "获取财务项目明细")
        financial_line_items = search_line_items(
            ticker,
            [
                "net_income",
                "earnings_per_share",
                "ebit",
                "operating_income",
                "revenue",
                "operating_margin",
                "total_assets",
                "total_liabilities",
                "current_assets",
                "current_liabilities",
                "free_cash_flow",
                "dividends_and_other_cash_distributions",
                "issuance_or_purchase_of_equity_shares"
            ],
            end_date,
            api_key=api_key,
        )

        progress.update_status(agent_id, ticker, "获取市值")
        market_cap = get_market_cap(ticker, end_date, api_key=api_key)

        # ─── 分析 ───────────────────────────────────────────────────────────
        progress.update_status(agent_id, ticker, "分析成长性")
        growth_analysis = analyze_growth(financial_line_items)

        progress.update_status(agent_id, ticker, "分析盈利能力")
        profitability_analysis = analyze_profitability(financial_line_items)

        progress.update_status(agent_id, ticker, "分析资产负债表")
        balancesheet_analysis = analyze_balance_sheet(financial_line_items)

        progress.update_status(agent_id, ticker, "分析现金流")
        cashflow_analysis = analyze_cash_flow(financial_line_items)

        progress.update_status(agent_id, ticker, "分析管理层行动")
        management_analysis = analyze_management_actions(financial_line_items)

        progress.update_status(agent_id, ticker, "计算内在价值")
        # 只计算一次内在价值
        intrinsic_value = calculate_intrinsic_value(financial_line_items, market_cap)

        # ─── 评分与安全边际 ──────────────────────────────────────────
        total_score = (
            growth_analysis["score"]
            + profitability_analysis["score"]
            + balancesheet_analysis["score"]
            + cashflow_analysis["score"]
            + management_analysis["score"]
        )
        # 修正：基于实际评分明细的正确 max_score 计算
        max_score = 24  # 8(盈利) + 7(成长) + 4(资产) + 3(现金流) + 2(管理) = 24

        # 计算安全边际
        margin_of_safety = (
            (intrinsic_value - market_cap) / market_cap if intrinsic_value and market_cap else None
        )

        # Jhunjhunwala 的决策规则（最低 30% 安全边际才有信心）
        if margin_of_safety is not None and margin_of_safety >= 0.30:
            signal = "bullish"
        elif margin_of_safety is not None and margin_of_safety <= -0.30:
            signal = "bearish"
        else:
            # 中性情况下使用质量评分作为决定因素
            quality_score = assess_quality_metrics(financial_line_items)
            if quality_score >= 0.7 and total_score >= max_score * 0.6:
                signal = "bullish"  # 高质量公司价格合理
            elif quality_score <= 0.4 or total_score <= max_score * 0.3:
                signal = "bearish"  # 质量差或基本面差
            else:
                signal = "neutral"

        # 基于安全边际和质量的信心度
        if margin_of_safety is not None:
            confidence = min(max(abs(margin_of_safety) * 150, 20), 95)  # 20-95% 范围
        else:
            confidence = min(max((total_score / max_score) * 100, 10), 80)  # 基于评分

        # 创建综合分析摘要
        intrinsic_value_analysis = analyze_rakesh_jhunjhunwala_style(
            financial_line_items,
            intrinsic_value=intrinsic_value,
            current_price=market_cap
        )

        analysis_data[ticker] = {
            "signal": signal,
            "score": total_score,
            "max_score": max_score,
            "margin_of_safety": margin_of_safety,
            "growth_analysis": growth_analysis,
            "profitability_analysis": profitability_analysis,
            "balancesheet_analysis": balancesheet_analysis,
            "cashflow_analysis": cashflow_analysis,
            "management_analysis": management_analysis,
            "intrinsic_value_analysis": intrinsic_value_analysis,
            "intrinsic_value": intrinsic_value,
            "market_cap": market_cap,
        }

        # ─── LLM：生成 Jhunjhunwala 风格的分析 ──────────────────────────────
        progress.update_status(agent_id, ticker, "生成 Jhunjhunwala 分析")
        jhunjhunwala_output = generate_jhunjhunwala_output(
            ticker=ticker,
            analysis_data=analysis_data[ticker],
            state=state,
            agent_id=agent_id,
        )

        jhunjhunwala_analysis[ticker] = jhunjhunwala_output.model_dump()

        progress.update_status(agent_id, ticker, "完成", analysis=jhunjhunwala_output.reasoning)

    # ─── 将消息推送回图状态 ──────────────────────────────────────
    message = HumanMessage(content=json.dumps(jhunjhunwala_analysis), name=agent_id)

    if state["metadata"]["show_reasoning"]:
        show_agent_reasoning(jhunjhunwala_analysis, "Rakesh Jhunjhunwala Agent")

    state["data"]["analyst_signals"][agent_id] = jhunjhunwala_analysis
    progress.update_status(agent_id, None, "完成")

    return {"messages": [message], "data": state["data"]}


def analyze_profitability(financial_line_items: list) -> dict[str, any]:
    """
    分析盈利能力指标，如净利润、EBIT、EPS、营业收入。
    关注强劲、持续的盈利增长和运营效率。
    """
    if not financial_line_items:
        return {"score": 0, "details": "无盈利能力数据"}

    latest = financial_line_items[0]
    score = 0
    reasoning = []

    # 计算 ROE（净资产收益率）- Jhunjhunwala 的关键指标
    if (getattr(latest, 'net_income', None) and latest.net_income > 0 and
        getattr(latest, 'total_assets', None) and getattr(latest, 'total_liabilities', None) and
        latest.total_assets and latest.total_liabilities):

        shareholders_equity = latest.total_assets - latest.total_liabilities
        if shareholders_equity > 0:
            roe = (latest.net_income / shareholders_equity) * 100
            if roe > 20:  # 优秀的 ROE
                score += 3
                reasoning.append(f"优秀的 ROE: {roe:.1f}%")
            elif roe > 15:  # 良好的 ROE
                score += 2
                reasoning.append(f"良好的 ROE: {roe:.1f}%")
            elif roe > 10:  # 不错的 ROE
                score += 1
                reasoning.append(f"不错的 ROE: {roe:.1f}%")
            else:
                reasoning.append(f"ROE 较低: {roe:.1f}%")
        else:
            reasoning.append("股东权益为负")
    else:
        reasoning.append("无法计算 ROE - 数据缺失")

    # 营业利润率分析
    if (getattr(latest, "operating_income", None) and latest.operating_income and
        getattr(latest, "revenue", None) and latest.revenue and latest.revenue > 0):
        operating_margin = (latest.operating_income / latest.revenue) * 100
        if operating_margin > 20:  # 优秀利润率
            score += 2
            reasoning.append(f"优秀的营业利润率: {operating_margin:.1f}%")
        elif operating_margin > 15:  # 良好利润率
            score += 1
            reasoning.append(f"良好的营业利润率: {operating_margin:.1f}%")
        elif operating_margin > 0:
            reasoning.append(f"正营业利润率: {operating_margin:.1f}%")
        else:
            reasoning.append(f"负营业利润率: {operating_margin:.1f}%")
    else:
        reasoning.append("无法计算营业利润率")

    # EPS 增长一致性（3年趋势）
    eps_values = [getattr(item, "earnings_per_share", None) for item in financial_line_items
                  if getattr(item, "earnings_per_share", None) is not None and getattr(item, "earnings_per_share", None) > 0]

    if len(eps_values) >= 3:
        # 计算 EPS 的复合年增长率
        initial_eps = eps_values[-1]  # 最早值
        final_eps = eps_values[0]     # 最新值
        years = len(eps_values) - 1

        if initial_eps > 0:
            eps_cagr = ((final_eps / initial_eps) ** (1/years) - 1) * 100
            if eps_cagr > 20:  # 高增长
                score += 3
                reasoning.append(f"高 EPS CAGR: {eps_cagr:.1f}%")
            elif eps_cagr > 15:  # 良好增长
                score += 2
                reasoning.append(f"良好 EPS CAGR: {eps_cagr:.1f}%")
            elif eps_cagr > 10:  # 中等增长
                score += 1
                reasoning.append(f"中等 EPS CAGR: {eps_cagr:.1f}%")
            else:
                reasoning.append(f"低 EPS CAGR: {eps_cagr:.1f}%")
        else:
            reasoning.append("无法从负基数计算 EPS 增长")
    else:
        reasoning.append("EPS 数据不足，无法进行增长分析")

    return {"score": score, "details": "; ".join(reasoning)}


def analyze_growth(financial_line_items: list) -> dict[str, any]:
    """
    使用 CAGR 分析收入和净利润增长趋势。
    Jhunjhunwala 青睐具有强劲、持续复合增长的公司。
    """
    if len(financial_line_items) < 3:
        return {"score": 0, "details": "数据不足，无法进行增长分析"}

    score = 0
    reasoning = []

    # 收入 CAGR 分析
    revenues = [getattr(item, "revenue", None) for item in financial_line_items
                if getattr(item, "revenue", None) is not None and getattr(item, "revenue", None) > 0]

    if len(revenues) >= 3:
        initial_revenue = revenues[-1]  # 最早
        final_revenue = revenues[0]     # 最新
        years = len(revenues) - 1

        if initial_revenue > 0:  # 修正：添加零值检查
            revenue_cagr = ((final_revenue / initial_revenue) ** (1/years) - 1) * 100

            if revenue_cagr > 20:  # 高增长
                score += 3
                reasoning.append(f"优秀的收入 CAGR: {revenue_cagr:.1f}%")
            elif revenue_cagr > 15:  # 良好增长
                score += 2
                reasoning.append(f"良好的收入 CAGR: {revenue_cagr:.1f}%")
            elif revenue_cagr > 10:  # 中等增长
                score += 1
                reasoning.append(f"中等收入 CAGR: {revenue_cagr:.1f}%")
            else:
                reasoning.append(f"低收入 CAGR: {revenue_cagr:.1f}%")
        else:
            reasoning.append("无法从零基数计算收入 CAGR")
    else:
        reasoning.append("收入数据不足，无法计算 CAGR")

    # Net Income CAGR Analysis
    net_incomes = [getattr(item, "net_income", None) for item in financial_line_items 
                   if getattr(item, "net_income", None) is not None and getattr(item, "net_income", None) > 0]
    
    if len(net_incomes) >= 3:
        initial_income = net_incomes[-1]  # Oldest
        final_income = net_incomes[0]     # Latest
        years = len(net_incomes) - 1
        
        if initial_income > 0:  # Fixed: Add zero check
            income_cagr = ((final_income / initial_income) ** (1/years) - 1) * 100
            
            if income_cagr > 25:  # Very high growth
                score += 3
                reasoning.append(f"Excellent income CAGR: {income_cagr:.1f}%")
            elif income_cagr > 20:  # High growth
                score += 2
                reasoning.append(f"High income CAGR: {income_cagr:.1f}%")
            elif income_cagr > 15:  # Good growth
                score += 1
                reasoning.append(f"Good income CAGR: {income_cagr:.1f}%")
            else:
                reasoning.append(f"Moderate income CAGR: {income_cagr:.1f}%")
        else:
            reasoning.append("Cannot calculate income CAGR from zero base")
    else:
        reasoning.append("Insufficient net income data for CAGR calculation")

    # Revenue Consistency Check (year-over-year)
    if len(revenues) >= 3:
        declining_years = sum(1 for i in range(1, len(revenues)) if revenues[i-1] > revenues[i])
        consistency_ratio = 1 - (declining_years / (len(revenues) - 1))
        
        if consistency_ratio >= 0.8:  # 80% or more years with growth
            score += 1
            reasoning.append(f"Consistent growth pattern ({consistency_ratio*100:.0f}% of years)")
        else:
            reasoning.append(f"Inconsistent growth pattern ({consistency_ratio*100:.0f}% of years)")

    return {"score": score, "details": "; ".join(reasoning)}


def analyze_balance_sheet(financial_line_items: list) -> dict[str, any]:
    """
    检查财务实力 - 健康的资产/负债结构、流动性。
    Jhunjhunwala 青睐资产负债表干净、债务可控的公司。
    """
    if not financial_line_items:
        return {"score": 0, "details": "无资产负债表数据"}

    latest = financial_line_items[0]
    score = 0
    reasoning = []

    # 负债与资产比率
    if (getattr(latest, "total_assets", None) and getattr(latest, "total_liabilities", None)
        and latest.total_assets and latest.total_liabilities
        and latest.total_assets > 0):
        debt_ratio = latest.total_liabilities / latest.total_assets
        if debt_ratio < 0.5:
            score += 2
            reasoning.append(f"低负债比率: {debt_ratio:.2f}")
        elif debt_ratio < 0.7:
            score += 1
            reasoning.append(f"中等负债比率: {debt_ratio:.2f}")
        else:
            reasoning.append(f"高负债比率: {debt_ratio:.2f}")
    else:
        reasoning.append("数据不足，无法计算负债比率")

    # 流动比率（流动性）
    if (getattr(latest, "current_assets", None) and getattr(latest, "current_liabilities", None)
        and latest.current_assets and latest.current_liabilities
        and latest.current_liabilities > 0):
        current_ratio = latest.current_assets / latest.current_liabilities
        if current_ratio > 2.0:
            score += 2
            reasoning.append(f"优秀的流动性，流动比率: {current_ratio:.2f}")
        elif current_ratio > 1.5:
            score += 1
            reasoning.append(f"良好的流动性，流动比率: {current_ratio:.2f}")
        else:
            reasoning.append(f"流动性较弱，流动比率: {current_ratio:.2f}")
    else:
        reasoning.append("数据不足，无法计算流动比率")

    return {"score": score, "details": "; ".join(reasoning)}


def analyze_cash_flow(financial_line_items: list) -> dict[str, any]:
    """
    评估自由现金流和股息行为。
    Jhunjhunwala 欣赏能产生强劲自由现金流并回报股东的公司。
    """
    if not financial_line_items:
        return {"score": 0, "details": "无现金流数据"}

    latest = financial_line_items[0]
    score = 0
    reasoning = []

    # 自由现金流分析
    if getattr(latest, "free_cash_flow", None) and latest.free_cash_flow:
        if latest.free_cash_flow > 0:
            score += 2
            reasoning.append(f"正自由现金流: {latest.free_cash_flow}")
        else:
            reasoning.append(f"负自由现金流: {latest.free_cash_flow}")
    else:
        reasoning.append("无自由现金流数据")

    # 股息分析
    if getattr(latest, "dividends_and_other_cash_distributions", None) and latest.dividends_and_other_cash_distributions:
        if latest.dividends_and_other_cash_distributions < 0:  # 负值表示股息支付的现金流出
            score += 1
            reasoning.append("公司向股东支付股息")
        else:
            reasoning.append("无重要股息支付")
    else:
        reasoning.append("无股息支付数据")

    return {"score": score, "details": "; ".join(reasoning)}


def analyze_management_actions(financial_line_items: list) -> dict[str, any]:
    """
    查看股份发行或回购以评估对股东的友好程度。
    Jhunjhunwala 喜欢回购股份或避免稀释的管理层。
    """
    if not financial_line_items:
        return {"score": 0, "details": "无管理层行动数据"}

    latest = financial_line_items[0]
    score = 0
    reasoning = []

    issuance = getattr(latest, "issuance_or_purchase_of_equity_shares", None)
    if issuance is not None:
        if issuance < 0:  # 负值表示股份回购
            score += 2
            reasoning.append(f"公司回购股份: {abs(issuance)}")
        elif issuance > 0:
            reasoning.append(f"检测到股份发行（潜在稀释）: {issuance}")
        else:
            score += 1
            reasoning.append("近期无股份发行或回购")
    else:
        reasoning.append("无股份发行或回购数据")

    return {"score": score, "details": "; ".join(reasoning)}


def assess_quality_metrics(financial_line_items: list) -> float:
    """
    根据 Jhunjhunwala 的标准评估公司质量。
    返回 0 到 1 之间的分数。
    """
    if not financial_line_items:
        return 0.5  # 中性分数
    
    latest = financial_line_items[0]
    quality_factors = []
    
    # ROE consistency and level
    if (getattr(latest, 'net_income', None) and getattr(latest, 'total_assets', None) and 
        getattr(latest, 'total_liabilities', None) and latest.total_assets and latest.total_liabilities):
        
        shareholders_equity = latest.total_assets - latest.total_liabilities
        if shareholders_equity > 0 and latest.net_income:
            roe = latest.net_income / shareholders_equity
            if roe > 0.20:  # ROE > 20%
                quality_factors.append(1.0)
            elif roe > 0.15:  # ROE > 15%
                quality_factors.append(0.8)
            elif roe > 0.10:  # ROE > 10%
                quality_factors.append(0.6)
            else:
                quality_factors.append(0.3)
        else:
            quality_factors.append(0.0)
    else:
        quality_factors.append(0.5)
    
    # Debt levels (lower is better)
    if (getattr(latest, 'total_assets', None) and getattr(latest, 'total_liabilities', None) and 
        latest.total_assets and latest.total_liabilities):
        debt_ratio = latest.total_liabilities / latest.total_assets
        if debt_ratio < 0.3:  # Low debt
            quality_factors.append(1.0)
        elif debt_ratio < 0.5:  # Moderate debt
            quality_factors.append(0.7)
        elif debt_ratio < 0.7:  # High debt
            quality_factors.append(0.4)
        else:  # Very high debt
            quality_factors.append(0.1)
    else:
        quality_factors.append(0.5)
    
    # Growth consistency
    net_incomes = [getattr(item, "net_income", None) for item in financial_line_items[:4] 
                   if getattr(item, "net_income", None) is not None and getattr(item, "net_income", None) > 0]
    
    if len(net_incomes) >= 3:
        declining_years = sum(1 for i in range(1, len(net_incomes)) if net_incomes[i-1] > net_incomes[i])
        consistency = 1 - (declining_years / (len(net_incomes) - 1))
        quality_factors.append(consistency)
    else:
        quality_factors.append(0.5)
    
    # Return average quality score
    return sum(quality_factors) / len(quality_factors) if quality_factors else 0.5


def calculate_intrinsic_value(financial_line_items: list, market_cap: float) -> float:
    """
    使用 Rakesh Jhunjhunwala 的方法计算内在价值：
    - 关注盈利能力和增长
    - 保守的折现率
    - 对持续表现者给予质量溢价
    """
    if not financial_line_items or not market_cap:
        return None
    
    try:
        latest = financial_line_items[0]
        
        # Need positive earnings as base
        if not getattr(latest, 'net_income', None) or latest.net_income <= 0:
            return None
        
        # Get historical earnings for growth calculation
        net_incomes = [getattr(item, "net_income", None) for item in financial_line_items[:5] 
                       if getattr(item, "net_income", None) is not None and getattr(item, "net_income", None) > 0]
        
        if len(net_incomes) < 2:
            # Use current earnings with conservative multiple for stable companies
            return latest.net_income * 12  # Conservative P/E of 12
        
        # Calculate sustainable growth rate using historical data
        initial_income = net_incomes[-1]  # Oldest
        final_income = net_incomes[0]     # Latest
        years = len(net_incomes) - 1
        
        # Calculate historical CAGR
        if initial_income > 0:  # Fixed: Add zero check
            historical_growth = ((final_income / initial_income) ** (1/years) - 1)
        else:
            historical_growth = 0.05  # Default to 5%
        
        # Conservative growth assumptions (Jhunjhunwala style)
        if historical_growth > 0.25:  # Cap at 25% for sustainability
            sustainable_growth = 0.20  # Conservative 20%
        elif historical_growth > 0.15:
            sustainable_growth = historical_growth * 0.8  # 80% of historical
        elif historical_growth > 0.05:
            sustainable_growth = historical_growth * 0.9  # 90% of historical
        else:
            sustainable_growth = 0.05  # Minimum 5% for inflation
        
        # Quality assessment affects discount rate
        quality_score = assess_quality_metrics(financial_line_items)
        
        # Discount rate based on quality (Jhunjhunwala preferred quality)
        if quality_score >= 0.8:  # High quality
            discount_rate = 0.12  # 12% for high quality companies
            terminal_multiple = 18
        elif quality_score >= 0.6:  # Medium quality
            discount_rate = 0.15  # 15% for medium quality
            terminal_multiple = 15
        else:  # Lower quality
            discount_rate = 0.18  # 18% for riskier companies
            terminal_multiple = 12
        
        # Simple DCF with terminal value
        current_earnings = latest.net_income
        terminal_value = 0
        dcf_value = 0
        
        # Project 5 years of earnings
        for year in range(1, 6):
            projected_earnings = current_earnings * ((1 + sustainable_growth) ** year)
            present_value = projected_earnings / ((1 + discount_rate) ** year)
            dcf_value += present_value
        
        # Terminal value (year 5 earnings * terminal multiple)
        year_5_earnings = current_earnings * ((1 + sustainable_growth) ** 5)
        terminal_value = (year_5_earnings * terminal_multiple) / ((1 + discount_rate) ** 5)
        
        total_intrinsic_value = dcf_value + terminal_value
        
        return total_intrinsic_value
        
    except Exception:
        # Fallback to simple earnings multiple
        if getattr(latest, 'net_income', None) and latest.net_income > 0:
            return latest.net_income * 15
        return None


def analyze_rakesh_jhunjhunwala_style(
    financial_line_items: list,
    owner_earnings: float = None,
    intrinsic_value: float = None,
    current_price: float = None,
) -> dict[str, any]:
    """
    Rakesh Jhunjhunwala 投资风格的综合分析。
    """
    # 运行子分析
    profitability = analyze_profitability(financial_line_items)
    growth = analyze_growth(financial_line_items)
    balance_sheet = analyze_balance_sheet(financial_line_items)
    cash_flow = analyze_cash_flow(financial_line_items)
    management = analyze_management_actions(financial_line_items)

    total_score = (
        profitability["score"]
        + growth["score"]
        + balance_sheet["score"]
        + cash_flow["score"]
        + management["score"]
    )

    details = (
        f"Profitability: {profitability['details']}\n"
        f"Growth: {growth['details']}\n"
        f"Balance Sheet: {balance_sheet['details']}\n"
        f"Cash Flow: {cash_flow['details']}\n"
        f"Management Actions: {management['details']}"
    )

    # Use provided intrinsic value or calculate if not provided
    if not intrinsic_value:
        intrinsic_value = calculate_intrinsic_value(financial_line_items, current_price)

    valuation_gap = None
    if intrinsic_value and current_price:
        valuation_gap = intrinsic_value - current_price

    return {
        "total_score": total_score,
        "details": details,
        "owner_earnings": owner_earnings,
        "intrinsic_value": intrinsic_value,
        "current_price": current_price,
        "valuation_gap": valuation_gap,
        "breakdown": {
            "profitability": profitability,
            "growth": growth,
            "balance_sheet": balance_sheet,
            "cash_flow": cash_flow,
            "management": management,
        },
    }


# ────────────────────────────────────────────────────────────────────────────────
# LLM 生成
# ────────────────────────────────────────────────────────────────────────────────
def generate_jhunjhunwala_output(
    ticker: str,
    analysis_data: dict[str, any],
    state: AgentState,
    agent_id: str,
) -> RakeshJhunjhunwalaSignal:
    """使用 Jhunjhunwala 的原则从 LLM 获取投资决策"""
    template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a Rakesh Jhunjhunwala AI agent. Decide on investment signals based on Rakesh Jhunjhunwala's principles:
                - Circle of Competence: Only invest in businesses you understand
                - Margin of Safety (> 30%): Buy at a significant discount to intrinsic value
                - Economic Moat: Look for durable competitive advantages
                - Quality Management: Seek conservative, shareholder-oriented teams
                - Financial Strength: Favor low debt, strong returns on equity
                - Long-term Horizon: Invest in businesses, not just stocks
                - Growth Focus: Look for companies with consistent earnings and revenue growth
                - Sell only if fundamentals deteriorate or valuation far exceeds intrinsic value

                When providing your reasoning, be thorough and specific by:
                1. Explaining the key factors that influenced your decision the most (both positive and negative)
                2. Highlighting how the company aligns with or violates specific Jhunjhunwala principles
                3. Providing quantitative evidence where relevant (e.g., specific margins, ROE values, debt levels)
                4. Concluding with a Jhunjhunwala-style assessment of the investment opportunity
                5. Using Rakesh Jhunjhunwala's voice and conversational style in your explanation

                For example, if bullish: "I'm particularly impressed with the consistent growth and strong balance sheet, reminiscent of quality companies that create long-term wealth..."
                For example, if bearish: "The deteriorating margins and high debt levels concern me - this doesn't fit the profile of companies that build lasting value..."

                Follow these guidelines strictly.
                """,
            ),
            (
                "human",
                """Based on the following data, create the investment signal as Rakesh Jhunjhunwala would:

                Analysis Data for {ticker}:
                {analysis_data}

                Return the trading signal in the following JSON format exactly:
                {{
                  "signal": "bullish" | "bearish" | "neutral",
                  "confidence": float between 0 and 100,
                  "reasoning": "string"
                }}
                """,
            ),
        ]
    )

    prompt = template.invoke({"analysis_data": json.dumps(analysis_data, indent=2), "ticker": ticker})

    # 解析失败时的默认回退信号
    def create_default_rakesh_jhunjhunwala_signal():
        return RakeshJhunjhunwalaSignal(signal="neutral", confidence=0.0, reasoning="分析出错，默认为中性")

    return call_llm(
        prompt=prompt,
        pydantic_model=RakeshJhunjhunwalaSignal,
        state=state,
        agent_name=agent_id,
        default_factory=create_default_rakesh_jhunjhunwala_signal,
    )
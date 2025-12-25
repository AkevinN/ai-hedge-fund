"""分析师配置相关的常量和工具"""

from src.agents import portfolio_manager
from src.agents.aswath_damodaran import aswath_damodaran_agent
from src.agents.ben_graham import ben_graham_agent
from src.agents.bill_ackman import bill_ackman_agent
from src.agents.cathie_wood import cathie_wood_agent
from src.agents.charlie_munger import charlie_munger_agent
from src.agents.fundamentals import fundamentals_analyst_agent
from src.agents.michael_burry import michael_burry_agent
from src.agents.phil_fisher import phil_fisher_agent
from src.agents.peter_lynch import peter_lynch_agent
from src.agents.sentiment import sentiment_analyst_agent
from src.agents.stanley_druckenmiller import stanley_druckenmiller_agent
from src.agents.technicals import technical_analyst_agent
from src.agents.valuation import valuation_analyst_agent
from src.agents.warren_buffett import warren_buffett_agent
from src.agents.rakesh_jhunjhunwala import rakesh_jhunjhunwala_agent
from src.agents.mohnish_pabrai import mohnish_pabrai_agent
from src.agents.news_sentiment import news_sentiment_agent
from src.agents.growth_agent import growth_analyst_agent

# 定义分析师配置 - 单一可信来源
ANALYST_CONFIG = {
    "aswath_damodaran": {
        "display_name": "Aswath Damodaran (估值之父)",
        "description": "估值学院院长",
        "investing_style": "专注于内在价值和财务指标，通过严谨的估值分析评估投资机会",
        "agent_func": aswath_damodaran_agent,
        "type": "analyst",
        "order": 0,
    },
    "ben_graham": {
        "display_name": "Ben Graham (价值投资之父)",
        "description": "价值投资开创者",
        "investing_style": "强调安全边际，通过系统性价值分析投资于基本面强劲的低估公司",
        "agent_func": ben_graham_agent,
        "type": "analyst",
        "order": 1,
    },
    "bill_ackman": {
        "display_name": "Bill Ackman (激进投资者)",
        "description": "维权投资专家",
        "investing_style": "通过战略性维权行动和逆向投资头寸影响管理层并释放价值",
        "agent_func": bill_ackman_agent,
        "type": "analyst",
        "order": 2,
    },
    "cathie_wood": {
        "display_name": "Cathie Wood (成长女王)",
        "description": "成长投资女王",
        "investing_style": "专注于颠覆性创新和成长，投资于引领技术进步和市场变革的公司",
        "agent_func": cathie_wood_agent,
        "type": "analyst",
        "order": 3,
    },
    "charlie_munger": {
        "display_name": "Charlie Munger (理性思考者)",
        "description": "理性思维大师",
        "investing_style": "提倡价值投资，专注于优质企业和长期成长，通过理性决策进行投资",
        "agent_func": charlie_munger_agent,
        "type": "analyst",
        "order": 4,
    },
    "michael_burry": {
        "display_name": "Michael Burry (做空传奇)",
        "description": "大空头逆向投资者",
        "investing_style": "进行逆向投资，经常做空高估市场，通过深入基本面分析投资低估资产",
        "agent_func": michael_burry_agent,
        "type": "analyst",
        "order": 5,
    },
    "mohnish_pabrai": {
        "display_name": "Mohnish Pabrai (Dhandho投资者)",
        "description": "Dhandho投资法开创者",
        "investing_style": "专注于价值投资和长期成长，通过基本面分析和安全边际进行投资",
        "agent_func": mohnish_pabrai_agent,
        "type": "analyst",
        "order": 6,
    },
    "peter_lynch": {
        "display_name": "Peter Lynch (十倍股猎手)",
        "description": "十倍股投资大师",
        "investing_style": "使用'买你懂的'策略，投资于商业模式易懂且成长潜力强劲的公司",
        "agent_func": peter_lynch_agent,
        "type": "analyst",
        "order": 6,
    },
    "phil_fisher": {
        "display_name": "Phil Fisher (闲聊投资者)",
        "description": "闲聊调研法开创者",
        "investing_style": "强调投资于管理层强大且产品创新的公司，通过闲聊调研专注于长期成长",
        "agent_func": phil_fisher_agent,
        "type": "analyst",
        "order": 7,
    },
    "rakesh_jhunjhunwala": {
        "display_name": "Rakesh Jhunjhunwala (印度大牛)",
        "description": "印度股神",
        "investing_style": "利用宏观经济洞察投资高成长行业，特别是新兴市场和国内机会",
        "agent_func": rakesh_jhunjhunwala_agent,
        "type": "analyst",
        "order": 8,
    },
    "stanley_druckenmiller": {
        "display_name": "Stanley Druckenmiller (宏观大师)",
        "description": "宏观投资大师",
        "investing_style": "专注于宏观经济趋势，通过自上而下的分析对货币、大宗商品和利率进行大额投注",
        "agent_func": stanley_druckenmiller_agent,
        "type": "analyst",
        "order": 9,
    },
    "warren_buffett": {
        "display_name": "Warren Buffett (奥马哈先知)",
        "description": "奥马哈先知",
        "investing_style": "通过价值投资和长期持有，寻找基本面强劲且具有竞争优势的公司",
        "agent_func": warren_buffett_agent,
        "type": "analyst",
        "order": 10,
    },
    "technical_analyst": {
        "display_name": "技术分析师",
        "description": "图表形态专家",
        "investing_style": "专注于图表形态和市场趋势进行投资决策，常用技术指标和价格行为分析",
        "agent_func": technical_analyst_agent,
        "type": "analyst",
        "order": 11,
    },
    "fundamentals_analyst": {
        "display_name": "基本面分析师",
        "description": "财务报表专家",
        "investing_style": "深入研究财务报表和经济指标，通过基本面分析评估公司的内在价值",
        "agent_func": fundamentals_analyst_agent,
        "type": "analyst",
        "order": 12,
    },
    "growth_analyst": {
        "display_name": "成长分析师",
        "description": "成长股专家",
        "investing_style": "分析成长趋势和估值，通过成长分析识别成长机会",
        "agent_func": growth_analyst_agent,
        "type": "analyst",
        "order": 13,
    },
    "news_sentiment_analyst": {
        "display_name": "新闻情绪分析师",
        "description": "新闻情绪专家",
        "investing_style": "分析新闻情绪预测市场走势，通过新闻分析识别投资机会",
        "agent_func": news_sentiment_agent,
        "type": "analyst",
        "order": 14,
    },
    "sentiment_analyst": {
        "display_name": "情绪分析师",
        "description": "市场情绪专家",
        "investing_style": "衡量市场情绪和投资者行为，通过行为分析预测市场走势并识别机会",
        "agent_func": sentiment_analyst_agent,
        "type": "analyst",
        "order": 15,
    },
    "valuation_analyst": {
        "display_name": "估值分析师",
        "description": "公司估值专家",
        "investing_style": "专注于确定公司公允价值，使用各种估值模型和财务指标进行投资决策",
        "agent_func": valuation_analyst_agent,
        "type": "analyst",
        "order": 16,
    },
}

# 从 ANALYST_CONFIG 派生 ANALYST_ORDER 以实现向后兼容
ANALYST_ORDER = [(config["display_name"], key) for key, config in sorted(ANALYST_CONFIG.items(), key=lambda x: x[1]["order"])]


def get_analyst_nodes():
    """获取分析师键到其 (node_name, agent_func) 元组的映射"""
    return {key: (f"{key}_agent", config["agent_func"]) for key, config in ANALYST_CONFIG.items()}


def get_agents_list():
    """获取 API 响应的代理列表"""
    return [
        {
            "key": key,
            "display_name": config["display_name"],
            "description": config["description"],
            "investing_style": config["investing_style"],
            "order": config["order"]
        }
        for key, config in sorted(ANALYST_CONFIG.items(), key=lambda x: x[1]["order"])
    ]

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class StockAnalysisRequest(BaseModel):
    stock_code: str


class DividendInfo(BaseModel):
    """分红信息"""
    year: int
    cash_dividend: float  # 每股分红
    bonus_shares: float   # 送股
    rights_issue: float   # 配股
    total_divident: float  # 总分红（含送股折算）


class FinancialMetrics(BaseModel):
    """财务指标"""
    # 基础信息
    stock_code: str
    stock_name: str
    industry: str

    # 股息相关
    dividend_yield: float  # 股息率 %
    dividend_years: int   # 连续分红年数

    # 派息率
    payout_ratio: float    # 派息率 %

    # 盈利质量
    net_profit_growth: List[float]  # 净利润增长率（近3年）
    roe_history: List[float]        # ROE历史（近5年）
    avg_roe: float                  # 平均ROE

    # 现金流
    operating_cash_flow: List[float]  # 经营现金流（近3年）
    cash_flow_covered: List[bool]     # 现金流覆盖净利润

    # 资产负债
    debt_ratio: float  # 资产负债率 %

    # 估值
    pe_ttm: float      # 市盈率TTM
    pb: float          # 市净率
    pe_percentile: float   # PE历史分位数 %
    pb_percentile: float   # PB历史分位数 %
    industry_pe: float     # 行业平均PE
    industry_pb: float     # 行业平均PB

    # 原始数据（用于调试）
    raw_dividends: Optional[List[DividendInfo]] = None

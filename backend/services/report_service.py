# -*- coding: utf-8 -*-
"""
每日财经早报服务
"""

import requests
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random


class ReportService:
    """每日财经早报服务"""

    # 投资知识库
    KNOWLEDGE_TIPS = [
        {
            "title": "ROE - 净资产收益率",
            "content": "ROE = 净利润 ÷ 净资产，衡量公司盈利能力的核心指标。巴菲特曾说：如果只能选一个指标选股，他会选ROE。一般ROE>15%的公司值得关注。",
            "category": "财务指标"
        },
        {
            "title": "PE - 市盈率",
            "content": "PE = 股价 ÷ 每股收益，表示按当前盈利回本需要的年数。PE越低理论上越便宜，但需结合行业和成长性判断。银行股PE通常较低，科技股PE通常较高。",
            "category": "估值指标"
        },
        {
            "title": "PB - 市净率",
            "content": "PB = 股价 ÷ 每股净资产，衡量股价相对账面价值的溢价。PB<1表示'破净'，可能被低估。重资产行业（银行、地产）更适合用PB估值。",
            "category": "估值指标"
        },
        {
            "title": "股息率",
            "content": "股息率 = 每股分红 ÷ 股价 × 100%，衡量投资现金回报。股息率>4%属于较高水平。高股息股票适合追求稳定收益的投资者。",
            "category": "收益指标"
        },
        {
            "title": "CAGR - 复合年增长率",
            "content": "CAGR计算一段时间内的年均增长率，消除波动影响。公式：CAGR = (期末值/期初值)^(1/年数) - 1。常用于评估公司成长性。",
            "category": "成长指标"
        },
        {
            "title": "自由现金流",
            "content": "自由现金流 = 经营现金流 - 资本支出，代表公司可自由支配的现金。持续为正说明公司'造血'能力强，是衡量盈利质量的重要指标。",
            "category": "财务指标"
        },
        {
            "title": "毛利率",
            "content": "毛利率 = (营收-成本) ÷ 营收 × 100%，反映产品定价能力和成本控制。高毛利率通常意味着强品牌或技术壁垒。茅台毛利率超90%。",
            "category": "盈利指标"
        },
        {
            "title": "资产负债率",
            "content": "资产负债率 = 总负债 ÷ 总资产 × 100%，衡量财务风险。<40%为优秀，<60%为良好。金融、地产行业负债率通常较高。",
            "category": "财务指标"
        },
        {
            "title": "定投策略",
            "content": "定期定额投资，平滑成本、分散风险。适合波动较大的市场。关键：选好标的、坚持长期、不择时。指数基金定投是最简单的投资方式。",
            "category": "投资策略"
        },
        {
            "title": "安全边际",
            "content": "格雷厄姆提出：买入价格应低于内在价值，留出'安全边际'。用50美分买1美元的东西，即使判断有误也不易亏损。",
            "category": "投资理念"
        },
        {
            "title": "护城河",
            "content": "巴菲特概念：企业长期竞争优势。五种护城河：品牌、转换成本、网络效应、成本优势、专利。有护城河的公司更值得长期持有。",
            "category": "投资理念"
        },
        {
            "title": "PE分位数",
            "content": "当前PE在历史中的位置。分位数<30%表示相对低估，>70%表示相对高估。帮助判断当前估值在历史上的便宜程度。",
            "category": "估值指标"
        },
        {
            "title": "MACD指标",
            "content": "趋势跟踪指标，由DIF线、DEA线和柱状图组成。金叉（DIF上穿DEA）为买入信号，死叉为卖出信号。适合判断趋势转折。",
            "category": "技术分析"
        },
        {
            "title": "止损策略",
            "content": "预设最大亏损比例（如10%），触发即卖出。避免小亏变大亏。关键：设置合理、执行坚决。高手也设止损，没有人能100%正确。",
            "category": "风险管理"
        },
        {
            "title": "分散投资",
            "content": "不要把鸡蛋放在一个篮子里。跨资产（股债商）、跨行业、跨市场分散，降低单一风险。但过度分散会拉低收益，适度即可。",
            "category": "风险管理"
        }
    ]

    # 每日术语库
    DAILY_TERMS = [
        {"term": "多头", "desc": "看涨市场，预期价格上涨的投资者"},
        {"term": "空头", "desc": "看跌市场，预期价格下跌的投资者"},
        {"term": "牛市", "desc": "持续上涨的市场行情"},
        {"term": "熊市", "desc": "持续下跌的市场行情"},
        {"term": "震荡市", "desc": "价格在一定区间内反复波动"},
        {"term": "回调", "desc": "上涨趋势中的暂时性下跌"},
        {"term": "反弹", "desc": "下跌趋势中的暂时性上涨"},
        {"term": "破位", "desc": "价格跌破重要支撑位"},
        {"term": "放量", "desc": "成交量明显放大"},
        {"term": "缩量", "desc": "成交量明显萎缩"},
        {"term": "换手率", "desc": "成交量/流通股本，反映交易活跃度"},
        {"term": "市净率", "desc": "PB，股价/每股净资产"},
        {"term": "市盈率", "desc": "PE，股价/每股收益"},
        {"term": "股息率", "desc": "每股分红/股价，现金回报率"},
        {"term": "派息率", "desc": "分红/净利润，分红占利润比例"},
        {"term": "除权除息", "desc": "分红送股后股价调整"},
        {"term": "解禁", "desc": "限售股可以流通交易"},
        {"term": "北向资金", "desc": "通过港股通流入A股的外资"},
        {"term": "南向资金", "desc": "通过港股通流入港股的内资"},
        {"term": "IPO", "desc": "首次公开募股，公司上市"},
        {"term": "打新", "desc": "申购新发行的股票"},
        {"term": "中签", "desc": "打新成功获得配售"},
        {"term": "涨停板", "desc": "股价涨幅达到上限（A股通常10%）"},
        {"term": "跌停板", "desc": "股价跌幅达到下限"},
        {"term": "T+1", "desc": "当日买入次日才能卖出"},
        {"term": "融券", "desc": "借股票卖出，看空操作"},
        {"term": "融资", "desc": "借钱买股票，加杠杆"},
        {"term": "仓位", "desc": "投入资金占总资金比例"},
        {"term": "满仓", "desc": "全部资金都买了股票"},
        {"term": "空仓", "desc": "不持有任何股票"},
    ]

    def get_morning_report(self, watchlist: List[Dict] = None) -> Dict[str, Any]:
        """
        生成每日财经早报

        Args:
            watchlist: 自选股列表

        Returns:
            早报内容字典
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]

        # 获取市场概况
        market_summary = self._get_market_summary()

        # 获取热点新闻
        hot_news = self._get_hot_news_brief()

        # 自选股动态
        watchlist_alerts = self._get_watchlist_alerts(watchlist) if watchlist else []

        # 知识小贴士（随机选择）
        knowledge_tip = random.choice(self.KNOWLEDGE_TIPS)

        # 每日术语（基于日期选择，每天固定一个）
        term_index = today.day % len(self.DAILY_TERMS)
        daily_term = self.DAILY_TERMS[term_index]

        return {
            "date": date_str,
            "weekday": weekday,
            "market_summary": market_summary,
            "hot_news": hot_news,
            "watchlist_alerts": watchlist_alerts,
            "knowledge_tip": knowledge_tip,
            "daily_term": daily_term,
            "generated_at": today.strftime("%H:%M")
        }

    def _get_market_summary(self) -> Dict[str, Any]:
        """获取市场概况"""
        try:
            # 获取上证指数和深证成指
            url = "https://qt.gtimg.cn/q=sh000001,sz399001"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=5, proxies={"http": None, "https": None})

            if resp.status_code == 200 and resp.text:
                lines = resp.text.strip().split('\n')
                summary = {"indices": []}

                for line in lines:
                    if '~' in line:
                        parts = line.split('=')[1].strip('"').split('~')
                        if len(parts) > 30:
                            name = parts[1]
                            price = float(parts[3])
                            change = float(parts[31])
                            change_pct = float(parts[32])

                            summary["indices"].append({
                                "name": name,
                                "price": round(price, 2),
                                "change": round(change, 2),
                                "change_pct": round(change_pct, 2),
                                "direction": "up" if change >= 0 else "down"
                            })

                if summary["indices"]:
                    # 生成市场评述
                    sh = summary["indices"][0]
                    if sh["change_pct"] > 1:
                        summary["comment"] = f"今日A股市场表现强劲，{sh['name']}大涨{abs(sh['change_pct'])}%，市场情绪乐观。"
                    elif sh["change_pct"] > 0:
                        summary["comment"] = f"今日A股小幅上涨，{sh['name']}涨{abs(sh['change_pct'])}%，市场震荡偏强。"
                    elif sh["change_pct"] > -1:
                        summary["comment"] = f"今日A股小幅调整，{sh['name']}跌{abs(sh['change_pct'])}%，市场震荡整理。"
                    else:
                        summary["comment"] = f"今日A股表现疲弱，{sh['name']}跌{abs(sh['change_pct'])}%，注意风险控制。"

                    return summary
        except Exception as e:
            print(f"获取市场概况失败: {e}")

        # 返回默认值
        return {
            "indices": [
                {"name": "上证指数", "price": "--", "change": "--", "change_pct": "--", "direction": "neutral"}
            ],
            "comment": "市场数据获取中..."
        }

    def _get_hot_news_brief(self) -> List[Dict]:
        """获取热点新闻摘要"""
        try:
            # 复用新闻服务
            from services.news_service import news_service
            news_list = news_service.get_hot_news(5)

            result = []
            for news in news_list[:5]:
                result.append({
                    "title": news.get("title", ""),
                    "source": news.get("source", ""),
                    "impact": news.get("impact", {}).get("name", "综合") if isinstance(news.get("impact"), dict) else "综合",
                    "sentiment": news.get("sentiment_label", "中性")
                })
            return result
        except Exception as e:
            print(f"获取热点新闻失败: {e}")
            return []

    def _get_watchlist_alerts(self, watchlist: List[Dict]) -> List[Dict]:
        """获取自选股动态提醒"""
        alerts = []

        if not watchlist:
            return alerts

        for stock in watchlist[:5]:  # 最多5只
            code = stock.get("stock_code", "")
            name = stock.get("stock_name", "")
            change = stock.get("price_change")

            if change is not None:
                if change > 3:
                    alerts.append({
                        "code": code,
                        "name": name,
                        "type": "大涨",
                        "message": f"涨幅{change}%，表现强劲",
                        "level": "info"
                    })
                elif change < -3:
                    alerts.append({
                        "code": code,
                        "name": name,
                        "type": "下跌",
                        "message": f"跌幅{abs(change)}%，注意风险",
                        "level": "warning"
                    })

        return alerts


# 全局实例
report_service = ReportService()

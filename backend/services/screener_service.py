# -*- coding: utf-8 -*-
"""
投资策略筛选服务
"""

from typing import Dict, List, Any
from database import Database
from services.stock_service import stock_service
from services.analyzer import dividend_db


class ScreenerService:
    """股票筛选服务"""

    # 策略定义
    STRATEGIES = {
        "high_dividend": {
            "name": "高股息策略",
            "description": "适合追求稳定分红的投资者",
            "conditions": [
                {"name": "股息率≥4%", "key": "dividend_yield", "op": ">=", "value": 4, "weight": 40},
                {"name": "派息率30%-70%", "key": "payout_ratio", "op": "range", "min": 30, "max": 70, "weight": 30},
                {"name": "负债率<60%", "key": "debt_ratio", "op": "<", "value": 60, "weight": 30}
            ]
        },
        "growth": {
            "name": "成长股策略",
            "description": "适合进取型投资者，追求高增长",
            "conditions": [
                {"name": "ROE>15%", "key": "roe", "op": ">", "value": 15, "weight": 40},
                {"name": "营收增长>0", "key": "revenue_growth", "op": ">", "value": 0, "weight": 30},
                {"name": "利润增长>0", "key": "profit_growth", "op": ">", "value": 0, "weight": 30}
            ]
        },
        "value": {
            "name": "价值投资策略",
            "description": "适合价值投资者，寻找被低估的股票",
            "conditions": [
                {"name": "PE分位数<30%", "key": "pe_percentile", "op": "<", "value": 30, "weight": 35},
                {"name": "PB分位数<30%", "key": "pb_percentile", "op": "<", "value": 30, "weight": 35},
                {"name": "股息率>2%", "key": "dividend_yield", "op": ">", "value": 2, "weight": 30}
            ]
        },
        "low_risk": {
            "name": "低风险策略",
            "description": "适合保守型投资者，注重安全性",
            "conditions": [
                {"name": "负债率<40%", "key": "debt_ratio", "op": "<", "value": 40, "weight": 35},
                {"name": "现金流健康", "key": "cashflow_positive", "op": "==", "value": True, "weight": 35},
                {"name": "风险排查通过", "key": "risk_pass", "op": "==", "value": True, "weight": 30}
            ]
        }
    }

    def screen_stocks(self, strategy: str) -> Dict[str, Any]:
        """
        根据策略筛选股票

        Args:
            strategy: 策略名称 (high_dividend, growth, value, low_risk)

        Returns:
            筛选结果
        """
        if strategy not in self.STRATEGIES:
            return {
                "success": False,
                "message": f"未知策略: {strategy}",
                "available_strategies": list(self.STRATEGIES.keys())
            }

        strategy_info = self.STRATEGIES[strategy]

        # 获取自选股列表
        watchlist = Database.get_watchlist()

        if not watchlist:
            return {
                "success": True,
                "strategy_name": strategy_info["name"],
                "description": strategy_info["description"],
                "stocks": [],
                "total": 0,
                "message": "自选股列表为空，请先添加股票到自选股"
            }

        results = []

        for item in watchlist:
            stock_code = item["stock_code"]
            stock_name = item.get("stock_name", stock_code)

            try:
                # 获取股票指标
                metrics = self._get_stock_metrics(stock_code)

                # 计算匹配得分
                match_result = self._calculate_match_score(metrics, strategy_info["conditions"])

                if match_result["matched"]:
                    results.append({
                        "code": stock_code,
                        "name": stock_name,
                        "match_score": match_result["score"],
                        "matched_conditions": match_result["matched_conditions"],
                        "metrics": metrics
                    })
            except Exception as e:
                print(f"筛选{stock_code}失败: {e}")

        # 按匹配得分排序
        results.sort(key=lambda x: x["match_score"], reverse=True)

        return {
            "success": True,
            "strategy_name": strategy_info["name"],
            "description": strategy_info["description"],
            "conditions": [c["name"] for c in strategy_info["conditions"]],
            "stocks": results,
            "total": len(results)
        }

    def _get_stock_metrics(self, stock_code: str) -> Dict:
        """获取股票筛选指标"""
        metrics = {
            "dividend_yield": 0,
            "payout_ratio": 0,
            "roe": 0,
            "debt_ratio": 0,
            "pe": 0,
            "pb": 0,
            "pe_percentile": 50,
            "pb_percentile": 50,
            "revenue_growth": 0,
            "profit_growth": 0,
            "cashflow_positive": False,
            "risk_pass": False
        }

        # 获取实时价格
        try:
            trade_data = stock_service.get_trade_data(stock_code)
            current_price = trade_data.get("f43", 0)
            metrics["pe"] = trade_data.get("f162", 0) or 0
            metrics["pb"] = trade_data.get("f167", 0) or 0
        except:
            current_price = 0

        # 获取股息率
        stock_div = dividend_db.get(stock_code, {"cash": 0})
        cash_div = stock_div.get("cash", 0)
        if current_price > 0 and cash_div > 0:
            metrics["dividend_yield"] = round(cash_div / current_price * 100, 2)

        # 获取其他指标（从analyzer的模拟数据）
        from services.analyzer import FinancialAnalyzer
        analyzer = FinancialAnalyzer()
        analyzer._stock_code = stock_code

        # 派息率
        payout = analyzer._analyze_payout_ratio_simplified(stock_code)
        metrics["payout_ratio"] = payout.get("payout_ratio", 0)

        # ROE和增长率
        profit = analyzer._analyze_profit_quality_simplified(stock_code)
        roe_history = profit.get("roe_history", [])
        if roe_history:
            metrics["roe"] = roe_history[0].get("roe", 0)
        metrics["revenue_growth"] = profit.get("revenue_cagr", 0) or 0
        metrics["profit_growth"] = profit.get("profit_cagr", 0) or 0

        # 负债率
        debt = analyzer._analyze_debt_ratio_simplified(stock_code)
        metrics["debt_ratio"] = debt.get("debt_ratio", 0)

        # 现金流
        cashflow = analyzer._analyze_cash_flow_simplified(stock_code)
        metrics["cashflow_positive"] = cashflow.get("all_positive", False)

        # 风险排查
        risk = analyzer._analyze_risk(stock_code)
        metrics["risk_pass"] = risk.get("all_pass", False)

        # 估值分位数（从分析结果获取）
        try:
            valuation = analyzer._analyze_valuation({}, [], trade_data, None, None, "")
            metrics["pe_percentile"] = valuation.get("pe_percentile", 50) or 50
            metrics["pb_percentile"] = valuation.get("pb_percentile", 50) or 50
        except:
            pass

        return metrics

    def _calculate_match_score(self, metrics: Dict, conditions: List[Dict]) -> Dict:
        """计算匹配得分"""
        total_score = 0
        matched_conditions = []

        for cond in conditions:
            key = cond["key"]
            op = cond["op"]
            weight = cond.get("weight", 20)

            value = metrics.get(key)

            if value is None:
                continue

            matched = False

            if op == ">=" and value >= cond["value"]:
                matched = True
            elif op == ">" and value > cond["value"]:
                matched = True
            elif op == "<=" and value <= cond["value"]:
                matched = True
            elif op == "<" and value < cond["value"]:
                matched = True
            elif op == "==" and value == cond["value"]:
                matched = True
            elif op == "range" and cond.get("min") <= value <= cond.get("max"):
                matched = True

            if matched:
                total_score += weight
                matched_conditions.append(cond["name"])

        # 需要至少满足一半的条件才算匹配
        threshold = sum(c.get("weight", 20) for c in conditions) / 2

        return {
            "score": total_score,
            "matched": total_score >= threshold,
            "matched_conditions": matched_conditions
        }

    def get_available_strategies(self) -> List[Dict]:
        """获取可用策略列表"""
        return [
            {
                "id": key,
                "name": info["name"],
                "description": info["description"],
                "conditions": [c["name"] for c in info["conditions"]]
            }
            for key, info in self.STRATEGIES.items()
        ]


# 全局实例
screener_service = ScreenerService()

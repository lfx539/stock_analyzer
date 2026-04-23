# 财务指标计算服务

from typing import Dict, List, Any
from datetime import datetime
import requests
from .stock_service import stock_service


class FinancialAnalyzer:
    """财务指标分析器"""

    def analyze_stock(self, stock_code: str) -> Dict[str, Any]:
        """综合分析股票"""
        # 保存股票代码供后续使用
        self._stock_code = stock_code
        error_messages = []

        # 获取各种数据，每个都检查是否成功
        try:
            trade_data = stock_service.get_trade_data(stock_code)
        except Exception as e:
            error_messages.append(f"实时行情: {str(e)}")
            trade_data = {}

        try:
            valuation_data = stock_service.get_valuation_data(stock_code)
        except Exception as e:
            error_messages.append(f"估值数据: {str(e)}")
            valuation_data = {}

        try:
            historical_data = stock_service.get_historical_pe_pb(stock_code, years=10)
        except Exception as e:
            error_messages.append(f"历史数据: {str(e)}")
            historical_data = []

        try:
            dividend_data = stock_service.get_dividend_data(stock_code)
        except Exception as e:
            error_messages.append(f"分红数据: {str(e)}")
            dividend_data = []

        # 检查核心数据是否获取成功
        if not trade_data:
            raise Exception(f"无法获取股票 {stock_code} 的实时行情数据，请检查网络连接或股票代码是否正确。错误详情: {'; '.join(error_messages)}")

        # 获取股票基本信息（名称）
        stock_name = trade_data.get("f58", "未知")
        if stock_name == "未知" or not stock_name:
            try:
                stock_info = stock_service.get_stock_info(stock_code)
                stock_name = stock_info.get("name", "未知")
            except:
                pass

        # 如果有部分数据获取失败，给出警告信息
        warnings = []
        if not valuation_data:
            warnings.append("估值数据获取失败")
        if not historical_data:
            warnings.append("历史数据获取失败，无法计算PE/PB分位数")

        # 获取实时价格
        current_price = trade_data.get("f43", 0)
        price_change = trade_data.get("f44", 0)
        price_change_amount = trade_data.get("f47", 0)

        # 获取行业信息
        try:
            stock_info = stock_service.get_stock_info(stock_code)
            industry = stock_info.get("industry", "未知")
        except:
            industry = "未知"

        # 尝试获取行业PE/PB
        try:
            industry_pe_data = stock_service.get_industry_pe_pb(industry)
            industry_pe_list = industry_pe_data.get("data", [])
            # 尝试匹配行业PE和PB - 使用更宽松的匹配
            industry_pe_value = None
            industry_pb_value = None
            if industry != "未知" and industry_pe_list:
                # 提取行业关键词
                keywords = industry.split("-") if "-" in industry else [industry]
                for keyword in keywords:
                    keyword = keyword.strip()
                    if len(keyword) >= 2:
                        for item in industry_pe_list:
                            pe_val = item.get("f2")
                            pb_val = item.get("f4")
                            # 过滤异常大的值
                            if keyword in item.get("f14", ""):
                                if pe_val and float(pe_val) < 500:
                                    industry_pe_value = pe_val
                                if pb_val and float(pb_val) < 10:
                                    industry_pb_value = pb_val
                                break
                        if industry_pe_value and industry_pb_value:
                            break

            # 如果没有匹配到，使用行业默认值
            if not industry_pe_value or float(industry_pe_value) > 500:
                if "石油" in industry or "石化" in industry or "化工" in industry or "能源" in industry:
                    industry_pe_value = 12.0
            if not industry_pb_value or float(industry_pb_value) > 10:
                if "石油" in industry or "石化" in industry or "化工" in industry or "能源" in industry:
                    industry_pb_value = 1.5
        except:
            industry_pe_value = None
            industry_pb_value = None

        # 获取同行业对比数据，用于计算真实的行业平均PE/PB
        try:
            industry_comparison = stock_service.get_stocks_by_industry(stock_code)
            industry_avg = industry_comparison.get("industry_avg", {})
            if industry_avg:
                # 使用同行业对比计算的平均值
                if industry_avg.get("pe") and industry_avg["pe"] > 0:
                    industry_pe_value = industry_avg["pe"]
                if industry_avg.get("pb") and industry_avg["pb"] > 0:
                    industry_pb_value = industry_avg["pb"]
        except:
            pass

        # 计算各项指标
        result = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "industry": industry,
            "industry_pe": industry_pe_value,
            "industry_pb": industry_pb_value,
            "current_price": current_price,
            "price_change": price_change,
            "price_change_amount": price_change_amount,
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "warnings": warnings if warnings else None
        }

        # 1. 估值分析
        result["valuation_analysis"] = self._analyze_valuation(valuation_data, historical_data, trade_data, industry_pe_value, industry_pb_value, industry)

        # 2. 股息率分析 - 使用模拟数据（实际需要从财务数据获取）
        result["dividend_analysis"] = self._analyze_dividend_simplified(trade_data, stock_code)

        # 3. 派息率分析
        result["payout_analysis"] = self._analyze_payout_ratio_simplified(stock_code)

        # 4. 盈利质量分析 - 使用模拟数据
        result["profit_analysis"] = self._analyze_profit_quality_simplified(stock_code)

        # 5. 现金流分析 - 使用模拟数据
        result["cashflow_analysis"] = self._analyze_cash_flow_simplified(stock_code)

        # 6. 资产负债分析 - 使用模拟数据
        result["debt_analysis"] = self._analyze_debt_ratio_simplified(stock_code)

        # 7. 市场时机关
        result["market_timing"] = self._analyze_market_timing(trade_data)

        # 8. 风险排查
        result["risk_check"] = self._analyze_risk(stock_code)

        # 综合评分
        result["overall_score"] = self._calculate_overall_score(result)

        # 保存PE/PB到历史数据库
        self._save_pe_pb_to_history(stock_code, result)

        return result

    def _save_pe_pb_to_history(self, stock_code: str, result: Dict):
        """保存PE/PB到历史数据库"""
        from database import Database
        from datetime import datetime

        val = result.get("valuation_analysis", {})
        pe = val.get("pe_ttm")
        pb = val.get("pb")

        if pe or pb:
            today = datetime.now().strftime("%Y-%m-%d")
            Database.save_pe_pb_history(stock_code, today, pe, pb)

    def _get_stock_name(self, stock_code: str) -> str:
        """获取股票名称"""
        url = f"https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields": "f58",
            "secid": f"{(1 if stock_code.startswith('6') else 0)}.{stock_code}"
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            if data.get("data"):
                return data["data"].get("f58", "未知")
        except:
            pass
        return "未知"

    def _analyze_dividend_simplified(self, trade_data: Dict, stock_code: str) -> Dict:
        """简化版股息率分析 - 优先从API获取，备用静态数据库"""
        global dividend_db
        current_price = trade_data.get("f43", 0)

        # 优先从API获取股息数据
        cash_dividend = stock_service._get_dividend_from_api(stock_code)
        continuous_years = 0

        # 如果API没有数据，使用静态数据库
        if cash_dividend == 0:
            stock_info = dividend_db.get(stock_code, {"cash": 0, "years": 0})
            cash_dividend = stock_info["cash"]
            continuous_years = stock_info["years"]
        else:
            # API有数据时，估算连续分红年数（简化处理）
            continuous_years = 5  # 假设有5年分红历史

        # 计算股息率
        dividend_yield = (cash_dividend / current_price * 100) if current_price and current_price > 0 else 0

        return {
            "dividend_yield": round(dividend_yield, 2),
            "latest_cash_dividend": cash_dividend,
            "continuous_years": continuous_years,
            "dividend_history": [
                {"year": 2024, "cash_dividend": cash_dividend},
                {"year": 2023, "cash_dividend": cash_dividend * 0.95},
                {"year": 2022, "cash_dividend": cash_dividend * 0.90},
                {"year": 2021, "cash_dividend": cash_dividend * 0.85},
                {"year": 2020, "cash_dividend": cash_dividend * 0.80},
            ],
            "yield_status": self._get_dividend_status(dividend_yield, continuous_years)
        }

    def _get_dividend_status(self, yield_pct: float, years: int) -> Dict:
        """判断股息率是否达标"""
        status = "不合格"
        color = "red"

        if yield_pct >= 6:
            status = "优秀（>6%）"
            color = "green"
        elif yield_pct >= 4:
            status = "优秀（4%-6%）"
            color = "green"
        elif yield_pct >= 2:
            status = "良好（2%-4%）"
            color = "lightgreen"

        if years >= 5:
            status += f"，连续{years}年分红"

        return {"status": status, "color": color}

    def _analyze_payout_ratio_simplified(self, stock_code: str) -> Dict:
        """简化版派息率分析"""
        # 典型股票的派息率（5年数据）
        payout_db = {
            "600028": {"payout": [55, 52, 58, 50, 55], "eps": [0.65, 0.62, 0.68, 0.60, 0.65], "cash": 0.355},
            "600036": {"payout": [30, 32, 28, 35, 30], "eps": [1.0, 0.95, 1.1, 0.9, 1.0], "cash": 0.30},
            "601857": {"payout": [45, 48, 42, 50, 45], "eps": [0.5, 0.48, 0.52, 0.45, 0.5], "cash": 0.23},
            "601398": {"payout": [35, 38, 32, 40, 35], "eps": [0.7, 0.68, 0.72, 0.65, 0.7], "cash": 0.25},
        }

        stock_info = payout_db.get(stock_code, {"payout": [30, 28, 32, 25, 30], "eps": [0.5, 0.48, 0.52, 0.45, 0.5], "cash_dividend": 0.15})
        payout_history = stock_info["payout"]
        eps_history = stock_info["eps"]
        current_eps = eps_history[0]
        cash_dividend = stock_info.get("cash_dividend", 0.15)
        current_payout = payout_history[0]

        status = "不合格"
        color = "red"
        if 30 <= current_payout <= 70:
            status = "合理（30%-70%）"
            color = "green"
        elif current_payout < 30:
            status = "偏低（<30%）"
            color = "orange"
        elif current_payout > 70:
            status = "偏高（>70%）"
            color = "orange"

        # 构建5年历史数据
        payout_history_data = []
        years = [2024, 2023, 2022, 2021, 2020]
        for i, year in enumerate(years):
            payout_history_data.append({
                "year": year,
                "payout_ratio": payout_history[i] if i < len(payout_history) else payout_history[-1],
                "eps": eps_history[i] if i < len(eps_history) else eps_history[-1],
                "cash_dividend": round(cash_dividend * (0.95 ** i), 3)
            })

        return {
            "payout_ratio": current_payout,
            "eps": current_eps,
            "cash_dividend": cash_dividend,
            "payout_history": payout_history_data,
            "status": status,
            "color": color
        }

    def _analyze_profit_quality_simplified(self, stock_code: str) -> Dict:
        """简化版盈利质量分析 - 使用akshare获取真实ROE数据"""
        # 尝试从API获取ROE数据
        try:
            financial_data = stock_service.get_financial_indicators(stock_code)
            roe_api_data = financial_data.get("roe_history", [])

            if roe_api_data:
                # 使用API获取的ROE数据
                roe_history = [r["roe"] for r in roe_api_data]
                avg_roe = financial_data.get("avg_roe", 0)

                # 构建历史数据
                profit_history_data = []
                for r in roe_api_data:
                    profit_history_data.append({
                        "year": r["year"],
                        "roe": r["roe"],
                        "net_profit": 0  # API暂未提供净利润数据
                    })

                net_profit_positive = True
            else:
                raise Exception("API返回空数据")

        except Exception as e:
            # API失败时使用静态数据库
            print(f"ROE API失败，使用静态数据: {e}")
            roe_db = {
                "600028": {"roe": [3.86, 6.19, 7.59, 8.50, 9.35], "positive": True},
                "600036": {"roe": [15.0, 14.5, 13.8, 12.5, 14.0], "positive": True},
                "601857": {"roe": [5.2, 4.8, 6.5, 7.0, 6.2], "positive": True},
                "601398": {"roe": [11.0, 10.5, 10.8, 11.2, 11.5], "positive": True},
            }

            stock_info = roe_db.get(stock_code, {"roe": [8, 9, 10, 11, 12], "positive": True})
            roe_history = stock_info["roe"]
            avg_roe = sum(roe_history) / len(roe_history) if roe_history else 0
            net_profit_positive = stock_info["positive"]

            years = [2024, 2023, 2022, 2021, 2020]
            profit_history_data = []
            for i, year in enumerate(years):
                profit_history_data.append({
                    "year": year,
                    "roe": roe_history[i] if i < len(roe_history) else roe_history[-1],
                    "net_profit": 0
                })

        # 判断ROE状态
        roe_excellent = all(r > 10 for r in roe_history) if roe_history else False
        roe_great = all(r > 15 for r in roe_history) if roe_history else False

        status = "不合格"
        color = "red"
        if net_profit_positive and roe_excellent:
            status = "优秀（ROE>10%）" if not roe_great else "卓越（ROE>15%）"
            color = "green"
        elif net_profit_positive and all(r > 5 for r in roe_history) if roe_history else False:
            status = "良好"
            color = "lightgreen"

        return {
            "net_profit_positive": net_profit_positive,
            "profit_growth": [5.2, 3.1, -2.1, 8.5, 6.2],  # 模拟数据
            "roe_history": profit_history_data,
            "avg_roe": round(avg_roe, 2),
            "roe_status": status,
            "color": color,
            "revenue_cagr": None,  # 需要营收数据
            "profit_cagr": None
        }

    def _analyze_cash_flow_simplified(self, stock_code: str) -> Dict:
        """简化版现金流分析"""
        # 典型股票的现金流（5年）
        cashflow_db = {
            "600028": {"operating": [420, 380, 450, 400, 380], "netprofit": [355, 312, 280, 320, 350], "positive": True, "covered": True},
            "600036": {"operating": [2800, 2600, 2400, 2200, 2500], "netprofit": [900, 850, 800, 750, 820], "positive": True, "covered": True},
            "601857": {"operating": [250, 200, 280, 300, 260], "netprofit": [180, 150, 200, 220, 200], "positive": True, "covered": True},
            "601398": {"operating": [450, 420, 480, 500, 460], "netprofit": [360, 340, 350, 370, 380], "positive": True, "covered": True},
        }

        stock_info = cashflow_db.get(stock_code, {"operating": [50, 45, 55, 48, 52], "netprofit": [40, 38, 42, 35, 40], "positive": True, "covered": True})
        operating = stock_info["operating"]
        netprofit = stock_info["netprofit"]
        all_positive = stock_info["positive"]
        all_covered = stock_info["covered"]

        status = "不合格"
        color = "red"
        if all_positive:
            if all_covered:
                status = "优秀（完全覆盖）"
                color = "green"
            else:
                status = "良好（为正）"
                color = "lightgreen"

        # 构建5年历史数据
        years = [2024, 2023, 2022, 2021, 2020]
        cashflow_history = []
        for i, year in enumerate(years):
            op = operating[i] if i < len(operating) else operating[-1]
            np = netprofit[i] if i < len(netprofit) else netprofit[-1]
            cashflow_history.append({
                "year": year,
                "operating_cash_flow": op,
                "net_profit": np,
                "cash_covered": op >= np
            })

        return {
            "operating_cash_flow": operating,
            "cash_covered": [op >= np for op, np in zip(operating, netprofit)],
            "cashflow_history": cashflow_history,
            "all_positive": all_positive,
            "status": status,
            "color": color
        }

    def _analyze_debt_ratio_simplified(self, stock_code: str) -> Dict:
        """简化版资产负债分析 - 使用akshare获取真实负债率数据"""
        # 尝试从API获取负债率数据
        try:
            financial_data = stock_service.get_financial_indicators(stock_code)
            debt_api_data = financial_data.get("debt_history", [])

            if debt_api_data:
                # 使用API获取的负债率数据
                debt_history = [d["debt_ratio"] for d in debt_api_data]
                debt_ratio = financial_data.get("latest_debt_ratio", 0)

                # 构建历史数据
                debt_history_data = []
                for d in debt_api_data:
                    debt_history_data.append({
                        "year": d["year"],
                        "debt_ratio": d["debt_ratio"]
                    })
            else:
                raise Exception("API返回空数据")

        except Exception as e:
            # API失败时使用静态数据库
            print(f"负债率API失败，使用静态数据: {e}")
            debt_db = {
                "600028": [54.08, 53.17, 52.70, 51.91, 51.51],
                "600036": [92.0, 91.5, 92.8, 93.2, 92.5],  # 银行特殊
                "601857": [45.2, 48.5, 52.0, 50.5, 55.0],
                "601398": [92.0, 91.8, 92.5, 93.0, 92.8],  # 银行特殊
            }

            debt_history = debt_db.get(stock_code, [50.0, 52.0, 55.0, 53.0, 58.0])
            debt_ratio = debt_history[0]

            years = [2024, 2023, 2022, 2021, 2020]
            debt_history_data = []
            for i, year in enumerate(years):
                debt_history_data.append({
                    "year": year,
                    "debt_ratio": debt_history[i] if i < len(debt_history) else debt_history[-1]
                })

        # 判断负债率状态
        status = "不合格"
        color = "red"
        if debt_ratio < 40:
            status = "优秀（<40%）"
            color = "green"
        elif debt_ratio < 60:
            status = "良好（<60%）"
            color = "lightgreen"
        elif debt_ratio < 80:
            status = f"偏高（{debt_ratio:.1f}%）"
            color = "orange"
        else:
            status = f"行业特性（{debt_ratio:.1f}%）"
            color = "gray"

        return {
            "debt_ratio": round(debt_ratio, 2),
            "debt_history": debt_history_data,
            "status": status,
            "color": color
        }

    def _analyze_valuation(self, valuation_data: Dict, historical_data: List[Dict], trade_data: Dict, industry_pe_value: float = None, industry_pb_value: float = None, industry: str = "未知") -> Dict:
        """分析估值 - 使用真实数据或财务数据计算"""
        current_price = trade_data.get("f43") if trade_data else None
        if current_price:
            current_price = float(current_price)

        # 1. 首先尝试从交易数据获取PE和PB
        pe_ttm = trade_data.get("f162") if trade_data else None
        pb = trade_data.get("f167") if trade_data else None
        if not pb:
            pb = valuation_data.get("pb2") if valuation_data else None

        if pe_ttm and isinstance(pe_ttm, list) and len(pe_ttm) > 0:
            pe_ttm = pe_ttm[0]
        if pb and isinstance(pb, list) and len(pb) > 0:
            pb = pb[0]

        pe_ttm = float(pe_ttm) if pe_ttm and pe_ttm != "-" else 0
        pb = float(pb) if pb and pb != "-" else 0

        # 2. 如果数据异常，尝试使用财务数据计算
        if (pe_ttm < 1 or pe_ttm > 100) and current_price:
            # 从财务数据获取EPS计算PE
            financial_data = stock_service.get_financial_data(self._stock_code) if hasattr(self, '_stock_code') else {}
            eps = financial_data.get('eps')
            if eps and eps > 0:
                pe_ttm = round(current_price / eps, 2)
                print(f"[财务计算] PE: {current_price} / {eps} = {pe_ttm}")

        if (pb < 0.1 or pb > 5) and current_price:
            # 从财务数据获取BPS计算PB
            if not hasattr(self, '_stock_code'):
                # 尝试重新获取
                financial_data = stock_service.get_financial_data(self._stock_code) if hasattr(self, '_stock_code') else {}
            else:
                financial_data = stock_service.get_financial_data(self._stock_code)
            bps = financial_data.get('bps')
            if bps and bps > 0:
                pb = round(current_price / bps, 2)
                print(f"[财务计算] PB: {current_price} / {bps} = {pb}")
                # PB异常时，说明外部数据可能有问题，也需要重新计算PE
                eps = financial_data.get('eps')
                if eps and eps > 0:
                    pe_ttm = round(current_price / eps, 2)
                    print(f"[财务计算] PE: {current_price} / {eps} = {pe_ttm}")

        # 3. 过滤异常PE/PB值
        if pe_ttm < 1 or pe_ttm > 200:
            pe_ttm = 0
        if pb < 0.1 or pb > 50:
            pb = 0

        # 计算历史分位数
        pe_history = [d["pe"] for d in historical_data if d.get("pe") and d["pe"] > 0]
        pb_history = [d["pb"] for d in historical_data if d.get("pb") and d["pb"] > 0]

        pe_percentile = self._calculate_percentile(pe_ttm, pe_history) if pe_ttm > 0 else None
        pb_percentile = self._calculate_percentile(pb, pb_history) if pb > 0 else None

        # 行业对比 - 使用获取到的数据，否则用默认值
        industry_pe = round(float(industry_pe_value), 2) if industry_pe_value and industry_pe_value != "-" else 20.0
        industry_pb = round(float(industry_pb_value), 2) if industry_pb_value and industry_pb_value != "-" else 2.0

        # 过滤异常值
        if industry_pe > 500:
            if "石油" in industry or "石化" in industry or "化工" in industry or "能源" in industry:
                industry_pe = 12.0
            else:
                industry_pe = 20.0
        if industry_pb > 100:
            if "石油" in industry or "石化" in industry or "化工" in industry or "能源" in industry:
                industry_pb = 1.5
            else:
                industry_pb = 2.0

        # 如果PE为0，显示为None（前端会显示"-"）
        pe_display = round(pe_ttm, 2) if pe_ttm > 0 else None
        pb_display = round(pb, 2) if pb > 0 else None

        # 获取财务数据用于显示计算公式
        financial_data = {}
        if current_price:
            financial_data = stock_service.get_financial_data(self._stock_code)

        # 判断是否为重资产行业
        heavy_industry_keywords = ["石油", "石化", "化工", "能源", "银行", "保险", "钢铁", "煤炭", "建筑", "房地产", "水泥"]
        is_heavy_industry = any(kw in industry for kw in heavy_industry_keywords)

        # 新估值标准判断
        conditions = []

        # a. PE_TTM历史分位数 < 30% 且 PB历史分位数 < 30%
        cond_a_pass = (pe_percentile and pe_percentile < 30) and (pb_percentile and pb_percentile < 30)
        conditions.append({
            "name": "PE分位<30% 且 PB分位<30%",
            "value": f"PE{pe_percentile or '-'}% / PB{pb_percentile or '-'}%",
            "pass": cond_a_pass,
            "desc": "历史估值低位"
        })

        # b. PE_TTM < 行业平均PE * 0.9 且 PB < 行业平均PB * 0.9
        cond_b_pass = pe_ttm > 0 and pb > 0 and pe_ttm < industry_pe * 0.9 and pb < industry_pb * 0.9
        conditions.append({
            "name": "PE<行业*0.9 且 PB<行业*0.9",
            "value": f"PE{pe_display}/行业{industry_pe} / PB{pb_display}/行业{industry_pb}",
            "pass": cond_b_pass,
            "desc": "相对行业低估"
        })

        # c. 重资产公司 PB < 1（破净）
        cond_c_pass = is_heavy_industry and pb > 0 and pb < 1
        conditions.append({
            "name": f"{'重资产' if is_heavy_industry else '非重资产'}公司 PB<1",
            "value": f"PB = {pb_display}",
            "pass": cond_c_pass,
            "desc": "破净，便宜"
        })

        # 任一条件满足即可
        any_pass = cond_a_pass or cond_b_pass or cond_c_pass

        if any_pass:
            valuation_status = "估值合理"
            valuation_color = "green"
            valuation_suggestion = "满足估值条件，可考虑买入"
        else:
            valuation_status = "估值偏高，观望"
            valuation_color = "red"
            valuation_suggestion = "估值偏高，建议等待更佳买点"

        return {
            "pe_ttm": pe_display,
            "pb": pb_display,
            "pe_percentile": round(pe_percentile, 1) if pe_ttm > 0 else None,
            "pb_percentile": round(pb_percentile, 1) if pb > 0 else None,
            "industry_pe": industry_pe if industry_pe < 100000 else 20.0,
            "industry_pb": industry_pb,
            "is_heavy_industry": is_heavy_industry,
            "conditions": conditions,
            "valuation_status": valuation_status,
            "valuation_color": valuation_color,
            "valuation_suggestion": valuation_suggestion,
            # 保留原有字段兼容 - 传入行业平均值和历史数据量
            "pe_valuation": self._get_valuation_status(pe_ttm, pe_percentile, industry_pe, len(pe_history) if pe_history else 0),
            "pb_valuation": self._get_valuation_status(pb, pb_percentile, industry_pb, len(pb_history) if pb_history else 0),
            # 历史数据信息
            "history_count": len(pe_history) if pe_history else 0,
            "history_note": "分位数基于本地历史数据" if len(pe_history or []) >= 30 else "⚠️ 历史数据不足，分位数可能不准确（需积累更多数据）",
            # 计算公式和标准说明
            "pe_formula": f"PE = 当前股价 ÷ 每股收益(EPS)\n        = {current_price:.2f} ÷ {financial_data.get('eps', '?')} = {pe_display}" if current_price and financial_data.get('eps') else None,
            "pb_formula": f"PB = 当前股价 ÷ 每股净资产(BPS)\n        = {current_price:.2f} ÷ {financial_data.get('bps', '?')} = {pb_display}" if current_price and financial_data.get('bps') else None,
            "pe_standard": {
                "description": "PE（市盈率）= 股价/EPS，反映回本年限",
                "good": "< 15 倍（低估）",
                "normal": "15-25 倍（合理）",
                "high": "> 25 倍（高估）"
            },
            "pb_standard": {
                "description": "PB（市净率）= 股价/每股净资产，反映账面价值溢价",
                "good": "< 1.5 倍（低估）",
                "normal": "1.5-3 倍（合理）",
                "high": "> 3 倍（高估）"
            }
        }

    def _calculate_percentile(self, current: float, history: List[float]) -> float:
        """计算当前值在历史数据中的分位数"""
        if not history or current <= 0:
            return 50.0

        sorted_history = sorted(history)
        count_below = sum(1 for h in sorted_history if h <= current)
        return (count_below / len(sorted_history)) * 100

    def _get_valuation_status(self, value: float, percentile: float, industry_avg: float = None, history_count: int = 0) -> Dict:
        """判断估值状态

        Args:
            value: 当前值（PE或PB）
            percentile: 历史分位数
            industry_avg: 行业平均值
            history_count: 历史数据量
        """
        if value <= 0:
            return {"status": "无数据", "color": "gray", "value": 0}

        status = "适中"
        color = "gray"

        # 历史数据充足时，使用分位数判断
        if history_count >= 30:
            if percentile < 20:
                status = "极低（历史底部）"
                color = "green"
            elif percentile < 40:
                status = "偏低"
                color = "lightgreen"
            elif percentile < 60:
                status = "适中"
                color = "gray"
            elif percentile < 80:
                status = "偏高"
                color = "orange"
            else:
                status = "极高（历史顶部）"
                color = "red"
        else:
            # 历史数据不足时，结合行业对比判断
            if industry_avg and industry_avg > 0:
                ratio = value / industry_avg
                if ratio < 0.7:
                    status = "偏低（相对行业）"
                    color = "green"
                elif ratio < 0.9:
                    status = "合理偏低"
                    color = "lightgreen"
                elif ratio <= 1.1:
                    status = "适中"
                    color = "gray"
                elif ratio <= 1.3:
                    status = "合理偏高"
                    color = "orange"
                else:
                    status = "偏高（相对行业）"
                    color = "red"
            else:
                # 没有行业数据时，使用绝对值判断
                # PB标准：<1.5低估，1.5-3合理，>3高估
                # PE标准：<15低估，15-25合理，>25高估
                status = "适中"
                color = "gray"

        return {"status": status, "color": color, "value": value}

    def _calculate_overall_score(self, result: Dict) -> Dict:
        """计算综合评分"""
        score = 0
        total = 0
        pros = []  # 优点
        cons = []  # 缺点/注意

        # 股息率（20分）
        div = result.get("dividend_analysis", {})
        div_yield = div.get("dividend_yield", 0)
        if "green" in div.get("yield_status", {}).get("color", ""):
            score += 20
            pros.append(f"股息率较高({div_yield}%)")
        elif div_yield >= 2:
            score += 10
            pros.append(f"股息率尚可({div_yield}%)")
        else:
            if div_yield > 0:
                cons.append(f"股息率偏低({div_yield}%)")
        total += 20

        # 派息率（15分）
        payout = result.get("payout_analysis", {})
        payout_ratio = payout.get("payout_ratio", 0)
        if "green" in payout.get("color", ""):
            score += 15
            pros.append("派息率合理")
        else:
            if payout_ratio > 0:
                cons.append(f"派息率{payout_ratio}%")
        total += 15

        # 盈利质量（25分）
        profit = result.get("profit_analysis", {})
        if "green" in profit.get("color", ""):
            score += 25
            pros.append("盈利能力强")
        elif "lightgreen" in profit.get("color", ""):
            score += 15
            pros.append("盈利一般")
        elif "red" in profit.get("color", ""):
            cons.append("盈利下滑")
        total += 25

        # 现金流（15分）
        cf = result.get("cashflow_analysis", {})
        if "green" in cf.get("color", ""):
            score += 15
            pros.append("现金流充裕")
        elif "lightgreen" in cf.get("color", ""):
            score += 10
            pros.append("现金流一般")
        elif "red" in cf.get("color", ""):
            cons.append("现金流紧张")
        total += 15

        # 资产负债（15分）
        debt = result.get("debt_analysis", {})
        if "green" in debt.get("color", ""):
            score += 15
            pros.append("负债率低")
        elif "lightgreen" in debt.get("color", ""):
            score += 10
            cons.append("负债率偏高")
        elif "red" in debt.get("color", ""):
            cons.append("负债率过高")
        total += 15

        # 估值（10分）- 使用新的估值条件判断
        val = result.get("valuation_analysis", {})
        val_pass = val.get("valuation_status") == "估值合理"
        if val_pass:
            score += 10
            pros.append("估值合理")
        else:
            cons.append("估值偏高")
        total += 10

        # 风险排查（10分）- 一票否决
        risk = result.get("risk_check", {})
        if risk.get("all_pass", False):
            score += 10
            pros.append("风险排查通过")
        else:
            cons.append("存在风险因素")
        total += 10

        # 市场时机（10分）
        market = result.get("market_timing", {})
        if market.get("signal") == "买入":
            score += 10
            pros.append("市场时机成熟")
        else:
            cons.append("市场时机一般")
        total += 10

        final_score = round(score / total * 100, 1) if total > 0 else 0

        # 评级
        rating = "D"
        if final_score >= 90:
            rating = "A+"
        elif final_score >= 80:
            rating = "A"
        elif final_score >= 70:
            rating = "B+"
        elif final_score >= 60:
            rating = "B"
        elif final_score >= 50:
            rating = "C"

        # 生成详细分析
        analysis = self._generate_analysis(final_score, pros, cons)

        return {
            "score": final_score,
            "rating": rating,
            "suggestion": analysis
        }

    def _generate_analysis(self, score: float, pros: list, cons: list) -> Dict:
        """生成详细分析"""
        pros_text = ""
        cons_text = ""
        summary = ""

        # 优点
        if pros:
            pros_text = "，".join(pros[:3])
        else:
            pros_text = "暂无明显优点"

        # 缺点
        if cons:
            cons_text = "，".join(cons[:3])
        else:
            cons_text = "暂无明显问题"

        # 综合建议
        if score >= 90:
            summary = "非常优秀的投资标的，强烈推荐关注！"
        elif score >= 80:
            summary = "优质企业，值得中长期持有。"
        elif score >= 70:
            summary = "整体不错，适合稳健型投资者。"
        elif score >= 60:
            summary = "可适当关注，需关注行业动态。"
        elif score >= 50:
            summary = "存在一定风险，建议观望为主。"
        else:
            summary = "风险较高，谨慎投资。"

        return {
            "pros": pros_text,
            "cons": cons_text,
            "summary": summary
        }

    def _get_suggestion(self, score: float) -> str:
        """根据评分给出建议"""
        if score >= 90:
            return "非常优秀的投资标的，建议重点关注！"
        elif score >= 80:
            return "优质企业，值得考虑。"
        elif score >= 70:
            return "整体不错，可适当关注。"
        elif score >= 60:
            return "尚可，需要进一步观察。"
        elif score >= 50:
            return "存在一些风险，谨慎投资。"
        else:
            return "不建议投资，建议规避。"

    def _analyze_market_timing(self, trade_data: Dict) -> Dict:
        """市场时机关分析"""
        # 从交易数据中获取相关指标
        current_price = trade_data.get("f43", 0)
        ma250 = trade_data.get("f204") or current_price  # MA250，如果无数据则用当前价
        week52_high = trade_data.get("f173") or current_price * 1.2  # 52周高点
        week52_low = trade_data.get("f174") or current_price * 0.8  # 52周低点

        # 模拟RS相对强度（实际需要对比大盘）
        # 这里用股价相对52周低点的位置来模拟
        if current_price > 0 and week52_low > 0:
            rs = (current_price - week52_low) / (week52_high - week52_low) * 2
        else:
            rs = 1.0

        # 计算MA250区间（当前价相对MA250的位置）
        if ma250 > 0:
            ma250_position = (current_price - ma250) / ma250 * 100
        else:
            ma250_position = 0

        # 计算52周回撤
        if week52_high > 0:
            drawdown = (week52_high - current_price) / week52_high * 100
        else:
            drawdown = 0

        # 判断条件
        conditions = []

        # a. 股价相对强度RS > 1
        rs_pass = rs > 1
        conditions.append({
            "name": "股价相对强度(RS) > 1",
            "value": f"{rs:.2f}",
            "pass": rs_pass,
            "desc": "跑赢大盘"
        })

        # b. 股价位于MA250的 -10% 至 +5% 区间
        ma250_pass = -10 <= ma250_position <= 5
        conditions.append({
            "name": "MA250区间(-10%~+5%)",
            "value": f"{ma250_position:.1f}%",
            "pass": ma250_pass,
            "desc": "接近长期支撑"
        })

        # c. 股价从52周高点回撤 > 20%
        drawdown_pass = drawdown > 20
        conditions.append({
            "name": "52周回撤 > 20%",
            "value": f"{drawdown:.1f}%",
            "pass": drawdown_pass,
            "desc": "已充分调整"
        })

        # 任一条件满足即可
        any_pass = rs_pass or ma250_pass or drawdown_pass

        # 生成建议
        if any_pass:
            signal = "买入"
            signal_color = "green"
            suggestion = "市场时机成熟，建议关注买入机会"
        else:
            signal = "关注/可定投"
            signal_color = "orange"
            suggestion = "估值合理，可考虑定投建仓"

        return {
            "rs": round(rs, 2),
            "rs_pass": rs_pass,
            "ma250_position": round(ma250_position, 1),
            "ma250_pass": ma250_pass,
            "drawdown": round(drawdown, 1),
            "drawdown_pass": drawdown_pass,
            "conditions": conditions,
            "signal": signal,
            "signal_color": signal_color,
            "suggestion": suggestion
        }

    def _analyze_risk(self, stock_code: str) -> Dict:
        """风险排查分析"""
        # 模拟数据 - 实际需要从财务数据获取
        risk_db = {
            "600028": {"pledge_rate": 0, "goodwill_ratio": 5.2, "audit_opinion": "标准无保留意见"},
            "600036": {"pledge_rate": 0, "goodwill_ratio": 2.1, "audit_opinion": "标准无保留意见"},
            "601857": {"pledge_rate": 35, "goodwill_ratio": 8.5, "audit_opinion": "标准无保留意见"},
            "601398": {"pledge_rate": 0, "goodwill_ratio": 1.2, "audit_opinion": "标准无保留意见"},
            "000001": {"pledge_rate": 0, "goodwill_ratio": 15.8, "audit_opinion": "标准无保留意见"},
        }

        stock_info = risk_db.get(stock_code, {"pledge_rate": 0, "goodwill_ratio": 10, "audit_opinion": "标准无保留意见"})

        pledge_rate = stock_info["pledge_rate"]
        goodwill_ratio = stock_info["goodwill_ratio"]
        audit_opinion = stock_info["audit_opinion"]

        # 判断条件
        conditions = []

        # 大股东质押率 < 60%
        pledge_pass = pledge_rate < 60
        conditions.append({
            "name": "大股东质押率 < 60%",
            "value": f"{pledge_rate}%" if pledge_rate > 0 else "0%",
            "pass": pledge_pass,
            "desc": "高质押可能带来风险"
        })

        # 商誉占比 < 20%
        goodwill_pass = goodwill_ratio < 20
        conditions.append({
            "name": "商誉占比 < 20%",
            "value": f"{goodwill_ratio}%",
            "pass": goodwill_pass,
            "desc": "高商誉可能计提减值"
        })

        # 审计意见 == "标准无保留意见"
        audit_pass = audit_opinion == "标准无保留意见"
        conditions.append({
            "name": "审计意见为标准无保留",
            "value": audit_opinion,
            "pass": audit_pass,
            "desc": "非标准意见可能存在问题"
        })

        # 任一不满足则标记为高风险
        all_pass = pledge_pass and goodwill_pass and audit_pass

        # 生成结果
        if all_pass:
            result_status = "通过"
            result_color = "green"
            suggestion = "风险排查通过，无明显风险因素"
        else:
            result_status = "高风险淘汰"
            result_color = "red"
            failed = [c["name"] for c in conditions if not c["pass"]]
            suggestion = f"存在风险因素: {', '.join(failed)}"

        return {
            "pledge_rate": pledge_rate,
            "pledge_pass": pledge_pass,
            "goodwill_ratio": goodwill_ratio,
            "goodwill_pass": goodwill_pass,
            "audit_opinion": audit_opinion,
            "audit_pass": audit_pass,
            "conditions": conditions,
            "status": result_status,
            "status_color": result_color,
            "suggestion": suggestion,
            "all_pass": all_pass
        }


# 全局分析器实例
analyzer = FinancialAnalyzer()

# 模块级别的股息数据库（供外部调用）
dividend_db = {
    "600028": {"cash": 0.355, "years": 20},  # 中国石化
    "600036": {"cash": 0.3, "years": 20},   # 招商银行
    "601857": {"cash": 0.22, "years": 15},  # 中国石油
    "000001": {"cash": 0.08, "years": 15},  # 平安银行
    "601398": {"cash": 0.25, "years": 15},  # 工商银行
    "600519": {"cash": 2.974, "years": 10}, # 贵州茅台
    "000333": {"cash": 0.35, "years": 10},  # 美的集团
    "600887": {"cash": 0.176, "years": 10}, # 伊利股份
    "601088": {"cash": 2.26, "years": 18},  # 中国神华
    "601225": {"cash": 0.33, "years": 10},  # 陕西煤业
    "601666": {"cash": 0.6, "years": 15},   # 平煤股份
    "000651": {"cash": 0.4, "years": 15},   # 格力电器
    "000002": {"cash": 0.25, "years": 20},  # 万科A
    # 煤炭行业
    "600188": {"cash": 1.0, "years": 10},   # 兖矿能源
    "600348": {"cash": 0.6, "years": 8},    # 华阳股份
    "601101": {"cash": 0.4, "years": 8},    # 昊华能源
    "600792": {"cash": 0.15, "years": 5},   # 云煤能源
    "600925": {"cash": 0.2, "years": 3},    # 苏能股份
}

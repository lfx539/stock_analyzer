# -*- coding: utf-8 -*-
"""
技术分析服务 - K线图表、技术指标、支撑压力位
"""

import requests
from typing import Dict, List, Any, Optional
import json


class ChartService:
    """技术分析服务"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/"
        }
        self.timeout = 15

    def get_kline_data(self, stock_code: str, period: str = 'daily', limit: int = 120) -> Dict[str, Any]:
        """
        获取K线数据

        Args:
            stock_code: 股票代码
            period: 周期 daily/weekly/monthly
            limit: 获取数量

        Returns:
            K线数据和技术指标
        """
        try:
            # 使用东方财富K线接口
            kline_data = self._fetch_kline_from_eastmoney(stock_code, period, limit)

            if not kline_data:
                return {"success": False, "message": "获取K线数据失败"}

            # 计算技术指标
            closes = [item['close'] for item in kline_data]
            highs = [item['high'] for item in kline_data]
            lows = [item['low'] for item in kline_data]
            volumes = [item.get('volume', 0) for item in kline_data]

            # MACD
            macd_data = self._calculate_macd(closes)

            # RSI
            rsi_data = self._calculate_rsi(closes, period=14)

            # KDJ
            kdj_data = self._calculate_kdj(highs, lows, closes, n=9)

            # 布林带
            boll_data = self._calculate_boll(closes, n=20)

            # 均线
            ma_data = {
                'ma5': self._calculate_ma(closes, 5),
                'ma10': self._calculate_ma(closes, 10),
                'ma20': self._calculate_ma(closes, 20),
                'ma60': self._calculate_ma(closes, 60)
            }

            # 支撑压力位
            support_resistance = self._find_support_resistance(kline_data)

            return {
                "success": True,
                "kline": kline_data,
                "indicators": {
                    "macd": macd_data,
                    "rsi": rsi_data,
                    "kdj": kdj_data,
                    "boll": boll_data,
                    "ma": ma_data
                },
                "support_resistance": support_resistance,
                "stock_code": stock_code,
                "period": period
            }

        except Exception as e:
            return {"success": False, "message": str(e)}

    def _fetch_kline_from_eastmoney(self, stock_code: str, period: str, limit: int) -> List[Dict]:
        """从东方财富获取K线数据"""
        # 市场代码
        if stock_code.startswith('6'):
            secid = f"1.{stock_code}"
        else:
            secid = f"0.{stock_code}"

        # 周期映射
        klt_map = {
            'daily': '101',      # 日K
            'weekly': '102',     # 周K
            'monthly': '103'     # 月K
        }
        klt = klt_map.get(period, '101')

        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": klt,
            "fqt": "1",  # 前复权
            "end": "20500101",
            "lmt": str(limit),
            "_": "1630000000000"
        }

        try:
            resp = requests.get(url, params=params, headers=self.headers,
                              timeout=self.timeout, proxies={"http": None, "https": None})

            if resp.status_code == 200:
                data = resp.json()
                if data.get("data") and data["data"].get("klines"):
                    klines = []
                    for line in data["data"]["klines"]:
                        parts = line.split(",")
                        if len(parts) >= 7:
                            klines.append({
                                "date": parts[0],
                                "open": float(parts[1]) if parts[1] else 0,
                                "close": float(parts[2]) if parts[2] else 0,
                                "high": float(parts[3]) if parts[3] else 0,
                                "low": float(parts[4]) if parts[4] else 0,
                                "volume": float(parts[5]) if parts[5] else 0,
                                "amount": float(parts[6]) if parts[6] else 0,
                                "change_pct": float(parts[7]) if len(parts) > 7 and parts[7] else 0,
                                "change": float(parts[8]) if len(parts) > 8 and parts[8] else 0,
                                "turnover": float(parts[9]) if len(parts) > 9 and parts[9] else 0
                            })
                    return klines
        except Exception as e:
            print(f"东方财富K线获取失败: {e}")

        return []

    # ========== 技术指标计算 ==========

    def _calculate_ma(self, data: List[float], period: int) -> List[Optional[float]]:
        """计算移动平均线"""
        result = [None] * len(data)
        for i in range(period - 1, len(data)):
            if data[i] is not None:
                result[i] = round(sum(data[i - period + 1:i + 1]) / period, 2)
        return result

    def _calculate_ema(self, data: List[float], period: int) -> List[Optional[float]]:
        """计算指数移动平均线"""
        result = [None] * len(data)
        if len(data) < period:
            return result

        # 第一个EMA值使用SMA
        sma = sum(data[:period]) / period
        result[period - 1] = round(sma, 4)

        # 后续使用EMA公式
        multiplier = 2 / (period + 1)
        for i in range(period, len(data)):
            if data[i] is not None and result[i - 1] is not None:
                ema = (data[i] - result[i - 1]) * multiplier + result[i - 1]
                result[i] = round(ema, 4)

        return result

    def _calculate_macd(self, closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """
        计算MACD指标
        MACD = DIF - DEA
        DIF = EMA(12) - EMA(26)
        DEA = EMA(DIF, 9)
        """
        if len(closes) < slow:
            return {"dif": [], "dea": [], "macd": []}

        ema_fast = self._calculate_ema(closes, fast)
        ema_slow = self._calculate_ema(closes, slow)

        # DIF
        dif = []
        for i in range(len(closes)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                dif.append(round(ema_fast[i] - ema_slow[i], 4))
            else:
                dif.append(None)

        # DEA
        dif_values = [d if d is not None else 0 for d in dif]
        dea = self._calculate_ema(dif_values, signal)

        # MACD柱
        macd = []
        for i in range(len(closes)):
            if dif[i] is not None and dea[i] is not None:
                macd.append(round((dif[i] - dea[i]) * 2, 4))
            else:
                macd.append(None)

        return {
            "dif": dif,
            "dea": dea,
            "macd": macd
        }

    def _calculate_rsi(self, closes: List[float], period: int = 14) -> List[Optional[float]]:
        """
        计算RSI指标
        RSI = 100 - 100 / (1 + RS)
        RS = 平均上涨幅度 / 平均下跌幅度
        """
        if len(closes) < period + 1:
            return [None] * len(closes)

        result = [None] * len(closes)

        # 计算价格变化
        changes = []
        for i in range(1, len(closes)):
            changes.append(closes[i] - closes[i - 1])

        # 计算RSI
        for i in range(period, len(closes)):
            period_changes = changes[i - period:i]
            gains = [c for c in period_changes if c > 0]
            losses = [-c for c in period_changes if c < 0]

            avg_gain = sum(gains) / period if gains else 0
            avg_loss = sum(losses) / period if losses else 0

            if avg_loss == 0:
                result[i] = 100
            else:
                rs = avg_gain / avg_loss
                result[i] = round(100 - (100 / (1 + rs)), 2)

        return result

    def _calculate_kdj(self, highs: List[float], lows: List[float], closes: List[float], n: int = 9) -> Dict:
        """
        计算KDJ指标
        RSV = (收盘价 - N日最低价) / (N日最高价 - N日最低价) * 100
        K = 2/3 * 前一日K + 1/3 * RSV
        D = 2/3 * 前一日D + 1/3 * K
        J = 3 * K - 2 * D
        """
        length = len(closes)
        k_values = [None] * length
        d_values = [None] * length
        j_values = [None] * length

        if length < n:
            return {"k": k_values, "d": d_values, "j": j_values}

        # 初始K、D值
        prev_k = 50
        prev_d = 50

        for i in range(n - 1, length):
            period_high = max(highs[i - n + 1:i + 1])
            period_low = min(lows[i - n + 1:i + 1])

            if period_high == period_low:
                rsv = 50
            else:
                rsv = (closes[i] - period_low) / (period_high - period_low) * 100

            # 计算K值
            k = 2 / 3 * prev_k + 1 / 3 * rsv
            k_values[i] = round(k, 2)

            # 计算D值
            d = 2 / 3 * prev_d + 1 / 3 * k
            d_values[i] = round(d, 2)

            # 计算J值
            j = 3 * k - 2 * d
            j_values[i] = round(j, 2)

            prev_k = k
            prev_d = d

        return {
            "k": k_values,
            "d": d_values,
            "j": j_values
        }

    def _calculate_boll(self, closes: List[float], n: int = 20, k: int = 2) -> Dict:
        """
        计算布林带指标
        中轨 = N日移动平均线
        上轨 = 中轨 + K * N日标准差
        下轨 = 中轨 - K * N日标准差
        """
        length = len(closes)
        upper = [None] * length
        middle = [None] * length
        lower = [None] * length

        if length < n:
            return {"upper": upper, "middle": middle, "lower": lower}

        for i in range(n - 1, length):
            period_data = closes[i - n + 1:i + 1]
            mid = sum(period_data) / n
            middle[i] = round(mid, 2)

            # 计算标准差
            variance = sum((x - mid) ** 2 for x in period_data) / n
            std = variance ** 0.5

            upper[i] = round(mid + k * std, 2)
            lower[i] = round(mid - k * std, 2)

        return {
            "upper": upper,
            "middle": middle,
            "lower": lower
        }

    def _find_support_resistance(self, kline_data: List[Dict], lookback: int = 30) -> Dict:
        """
        识别支撑位和压力位

        方法：
        1. 找出近期局部高点和低点
        2. 找出成交密集区
        3. 识别整数关口
        """
        if len(kline_data) < 10:
            return {"support": [], "resistance": []}

        # 取最近的数据
        recent_data = kline_data[-lookback:] if len(kline_data) > lookback else kline_data

        closes = [d['close'] for d in recent_data]
        highs = [d['high'] for d in recent_data]
        lows = [d['low'] for d in recent_data]

        current_price = closes[-1]

        support_levels = []
        resistance_levels = []

        # 1. 找局部极值点
        for i in range(2, len(recent_data) - 2):
            # 局部低点（支撑）
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                if lows[i] < current_price:
                    support_levels.append({
                        "price": round(lows[i], 2),
                        "type": "局部低点",
                        "strength": 1
                    })

            # 局部高点（压力）
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                if highs[i] > current_price:
                    resistance_levels.append({
                        "price": round(highs[i], 2),
                        "type": "局部高点",
                        "strength": 1
                    })

        # 2. 添加近期的最低价和最高价
        min_low = min(lows)
        max_high = max(highs)

        if min_low < current_price:
            support_levels.append({
                "price": round(min_low, 2),
                "type": "期间最低",
                "strength": 2
            })

        if max_high > current_price:
            resistance_levels.append({
                "price": round(max_high, 2),
                "type": "期间最高",
                "strength": 2
            })

        # 3. 整数关口
        price_floor = int(current_price / 10) * 10
        for i in range(-3, 4):
            level = price_floor + i * 10
            if level > 0 and level < current_price:
                support_levels.append({
                    "price": level,
                    "type": "整数关口",
                    "strength": 1
                })
            elif level > current_price:
                resistance_levels.append({
                    "price": level,
                    "type": "整数关口",
                    "strength": 1
                })

        # 去重并排序
        support_levels = self._dedupe_levels(support_levels, current_price, is_support=True)
        resistance_levels = self._dedupe_levels(resistance_levels, current_price, is_support=False)

        return {
            "support": support_levels[:5],  # 最多返回5个
            "resistance": resistance_levels[:5],
            "current_price": round(current_price, 2)
        }

    def _dedupe_levels(self, levels: List[Dict], current_price: float, is_support: bool) -> List[Dict]:
        """去重并合并相近的价位"""
        if not levels:
            return []

        # 按价格排序
        levels.sort(key=lambda x: x['price'], reverse=not is_support)

        # 合并相近的价位（差距小于2%）
        merged = []
        for level in levels:
            if not merged:
                merged.append(level)
            else:
                last = merged[-1]
                if abs(level['price'] - last['price']) / last['price'] > 0.02:
                    merged.append(level)
                else:
                    # 合并，保留强度更高的
                    if level['strength'] > last['strength']:
                        merged[-1] = level

        return merged

    def analyze_trend(self, stock_code: str) -> Dict:
        """
        分析股票趋势

        Returns:
            {
                "trend": "up/down/sideways",
                "trend_name": "上涨/下跌/震荡",
                "strength": 0-100,
                "ma_status": "多头排列/空头排列/缠绕",
                "price_position": "均线上方/均线下方/均线附近",
                "suggestion": "操作建议"
            }
        """
        try:
            # 获取日K数据
            kline_result = self.get_kline_data(stock_code, 'daily', 60)

            if not kline_result.get("success") or not kline_result.get("kline"):
                return self._get_default_trend()

            kline = kline_result["kline"]
            indicators = kline_result["indicators"]

            closes = [d['close'] for d in kline]
            current_price = closes[-1]

            # 均线数据
            ma5 = indicators["ma"]["ma5"]
            ma10 = indicators["ma"]["ma10"]
            ma20 = indicators["ma"]["ma20"]
            ma60 = indicators["ma"]["ma60"]

            # 1. 判断均线排列
            ma5_last = ma5[-1] if ma5[-1] else 0
            ma10_last = ma10[-1] if ma10[-1] else 0
            ma20_last = ma20[-1] if ma20[-1] else 0
            ma60_last = ma60[-1] if ma60[-1] else 0

            if ma5_last > ma10_last > ma20_last > ma60_last and ma5_last > 0:
                ma_status = "多头排列"
                ma_score = 80
            elif ma5_last < ma10_last < ma20_last < ma60_last and ma5_last > 0:
                ma_status = "空头排列"
                ma_score = 20
            else:
                ma_status = "均线缠绕"
                ma_score = 50

            # 2. 判断价格位置
            ma20_val = ma20_last if ma20_last else current_price
            diff_from_ma20 = (current_price - ma20_val) / ma20_val * 100 if ma20_val > 0 else 0

            if diff_from_ma20 > 3:
                price_position = "均线上方"
                price_score = 70
            elif diff_from_ma20 < -3:
                price_position = "均线下方"
                price_score = 30
            else:
                price_position = "均线附近"
                price_score = 50

            # 3. 判断趋势方向（用最近20天的涨跌幅）
            if len(closes) >= 20:
                change_20d = (closes[-1] - closes[-20]) / closes[-20] * 100
            else:
                change_20d = 0

            if len(closes) >= 5:
                change_5d = (closes[-1] - closes[-5]) / closes[-5] * 100
            else:
                change_5d = 0

            # 4. 判断震荡程度
            if len(closes) >= 20:
                recent_closes = closes[-20:]
                avg = sum(recent_closes) / len(recent_closes)
                volatility = sum(abs(c - avg) / avg for c in recent_closes) / len(recent_closes) * 100
            else:
                volatility = 0

            # 综合判断趋势
            trend_score = (ma_score * 0.4 + price_score * 0.3 +
                          (70 if change_20d > 5 else 30 if change_20d < -5 else 50) * 0.3)

            if trend_score >= 65:
                trend = "up"
                trend_name = "上升趋势"
                suggestion = "趋势向上，可考虑逢低买入"
            elif trend_score <= 35:
                trend = "down"
                trend_name = "下降趋势"
                suggestion = "趋势向下，建议观望或减仓"
            else:
                trend = "sideways"
                trend_name = "震荡趋势"
                suggestion = "趋势不明，建议轻仓或观望"

            # 5. 资金流向参考（如果有）
            money_flow_score = 50
            try:
                from services.stock_service import stock_service
                flow = stock_service.get_money_flow(stock_code)
                if flow.get("main_net"):
                    # 主力净流入为正加分，为负减分
                    main_net = flow["main_net"]
                    if main_net > 50:
                        money_flow_score = 70
                    elif main_net < -50:
                        money_flow_score = 30
            except:
                pass

            # 最终强度
            strength = round(trend_score * 0.7 + money_flow_score * 0.3, 1)

            return {
                "trend": trend,
                "trend_name": trend_name,
                "strength": strength,
                "ma_status": ma_status,
                "price_position": price_position,
                "change_5d": round(change_5d, 2),
                "change_20d": round(change_20d, 2),
                "volatility": round(volatility, 2),
                "suggestion": suggestion,
                "score_detail": {
                    "ma_score": ma_score,
                    "price_score": price_score,
                    "trend_score": round(trend_score, 1)
                }
            }

        except Exception as e:
            print(f"趋势分析失败: {e}")
            return self._get_default_trend()

    def _get_default_trend(self) -> Dict:
        """返回默认趋势数据"""
        return {
            "trend": "sideways",
            "trend_name": "数据不足",
            "strength": 50,
            "ma_status": "未知",
            "price_position": "未知",
            "change_5d": 0,
            "change_20d": 0,
            "volatility": 0,
            "suggestion": "数据不足，无法判断趋势"
        }


# 全局实例
chart_service = ChartService()

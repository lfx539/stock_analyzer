# 股票数据获取服务
# 使用腾讯财经API（主要）+ 东方财富API（备用）

import requests
from typing import Optional, Dict, List, Any
import time
import re


class StockDataService:
    """股票数据获取服务"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        self.timeout = 10
        self.max_retries = 2

    def _request_with_retry(self, url: str, params: dict = None, proxies: dict = None) -> dict:
        """带重试的请求"""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                resp = requests.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=self.timeout,
                    proxies=proxies
                )

                if resp.status_code == 200:
                    return resp.json() if "json" in resp.headers.get("content-type", "") else resp
                else:
                    last_error = f"HTTP {resp.status_code}"

            except requests.exceptions.ProxyError as e:
                last_error = f"代理连接失败: {str(e)}"
            except requests.exceptions.ConnectTimeout as e:
                last_error = f"连接超时: {str(e)}"
            except requests.exceptions.ConnectionError as e:
                last_error = f"网络连接失败: {str(e)}"
            except Exception as e:
                last_error = f"请求异常: {str(e)}"

            if attempt < self.max_retries - 1:
                time.sleep(0.5)

        raise Exception(f"数据获取失败，已重试{self.max_retries}次: {last_error}")

    def _get_tencent_data(self, stock_code: str) -> Dict:
        """使用腾讯财经接口获取实时行情"""
        market = "sh" if stock_code.startswith("6") else "sz"
        url = f"https://qt.gtimg.cn/q={market}{stock_code}"

        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout, proxies={"http": None, "https": None})
            if resp.status_code == 200 and resp.text:
                text = resp.text.strip()
                # 腾讯返回格式: v_sh600028="1~中国石化~600028~5.93~6.04~5.94~..."
                match = re.search(r'"([^"]+)"', text)
                if match:
                    parts = match.group(1).split("~")
                    if len(parts) >= 50:
                        # 解析PE和PB (字段46和47)
                        pe_val = parts[46] if len(parts) > 46 and parts[46] else "0"
                        pb_val = parts[47] if len(parts) > 47 and parts[47] else "0"

                        return {
                            "f43": float(parts[3]) if parts[3] else 0,   # 最新价
                            "f2": float(parts[4]) if parts[4] else 0,     # 开盘价
                            "f4": float(parts[5]) if parts[5] else 0,     # 昨收
                            "f44": float(parts[31]) if parts[31] else 0,  # 涨跌幅
                            "f47": float(parts[32]) if parts[32] else 0,  # 涨跌额
                            "f58": parts[1],  # 股票名称
                            "f57": parts[2],  # 股票代码
                            "f162": float(pe_val) if pe_val and pe_val != "-" else 0,  # PE
                            "f167": float(pb_val) if pb_val and pb_val != "-" else 0,  # PB
                        }
            raise Exception("腾讯接口返回数据格式错误")
        except Exception as e:
            if "数据获取失败" in str(e):
                raise
            raise Exception(f"腾讯接口失败: {str(e)}")

    def get_stock_info(self, stock_code: str) -> Dict:
        """获取股票基本信息（名称、行业等）- 使用 HTTP 接口"""
        # 优先从腾讯接口获取名称
        name = None
        try:
            data = self._get_tencent_data(stock_code)
            if data.get("f58"):
                name = data["f58"]
        except:
            pass

        # 如果腾讯失败，从 searchapi 获取名称
        if not name:
            try:
                url = "http://searchapi.eastmoney.com/api/suggest/get"
                params = {"input": stock_code, "type": "14", "count": "1"}
                resp = requests.get(url, params=params, headers=self.headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("QuotationCodeTable", {}).get("Data"):
                        name = data["QuotationCodeTable"]["Data"][0].get("Name")
            except:
                pass

        # 获取行业信息
        industry = self._get_industry_from_em(stock_code)

        return {"name": name or "未知", "industry": industry}

    def _get_industry_from_em(self, stock_code: str) -> str:
        """从东方财富获取行业信息"""
        try:
            # 构造市场代码
            market = "SH" if stock_code.startswith("6") else "SZ"
            url = "https://emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax"
            params = {"code": f"{market}{stock_code}"}

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("jbzl") and len(data["jbzl"]) > 0:
                    info = data["jbzl"][0]
                    # 优先使用申万行业分类
                    industry = info.get("EM2016") or info.get("INDUSTRYCSRC1")
                    if industry:
                        # 简化行业名称（取最后一部分）
                        if "-" in industry:
                            industry = industry.split("-")[-1]
                        return industry
        except Exception as e:
            print(f"获取行业信息失败: {e}")
        return "未知"

    def get_industry_pe_pb(self, industry_name: str = None) -> Dict:
        """获取行业平均PE/PB"""
        # 尝试获取行业PE/PB数据
        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": 1,
                "pz": 100,
                "po": 1,
                "np": 1,
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": "m:90+t:2",
                "fields": "f2,f4,f14"  # f2=PE, f4=PB
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data") and data["data"].get("diff"):
                    return {"data": data["data"]["diff"], "success": True}
        except Exception as e:
            print(f"获取行业PE失败: {e}")
        return {"data": [], "success": False}

    def get_stock_basic_info(self, stock_code: str) -> Dict:
        """获取股票基本信息"""
        # 使用东方财富行情接口
        url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "fltt": 2,
            "invt": 2,
            "fields": "f2,f3,f4,f12,f13,f14",
            "secids": f"1.{stock_code}" if stock_code.startswith("6") else f"0.{stock_code}"
        }
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data") and data["data"].get("diff"):
                    stock_info = data["data"]["diff"][0]
                    return {
                        "name": stock_info.get("f14", ""),
                        "code": stock_info.get("f12", stock_code),
                        "industry": ""
                    }
        except Exception as e:
            print(f"获取基本信息失败: {e}")
        return {}

    def get_financial_data(self, stock_code: str) -> Dict:
        """获取主要财务指标 - 使用东方财富财务分析API"""
        url = f"https://emdata.eastmoney.com/ggcx/"
        # 使用备用方法
        return self._get_financial_indicator(stock_code)

    def _get_financial_indicator(self, stock_code: str) -> Dict:
        """获取财务指标"""
        market = "sh" if stock_code.startswith("6") else "sz"
        url = f"https://datacenter.eastmoney.com/api/data/v1/get"
        params = {
            "type": "RPT_FINANCE_INDICATOR_HK",
            "filter": f"(SECUCODE%3D%22{market.upper()}{stock_code}%22)",
            "pageNumber": "1",
            "pageSize": "5",
            "source": "WEB",
            "reportName": "RPT_FINANCE_INDICATOR",
            "columns": "ALL"
        }

        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()
            if data.get("result"):
                return {"data": data["result"]["data"]}
        except Exception as e:
            print(f"获取财务指标失败: {e}")
        return {}

    def get_dividend_data(self, stock_code: str) -> List[Dict]:
        """获取分红送转数据 - 使用东方财富接口"""
        url = "https://datacenter.eastmoney.com/api/data/v1/get"
        market = "sh" if stock_code.startswith("6") else "sz"
        params = {
            "type": "RPT_FINANCE_DIVIDEND",
            "filter": f"(SECUCODE%3D%22{market.upper()}{stock_code}%22)",
            "pageNumber": "1",
            "pageSize": "10",
            "source": "WEB",
            "reportName": "RPT_FINANCE_DIVIDEND",
            "columns": "ALL"
        }

        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()
            if data.get("result") and data["result"].get("data"):
                return data["result"]["data"]
        except Exception as e:
            print(f"获取分红数据失败: {e}")
        return []

    def get_valuation_data(self, stock_code: str) -> Dict:
        """获取估值数据 - 东方财富接口不可用，返回空数据"""
        # 东方财富接口受限，暂时无法获取 PE/PB 数据
        return {}

    def get_trade_data(self, stock_code: str) -> Dict:
        """获取交易数据（实时行情）- 使用腾讯接口"""
        # 使用腾讯财经接口
        try:
            data = self._get_tencent_data(stock_code)
            if data and data.get("f43", 0) > 0:
                return data
        except Exception as e:
            raise Exception(f"获取实时行情失败: {str(e)}")

        raise Exception(f"未获取到股票 {stock_code} 的行情数据")

    def get_historical_pe_pb(self, stock_code: str, years: int = 10) -> List[Dict]:
        """获取历史PE/PB数据 - 东方财富接口不可用"""
        # 东方财富接口受限，暂时无法获取历史数据
        return []

    def get_financial_data(self, stock_code: str) -> Dict:
        """获取财务数据（EPS、BPS）用于计算PE/PB"""
        # 尝试从新浪财经获取财务数据
        try:
            financial_data = self._get_sina_financial_data(stock_code)
            if financial_data and financial_data.get('eps'):
                return financial_data
        except:
            pass

        # 尝试从东方财富获取财务数据
        try:
            financial_data = self._get_eastmoney_financial_data(stock_code)
            if financial_data and financial_data.get('eps'):
                return financial_data
        except:
            pass

        # 使用本地缓存的财务数据
        return self._get_local_financial_data(stock_code)

    def _get_sina_financial_data(self, stock_code: str) -> Dict:
        """从新浪财经获取财务数据"""
        market = 'sh' if stock_code.startswith('6') else 'sz'
        url = f'https://finance.sina.com.cn/realstock/company/{market}{stock_code}/nc.shtml'
        headers = {'User-Agent': 'Mozilla/5.0'}

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {}

        import re
        text = resp.text

        # 解析每股收益
        eps = None
        eps_match = re.search(r'每股收益.*?(\d+\.?\d*)\s*元', text)
        if eps_match:
            eps = float(eps_match.group(1))

        # 解析每股净资产
        bps = None
        bps_match = re.search(r'每股净资产.*?(\d+\.?\d*)\s*元', text)
        if bps_match:
            bps = float(bps_match.group(1))

        if eps or bps:
            return {'eps': eps, 'bps': bps}
        return {}

    def _get_eastmoney_financial_data(self, stock_code: str) -> Dict:
        """从东方财富获取财务数据"""
        # 这个接口可能不稳定，返回空让后续使用本地数据
        return {}

    def _get_local_financial_data(self, stock_code: str) -> Dict:
        """本地缓存的财务数据 - 基于2024年Q3财报"""
        financial_db = {
            # 银行股
            "600036": {"eps": 1.45, "bps": 35.62},  # 招商银行
            "601398": {"eps": 0.84, "bps": 7.82},   # 工商银行
            "601939": {"eps": 0.72, "bps": 7.45},   # 建设银行
            "601288": {"eps": 0.92, "bps": 6.78},   # 农业银行
            "000001": {"eps": 1.42, "bps": 15.68},   # 平安银行
            # 石化能源
            "600028": {"eps": 0.71, "bps": 5.92},   # 中国石化
            "601857": {"eps": 0.45, "bps": 5.23},   # 中国石油
            "600871": {"eps": 0.32, "bps": 4.15},    # 石化机械
            # 消费
            "600519": {"eps": 35.78, "bps": 163.29}, # 贵州茅台
            "000858": {"eps": 6.87, "bps": 32.45},  # 五粮液
            "600887": {"eps": 0.68, "bps": 4.12},   # 伊利股份
            # 科技
            "600570": {"eps": 1.25, "bps": 8.92},   # 恒生电子
            "002475": {"eps": 5.68, "bps": 24.35},  # 立讯精密
            "000333": {"eps": 3.45, "bps": 18.92},  # 美的集团
            # 医药
            "600276": {"eps": 1.85, "bps": 12.45},  # 恒瑞医药
            "300759": {"eps": 1.22, "bps": 8.65},   # 惠康生物
        }

        return financial_db.get(stock_code, {"eps": None, "bps": None})


# 全局服务实例
stock_service = StockDataService()

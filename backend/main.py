# -*- coding: utf-8 -*-
"""
股票分析系统 - 后端API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn
import requests
import re

from services.stock_service import stock_service
from services.analyzer import analyzer
from services.news_service import news_service
from database import Database

app = FastAPI(
    title="股票分析系统API",
    description="用于分析股票财务指标和估值数据",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StockCodeRequest(BaseModel):
    stock_code: str


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "股票分析系统API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze_stock(request: StockCodeRequest) -> Dict[str, Any]:
    """
    分析股票

    参数:
        stock_code: 股票代码（如 600028）

    返回:
        包含所有分析结果的JSON
    """
    stock_code = request.stock_code.strip()

    # 验证股票代码格式
    if not stock_code.isdigit() or len(stock_code) != 6:
        raise HTTPException(status_code=400, detail="股票代码应为6位数字")

    try:
        result = analyzer.analyze_stock(stock_code)
        return result
    except Exception as e:
        error_msg = str(e)
        # 判断是否是网络问题
        if "代理" in error_msg or "网络" in error_msg or "连接" in error_msg:
            detail = f"网络连接失败: {error_msg}。请检查网络设置或关闭代理软件后重试。"
        else:
            detail = error_msg
        raise HTTPException(status_code=500, detail=detail)


@app.get("/api/stock/{stock_code}")
async def get_stock_info(stock_code: str) -> Dict[str, Any]:
    """获取股票基本信息"""
    try:
        basic = stock_service.get_stock_basic_info(stock_code)
        trade = stock_service.get_trade_data(stock_code)
        return {
            "basic": basic,
            "trade": trade
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
async def search_stocks(q: str = "", limit: int = 10) -> Dict[str, Any]:
    """
    搜索股票（实时从东方财富API获取）

    参数:
        q: 搜索关键词（股票代码或名称）
        limit: 返回结果数量，默认10

    返回:
        股票列表 [{code, name}, ...]
    """
    if not q or len(q.strip()) < 1:
        return {"stocks": [], "total": 0}

    try:
        q = q.strip()

        # 调用东方财富实时搜索API
        url = "https://searchapi.eastmoney.com/api/suggest/get"
        params = {
            "input": q,
            "type": 14,  # A股搜索
            "token": "D43BF722C8E33BDC906FB84D85E326E8",
            "count": limit
        }

        resp = requests.get(url, params=params, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.eastmoney.com/"
        }, timeout=5, proxies={"http": None, "https": None})

        if resp.status_code != 200:
            return {"stocks": [], "total": 0, "error": "API请求失败"}

        data = resp.json()
        results = []

        # 解析返回数据
        quot_list = data.get("QuotationCodeTable", {}).get("Data", [])
        for item in quot_list:
            code = item.get("Code", "")
            name = item.get("Name", "")

            # 过滤掉非A股（保留沪市和深市）
            if code and name and len(code) == 6:
                # 添加市场前缀
                market = "sh" if code.startswith("6") else "sz"
                results.append({
                    "code": code,
                    "name": name,
                    "market": market
                })

        return {
            "stocks": results,
            "total": len(results),
            "query": q
        }
    except Exception as e:
        return {"stocks": [], "total": 0, "error": str(e)}


@app.get("/api/recommend_stocks")
async def recommend_stocks(keywords: str = "", limit: int = 6) -> Dict[str, Any]:
    """
    根据关键词推荐相关股票（动态从API获取）

    参数:
        keywords: 关键词（如新闻标题中的行业关键词）
        limit: 返回数量，默认6

    返回:
        股票列表 [{code, name, reason}, ...]
    """
    if not keywords or len(keywords.strip()) < 1:
        return {"stocks": [], "total": 0}

    try:
        # 从关键词中提取股票代码
        # 尝试直接匹配6位数字代码
        code_pattern = re.findall(r'\b(\d{6})\b', keywords)
        if code_pattern:
            codes = list(set(code_pattern))[:3]
            stocks = []
            for code in codes:
                try:
                    market = "sh" if code.startswith("6") else "sz"
                    url = f"https://qt.gtimg.cn/q={market}{code}"
                    resp = requests.get(url, headers={
                        "User-Agent": "Mozilla/5.0"
                    }, timeout=3, proxies={"http": None, "https": None})
                    if resp.status_code == 200 and resp.text and resp.text.strip() != "null":
                        data = resp.text.split('=')[1].strip('"')
                        parts = data.split('~')
                        if len(parts) > 3 and parts[1]:
                            stocks.append({
                                "code": code,
                                "name": parts[1],
                                "reason": "新闻关联"
                            })
                except:
                    pass
            if stocks:
                return {"stocks": stocks, "total": len(stocks)}

        # 从关键词中提取中文词进行搜索
        # 提取关键行业词
        industry_keywords = _extract_industry_keywords(keywords)

        stocks = []
        seen_codes = set()

        for kw in industry_keywords[:3]:  # 最多搜索3个关键词
            try:
                url = "https://searchapi.eastmoney.com/api/suggest/get"
                params = {
                    "input": kw,
                    "type": 14,
                    "token": "D43BF722C8E33BDC906FB84D85E326E8",
                    "count": 3
                }
                resp = requests.get(url, params=params, timeout=3, proxies={"http": None, "https": None})
                if resp.status_code == 200:
                    data = resp.json()
                    quot_list = data.get("QuotationCodeTable", {}).get("Data", [])
                    for item in quot_list:
                        code = item.get("Code", "")
                        name = item.get("Name", "")
                        if code and name and len(code) == 6 and code not in seen_codes:
                            seen_codes.add(code)
                            stocks.append({
                                "code": code,
                                "name": name,
                                "reason": f"关联\"{kw}\""
                            })
                            if len(stocks) >= limit:
                                break
            except:
                pass
            if len(stocks) >= limit:
                break

        return {"stocks": stocks[:limit], "total": len(stocks)}
    except Exception as e:
        return {"stocks": [], "total": 0, "error": str(e)}


def _extract_industry_keywords(text: str) -> list:
    """从文本中提取行业关键词和公司名称"""
    # 定义常见行业关键词
    industry_words = [
        "人工智能", "AI", "芯片", "半导体", "云计算", "新能源", "光伏", "新能源汽车",
        "锂电池", "储能", "电力", "石油", "煤炭", "钢铁", "有色金属", "稀土",
        "银行", "保险", "券商", "医药", "医疗", "消费", "食品", "白酒", "家电",
        "房地产", "建筑", "基建", "航运", "航空", "军工", "5G", "数字经济",
        "互联网", "软件", "物联网", "大数据", "高铁", "污水处理", "环保",
        "算力", "人工智能", "机器人", "自动驾驶", "量子计算", "卫星导航", "6G"
    ]

    found = []
    text_lower = text.lower()

    # 1. 先提取可能是公司名的中文词（3-6个字符，可能包含股份、有限、科技、智联等）
    company_patterns = re.findall(r'[\u4e00-\u9fa5]{2,8}(?:股份|有限|科技|智联|集团|实业|发展|投资|能源|新材|智能|医疗|制药|电子|机械)', text)
    if company_patterns:
        found.extend(company_patterns[:2])

    # 2. 提取纯公司名（3-4个字符的公司简称）
    simple_names = re.findall(r'(?:^|[\u4e00-\u9fa5])([^\u4e00-\u9fa5]{0,3}(?:股份|有限|科技|智联|集团|实业))', text)
    # 也提取常见的公司名模式：2-4个字符后面跟着"涨停"、"上涨"等
    potential_stocks = re.findall(r'([\u4e00-\u9fa5]{2,4})(?:涨停|上涨|大跌|涨幅)', text)
    for name in potential_stocks:
        if name not in found:
            found.append(name)

    # 3. 匹配行业关键词
    for word in industry_words:
        if word in text or word.lower() in text_lower:
            if word not in found:
                found.append(word)

    # 4. 如果还没找到，提取所有2-6个连续中文字符
    if not found:
        chinese = re.findall(r'[\u4e00-\u9fa5]{2,6}', text)
        # 过滤掉常见的无意义词
        stop_words = ["今日", "昨日", "表示", "记者", "消息", "报道", "公司", "方面", "可能"]
        chinese = [c for c in chinese if c not in stop_words]
        if chinese:
            found = chinese[:3]

    return found


# ========== 新闻API ==========
@app.get("/api/news")
async def get_hot_news(limit: int = 10) -> Dict[str, Any]:
    """获取热点新闻"""
    try:
        news = news_service.get_hot_news(limit)
        return {
            "news": news,
            "count": len(news),
            "categories": ["科技", "AI", "能源", "计算机", "稀有金属"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recommend")
async def get_stock_recommendations() -> Dict[str, Any]:
    """获取股票推荐"""
    try:
        recommendations = news_service.get_recommended_stocks()
        return {
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 自选股API ==========
class WatchlistRequest(BaseModel):
    stock_code: str
    stock_name: Optional[str] = None
    notes: Optional[str] = None

@app.get("/api/watchlist")
async def get_watchlist() -> Dict[str, Any]:
    """获取自选股列表"""
    try:
        watchlist = Database.get_watchlist()

        # 补充实时行情和股息率
        result = []
        for item in watchlist:
            stock_code = item['stock_code']
            try:
                trade_data = stock_service.get_trade_data(stock_code)
                item['current_price'] = trade_data.get('f43')
                item['price_change'] = trade_data.get('f44')
                item['price_change_amount'] = trade_data.get('f47')

                # 计算股息率（使用本地数据）
                financial_data = stock_service.get_financial_data(stock_code)
                if financial_data.get('eps'):
                    current_price = float(trade_data.get('f43', 0))
                    eps = financial_data.get('eps')
                    cash_div = financial_data.get('cash_dividend', 0)
                    # 如果本地没有分红数据，尝试从dividend_db获取
                    if not cash_div:
                        from services.analyzer import dividend_db
                        stock_info = dividend_db.get(stock_code, {})
                        cash_div = stock_info.get('cash', 0)
                    if current_price > 0 and cash_div:
                        item['dividend_yield'] = round(cash_div / current_price * 100, 2)
                        item['cash_dividend'] = cash_div
            except:
                item['current_price'] = None
                item['price_change'] = None
                item['price_change_amount'] = None
            result.append(item)

        return {"watchlist": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/watchlist")
async def add_watchlist(request: WatchlistRequest) -> Dict[str, Any]:
    """添加自选股"""
    try:
        # 获取股票名称（如果未提供）
        stock_name = request.stock_name
        if not stock_name:
            try:
                basic = stock_service.get_stock_basic_info(request.stock_code)
                stock_name = basic.get('name') or basic.get('Name') or request.stock_code
            except:
                stock_name = request.stock_code

        success = Database.add_watchlist(
            request.stock_code,
            stock_name,
            request.notes
        )

        if success:
            return {"message": f"已添加 {stock_name} 到自选股", "success": True}
        else:
            return {"message": f"{stock_name} 已在自选股中", "success": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/watchlist/{stock_code}")
async def remove_watchlist(stock_code: str) -> Dict[str, Any]:
    """删除自选股"""
    try:
        success = Database.remove_watchlist(stock_code)
        if success:
            return {"message": f"已删除 {stock_code}", "success": True}
        else:
            return {"message": f"{stock_code} 不在自选股中", "success": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

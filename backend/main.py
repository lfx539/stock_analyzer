# -*- coding: utf-8 -*-
"""
股票分析系统 - 后端API
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn

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

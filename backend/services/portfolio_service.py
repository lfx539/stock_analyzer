# -*- coding: utf-8 -*-
"""
投资组合服务
"""

from typing import List, Dict, Any, Optional
from database import Database


class PortfolioService:
    """投资组合服务"""

    def create_portfolio(self, name: str, initial_capital: float) -> Dict[str, Any]:
        """
        创建投资组合

        Args:
            name: 组合名称
            initial_capital: 初始资金

        Returns:
            创建结果
        """
        if not name or not name.strip():
            return {"success": False, "message": "组合名称不能为空"}

        if initial_capital <= 0:
            return {"success": False, "message": "初始资金必须大于0"}

        portfolio_id = Database.create_portfolio(name.strip(), initial_capital)

        return {
            "success": True,
            "message": f"组合'{name}'创建成功",
            "portfolio_id": portfolio_id
        }

    def get_portfolios(self) -> List[Dict[str, Any]]:
        """获取所有投资组合"""
        portfolios = Database.get_portfolios()

        # 计算每个组合的市值和收益
        for p in portfolios:
            p['holdings'] = self._calculate_holdings_value(p['id'])
            p['current_value'] = p['cash'] + p['holdings']['total_value']
            p['profit'] = p['current_value'] - p['initial_capital']
            p['profit_pct'] = round((p['current_value'] - p['initial_capital']) / p['initial_capital'] * 100, 2)

        return portfolios

    def get_portfolio_detail(self, portfolio_id: int) -> Optional[Dict[str, Any]]:
        """获取组合详情"""
        portfolio = Database.get_portfolio(portfolio_id)
        if not portfolio:
            return None

        # 获取持仓
        holdings = Database.get_holdings(portfolio_id)

        # 获取实时价格和市值
        from services.stock_service import stock_service
        total_market_value = 0

        for h in holdings:
            try:
                trade_data = stock_service.get_trade_data(h['stock_code'])
                current_price = trade_data.get('f43', 0)
                h['current_price'] = current_price
                h['market_value'] = round(current_price * h['shares'], 2)
                h['cost_price'] = round(h['cost'] / h['shares'], 2) if h['shares'] > 0 else 0
                h['profit'] = round(h['market_value'] - h['cost'], 2)
                h['profit_pct'] = round((h['market_value'] - h['cost']) / h['cost'] * 100, 2) if h['cost'] > 0 else 0
                total_market_value += h['market_value']
            except:
                h['current_price'] = None
                h['market_value'] = 0

        portfolio['holdings_list'] = holdings
        portfolio['total_market_value'] = total_market_value
        portfolio['current_value'] = portfolio['cash'] + total_market_value
        portfolio['profit'] = round(portfolio['current_value'] - portfolio['initial_capital'], 2)
        portfolio['profit_pct'] = round((portfolio['current_value'] - portfolio['initial_capital']) / portfolio['initial_capital'] * 100, 2)

        # 获取交易记录
        portfolio['transactions'] = Database.get_transactions(portfolio_id)

        return portfolio

    def trade(self, portfolio_id: int, stock_code: str, stock_name: str,
              trans_type: str, shares: float, price: float) -> Dict[str, Any]:
        """
        执行交易

        Args:
            portfolio_id: 组合ID
            stock_code: 股票代码
            stock_name: 股票名称
            trans_type: 交易类型 'buy' 或 'sell'
            shares: 股数
            price: 价格

        Returns:
            交易结果
        """
        if trans_type not in ['buy', 'sell']:
            return {"success": False, "message": "交易类型必须是 'buy' 或 'sell'"}

        if shares <= 0:
            return {"success": False, "message": "股数必须大于0"}

        if price <= 0:
            return {"success": False, "message": "价格必须大于0"}

        # 获取组合信息
        portfolio = Database.get_portfolio(portfolio_id)
        if not portfolio:
            return {"success": False, "message": "组合不存在"}

        amount = round(shares * price, 2)

        # 检查资金/持仓
        if trans_type == 'buy':
            if amount > portfolio['cash']:
                return {"success": False, "message": f"资金不足，当前可用 {portfolio['cash']:.2f} 元"}
        else:
            # 检查持仓
            holdings = Database.get_holdings(portfolio_id)
            holding = next((h for h in holdings if h['stock_code'] == stock_code), None)
            if not holding or holding['shares'] < shares:
                return {"success": False, "message": f"持仓不足"}

        # 添加交易记录
        Database.add_transaction(portfolio_id, stock_code, stock_name, trans_type, shares, price, amount)

        # 更新现金
        if trans_type == 'buy':
            new_cash = portfolio['cash'] - amount
        else:
            new_cash = portfolio['cash'] + amount

        Database.update_portfolio_cash(portfolio_id, round(new_cash, 2))

        return {
            "success": True,
            "message": f"{'买入' if trans_type == 'buy' else '卖出'}成功：{stock_name} {shares}股 @ {price}元"
        }

    def delete_portfolio(self, portfolio_id: int) -> Dict[str, Any]:
        """删除投资组合"""
        portfolio = Database.get_portfolio(portfolio_id)
        if not portfolio:
            return {"success": False, "message": "组合不存在"}

        Database.delete_portfolio(portfolio_id)
        return {"success": True, "message": f"组合'{portfolio['name']}'已删除"}

    def rename_portfolio(self, portfolio_id: int, new_name: str) -> Dict[str, Any]:
        """重命名投资组合"""
        if not new_name or not new_name.strip():
            return {"success": False, "message": "组合名称不能为空"}

        portfolio = Database.get_portfolio(portfolio_id)
        if not portfolio:
            return {"success": False, "message": "组合不存在"}

        Database.rename_portfolio(portfolio_id, new_name.strip())
        return {"success": True, "message": f"组合已重命名为'{new_name}'"}

    def _calculate_holdings_value(self, portfolio_id: int) -> Dict[str, Any]:
        """计算持仓市值"""
        holdings = Database.get_holdings(portfolio_id)

        from services.stock_service import stock_service
        total_value = 0

        for h in holdings:
            try:
                trade_data = stock_service.get_trade_data(h['stock_code'])
                current_price = trade_data.get('f43', 0)
                total_value += current_price * h['shares']
            except:
                pass

        return {
            "holdings_count": len(holdings),
            "total_value": round(total_value, 2)
        }


# 全局实例
portfolio_service = PortfolioService()

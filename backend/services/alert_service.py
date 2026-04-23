# -*- coding: utf-8 -*-
"""
价格预警服务
"""

from typing import List, Dict, Any
from database import Database


class AlertService:
    """价格预警服务"""

    def create_alert(self, stock_code: str, stock_name: str, target_price: float, alert_type: str) -> Dict[str, Any]:
        """
        创建价格预警

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            target_price: 目标价格
            alert_type: 预警类型 'above'(站上) 或 'below'(跌破)

        Returns:
            创建结果
        """
        # 验证
        if alert_type not in ['above', 'below']:
            return {"success": False, "message": "预警类型必须是 'above' 或 'below'"}

        if target_price <= 0:
            return {"success": False, "message": "目标价格必须大于0"}

        alert_id = Database.add_alert(stock_code, stock_name, target_price, alert_type)

        return {
            "success": True,
            "message": f"已设置预警：{stock_name} {'站上' if alert_type == 'above' else '跌破'} {target_price}元",
            "alert_id": alert_id
        }

    def get_all_alerts(self) -> List[Dict[str, Any]]:
        """获取所有预警"""
        return Database.get_alerts()

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃预警"""
        return Database.get_active_alerts()

    def delete_alert(self, alert_id: int) -> Dict[str, Any]:
        """删除预警"""
        success = Database.remove_alert(alert_id)
        if success:
            return {"success": True, "message": "预警已删除"}
        return {"success": False, "message": "预警不存在"}

    def check_alerts(self) -> List[Dict[str, Any]]:
        """
        检查所有活跃预警，返回已触发的预警

        Returns:
            触发的预警列表
        """
        from services.stock_service import stock_service

        active_alerts = Database.get_active_alerts()
        triggered = []

        for alert in active_alerts:
            stock_code = alert['stock_code']

            try:
                # 获取当前价格
                trade_data = stock_service.get_trade_data(stock_code)
                current_price = trade_data.get('f43')

                if current_price and current_price > 0:
                    target_price = alert['target_price']
                    alert_type = alert['alert_type']

                    # 检查是否触发
                    is_triggered = False
                    if alert_type == 'above' and current_price >= target_price:
                        is_triggered = True
                    elif alert_type == 'below' and current_price <= target_price:
                        is_triggered = True

                    if is_triggered:
                        # 标记为已触发
                        Database.trigger_alert(alert['id'])
                        triggered.append({
                            **alert,
                            'current_price': current_price,
                            'message': f"{alert['stock_name']} 已{'站上' if alert_type == 'above' else '跌破'} 目标价 {target_price}元，当前价格 {current_price}元"
                        })
            except Exception as e:
                print(f"检查预警失败 {stock_code}: {e}")
                continue

        return triggered

    def get_alerts_with_current_price(self) -> List[Dict[str, Any]]:
        """获取预警列表并补充当前价格"""
        from services.stock_service import stock_service

        alerts = Database.get_alerts()

        for alert in alerts:
            try:
                trade_data = stock_service.get_trade_data(alert['stock_code'])
                alert['current_price'] = trade_data.get('f43')
            except:
                alert['current_price'] = None

        return alerts


# 全局实例
alert_service = AlertService()

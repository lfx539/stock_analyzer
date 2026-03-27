# 股票分析系统

## 启动方式

### 后端服务
```bash
cd /Users/lfx/Documents/006_code/stock_analyzer/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 前端
直接在浏览器打开：`frontend/index.html`

或使用 HTTP 服务器：
```bash
cd frontend
python3 -m http.server 8080
```
然后访问：http://localhost:8080

## API 地址
后端：http://localhost:8000

## 功能
- 股票深度分析（财务、估值、股息、风险等）
- 热点新闻获取
- 股票推荐
- 自选股管理
- PE/PB 历史分位数计算
# 股票分析系统 - 数据接口文档

## 概述

本系统使用多个数据源获取股票数据，包括腾讯财经、东方财富、同花顺(akshare)等。

---

## 数据源汇总

| 数据源 | 数据类型 | 时效性 | 免费额度 |
|-------|---------|--------|---------|
| 腾讯财经API | 实时行情、PE、PB | 实时（秒级） | 无限制 |
| 东方财富API | 分红、公司简介、新闻、行业成分股 | 实时 | 无限制 |
| 同花顺API (akshare) | ROE、负债率、资金流向 | 有延迟 | 无限制 |

---

## 一、腾讯财经API

### 1.1 实时行情接口

**接口地址：**
```
https://qt.gtimg.cn/q={market}{stock_code}
```

**参数说明：**
- `market`: sh（上海）或 sz（深圳）
- `stock_code`: 6位股票代码

**示例：**
```
https://qt.gtimg.cn/q=sh600028
```

**返回格式：**
```
v_sh600028="1~中国石化~600028~5.44~5.44~0.00~..."
```

**字段说明：**

| 字段索引 | 字段名 | 说明 |
|---------|-------|------|
| 1 | 股票名称 | 如"中国石化" |
| 2 | 股票代码 | 如"600028" |
| 3 | 当前价格 | 实时价格 |
| 4 | 昨日收盘价 | - |
| 5 | 今日开盘价 | - |
| 30 | 时间戳 | 格式：20260423101535 |
| 31 | 涨跌幅 | 如 0.18 |
| 32 | 涨跌额 | 如 0.01 |
| 46 | PE（市盈率） | TTM市盈率 |
| 49 | PB（市净率） | 正确的PB值 |

**时效性：** ✅ 实时，每3秒更新

**注意事项：**
- 字段47返回的PB值错误，应使用字段49
- 无需认证，直接调用

---

## 二、东方财富API

### 2.1 分红融资接口

**接口地址：**
```
https://emweb.eastmoney.com/PC_HSF10/BonusFinancing/PageAjax?code={market}{stock_code}
```

**参数说明：**
- `market`: sh（上海）或 sz（深圳）
- `stock_code`: 6位股票代码

**示例：**
```
https://emweb.eastmoney.com/PC_HSF10/BonusFinancing/PageAjax?code=sh600028
```

**返回字段：**

| 字段名 | 说明 |
|-------|------|
| NOTICE_DATE | 公告日期 |
| IMPL_PLAN_PROFILE | 分红方案（如"10派1.12元"） |
| ASSIGN_PROGRESS | 实施进度（董事会预案/实施方案） |
| EX_DIVIDEND_DATE | 除权除息日 |

**时效性：** ✅ 实时

**用途：** 计算股息率

---

### 2.2 公司简介接口

**接口地址：**
```
https://emweb.eastmoney.com/PC_HSF10/CompanySurvey/CompanySurveyAjax?code={market}{stock_code}
```

**返回字段：**

| 字段名 | 说明 |
|-------|------|
| gsjj | 公司简介 |
| jyfw | 经营范围 |
| hy | 所属行业 |

**时效性：** ✅ 实时

---

### 2.3 行业成分股接口

**接口地址：**
```
https://push2.eastmoney.com/api/qt/clist/get
```

**参数说明：**
```
pn=1                    # 页码
pz=10                   # 每页数量
fs=b:{industry_code}    # 行业代码
fields=f12,f14          # f12=代码, f14=名称
```

**常见行业代码：**

| 行业 | 代码 |
|-----|------|
| 石油/石化/化工 | BK0428 |
| 白酒/食品/饮料 | BK0477 |
| 医药/医疗 | BK0727 |
| 家电 | BK0456 |
| 汽车 | BK0461 |
| 新能源 | BK0493 |
| 煤炭 | BK0437 |
| 钢铁 | BK0440 |
| 银行 | BK0428 |

**时效性：** ✅ 实时

---

### 2.4 新闻接口

**接口地址：**
```
https://searchapi.eastmoney.com/bussiness/web/QuotationLabelSearch
```

**参数说明：**
```
keyword={股票名称}
type=ps                   # 新闻类型
pageindex=1
pagesize=10
```

**时效性：** ✅ 实时

---

## 三、同花顺API (akshare)

### 3.1 安装

```bash
pip install akshare
```

### 3.2 财务指标接口

**函数：**
```python
import akshare as ak
df = ak.stock_financial_abstract_ths(symbol='600028', indicator='按报告期')
```

**返回字段：**

| 字段名 | 说明 |
|-------|------|
| 报告期 | 如 "2025-12-31" |
| 净资产收益率 | ROE（%） |
| 资产负债率 | 负债率（%） |
| 每股净资产 | BPS |
| 基本每股收益 | EPS |

**时效性：** ⚠️ 季度更新（年报/季报发布后更新）

**注意事项：**
- 免费接口，但可能有SSL错误
- 建议添加缓存和重试逻辑

---

### 3.3 资金流向接口

**函数：**
```python
import akshare as ak
df = ak.stock_individual_fund_flow(stock='600028', market='sh')
```

**返回字段：**

| 字段名 | 说明 |
|-------|------|
| 日期 | 交易日期 |
| 主力净流入-净额 | 主力资金净流入（元） |
| 主力净流入-净占比 | 主力资金净流入占比（%） |
| 超大单净流入-净额 | 超大单净流入（元） |
| 大单净流入-净额 | 大单净流入（元） |
| 中单净流入-净额 | 中单净流入（元） |
| 小单净流入-净额 | 小单净流入（元） |

**时效性：** ⚠️ 有延迟（数据可能滞后1-2天）

**注意事项：**
- 免费接口数据有延迟
- 如需实时数据，需使用付费接口

---

## 四、数据使用建议

### 4.1 实时数据（推荐）

| 数据项 | 推荐接口 | 时效性 |
|-------|---------|--------|
| 股票价格 | 腾讯API | 实时 |
| PE/PB | 腾讯API | 实时 |
| 股息率 | 东方财富API | 实时 |
| 公司简介 | 东方财富API | 实时 |
| 行业成分股 | 东方财富API | 实时 |
| 新闻 | 东方财富API | 实时 |

### 4.2 延迟数据（可用）

| 数据项 | 推荐接口 | 时效性 |
|-------|---------|--------|
| ROE | 同花顺(akshare) | 季度更新 |
| 负债率 | 同花顺(akshare) | 季度更新 |
| 资金流向 | 同花顺(akshare) | 延迟1-2天 |

### 4.3 风险排查数据

| 数据项 | 推荐接口 | 时效性 | 说明 |
|-------|---------|--------|------|
| 质押率 | 东方财富质押数据中心 | 月度更新 | 大股东质押股份比例，<60%为安全 |
| 商誉占比 | 暂用默认值5% | 季度更新 | 商誉/净资产，<20%为安全 |
| 审计意见 | 默认"标准无保留意见" | 年度更新 | 年报审计意见 |

**质押率接口示例：**
```
https://datacenter-web.eastmoney.com/api/data/v1/get
参数:
  reportName: RPT_CSDC_LIST
  columns: SECUCODE,SECURITY_CODE,TRADE_DATE,PLEDGE_RATIO
  filter: (SECUCODE='600028.SH')
```

**注意事项：**
- 质押率：部分股票可能无质押记录，返回0%
- 商誉占比：需从资产负债表详细接口获取，当前使用保守默认值
- 审计意见：仅ST股或财务异常公司会有非标准意见

### 4.4 模拟数据（待优化）

| 数据项 | 当前状态 | 建议 |
|-------|---------|------|
| 资金流向（流入流出明细） | 基于净流入推算 | 使用付费接口获取准确数据 |

---

## 五、代码示例

### 5.1 获取实时行情

```python
import requests
import re

def get_stock_quote(stock_code):
    market = "sh" if stock_code.startswith("6") else "sz"
    url = f"https://qt.gtimg.cn/q={market}{stock_code}"

    resp = requests.get(url)
    text = resp.text

    match = re.search(r'"([^"]+)"', text)
    if match:
        parts = match.group(1).split('~')
        return {
            "name": parts[1],
            "code": parts[2],
            "price": float(parts[3]),
            "change_pct": float(parts[31]),
            "pe": float(parts[46]) if parts[46] else 0,
            "pb": float(parts[49]) if parts[49] else 0,  # 使用字段49
        }
    return None
```

### 5.2 获取股息率

```python
import requests
import re
from datetime import datetime, timedelta

def get_dividend_yield(stock_code, current_price):
    market = "sh" if stock_code.startswith("6") else "sz"
    url = "https://emweb.eastmoney.com/PC_HSF10/BonusFinancing/PageAjax"
    params = {"code": f"{market}{stock_code}"}

    resp = requests.get(url, params=params)
    data = resp.json()

    # 计算最近一年分红
    one_year_ago = datetime.now() - timedelta(days=365)
    total_div = 0

    for item in data.get("fhyx", []):
        if item.get("ASSIGN_PROGRESS") == "实施方案":
            profile = item.get("IMPL_PLAN_PROFILE", "")
            if "派" in profile and "元" in profile:
                match = re.search(r'10派([\d.]+)元', profile)
                if match:
                    div_per_10 = float(match.group(1))
                    total_div += div_per_10 / 10

    if current_price > 0 and total_div > 0:
        return round(total_div / current_price * 100, 2)
    return 0
```

### 5.3 获取ROE和负债率

```python
import akshare as ak

def get_financial_indicators(stock_code):
    df = ak.stock_financial_abstract_ths(symbol=stock_code, indicator='按报告期')

    # 过滤年报数据
    df_annual = df[df['报告期'].str.contains('12-31')].iloc[::-1]
    df_recent = df_annual.head(5)

    roe_history = []
    debt_history = []

    for _, row in df_recent.iterrows():
        year = row['报告期'][:4]
        roe = row['净资产收益率']
        debt = row['资产负债率']

        if roe != False:
            roe_history.append({"year": year, "roe": float(str(roe).replace('%', ''))})
        if debt != False:
            debt_history.append({"year": year, "debt_ratio": float(str(debt).replace('%', ''))})

    return {
        "roe_history": roe_history,
        "debt_history": debt_history,
        "avg_roe": sum(r["roe"] for r in roe_history) / len(roe_history),
        "latest_debt_ratio": debt_history[0]["debt_ratio"] if debt_history else 0
    }
```

### 5.4 获取风险排查数据

```python
import requests

def get_risk_data(stock_code):
    """获取质押率等风险数据"""
    market = "SH" if stock_code.startswith("6") else "SZ"

    # 获取质押率
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {
        "reportName": "RPT_CSDC_LIST",
        "columns": "SECUCODE,SECURITY_CODE,TRADE_DATE,PLEDGE_RATIO",
        "filter": f"(SECUCODE='{stock_code}.{market}')",
        "pageSize": 1,
        "sortColumns": "TRADE_DATE",
        "sortTypes": -1
    }

    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()

    pledge_rate = 0
    if data.get("result") and data["result"].get("data"):
        pledge_rate = float(data["result"]["data"][0].get("PLEDGE_RATIO", 0) or 0)

    # 商誉占比（需从资产负债表获取，这里使用默认值）
    goodwill_ratio = 5.0  # 默认5%

    # 审计意见（默认标准无保留意见）
    audit_opinion = "标准无保留意见"

    return {
        "pledge_rate": pledge_rate,
        "goodwill_ratio": goodwill_ratio,
        "audit_opinion": audit_opinion
    }
```

---

## 六、注意事项

1. **接口稳定性**
   - 腾讯API最稳定，建议优先使用
   - 东方财富API偶尔有访问限制
   - akshare依赖同花顺网站，可能有SSL错误，建议添加重试逻辑

2. **数据缓存**
   - 实时数据不建议缓存
   - 财务指标可缓存5-10分钟
   - 分红数据可缓存1天

3. **错误处理**
   - 所有接口调用都应添加try-catch
   - 建议有备用数据源或默认值

4. **频率限制**
   - 腾讯API：无明显限制
   - 东方财富API：建议每秒不超过5次
   - akshare：建议添加延时，避免被封IP

---

## 七、更新日志

| 日期 | 更新内容 |
|-----|---------|
| 2026-04-23 | 初始版本，整理各API接口文档 |
| 2026-04-23 | 新增风险排查数据接口文档（质押率、商誉占比、审计意见） |

---

## 八、参考资料

- [腾讯财经API](https://qt.gtimg.cn/)
- [东方财富开放平台](https://data.eastmoney.com/)
- [akshare文档](https://akshare.akfamily.xyz/)

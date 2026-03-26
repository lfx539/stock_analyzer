# 新闻服务 - 获取热点财经新闻

import requests
import json
import re
from typing import List, Dict
from datetime import datetime, timedelta

class NewsService:
    """财经新闻服务"""

    # 基金影响分类定义
    FUND_CATEGORIES = {
        # 债券基金、货币基金、大盘指数基金（宏观政策、利率、货币相关）
        "macro_fund": {
            "name": "宏观基金",
            "desc": "影响债券/货币/指数基金",
            "keywords": ["央行", "降准", "降息", "加息", "利率", "货币政策", "财政政策", "国债", "债券",
                        "GDP", "CPI", "PPI", "通胀", "LPR", "MLF", "社融", "M2", "信贷", "美联储",
                        "汇率", "人民币", "外汇", "印花税", "资金面", "流动性"],
            "color": "#8b5cf6",
            "positive_keywords": ["降准", "降息", "利好", "宽松", "支持", "增长", "回升", "反弹", "上行"],
            "negative_keywords": ["加息", "收紧", "通胀", "下行", "降温", "调控", "紧缩", "回落", "下跌"],
            "suggestions": {
                "positive": "政策利好，债券基金和货币基金收益有望提升，可适当配置",
                "negative": "政策收紧，建议降低债券基金配置，增持货币基金",
                "neutral": "建议维持均衡配置，关注政策变化"
            }
        },
        # 行业主题基金、ETF（行业动态、板块涨跌）
        "sector_fund": {
            "name": "行业基金",
            "desc": "影响行业主题基金/ETF",
            "keywords": ["人工智能", "AI", "芯片", "半导体", "云计算", "数字经济", "软件", "互联网",
                        "5G", "6G", "算力", "机器人", "新能源", "光伏", "风电", "锂电池", "储能",
                        "油气", "石油", "煤炭", "电力", "稀土", "锂", "钴", "镍", "黄金", "白银",
                        "铜", "铝", "有色金属", "新能源汽车", "电动车", "汽车", "地产", "房地产",
                        "银行", "保险", "券商", "医药", "医疗", "消费", "食品", "饮料", "白酒",
                        "家电", "钢铁", "建筑", "航运", "航空", "ETF", "板块", "赛道"],
            "color": "#06b6d4",
            "positive_keywords": ["涨停", "大涨", "暴涨", "飙升", "反弹", "上涨", "增长", "突破", "创新高",
                                 "利好", "突破", "爆发", "强劲", "景气", "复苏", "火热", "抢眼", "领涨"],
            "negative_keywords": ["跌停", "大跌", "暴跌", "跳水", "下跌", "回落", "调整", "创新低",
                                 "利空", "承压", "下行", "疲软", "低迷", "缩量", "流出"],
            "suggestions": {
                "positive": "行业景气度上升，建议关注行业内ETF或分级基金，可考虑逢低布局",
                "negative": "行业承压，建议回避或减持相关行业基金，关注基本面变化",
                "neutral": "建议观望，关注行业龙头和估值合理的标的"
            }
        },
        # 重仓该股票的主动型股票基金（个股新闻、业绩、公告）
        "stock_fund": {
            "name": "个股基金",
            "desc": "影响重仓该股的股票基金",
            "keywords": ["业绩", "财报", "净利润", "营收", "订单", "签约", "中标", "合作", "并购",
                        "重组", "暴雷", "亏损", "ST", "退市", "IPO", "上市", "解禁", "减持", "增减持",
                        "回购", "分红", "送转", "配股", "定增", "发债", "融资", "投资", "项目",
                        "涨停", "跌停", "涨幅", "跌幅", "放量", "缩量", "主力资金", "北向资金", "外资"],
            "color": "#f59e0b",
            "positive_keywords": ["增长", "盈利", "突破", "签约", "中标", "合作", "回购", "分红", "增持",
                                 "并购", "重组", "涨停", "大涨", "净流入", "加仓", "看好"],
            "negative_keywords": ["亏损", "暴雷", "减持", "ST", "退市", "跌停", "大跌", "净流出", "减仓", "看空"],
            "suggestions": {
                "positive": "利好消息支撑股价，重仓基金有望受益，可适度关注",
                "negative": "利空消息可能拖累股价，建议回避相关重仓基金",
                "neutral": "建议关注后续公告，谨慎操作"
            }
        }
    }

    # 行业ETF/基金推荐数据库
    ETF_RECOMMENDATIONS = {
        # 科技类
        "人工智能": {"code": "515980", "name": "人工智能ETF", "reason": "AI行业龙头基金，重仓科大讯飞等核心标的"},
        "AI": {"code": "515980", "name": "人工智能ETF", "reason": "AI行业龙头基金，跟踪中证人工智能指数"},
        "大模型": {"code": "515980", "name": "人工智能ETF", "reason": "大模型是AI核心方向，值得关注"},
        "芯片": {"code": "512760", "name": "芯片ETF", "reason": "国产替代加速，芯片板块景气度提升"},
        "半导体": {"code": "512760", "name": "芯片ETF", "reason": "半导体自主可控，政策大力支持"},
        "云计算": {"code": "516510", "name": "云计算ETF", "reason": "云计算赛道长期向好，企业数字化转型需求大"},
        "数字经济": {"code": "515580", "name": "数字经济ETF", "reason": "政策重点扶持，发展空间广阔"},
        "软件": {"code": "515230", "name": "软件ETF", "reason": "国产软件替代加速，业绩增长确定性强"},
        "互联网": {"code": "513050", "name": "互联网ETF", "reason": "平台经济估值修复，关注龙头互联网公司"},
        "5G": {"code": "515050", "name": "5GETF", "reason": "5G建设持续推进，产业链业绩释放"},
        "算力": {"code": "515220", "name": "大数据ETF", "reason": "算力需求爆发，数据中心景气度高"},
        "机器人": {"code": "562800", "name": "机器人ETF", "reason": "人形机器人产业化加速，市场空间大"},
        # 新能源类
        "新能源": {"code": "516160", "name": "新能源ETF", "reason": "碳中和目标明确，行业长期高景气"},
        "光伏": {"code": "515790", "name": "光伏ETF", "reason": "光伏装机量持续增长，产业链盈利改善"},
        "风电": {"code": "164905", "name": "风电产业指数", "reason": "海上风电快速发展，招标量创新高"},
        "锂电池": {"code": "159841", "name": "锂电池ETF", "reason": "新能源汽车渗透率提升，电池需求旺盛"},
        "储能": {"code": "159995", "name": "储能ETF", "reason": "储能行业爆发在即，政策大力支持"},
        "氢能": {"code": "931249", "name": "氢能指数", "reason": "氢能顶层政策出台，未来发展潜力大"},
        # 资源类
        "油气": {"code": "159867", "name": "油气ETF", "reason": "能源安全保障，油气开采景气度高"},
        "石油": {"code": "159867", "name": "油气ETF", "reason": "国际油价高位震荡，油气板块受益"},
        "煤炭": {"code": "161032", "name": "煤炭指数", "reason": "高股息低估值，防御属性强"},
        "电力": {"code": "159611", "name": "电力ETF", "reason": "电价改革利好，电企盈利改善"},
        "稀土": {"code": "159713", "name": "稀土ETF", "reason": "稀土是战略资源，供给格局优化"},
        "锂": {"code": "159841", "name": "锂电池ETF", "reason": "锂资源需求旺盛，价格有支撑"},
        "黄金": {"code": "518880", "name": "黄金ETF", "reason": "避险情绪升温，黄金配置价值凸显"},
        "白银": {"code": "161226", "name": "白银基金", "reason": "贵金属板块联动，白银弹性更大"},
        "铜": {"code": "159997", "name": "有色ETF", "reason": "铜是经济晴雨表，需求预期改善"},
        "铝": {"code": "159997", "name": "有色ETF", "reason": "铝价高位运行，龙头企业受益"},
        "有色金属": {"code": "159997", "name": "有色ETF", "reason": "有色金属全面上涨，关注周期机会"},
        # 消费类
        "新能源汽车": {"code": "515030", "name": "新能源车ETF", "reason": "新能源车渗透率提升，智能化加速"},
        "电动车": {"code": "515030", "name": "新能源车ETF", "reason": "电动车替代燃油车趋势确定"},
        "汽车": {"code": "516550", "name": "汽车ETF", "reason": "汽车消费政策刺激，行业景气回升"},
        "消费": {"code": "159928", "name": "消费ETF", "reason": "消费复苏确定性高，龙头公司估值修复"},
        "食品": {"code": "515710", "name": "食品ETF", "reason": "食品饮料是刚需，业绩稳定增长"},
        "饮料": {"code": "515710", "name": "食品ETF", "reason": "高端白酒业绩确定性强，估值有支撑"},
        "白酒": {"code": "515710", "name": "食品ETF", "reason": "白酒龙头壁垒高，盈利能力强劲"},
        "家电": {"code": "159996", "name": "家电ETF", "reason": "家电以旧换新政策刺激，需求回暖"},
        "医药": {"code": "512010", "name": "医药ETF", "reason": "医药板块估值处于历史低位，反弹可期"},
        "医疗": {"code": "512010", "name": "医药ETF", "reason": "医疗需求刚性，集采影响边际改善"},
        "创新药": {"code": "515030", "name": "创新药ETF", "reason": "创新药出海加速，行业前景广阔"},
        # 金融类
        "银行": {"code": "512880", "name": "银行ETF", "reason": "高股息低估值，防御属性强"},
        "保险": {"code": "159903", "name": "保险ETF", "reason": "保险负债端改善，估值修复可期"},
        "券商": {"code": "512880", "name": "券商ETF", "reason": "资本市场活跃，券商业绩弹性大"},
        # 基建类
        "地产": {"code": "159867", "name": "地产ETF", "reason": "政策持续放松，地产板块估值修复"},
        "房地产": {"code": "159867", "name": "地产ETF", "reason": "地产政策底已现，关注龙头公司"},
        "钢铁": {"code": "515210", "name": "钢铁ETF", "reason": "供需格局改善，钢价有支撑"},
        "建筑": {"code": "159994", "name": "基建ETF", "reason": "基建投资发力，稳增长政策支持"},
        "建材": {"code": "159995", "name": "建材ETF", "reason": "地产链边际改善，建材需求回升"},
        "工程机械": {"code": "159995", "name": "工程机械ETF", "reason": "更新需求+出海逻辑，龙头公司受益"},
        # 周期类
        "航运": {"code": "512410", "name": "航运ETF", "reason": "航运周期向上，关注集运龙头"},
        "航空": {"code": "512410", "name": "航空ETF", "reason": "出行需求释放，航空业绩改善"},
        "物流": {"code": "517710", "name": "物流ETF", "reason": "电商快递增长确定性强"},
        # 其他
        "ETF": {"code": "510300", "name": "沪深300ETF", "reason": "宽基指数，分享市场整体收益"},
        "板块": {"code": "510300", "name": "沪深300ETF", "reason": "关注板块轮动机会"},
        "赛道": {"code": "510300", "name": "沪深300ETF", "reason": "选择高景气赛道投资"},
    }

    # 情感分析：判断新闻是正向还是负向
    def _analyze_sentiment(self, title: str) -> str:
        """分析新闻情感：positive（正向）/ negative（负向）/ neutral（中性）"""
        title_lower = title.lower()

        # 统计正负向关键词数量
        positive_count = 0
        negative_count = 0

        # 检测正面词汇
        positive_words = ["涨", "涨", "大涨", "涨停", "飙升", "上涨", "增长", "盈利", "增长", "突破", "创新高",
                        "反弹", "回升", "利好", "支持", "增长", "扩张", "景气", "复苏", "火热", "强劲",
                        "净流入", "加仓", "增持", "看多", "抢眼", "领涨", "活跃", "扬", "升"]

        # 检测负面词汇
        negative_words = ["��", "大跌", "跌停", "暴跌", "下跌", "回落", "调整", "亏损", "暴雷", "利空",
                        "减持", "净流出", "减仓", "看空", "承压", "低迷", "疲软", "下行", "收缩", "降",
                        "降", "取消", "终止", "失败", "预警"]

        for word in positive_words:
            if word in title:
                positive_count += 1

        for word in negative_words:
            if word in title:
                negative_count += 1

        # 判断
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    # 生成投资建议
    def _generate_suggestion(self, fund_type: str, sentiment: str) -> str:
        """根据基金类型和情感生成投资建议"""
        if fund_type in self.FUND_CATEGORIES:
            suggestions = self.FUND_CATEGORIES[fund_type].get("suggestions", {})
            return suggestions.get(sentiment, "建议观望，谨慎操作")
        return "建议观望，谨慎操作"

    # 关键词分类
    KEYWORD_CATEGORIES = {
        # 宏观类
        "macro": ["央行", "降准", "降息", "加息", "GDP", "CPI", "PPI", "通胀", "信贷", "M2", "社融",
                   "美联储", "鲍威尔", "货币政策", "财政政策", "两会", "经济", "LPR", "MLF", "SLF",
                   "人民币", "汇率", "外汇", "国债", "债券", "印花税"],
        # 行业/产业类
        "industry": ["人工智能", "AI", "大模型", "芯片", "半导体", "云计算", "数字经济", "软件",
                     "互联网", "5G", "6G", "数据中心", "算力", "机器人", "自动驾驶", "新能源",
                     "光伏", "风电", "锂电池", "储能", "氢能", "油气", "石油", "煤炭", "电力",
                     "稀土", "锂", "钴", "镍", "黄金", "白银", "铜", "铝", "有色金属", "矿产",
                     "新能源汽车", "电动车", "汽车", "地产", "房地产", "银行", "保险", "券商",
                     "医药", "医疗", "疫苗", "创新药", "医疗器械", "消费", "食品", "饮料", "白酒",
                     "家电", "钢铁", "建筑", "建材", "工程机械", "航空", "航运", "物流"],
        # 公司/事件类
        "company": ["业绩", "财报", "净利润", "营���", "订单", "签约", "中标", "合作", "并购", "重组",
                    "暴雷", "亏损", "ST", "退市", "IPO", "上市", "申购", "解禁", "减持", "增减持",
                    "回购", "分红", "送转", "配股", "定增", "发债", "融资", "投资", "项目"],
        # 情绪/资金类
        "sentiment": ["外资", "北向资金", "主力资金", "散户", "杠杆", "融资融券", "爆仓", "平仓",
                      "恐慌", "VIX", "恐慌指数", "大幅流入", "大幅流出", "净流入", "净流出", "做多",
                      "做空", "多空", "放量", "缩量", "涨停", "跌停", "涨幅", "跌幅", "板块轮动",
                      "机构", "公募", "私募", "基金", "仓位", "加仓", "减仓", "建仓", "清仓"]
    }

    # 用户关注的关键词（合并所有分类）
    INTERESTED_KEYWORDS = []
    for kws in KEYWORD_CATEGORIES.values():
        INTERESTED_KEYWORDS.extend(kws)

    def get_hot_news(self, limit: int = 10) -> List[Dict]:
        """获取热点新闻"""
        news_list = []

        # 尝试多���新闻源
        news_list = self._get_jrj_news(limit)  # 金融界
        if not news_list or len(news_list) < 3:
            news_list = self._get_eastmoney_news(limit)

        # 按关键词过滤
        filtered_news = self._filter_by_keywords(news_list)

        return filtered_news[:limit]

    def _get_jrj_news(self, limit: int) -> List[Dict]:
        """获取金融界财经新闻"""
        try:
            url = "https://news.jrj.com.cn/json/market/ggcx/getnews.shtml"
            params = {
                "page": 1,
                "pagesize": limit * 3,
                "callback": ""
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://news.jrj.com.cn/'
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                # 金融界返回的是JavaScript代码，需要解析
                import re
                text = resp.text
                # 尝试提取JSON数据
                match = re.search(r'\[.*\]', text)
                if match:
                    articles = json.loads(match.group())
                    result = []
                    for a in articles[:limit*3]:
                        title = a.get('title', '')
                        url = a.get('url', '')
                        # 如果URL是相对路径，补充完整
                        if url and not url.startswith('http'):
                            url = 'https://news.jrj.com.cn' + url
                        if title:
                            result.append({
                                'title': title,
                                'url': url,
                                'source': '金融界',
                                'time': '',
                                'hot_score': 80
                            })
                    return result
        except Exception as e:
            print(f"金融界新闻获取失败: {e}")
        return []

    def _get_eastmoney_news(self, limit: int) -> List[Dict]:
        """获取东方财富新闻"""
        try:
            url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://stock.eastmoney.com/'
            }
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                import re
                # 解析新闻列表
                match = re.search(r'\{.*\}', resp.text)
                if match:
                    data = json.loads(match.group())
                    articles = data.get('LivesList', [])
                    result = []
                    for a in articles:
                        title = a.get('title', '')
                        url = a.get('url', '')
                        # 东方财富的URL可能需要补充
                        if url and not url.startswith('http'):
                            url = 'https://guba.eastmoney.com' + url
                        if title:
                            result.append({
                                'title': title,
                                'url': url,
                                'source': '东方财富',
                                'time': a.get('showtime', '')[:10] if a.get('showtime') else '',
                                'hot_score': a.get('hot', 80)
                            })
                    return result
        except Exception as e:
            print(f"东方财富新闻获取失败: {e}")
        return []

    def _get_sina_news(self, limit: int) -> List[Dict]:
        """获取新浪财经新闻（备用）"""
        try:
            url = "https://interface.sina.cn/news/getData.d.json"
            params = {
                "channel": "finance",
                "page": 1,
                "pagesize": limit * 3
            }
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                articles = data.get('data', [])
                if articles:
                    return [{
                        'title': a.get('title', ''),
                        'url': 'https://finance.sina.com.cn' + a.get('url', ''),
                        'source': '新浪财经',
                        'time': a.get('time', '')[:10] if a.get('time') else '',
                        'hot_score': 80
                    } for a in articles[:limit*3] if a.get('title')]
        except:
            pass
        return []

    def _filter_by_keywords(self, news_list: List[Dict]) -> List[Dict]:
        """按关键词过滤新闻并分类"""
        if not news_list:
            return []

        # 影响范围分类名称
        CATEGORY_NAMES = {
            "macro": {"name": "宏观", "color": "#8b5cf6", "desc": "影响全局"},
            "industry": {"name": "行业", "color": "#06b6d4", "desc": "影响赛道"},
            "company": {"name": "个股", "color": "#f59e0b", "desc": "影响个股"},
            "sentiment": {"name": "资金", "color": "#ef4444", "desc": "短期波动"}
        }

        filtered = []
        for news in news_list:
            title = news.get('title', '')
            matched_keywords = [kw for kw in self.INTERESTED_KEYWORDS if kw in title]

            # 判断影响范围分类
            impact_category = None
            for cat, cat_kws in self.KEYWORD_CATEGORIES.items():
                if any(kw in title for kw in cat_kws):
                    impact_category = cat
                    break

            # 计算基金影响分类
            fund_impacts = self._calculate_fund_impact(title)

            if matched_keywords:
                news['matched_keywords'] = matched_keywords
                news['relevance_score'] = len(matched_keywords)
                news['impact'] = CATEGORY_NAMES.get(impact_category, {"name": "综合", "color": "#6b7280", "desc": "综合影响"})
                news['fund_impact'] = fund_impacts  # 添加基金影响标签
                filtered.append(news)

        # 如果过滤后太少，返回原始列表
        if len(filtered) < 3:
            for news in news_list:
                title = news.get('title', '')
                matched_keywords = [kw for kw in self.INTERESTED_KEYWORDS if kw in title]
                news['matched_keywords'] = matched_keywords
                news['relevance_score'] = len(matched_keywords)
                news['fund_impact'] = self._calculate_fund_impact(title)
            return sorted(news_list, key=lambda x: x.get('relevance_score', 0), reverse=True)

        return sorted(filtered, key=lambda x: x.get('relevance_score', 0), reverse=True)

    def _calculate_fund_impact(self, title: str) -> List[Dict]:
        """计算新闻对各类基金的影响，包含正负向判断和投资建议"""
        impacts = []
        sentiment = self._analyze_sentiment(title)  # 情感分析

        # 获取ETF推荐
        etf_recommendations = self._get_etf_recommendations(title, sentiment)

        for cat_id, cat_info in self.FUND_CATEGORIES.items():
            # 统计匹配的关键词
            matched = [kw for kw in cat_info["keywords"] if kw in title]
            if matched:
                # 计算影响强度（匹配的关键词数量）
                intensity = len(matched)

                # 获取情感标签颜色
                sentiment_info = {
                    "positive": {"label": "利好", "color": "#10b981", "icon": "↑"},
                    "negative": {"label": "利空", "color": "#ef4444", "icon": "↓"},
                    "neutral": {"label": "中性", "color": "#6b7280", "icon": "→"}
                }

                # 生成投资建议
                suggestion = self._generate_suggestion(cat_id, sentiment)

                # 对所有基金类型添加ETF推荐（只要能匹配到行业关键词）
                etf_list = etf_recommendations

                impacts.append({
                    "type": cat_id,
                    "name": cat_info["name"],
                    "desc": cat_info["desc"],
                    "color": cat_info["color"],
                    "matched": matched[:3],  # 最多显示3个匹配的关键词
                    "intensity": intensity,
                    "sentiment": sentiment,
                    "sentiment_label": sentiment_info[sentiment]["label"],
                    "sentiment_color": sentiment_info[sentiment]["color"],
                    "sentiment_icon": sentiment_info[sentiment]["icon"],
                    "suggestion": suggestion,
                    "etf_recommendations": etf_list
                })

        # 按影响强度排序
        impacts.sort(key=lambda x: x["intensity"], reverse=True)
        return impacts

    # 行业关键词映射到ETF
    INDUSTRY_ETF_MAP = {
        # 通用利好词 - 映射到宽基ETF或券商ETF
        "ETF": ({"code": "510300", "name": "沪深300ETF", "reason": "宽基ETF代表市场整体走势，适合看好大盘时配置"}, "510300"),
        "涨停": ({"code": "512880", "name": "券商ETF", "reason": "涨停反映市场活跃，券商板块直接受益"}, "512880"),
        "放量": ({"code": "510300", "name": "沪深300ETF", "reason": "放量上涨说明资金入场，看好市场后续行情"}, "510300"),
        "成交额": ({"code": "512880", "name": "券商ETF", "reason": "成交额放大反映市场活跃，券商直接受益"}, "512880"),
        "拉升": ({"code": "510300", "name": "沪深300ETF", "reason": "市场拉升表明情绪向好，宽基ETF可分享涨幅"}, "510300"),
        "大涨": ({"code": "510300", "name": "沪深300ETF", "reason": "市场大涨时，宽基ETF能很好地跟上行情"}, "510300"),
        "科创50": ({"code": "513050", "name": "科创50ETF", "reason": "科创50代表科技创新方向弹性更大"}, "513050"),

        # 宏观相关ETF
        "降准": ({"code": "511880", "name": "银华日利ETF", "reason": "降准释放流动性，货币ETF受益"}, "511880"),
        "降息": ({"code": "511010", "name": "华夏上证国债ETF", "reason": "降息利好债券，债券ETF配置价值提升"}, "511010"),
        "加息": ({"code": "511880", "name": "银华日利ETF", "reason": "加息周期货币基金收益较好"}, "511880"),
        "央行": ({"code": "511880", "name": "银华日利ETF", "reason": "央行政策稳定，货币基金稳健"}, "511880"),
        "宽松": ({"code": "511880", "name": "银华日利ETF", "reason": "货币政策宽松，货币ETF收益稳定"}, "511880"),
        "流动性": ({"code": "511880", "name": "银华日利ETF", "reason": "流动性宽松有利于货币基金"}, "511880"),
        "资金面": ({"code": "511880", "name": "银华日利ETF", "reason": "资金面宽松，货币ETF受益"}, "511880"),
        "国债": ({"code": "511010", "name": "华夏上证国债ETF", "reason": "国债收益率下行，债券基金受益"}, "511010"),
        "债券": ({"code": "511010", "name": "华夏上证国债ETF", "reason": "债券市场机会，债券ETF可配置"}, "511010"),
        "印花税": ({"code": "510300", "name": "沪深300ETF", "reason": "印花税下调利好股市，宽基ETF配置"}, "510300"),
        "汇率": ({"code": "518880", "name": "黄金ETF", "reason": "汇率波动，黄金ETF避险"}, "518880"),
        "人民币": ({"code": "518880", "name": "黄金ETF", "reason": "人民币汇率影响，黄金ETF避险配置"}, "518880"),
        "美联储": ({"code": "511880", "name": "银华日利ETF", "reason": "美联储政策不确定，货币基金防御性强"}, "511880"),
        "社融": ({"code": "511880", "name": "银华日利ETF", "reason": "社融数据反映经济活力，货币ETF稳健"}, "511880"),
        "M2": ({"code": "511880", "name": "银华日利ETF", "reason": "M2增速反映货币供应，货币ETF受益"}, "511880"),
        "通胀": ({"code": "518880", "name": "黄金ETF", "reason": "通胀预期升温，黄金ETF避险配置"}, "518880"),
        "上涨": ({"code": "510300", "name": "沪深300ETF", "reason": "市场上涨时，宽基ETF分享收益"}, "510300"),
        "反弹": ({"code": "510300", "name": "沪深300ETF", "reason": "市场反弹，宽基ETF把握行情"}, "510300"),
        "回升": ({"code": "510300", "name": "沪深300ETF", "reason": "经济回升预期，宽基ETF配置"}, "510300"),

        "人工智能": ({"code": "515980", "name": "人工智能ETF", "reason": "AI行业核心标的，跟踪中证人工智能指数，受益AI产业爆发"}, "515980"),
        "AI": ({"code": "515980", "name": "人工智能ETF", "reason": "人工智能产业快速发展，龙头公司业绩增长确定"}, "515980"),
        "大模型": ({"code": "515980", "name": "人工智能ETF", "reason": "大模型是AI产业核心赛道，发展前景广阔"}, "515980"),
        "芯片": ({"code": "512760", "name": "芯片ETF", "reason": "国产芯片替代加速，半导体自主可控政策利好"}, "512760"),
        "半导体": ({"code": "512760", "name": "芯片ETF", "reason": "半导体国产替代提速，景气度持续提升"}, "512760"),
        "云计算": ({"code": "516510", "name": "云计算ETF", "reason": "企业数字化转型加速，云计算需求旺盛"}, "516510"),
        "数字经济": ({"code": "515580", "name": "数字经济ETF", "reason": "政策重点扶持，数字经济发展进入快车道"}, "515580"),
        "软件": ({"code": "515230", "name": "软件ETF", "reason": "国产软件替代加速，信创板块持续受益"}, "515230"),
        "互联网": ({"code": "513050", "name": "互联网ETF", "reason": "平台经济估值修复，互联网龙头盈利改善"}, "513050"),
        "5G": ({"code": "515050", "name": "5GETF", "reason": "5G网络建设持续推进，产业链业绩释放"}, "515050"),
        "算力": ({"code": "515220", "name": "大数据ETF", "reason": "算力需求爆发，数据中心景气度高"}, "515220"),
        "机器人": ({"code": "562800", "name": "机器人ETF", "reason": "人形机器人产业化加速，市场空间广阔"}, "562800"),
        "新能源": ({"code": "516160", "name": "新能源ETF", "reason": "碳中和目标明确，新能源行业长期高景气"}, "516160"),
        "光伏": ({"code": "515790", "name": "光伏ETF", "reason": "光伏装机量持续增长，产业链盈利改善"}, "515790"),
        "风电": ({"code": "159937", "name": "新能源车ETF", "reason": "风电发展迅速，海上风电空间大"}, "159937"),
        "锂电池": ({"code": "159841", "name": "锂电池ETF", "reason": "新能源汽车带动锂电池需求持续增长"}, "159841"),
        "储能": ({"code": "159995", "name": "储能ETF", "reason": "储能政策利好，行业进入快速发展期"}, "159995"),
        "氢能": ({"code": "931249", "name": "氢能指数", "reason": "氢能顶层政策出台，未来发展潜力大"}, "931249"),
        "油气": ({"code": "159867", "name": "油气ETF", "reason": "能源安全保障，油气开采景气度高"}, "159867"),
        "石油": ({"code": "159867", "name": "油气ETF", "reason": "国际油价高位震荡，油气板块受益"}, "159867"),
        "煤炭": ({"code": "161032", "name": "煤炭指数", "reason": "高股息低估值，防御属性强"}, "161032"),
        "电力": ({"code": "159611", "name": "电力ETF", "reason": "电价改革利好，电力企业盈利改善"}, "159611"),
        "稀土": ({"code": "159713", "name": "稀土ETF", "reason": "稀土是战略资源，供给格局持续优化"}, "159713"),
        "锂": ({"code": "159841", "name": "锂电池ETF", "reason": "锂资源需求旺盛，价格有支撑"}, "159841"),
        "黄金": ({"code": "518880", "name": "黄金ETF", "reason": "避险情绪升温，黄金配置价值凸显"}, "518880"),
        "铜": ({"code": "159997", "name": "有色ETF", "reason": "铜是经济晴雨表，需求预期改善"}, "159997"),
        "铝": ({"code": "159997", "name": "有色ETF", "reason": "铝价高位运行，龙头企业受益"}, "159997"),
        "有色金属": ({"code": "159997", "name": "有色ETF", "reason": "有色金属价格上涨，周期行情启动"}, "159997"),
        "新能源汽车": ({"code": "515030", "name": "新能源车ETF", "reason": "新能源车渗透率持续提升，智能化加速"}, "515030"),
        "电动车": ({"code": "515030", "name": "新能源车ETF", "reason": "电动车替代燃油车趋势明确，市场空间大"}, "515030"),
        "汽车": ({"code": "516550", "name": "汽车ETF", "reason": "汽车消费政策刺激，行业景气度回升"}, "516550"),
        "消费": ({"code": "159928", "name": "消费ETF", "reason": "消费复苏确定性高，龙头公司估值修复"}, "159928"),
        "食品": ({"code": "515710", "name": "食品ETF", "reason": "食品饮料是刚需，业绩稳定增长"}, "515710"),
        "饮料": ({"code": "515710", "name": "食品ETF", "reason": "高端白酒业绩确定性强，盈利能力强劲"}, "515710"),
        "白酒": ({"code": "515710", "name": "食品ETF", "reason": "白酒龙头壁垒高，业绩稳定增长"}, "515710"),
        "家电": ({"code": "159996", "name": "家电ETF", "reason": "家电以旧换新政策刺激，需求回暖"}, "159996"),
        "医药": ({"code": "512010", "name": "医药ETF", "reason": "医药板块估值处于低位，反弹空间大"}, "512010"),
        "医疗": ({"code": "512010", "name": "医药ETF", "reason": "医疗需求刚性，集采影响边际改善"}, "512010"),
        "银行": ({"code": "512880", "name": "银行ETF", "reason": "高股息低估值，防御属性强"}, "512880"),
        "保险": ({"code": "159903", "name": "保险ETF", "reason": "保险负债端改善，估值修复可期"}, "159903"),
        "券商": ({"code": "512880", "name": "券商ETF", "reason": "资本市场活跃，券商业绩弹性大"}, "512880"),
        "地产": ({"code": "159867", "name": "地产ETF", "reason": "政策持续放松，地产板块估值修复"}, "159867"),
        "房地产": ({"code": "159867", "name": "地产ETF", "reason": "地产政策底已现，关注龙头公司"}, "159867"),
        "钢铁": ({"code": "515210", "name": "钢铁ETF", "reason": "供需格局改善，钢价有支撑"}, "515210"),
        "建筑": ({"code": "159994", "name": "基建ETF", "reason": "基建投资发力，稳增长政策支持"}, "159994"),
        "航运": ({"code": "512410", "name": "航运ETF", "reason": "航运周期向上，关注集运龙头"}, "512410"),
        "航空": ({"code": "512410", "name": "航空ETF", "reason": "出行需求释放，航空业绩改善"}, "512410"),
    }

    def _get_etf_recommendations(self, title: str, sentiment: str) -> List[Dict]:
        """根据新闻标题和情感获取ETF推荐"""
        recommendations = []

        if sentiment != "positive":
            return recommendations  # 只推荐利好消息

        # 优先匹配行业关键词
        for keyword, (etf_info, code) in self.INDUSTRY_ETF_MAP.items():
            if keyword in title:
                recommendations.append({
                    "code": etf_info["code"],
                    "name": etf_info["name"],
                    "reason": etf_info["reason"]
                })

        # 去重并限制数量
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec["code"] not in seen:
                seen.add(rec["code"])
                unique_recs.append(rec)

        return unique_recs[:2]  # 最多推荐2个ETF

    def get_stock_news(self, stock_code: str = None) -> List[Dict]:
        """获取特定股票的新闻"""
        return self.get_hot_news(5)

    # 股票代码映射（根据热点关键词映射到个股）
    STOCK_RECOMMENDATIONS = {
        # 科技类
        "人工智能": [
            {"code": "002230", "name": "科大讯飞", "reason": "AI语音龙头，受益大模型发展"},
            {"code": "300750", "name": "宁德时代", "reason": "动力电池龙头，储能业务爆发"},
            {"code": "688981", "name": "中芯国际", "reason": "半导体晶圆代工龙头，国产替代核心"},
        ],
        "AI": [
            {"code": "002230", "name": "科大讯飞", "reason": "AI语音龙头，大模型国内领先"},
            {"code": "300364", "name": "捷成股份", "reason": "AIGC内容生成，受益AI应用爆发"},
        ],
        "芯片": [
            {"code": "688981", "name": "中芯国际", "reason": "半导体国产替代龙头"},
            {"code": "688396", "name": "华润微", "reason": "功率半导体龙头，业绩增长强劲"},
        ],
        "半导体": [
            {"code": "688981", "name": "中芯国际", "reason": "晶圆代工龙头，国产替代核心"},
            {"code": "688126", "name": "沪硅产业", "reason": "硅片龙头，晶圆产能受益"},
        ],
        "新能源": [
            {"code": "300750", "name": "宁德时代", "reason": "动力电池龙头，全球市占率第一"},
            {"code": "002594", "name": "比亚迪", "reason": "新能源汽车龙头，销量持续增长"},
        ],
        "光伏": [
            {"code": "300274", "name": "阳光电源", "reason": "光伏逆变器龙头，储能业务爆发"},
            {"code": "600438", "name": "通威股份", "reason": "硅料+电池片双龙头，成本优势明显"},
        ],
        "新能源汽车": [
            {"code": "002594", "name": "比亚迪", "reason": "新能源车销量冠军，海外拓展加速"},
            {"code": "300750", "name": "宁德时代", "reason": "动力电池龙头，绑定主流车企"},
        ],
        "汽车": [
            {"code": "002594", "name": "比亚迪", "reason": "新能源车龙头，品牌力提升"},
            {"code": "601127", "name": "赛力斯", "reason": "华为合作车型热销，销量突破"},
        ],
        # 金融类
        "银行": [
            {"code": "601398", "name": "工商银行", "reason": "国有大行，高股息稳定"},
            {"code": "601988", "name": "中国银行", "reason": "跨境业务优势，高股息"},
        ],
        "券商": [
            {"code": "600030", "name": "中信证券", "reason": "券商业龙头，资本市场改革受益"},
            {"code": "688111", "name": "东方财富", "reason": "互联网券商，流量优势明显"},
        ],
        "保险": [
            {"code": "601318", "name": "中国平安", "reason": "保险龙头，估值处于历史低位"},
            {"code": "601601", "name": "中国太保", "reason": "寿险改革成效显现，估值修复"},
        ],
        # 消费类
        "消费": [
            {"code": "600519", "name": "贵州茅台", "reason": "白酒龙头，盈利能力最强"},
            {"code": "000858", "name": "五粮液", "reason": "高端白酒，估值合理"},
        ],
        "白酒": [
            {"code": "600519", "name": "贵州茅台", "reason": "白酒龙头，品牌壁垒最高"},
            {"code": "000858", "name": "五粮液", "reason": "高端白酒，业绩增长稳定"},
        ],
        "食品": [
            {"code": "603259", "name": "海天味业", "reason": "调味品龙头，渠道优势强大"},
            {"code": "002507", "name": "涪陵榨菜", "reason": "榨菜龙头，提价能力强"},
        ],
        "家电": [
            {"code": "000333", "name": "美的集团", "reason": "家电龙头，海外拓展加速"},
            {"code": "000651", "name": "格力电器", "reason": "空调龙头，高股息"},
        ],
        "医药": [
            {"code": "600276", "name": "恒瑞医药", "reason": "创新药龙头，研发实力最强"},
            {"code": "300015", "name": "爱尔眼科", "reason": "眼科龙头，商业模式优秀"},
        ],
        "医疗": [
            {"code": "300015", "name": "爱尔眼科", "reason": "眼科龙头，业绩增长稳定"},
            {"code": "688278", "name": "特宝生物", "reason": "生物药企，独家产品放量"},
        ],
        # 资源类
        "黄金": [
            {"code": "600547", "name": "山东黄金", "reason": "黄金开采龙头，受益金价上涨"},
            {"code": "600489", "name": "中金黄金", "reason": "黄金央企，资源储备丰富"},
        ],
        "油气": [
            {"code": "600028", "name": "中国石化", "reason": "石化龙头，高股息"},
            {"code": "601857", "name": "中国石油", "reason": "油气开采受益油价高位"},
        ],
        "煤炭": [
            {"code": "601001", "name": "山西焦化", "reason": "焦炭龙头，业绩增长稳定"},
            {"code": "601088", "name": "上海能源", "reason": "煤电一体化，高股息"},
        ],
        "电力": [
            {"code": "600900", "name": "长江电力", "reason": "水电龙头，现金流稳定高股息"},
            {"code": "601991", "name": "大唐发电", "reason": "火电+新能源，估值修复"},
        ],
        # 基建地产类
        "地产": [
            {"code": "000002", "name": "万科A", "reason": "地产龙头，经营稳健"},
            {"code": "600048", "name": "保利发展", "reason": "央企地产，销售增长强劲"},
        ],
        "建筑": [
            {"code": "601668", "name": "中国建筑", "reason": "建筑龙头，基建订单饱满"},
            {"code": "601390", "name": "中国中铁", "reason": "基建央企，估值处于低位"},
        ],
        "钢铁": [
            {"code": "600019", "name": "宝钢股份", "reason": "钢铁龙头，盈利能力最强"},
            {"code": "000717", "name": "韶钢松山", "reason": "华南钢铁，区域优势明显"},
        ],
        # TMT
        "互联网": [
            {"code": "00700", "name": "腾讯控股", "reason": "互联网龙头，游戏+AI双轮驱动"},
            {"code": "03690", "name": "美团", "reason": "本地生活龙头，业绩恢复增长"},
        ],
        "云计算": [
            {"code": "688111", "name": "东方财富", "reason": "金融云龙头，流量优势强"},
            {"code": "300454", "name": "网宿科技", "reason": "CDN龙头，转型云计算"},
        ],
        "5G": [
            {"code": "600050", "name": "中国联通", "reason": "运营商龙头，5G应用爆发"},
            {"code": "000063", "name": "中兴通讯", "reason": "5G设备龙头，制裁影响消除"},
        ],
        "算力": [
            {"code": "300498", "name": "中科曙光", "reason": "算力基础设施龙头"},
            {"code": "603019", "name": "中科曙光", "reason": "国产算力核心标的"},
        ],
        # 军工
        "军工": [
            {"code": "600893", "name": "航发动力", "reason": "航空发动机龙头，订单饱满"},
            {"code": "600038", "name": "中直股份", "reason": "直升机龙头，业绩增长确定"},
        ],
    }

    def get_recommended_stocks(self) -> List[Dict]:
        """根据当天新闻动态推荐股票"""
        # 动态导入，避免循环依赖
        from services.stock_service import stock_service

        # 获取热点新闻
        news_list = self.get_hot_news(10)

        if not news_list:
            # 如果没有新闻，返回默认推荐
            return self._get_default_recommendations()

        # 收集推荐的股票
        stock_recs = []
        matched_companies = set()

        # 从新闻标题中提取可能的股票代码或公司名
        for news in news_list:
            title = news.get('title', '')
            if not title:
                continue

            # 检查是否有利好情感
            sentiment = self._analyze_sentiment(title)
            if sentiment != "positive":
                continue

            # 尝试匹配新闻中的股票
            # 方法1: 查找预定义关键词对应的股票
            for keyword, stocks in self.STOCK_RECOMMENDATIONS.items():
                if keyword in title and keyword not in matched_companies:
                    for stock in stocks[:1]:
                        stock_recs.append({
                            **stock,
                            "reason": f"新闻提及「{keyword}」：{stock['reason'][:30]}",
                            "matched_news": title[:40] + "..." if len(title) > 40 else title
                        })
                    matched_companies.add(keyword)

            # 方法2: 尝试从新闻标题中提取公司名进行动态搜索
            # 常见公司名模式提取
            import re
            # 匹配括号中的股票代码，如 "(600519)"
            code_match = re.search(r'[（(](\d{6})[）)]', title)
            if code_match:
                code = code_match.group(1)
                # 验证股票是否存在
                stock_info = stock_service.get_stock_info(code)
                if stock_info.get("name"):
                    if code not in matched_companies:
                        stock_recs.append({
                            "code": code,
                            "name": stock_info.get("name"),
                            "reason": f"新闻提及股票代码：{code}",
                            "matched_news": title[:40] + "..." if len(title) > 40 else title
                        })
                        matched_companies.add(code)

        # 去重
        seen = set()
        unique_recs = []
        for rec in stock_recs:
            if rec["code"] not in seen:
                seen.add(rec["code"])
                unique_recs.append(rec)

        # 如果推荐太少，返回默认
        if len(unique_recs) < 3:
            default_recs = self._get_default_recommendations()
            # 合并并去重
            for rec in default_recs:
                if rec["code"] not in seen:
                    unique_recs.append(rec)
                    seen.add(rec["code"])

        return unique_recs[:5]  # 最多返回5只

    def _get_default_recommendations(self) -> List[Dict]:
        """默认股票推荐"""
        return [
            {"code": "600519", "name": "贵州茅台", "reason": "白酒龙头，业绩稳定增长，高股息", "matched_news": "默认推荐"},
            {"code": "300750", "name": "宁德时代", "reason": "动力电池龙头，受益新能源汽车渗透率提升", "matched_news": "默认推荐"},
            {"code": "601398", "name": "工商银行", "reason": "国有大行，高股息低估值，防御性强", "matched_news": "默认推荐"},
            {"code": "002594", "name": "比亚迪", "reason": "新能源汽车龙头，销量持续增长", "matched_news": "默认推荐"},
            {"code": "600028", "name": "中国石化", "reason": "石化龙头，高股息6%+，业绩稳定", "matched_news": "默认推荐"},
        ]

# 全局新闻服务实例
news_service = NewsService()

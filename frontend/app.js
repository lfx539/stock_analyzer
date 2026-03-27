// 股票分析系统 - Vue 3 应用

const API_BASE = 'http://localhost:8000';

const { createApp, ref } = Vue;

createApp({
    setup() {
        const stockCode = ref('');
        const loading = ref(false);
        const error = ref('');
        const result = ref(null);

        // 新闻相关
        const news = ref([]);
        const newsLoading = ref(false);

        // 推荐股票相关
        const recommendations = ref([]);
        const recommendationsLoading = ref(false);

        // ETF推荐
        const etfRecommendations = ref([]);

        // 自选股相关
        const watchlist = ref([]);
        const watchlistLoading = ref(false);
        const showAddWatchlist = ref(false);
        const newWatchlistCode = ref('');

        // 带超时的fetch函数
        const fetchWithTimeout = async (url, options = {}, timeout = 8000) => {
            const controller = new AbortController();
            const id = setTimeout(() => controller.abort(), timeout);
            try {
                const response = await fetch(url, { ...options, signal: controller.signal });
                return response;
            } finally {
                clearTimeout(id);
            }
        };

        // 加载热点新闻
        const loadNews = async () => {
            newsLoading.value = true;
            try {
                const response = await fetchWithTimeout(`${API_BASE}/api/news?limit=10`, {}, 10000);
                if (!response.ok) throw new Error('网络错误');
                const data = await response.json();
                news.value = data.news || [];
                updateETFs();
            } catch (err) {
                console.error('加载新闻失败:', err);
                news.value = [];
            } finally {
                newsLoading.value = false;
            }
        };

        // 加载股票推荐
        const loadRecommendations = async () => {
            recommendationsLoading.value = true;
            try {
                const response = await fetchWithTimeout(`${API_BASE}/api/recommend`, {}, 10000);
                if (!response.ok) throw new Error('网络错误');
                const data = await response.json();
                recommendations.value = data.recommendations || [];
            } catch (err) {
                console.error('加载推荐失败:', err);
                recommendations.value = [];
            } finally {
                recommendationsLoading.value = false;
            }
        };

        // 获取去重后的ETF推荐
        const updateETFs = () => {
            if (!news.value || news.value.length === 0) {
                etfRecommendations.value = [];
                return;
            }
            const etfSet = new Map();
            for (const item of news.value) {
                const impacts = item.fund_impact || [];
                for (const fund of impacts) {
                    const etfs = fund.etf_recommendations || [];
                    for (const etf of etfs) {
                        if (etf && etf.code && !etfSet.has(etf.code)) {
                            etfSet.set(etf.code, etf);
                        }
                    }
                }
            }
            etfRecommendations.value = Array.from(etfSet.values());
        };

        // 加载自选股列表
        const loadWatchlist = async () => {
            watchlistLoading.value = true;
            try {
                const response = await fetchWithTimeout(`${API_BASE}/api/watchlist`, {}, 10000);
                if (!response.ok) throw new Error('网络错误');
                const data = await response.json();
                watchlist.value = data.watchlist || [];
            } catch (err) {
                console.error('加载自选股失败:', err);
                watchlist.value = [];
            } finally {
                watchlistLoading.value = false;
            }
        };

        // 添加自选股
        const addToWatchlist = async () => {
            if (!newWatchlistCode.value || !/^\d{6}$/.test(newWatchlistCode.value)) {
                alert('请输入6位股票代码');
                return;
            }
            try {
                const response = await fetch(`${API_BASE}/api/watchlist`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ stock_code: newWatchlistCode.value })
                });
                const data = await response.json();
                alert(data.message);
                if (data.success) {
                    showAddWatchlist.value = false;
                    newWatchlistCode.value = '';
                    await loadWatchlist();
                }
            } catch (err) {
                alert('添加失败: ' + err.message);
            }
        };

        // 删除自选股
        const removeFromWatchlist = async (stockCode) => {
            if (!confirm(`确定要删除 ${stockCode} 吗?`)) return;
            try {
                const response = await fetch(`${API_BASE}/api/watchlist/${stockCode}`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                alert(data.message);
                await loadWatchlist();
            } catch (err) {
                alert('删除失败: ' + err.message);
            }
        };

        // 复制股票代码
        const copyCode = async (code, event) => {
            try {
                await navigator.clipboard.writeText(code);
                // 显示成功提示
                const btn = event.target.closest('button');
                const originalHTML = btn.innerHTML;
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>';
                setTimeout(() => {
                    btn.innerHTML = originalHTML;
                }, 1500);
            } catch (err) {
                // 复制失败时使用alert
                alert('复制失败，请手动复制: ' + code);
            }
        };

        // 分析股票 - 跳转到分析页面
        const analyze = () => {
            if (!stockCode.value) {
                error.value = '请输入股票代码';
                return;
            }

            // 验证股票代码
            if (!/^\d{6}$/.test(stockCode.value)) {
                error.value = '请输入6位数字的股票代码';
                return;
            }

            // 跳转到分析页面
            window.location.href = `analyze.html?code=${stockCode.value}`;
        };

        // 分析指定股票（用于推荐列表点击）
        const analyzeStock = (code) => {
            if (!code) return;
            window.location.href = `analyze.html?code=${code}`;
        };

        // 获取状态背景色
        const getStatusColor = (color) => {
            const colors = {
                green: '#d1fae5',
                lightgreen: '#ecfdf5',
                orange: '#fef3c7',
                red: '#fee2e2',
                gray: '#f1f5f9'
            };
            return colors[color] || colors.gray;
        };

        // 获取状态文字颜色
        const getStatusTextColor = (color) => {
            const colors = {
                green: '#065f46',
                lightgreen: '#047857',
                orange: '#92400e',
                red: '#991b1b',
                gray: '#475569'
            };
            return colors[color] || colors.gray;
        };

        // 获取分位数样式类
        const getPercentileClass = (percentile) => {
            if (percentile < 40) return 'low';
            if (percentile < 70) return 'medium';
            return 'high';
        };

        // 格式化数值，如果为0或null显示"-"
        const formatValue = (value) => {
            if (value === null || value === undefined || value === 0) return '-';
            return value;
        };

        // 格式化百分比
        const formatPercent = (value) => {
            if (value === null || value === undefined) return '-';
            return value + '%';
        };

        // 初始化加载
        loadNews();
        loadWatchlist();
        loadRecommendations();

        return {
            stockCode,
            loading,
            error,
            result,
            analyze,
            analyzeStock,
            getStatusColor,
            getStatusTextColor,
            getPercentileClass,
            formatValue,
            formatPercent,
            // 新闻相关
            news,
            newsLoading,
            // 推荐股票相关
            recommendations,
            etfRecommendations,
            recommendationsLoading,
            // 自选股相关
            watchlist,
            watchlistLoading,
            showAddWatchlist,
            newWatchlistCode,
            addToWatchlist,
            removeFromWatchlist,
            copyCode
        };
    }
}).mount('#app');

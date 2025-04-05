/**
 * 豆瓣电影详情页JavaScript
 * 用于初始化和配置评论词云和评分趋势图表
 */

// 全局变量初始化
window.commentKeywords = window.commentKeywords || [];
window.ratingTrends = window.ratingTrends || [];
window.strategyWordcloudData = window.strategyWordcloudData || {};

/**
 * 调试信息显示函数
 */
function showDebugInfo(container, title, data) {
    const debugDiv = document.getElementById(container);
    if (debugDiv) {
        let msg = `<div class="alert alert-secondary mb-2" style="font-size:12px; padding:8px;">
                    <strong>${title}:</strong> `;
        
        if (data === null || data === undefined) {
            msg += '无数据';
        } else if (typeof data === 'object') {
            if (Array.isArray(data)) {
                msg += `数组 [${data.length}项]`;
                if (data.length > 0) {
                    msg += ` 示例: ${JSON.stringify(data[0]).substring(0, 50)}${JSON.stringify(data[0]).length > 50 ? '...' : ''}`;
                }
            } else {
                msg += `对象 ${JSON.stringify(data).substring(0, 50)}${JSON.stringify(data).length > 50 ? '...' : ''}`;
            }
        } else {
            msg += `${data}`;
        }
        
        msg += '</div>';
        debugDiv.innerHTML = msg;
    }
}

/**
 * 生成示例词云数据
 */
function generateSampleWordcloud() {
    const words = ['电影', '好看', '演技', '导演', '剧情', '精彩', '故事', '演员', '场景', '音乐', 
                 '感人', '画面', '经典', '推荐', '情节', '喜欢', '不错', '表演', '期待', '值得'];
    const result = [];
    
    for (const word of words) {
        const weight = Math.floor(Math.random() * 95) + 5; // 5-100之间的随机值
        result.push({
            name: word,
            value: weight
        });
    }
    
    console.log("已生成示例词云数据:", result);
    return result;
}

/**
 * 初始化数据
 */
function initData() {
    console.log("开始初始化数据...");
    
    try {
        // 评论关键词（用于词云展示）
        if (typeof commentKeywordsJson !== 'undefined') {
            try {
                // 记录原始数据长度和可能的问题
                console.log("词云数据原始状态:", {
                    "类型": typeof commentKeywordsJson,
                    "长度": commentKeywordsJson ? commentKeywordsJson.length : 0,
                    "值": commentKeywordsJson && commentKeywordsJson.length < 100 ? commentKeywordsJson : (commentKeywordsJson ? commentKeywordsJson.substring(0, 100) + "..." : "无数据")
                });
                
                // 尝试解析JSON字符串
                if (commentKeywordsJson && commentKeywordsJson !== '[]' && commentKeywordsJson !== 'null') {
                    window.commentKeywords = JSON.parse(commentKeywordsJson);
                    console.log("词云数据加载成功，共 " + window.commentKeywords.length + " 个关键词");
                    if (window.commentKeywords.length > 0) {
                        console.log("首个词云数据样本:", window.commentKeywords[0]);
                    }
                    showDebugInfo('wordcloud-debug', '词云数据', window.commentKeywords);
                } else {
                    console.warn("词云数据为空或无效:", commentKeywordsJson);
                    window.commentKeywords = [];
                    // 显示调试信息
                    showDebugInfo('wordcloud-debug', '词云数据为空', null);
                }
            } catch (e) {
                console.error("词云数据解析失败:", e, "原始数据:", commentKeywordsJson.substring(0, 100) + "...");
                window.commentKeywords = [];
                
                const debugDiv = document.getElementById('wordcloud-debug');
                if (debugDiv) {
                    debugDiv.innerHTML = '<div class="alert alert-danger">词云数据解析失败: ' + e.message + '</div>';
                }
            }
        } else {
            console.warn("commentKeywordsJson 变量未定义");
            window.commentKeywords = [];
            showDebugInfo('wordcloud-debug', 'commentKeywordsJson变量未定义', null);
        }
    } catch(e) {
        console.error("处理词云数据时出错:", e);
        window.commentKeywords = [];
    }
    
    try {
        // 评分趋势数据
        if (typeof ratingTrendsJson !== 'undefined' && ratingTrendsJson && ratingTrendsJson !== '[]' && ratingTrendsJson !== 'null') {
            window.ratingTrends = JSON.parse(ratingTrendsJson);
            console.log("评分趋势数据加载成功，共 " + window.ratingTrends.length + " 个数据点");
        } else {
            console.warn("评分趋势数据为空或无效");
            window.ratingTrends = [];
        }
    } catch(e) {
        console.error("评分趋势数据解析失败:", e);
        window.ratingTrends = [];
    }

    try {
        // 策略词云数据初始化
        window.strategyWordcloudData = {};
        
        // 顺序策略词云
        if (typeof sequentialWordcloudJson !== 'undefined' && sequentialWordcloudJson && sequentialWordcloudJson !== '[]' && sequentialWordcloudJson !== 'null') {
            window.strategyWordcloudData.sequential = JSON.parse(sequentialWordcloudJson);
            console.log("顺序策略词云数据加载成功，共 " + window.strategyWordcloudData.sequential.length + " 个关键词");
        } else {
            console.warn("顺序策略词云数据为空或无效");
            window.strategyWordcloudData.sequential = [];
        }
        
        // 随机页码策略词云
        if (typeof randomPagesWordcloudJson !== 'undefined' && randomPagesWordcloudJson && randomPagesWordcloudJson !== '[]' && randomPagesWordcloudJson !== 'null') {
            window.strategyWordcloudData.random_pages = JSON.parse(randomPagesWordcloudJson);
            console.log("随机页码策略词云数据加载成功，共 " + window.strategyWordcloudData.random_pages.length + " 个关键词");
        } else {
            console.warn("随机页码策略词云数据为空或无效");
            window.strategyWordcloudData.random_pages = [];
        }
        
        // 随机间隔策略词云
        if (typeof randomIntervalWordcloudJson !== 'undefined' && randomIntervalWordcloudJson && randomIntervalWordcloudJson !== '[]' && randomIntervalWordcloudJson !== 'null') {
            window.strategyWordcloudData.random_interval = JSON.parse(randomIntervalWordcloudJson);
            console.log("随机间隔策略词云数据加载成功，共 " + window.strategyWordcloudData.random_interval.length + " 个关键词");
        } else {
            console.warn("随机间隔策略词云数据为空或无效");
            window.strategyWordcloudData.random_interval = [];
        }
        
        // 随机区块策略词云
        if (typeof randomBlockWordcloudJson !== 'undefined' && randomBlockWordcloudJson && randomBlockWordcloudJson !== '[]' && randomBlockWordcloudJson !== 'null') {
            window.strategyWordcloudData.random_block = JSON.parse(randomBlockWordcloudJson);
            console.log("随机区块策略词云数据加载成功，共 " + window.strategyWordcloudData.random_block.length + " 个关键词");
        } else {
            console.warn("随机区块策略词云数据为空或无效");
            window.strategyWordcloudData.random_block = [];
        }
        
    } catch(e) {
        console.error("策略词云数据解析失败:", e);
        window.strategyWordcloudData = {
            sequential: [],
            random_pages: [],
            random_interval: [],
            random_block: []
        };
    }
    
    // 主词云数据与评论关键词相同
    window.wordcloudData = window.commentKeywords;
    
    // 调试输出
    console.log("主词云数据类型:", typeof window.wordcloudData, Array.isArray(window.wordcloudData) ? "是数组" : "不是数组");
    console.log("主词云数据长度:", window.wordcloudData ? window.wordcloudData.length : 0);
    
    // 如果数据为空，生成示例数据并显示调试信息
    if (!window.wordcloudData || window.wordcloudData.length === 0) {
        console.warn("词云数据为空，生成示例数据");
        window.wordcloudData = generateSampleWordcloud();
        
        // 同时更新commentKeywords和其他词云数据
        window.commentKeywords = window.wordcloudData;
        
        // 如果策略词云数据为空，也生成示例数据
        let hasStrategyData = Object.values(window.strategyWordcloudData).some(data => data && data.length > 0);
        if (!hasStrategyData) {
            console.warn("所有策略词云数据为空，生成示例数据");
            window.strategyWordcloudData = {
                sequential: generateSampleWordcloud(),
                random_pages: generateSampleWordcloud(),
                random_interval: generateSampleWordcloud(),
                random_block: generateSampleWordcloud()
            };
        }
        
        const debugDiv = document.getElementById('wordcloud-debug');
        if (debugDiv) {
            debugDiv.innerHTML = '<div class="alert alert-warning">后端未返回词云数据，已生成示例数据用于展示</div>';
        }
    }
    
    console.log("数据初始化完成");
}

document.addEventListener('DOMContentLoaded', function() {
    // 检查ECharts库和词云扩展是否正确加载
    if (typeof echarts === 'undefined') {
        console.error('错误: ECharts库未加载！词云无法显示。请检查网络连接或CDN状态。');
        document.getElementById('wordcloud-debug').innerHTML = 
            '<div class="alert alert-danger">ECharts库加载失败，词云无法显示。请检查网络连接。</div>';
        return;
    } else {
        console.log('ECharts库加载成功');
        // 尝试检测词云扩展是否加载
        try {
            const testChart = echarts.init(document.createElement('div'));
            const testOption = {
                series: [{
                    type: 'wordCloud',
                    data: [{ name: 'test', value: 1 }]
                }]
            };
            testChart.setOption(testOption);
            console.log('ECharts词云扩展加载成功');
            testChart.dispose();
        } catch (e) {
            console.error('错误: ECharts词云扩展未加载！', e);
            document.getElementById('wordcloud-debug').innerHTML = 
                '<div class="alert alert-danger">ECharts词云扩展加载失败，词云无法显示。请检查网络连接。</div>';
            return;
        }
    }
    
    // 确保DOM容器存在
    if (!document.getElementById('wordcloud')) {
        console.error('错误: 找不到词云DOM容器 (id="wordcloud")');
    }
    
    // 初始化数据
    initData();
    
    // 初始化所有图表
    initCharts();
    
    // 监听窗口大小变化
    window.addEventListener('resize', handleResize);
    
    // 监听策略选择器变化
    initStrategySelector();
    
    // 为更新按钮添加点击事件
    initUpdateButton();
});

/**
 * 初始化所有图表 - 增加延迟确保DOM已渲染
 */
function initCharts() {
    console.log("开始初始化图表...");
    
    // 输出词云数据状态
    console.log("词云数据检查:", {
        "commentKeywords类型": typeof window.commentKeywords,
        "commentKeywords是否数组": Array.isArray(window.commentKeywords),
        "commentKeywords长度": window.commentKeywords ? window.commentKeywords.length : 0,
        "wordcloudData类型": typeof window.wordcloudData,
        "wordcloudData是否数组": Array.isArray(window.wordcloudData),
        "wordcloudData长度": window.wordcloudData ? window.wordcloudData.length : 0
    });
    
    // 延迟执行确保DOM已完全渲染
    setTimeout(function() {
        console.log("DOM已就绪，开始渲染图表");
        
        // 初始化主词云
        initMainWordcloud();
        
        // 初始化策略词云
        initStrategyWordcloud();
        
        // 初始化评分趋势图
        initRatingTrend();
        
        console.log("图表初始化完成");
        
        // 主动触发一次窗口大小调整，以确保图表正确渲染
        window.dispatchEvent(new Event('resize'));
    }, 100);
}

/**
 * 处理窗口大小变化
 */
function handleResize() {
    // 重绘所有图表
    if (window.wordcloudChart) window.wordcloudChart.resize();
    if (window.strategyWordcloudChart) window.strategyWordcloudChart.resize();
    if (window.ratingChart) window.ratingChart.resize();
}

/**
 * 初始化策略选择器
 */
function initStrategySelector() {
    const selector = document.getElementById('strategySelector');
    if (!selector) return;
    
    selector.addEventListener('change', function() {
        const strategy = this.value;
        
        // 隐藏所有策略说明
        document.querySelectorAll('.strategy-detail').forEach(function(el) {
            el.style.display = 'none';
        });
        
        // 显示当前策略说明
        const infoElement = document.getElementById(strategy + 'Info');
        if (infoElement) {
            infoElement.style.display = 'block';
        } else {
            // 使用switch语句作为备选方案
            let backupElement;
            switch(strategy) {
                case 'sequential':
                    backupElement = document.getElementById('sequentialInfo');
                    break;
                case 'random_pages':
                    backupElement = document.getElementById('randomPagesInfo');
                    break;
                case 'random_interval':
                    backupElement = document.getElementById('randomIntervalInfo');
                    break;
                case 'random_block':
                    backupElement = document.getElementById('randomBlockInfo');
                    break;
            }
            
            if (backupElement) {
                backupElement.style.display = 'block';
            }
        }
        
        // 给DOM一些时间更新后再渲染词云
        console.log(`选择了策略 "${strategy}", 延迟50ms后渲染`);
        setTimeout(function() {
            renderStrategyWordcloud(strategy);
        }, 50);
    });
}

/**
 * 初始化主词云
 */
function initMainWordcloud() {
    if (typeof echarts === 'undefined') {
        console.error('ECharts库未加载，词云无法初始化');
        return;
    }
    const container = document.getElementById('wordcloud');
    if (!container) {
        console.error('主词云容器不存在');
        return;
    }
    
    // 检查容器可见性和尺寸
    const containerStyle = window.getComputedStyle(container);
    console.log("词云容器可见性检查:", {
        "display": containerStyle.display,
        "visibility": containerStyle.visibility,
        "height": containerStyle.height,
        "width": containerStyle.width,
        "offsetHeight": container.offsetHeight,
        "offsetWidth": container.offsetWidth
    });
    
    // 如果容器不可见或尺寸为0，延迟渲染
    if (container.offsetHeight === 0 || container.offsetWidth === 0 || 
        containerStyle.display === 'none' || containerStyle.visibility === 'hidden') {
        console.warn("词云容器尺寸为0或不可见，将延迟渲染");
        setTimeout(initMainWordcloud, 500);  // 500ms后重试
        return;
    }
    
    console.log("开始初始化主词云");
    
    // 使用从HTML中传递的数据
    let data = window.wordcloudData || window.commentKeywords || [];
    console.log("原始词云数据:", typeof data, Array.isArray(data) ? data.length : "非数组", 
                Array.isArray(data) && data.length > 0 ? data[0] : "无数据");
    
    // 无论输入数据状态如何，总是确保有示例数据作为备用
    const sampleData = generateSampleWordcloud();
    
    // 如果数据为空，使用示例数据
    if (!data || data.length === 0) {
        console.warn('主词云数据不存在或为空，使用示例数据');
        data = sampleData;
        
        // 更新全局数据
        window.wordcloudData = data;
        window.commentKeywords = data;
    }
    
    try {
        // 如果数据是字符串，尝试解析JSON
        if (typeof data === 'string') {
            try {
                console.log("尝试解析字符串数据:", data.substring(0, 100) + "...");
                data = JSON.parse(data);
                console.log("字符串解析后:", data);
            } catch (e) {
                console.error("解析JSON字符串失败:", e);
                data = generateSampleWordcloud();
            }
        }
        
        // 确保数据格式正确，避免渲染错误
        const processedData = processWordcloudData(data);
        console.log("处理后的词云数据:", processedData);
        
        // 如果处理后的数据为空，使用示例数据
        if (!processedData || processedData.length === 0) {
            console.warn("处理后的词云数据为空，使用示例数据");
            const sampleData = processWordcloudData(generateSampleWordcloud());
            
            // 清除容器现有内容
            container.innerHTML = '';
            
            // 显示使用示例数据的提示
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-warning mb-2';
            alertDiv.style.fontSize = '12px';
            alertDiv.innerHTML = '未找到有效的词云数据，使用示例数据展示';
            container.appendChild(alertDiv);
            
            // 创建词云容器
            const wordcloudDiv = document.createElement('div');
            wordcloudDiv.style.width = '100%';
            wordcloudDiv.style.height = '250px';
            container.appendChild(wordcloudDiv);
            
            // 初始化ECharts实例
            const chart = echarts.init(wordcloudDiv);
            window.wordcloudChart = chart;
            
            // 配置词云选项
            const option = getWordcloudOption(sampleData);
            
            // 设置选项并渲染图表
            chart.setOption(option);
            console.log('使用示例数据初始化主词云成功，渲染了 ' + sampleData.length + ' 个关键词');
            return;
        }
        
        // 清空容器内容
        container.innerHTML = '';
        
        // 初始化ECharts实例
        const chart = echarts.init(container);
        window.wordcloudChart = chart;
        
        // 配置词云选项
        const option = getWordcloudOption(processedData);
        
        // 设置选项并渲染图表
        chart.setOption(option);
        console.log('主词云初始化成功，渲染了 ' + processedData.length + ' 个关键词');
    } catch (error) {
        console.error('初始化主词云时出错:', error);
        container.innerHTML = '<div class="alert alert-danger">词云渲染失败: ' + error.message + '</div>';
        
        // 尝试使用示例数据作为备选方案
        try {
            // 显示错误信息后，添加一个新的区域用于展示示例词云
            const fallbackDiv = document.createElement('div');
            fallbackDiv.style.width = '100%';
            fallbackDiv.style.height = '250px';
            container.appendChild(fallbackDiv);
            
            const sampleData = processWordcloudData(generateSampleWordcloud());
            const chart = echarts.init(fallbackDiv);
            chart.setOption(getWordcloudOption(sampleData));
            console.log('使用备选示例数据渲染词云');
        } catch (fallbackError) {
            console.error('备选方案也失败:', fallbackError);
        }
    }
}

/**
 * 获取词云图表配置 (主词云)
 * 注意：此函数的配置与策略词云配置(getStrategyWordcloudOption)基本保持一致
 * 唯一区别是颜色处理方式略有不同，主词云使用随机色彩
 */
function getWordcloudOption(data) {
    return {
        tooltip: {
            show: true,
            formatter: function(params) {
                return params.name + ': ' + params.value;
            }
        },
        series: [{
            type: 'wordCloud',
            shape: 'circle',
            left: 'center',
            top: 'center',
            width: '90%',
            height: '90%',
            right: null,
            bottom: null,
            sizeRange: [12, 50],
            rotationRange: [-90, 90],
            rotationStep: 45,
            gridSize: 8,
            drawOutOfBound: false,
            textStyle: {
                fontFamily: 'sans-serif',
                fontWeight: 'bold',
                color: function () {
                    // 主词云使用随机色彩，色彩值范围控制在100-200之间，避免过浅或过深
                    return 'rgb(' + [
                        Math.round(100 + Math.random() * 100),
                        Math.round(100 + Math.random() * 100),
                        Math.round(100 + Math.random() * 100)
                    ].join(',') + ')';
                }
            },
            emphasis: {
                textStyle: {
                    shadowBlur: 10,
                    shadowColor: '#333'
                }
            },
            data: data
        }]
    };
}

/**
 * 处理词云数据，确保格式正确
 */
function processWordcloudData(data) {
    console.log("开始处理词云数据:", {
        "数据类型": typeof data,
        "是否数组": Array.isArray(data),
        "数据长度": data ? (Array.isArray(data) ? data.length : "非数组") : "无数据"
    });
    
    // 处理空数据情况
    if (!data) {
        console.warn("词云数据为空");
        return [];
    }
    
    // 处理非数组数据
    if (!Array.isArray(data)) {
        console.warn('词云数据不是数组，尝试转换');
        
        // 尝试将字符串解析为JSON
        if (typeof data === 'string') {
            try {
                console.log("尝试解析JSON字符串");
                data = JSON.parse(data);
                console.log("JSON解析结果:", {
                    "是否数组": Array.isArray(data),
                    "数据长度": Array.isArray(data) ? data.length : "非数组"
                });
            } catch (e) {
                console.error('解析词云数据字符串失败:', e);
                return [];
            }
        } 
        // 如果是对象但不是数组，尝试转换为数组
        else if (typeof data === 'object' && data !== null) {
            console.log("数据是对象但不是数组，尝试转换");
            
            // 如果是对象但包含items或data属性，可能是包装的数据
            if (data.items && Array.isArray(data.items)) {
                data = data.items;
            } else if (data.data && Array.isArray(data.data)) {
                data = data.data;
            } else if (data.keywords && Array.isArray(data.keywords)) {
                data = data.keywords;
            } else {
                // 尝试将对象转换为键值对数组
                try {
                    data = Object.entries(data).map(([key, value]) => {
                        return { name: key, value: typeof value === 'number' ? value : 1 };
                    });
                } catch (e) {
                    console.error('转换对象到数组失败:', e);
                    return [];
                }
            }
        } else {
            console.error('无法处理的数据类型:', typeof data);
            return [];
        }
    }
    
    // 防止在转换后仍然不是数组的情况
    if (!Array.isArray(data)) {
        console.error('转换后数据仍然不是数组');
        return [];
    }
    
    // 如果数组为空则直接返回
    if (data.length === 0) {
        console.warn('处理的数据数组为空');
        return [];
    }
    
    console.log("数据转换为数组后前3个元素:", data.slice(0, 3));
    
    // 确保每个数据项都有name和value属性
    const processedData = data.map((item, index) => {
        // 如果是空项或null，跳过
        if (!item) {
            console.warn(`数据项 ${index} 为空`);
            return { name: `unknown_${index}`, value: 1 };
        }
        
        // 如果是对象但没有正确的属性
        if (typeof item === 'object' && item !== null) {
            // 如果已经是正确格式，直接返回
            if (item.name !== undefined && item.value !== undefined) {
                return { 
                    name: String(item.name), 
                    value: typeof item.value === 'number' ? item.value : 1 
                };
            }
            
            // 如果缺少name属性，尝试使用其他替代属性
            const name = item.name || item.word || item.keyword || item.text || item.key || item.term || `unknown_${index}`;
            // 如果缺少value属性，尝试使用其他替代属性，或使用默认值
            const value = item.value || item.weight || item.score || item.count || item.frequency || 1;
            
            return { name: String(name), value: typeof value === 'number' ? value : 1 };
        }
        // 如果是简单值，如字符串，转换为对象格式
        else if (typeof item === 'string') {
            return { name: item, value: 1 };
        }
        // 如果是数字，假设它是值，使用索引作为名称
        else if (typeof item === 'number') {
            return { name: `term_${index}`, value: item };
        }
        // 如果是数组形式 [name, value]
        else if (Array.isArray(item)) {
            if (item.length >= 2) {
                return { 
                    name: String(item[0]), 
                    value: typeof item[1] === 'number' ? item[1] : 1 
                };
            } else if (item.length === 1) {
                return { name: String(item[0]), value: 1 };
            }
        }
        
        // 默认返回
        console.warn(`未知数据格式的项 ${index}:`, item);
        return { name: `unknown_${index}`, value: 1 };
    })
    // 过滤掉无效项并只保留有意义的关键词
    .filter(item => {
        return item.name && 
               item.name !== 'unknown' && 
               !item.name.startsWith('unknown_') && 
               item.name.trim() !== '' &&
               item.value > 0;
    });
    
    console.log(`处理完成: 原始数据 ${data.length} 项，处理后 ${processedData.length} 项`);
    return processedData;
}

/**
 * 初始化策略词云
 */
function initStrategyWordcloud() {
    if (typeof echarts === 'undefined') {
        console.error('ECharts库未加载，策略词云无法初始化');
        return;
    }
    
    const container = document.getElementById('strategyWordcloud');
    if (!container) {
        console.error('策略词云容器不存在');
        return;
    }
    
    // 检查容器可见性和尺寸
    const containerStyle = window.getComputedStyle(container);
    console.log("策略词云容器可见性检查:", {
        "display": containerStyle.display,
        "visibility": containerStyle.visibility,
        "height": containerStyle.height,
        "width": containerStyle.width,
        "offsetHeight": container.offsetHeight,
        "offsetWidth": container.offsetWidth
    });
    
    // 如果容器不可见或尺寸为0，延迟渲染
    if (container.offsetHeight === 0 || container.offsetWidth === 0 || 
        containerStyle.display === 'none' || containerStyle.visibility === 'hidden') {
        console.warn("策略词云容器尺寸为0或不可见，将延迟渲染");
        setTimeout(initStrategyWordcloud, 500);  // 500ms后重试
        return;
    }
    
    console.log("开始初始化策略词云");
    
    try {
        // 清空容器内容确保干净状态
        container.innerHTML = '';
        
        // 创建图表容器以确保尺寸正确
        const chartDiv = document.createElement('div');
        chartDiv.style.width = '100%';
        chartDiv.style.height = '250px';
        container.appendChild(chartDiv);
        
        // 初始化ECharts实例
        const chart = echarts.init(chartDiv);
        window.strategyWordcloudChart = chart;
        
        // 获取策略选择器当前选择的策略
        const selector = document.getElementById('strategySelector');
        const defaultStrategy = selector ? selector.value : 'sequential';
        
        console.log(`初始化策略词云完成，开始渲染默认策略: ${defaultStrategy}`);
        // 渲染默认策略词云
        renderStrategyWordcloud(defaultStrategy);
    } catch (error) {
        console.error('初始化策略词云时出错:', error);
        container.innerHTML = '<div class="alert alert-danger">策略词云初始化失败: ' + error.message + '</div>';
    }
}

/**
 * 渲染策略词云
 */
function renderStrategyWordcloud(strategy) {
    if (typeof echarts === 'undefined') {
        console.error('ECharts库未加载，策略词云无法渲染');
        return;
    }
    
    const container = document.getElementById('strategyWordcloud');
    if (!container) {
        console.error('策略词云容器不存在');
        return;
    }
    
    // 检查容器可见性和尺寸
    const containerStyle = window.getComputedStyle(container);
    console.log(`策略 "${strategy}" 词云容器可见性检查:`, {
        "display": containerStyle.display,
        "visibility": containerStyle.visibility,
        "height": containerStyle.height,
        "width": containerStyle.width,
        "offsetHeight": container.offsetHeight,
        "offsetWidth": container.offsetWidth
    });
    
    // 如果容器不可见或尺寸为0，延迟渲染
    if (container.offsetHeight === 0 || container.offsetWidth === 0 || 
        containerStyle.display === 'none' || containerStyle.visibility === 'hidden') {
        console.warn(`策略 "${strategy}" 词云容器尺寸为0或不可见，将延迟渲染`);
        setTimeout(function() {
            renderStrategyWordcloud(strategy);
        }, 200);  // 200ms后重试
        return;
    }
    
    console.log(`开始渲染策略 "${strategy}" 词云，容器尺寸: ${container.offsetWidth}x${container.offsetHeight}`);
    
    // 从HTML中获取的策略词云数据
    const data = window.strategyWordcloudData[strategy] || [];
    console.log(`策略 "${strategy}" 词云数据:`, {
        "数据类型": typeof data,
        "是否数组": Array.isArray(data),
        "数据长度": data ? (Array.isArray(data) ? data.length : "非数组") : "无数据",
        "数据样本": Array.isArray(data) && data.length > 0 ? data[0] : "无数据"
    });
    
    // 准备示例数据，无论如何都确保有数据可用
    const sampleData = generateSampleWordcloud().map(item => {
        // 为不同策略修改样本数据，使其有所不同
        return {
            name: item.name,
            value: Math.round(item.value * (0.5 + Math.random()))
        };
    });
    
    // 如果没有真实数据，使用示例数据但显示提示
    if (!data || data.length === 0) {
        console.warn(`策略 "${strategy}" 没有词云数据，将使用示例数据`);
        
        // 清空容器
        container.innerHTML = '';
        
        // 添加警告提示
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-warning mb-2';
        alertDiv.style.fontSize = '12px';
        alertDiv.innerHTML = `暂无 "${strategy}" 策略的评论数据，使用示例数据展示`;
        container.appendChild(alertDiv);
        
        // 创建图表容器
        const chartDiv = document.createElement('div');
        chartDiv.style.width = '100%';
        chartDiv.style.height = '250px';
        container.appendChild(chartDiv);
        
        // 渲染示例数据
        try {
            const chart = echarts.init(chartDiv);
            window.strategyWordcloudChart = chart;
            
            const option = getStrategyWordcloudOption(strategy, sampleData);
            chart.setOption(option);
            console.log(`策略 "${strategy}" 词云使用示例数据渲染成功`);
        } catch (error) {
            console.error(`示例数据渲染策略 "${strategy}" 词云失败:`, error);
            chartDiv.innerHTML = '<div class="alert alert-danger">词云渲染失败: ' + error.message + '</div>';
        }
        
        return;
    }
    
    try {
        // 确保数据格式正确
        const processedData = processWordcloudData(data);
        
        if (processedData.length === 0) {
            console.warn(`策略 "${strategy}" 数据处理后为空，将使用示例数据`);
            
            // 清空容器内容
            container.innerHTML = '';
            
            // 添加警告
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-warning mb-2';
            alertDiv.style.fontSize = '12px';
            alertDiv.innerHTML = `策略 "${strategy}" 的数据格式错误，使用示例数据`;
            container.appendChild(alertDiv);
            
            // 创建图表容器
            const chartDiv = document.createElement('div');
            chartDiv.style.width = '100%';
            chartDiv.style.height = '250px';
            container.appendChild(chartDiv);
            
            // 渲染示例数据
            const chart = echarts.init(chartDiv);
            window.strategyWordcloudChart = chart;
            
            const option = getStrategyWordcloudOption(strategy, sampleData);
            chart.setOption(option);
            
            return;
        }
        
        // 清空容器内容
        container.innerHTML = '';
        
        // 创建专用的图表容器以确保尺寸正确
        const chartDiv = document.createElement('div');
        chartDiv.style.width = '100%';
        chartDiv.style.height = '250px';
        container.appendChild(chartDiv);
        
        // 重新初始化图表
        const chart = echarts.init(chartDiv);
        window.strategyWordcloudChart = chart;
        
        // 确保容器仍有尺寸
        if (chartDiv.offsetHeight === 0 || chartDiv.offsetWidth === 0) {
            console.warn(`策略 "${strategy}" 词云图表容器尺寸为0，延迟渲染`);
            setTimeout(function() {
                renderStrategyWordcloud(strategy);
            }, 200);
            return;
        }
        
        // 配置词云选项
        const option = getStrategyWordcloudOption(strategy, processedData);
        
        chart.setOption(option);
        console.log(`策略词云 "${strategy}" 渲染成功，共 ${processedData.length} 个关键词`);
    } catch (error) {
        console.error(`渲染策略词云 "${strategy}" 时出错:`, error);
        container.innerHTML = '<div class="alert alert-danger">词云渲染失败: ' + error.message + '</div>';
    }
}

/**
 * 获取策略词云图表配置
 * 注意：此函数的配置与主词云配置(getWordcloudOption)基本保持一致
 * 唯一区别是颜色处理方式，策略词云根据不同策略使用不同的基础颜色
 */
function getStrategyWordcloudOption(strategy, data) {
    // 为不同策略使用不同的颜色配置
    const colors = {
        sequential: [122, 162, 247],    // 蓝色系
        random_pages: [250, 128, 114],  // 橙红系
        random_interval: [50, 205, 50], // 绿色系
        random_block: [186, 85, 211]    // 紫色系
    };
    
    const baseColor = colors[strategy] || [120, 120, 120];
    
    return {
        tooltip: {
            show: true,
            formatter: function(params) {
                return params.name + ': ' + params.value;
            }
        },
        series: [{
            type: 'wordCloud',
            shape: 'circle',
            left: 'center',
            top: 'center',
            width: '90%',
            height: '90%',
            right: null,
            bottom: null,
            sizeRange: [12, 50],
            rotationRange: [-90, 90],
            rotationStep: 45,
            gridSize: 8,
            drawOutOfBound: false,
            textStyle: {
                fontFamily: 'sans-serif',
                fontWeight: 'bold',
                color: function () {
                    // 策略词云基于特定的基础颜色，并添加随机变化来增加丰富度
                    return 'rgb(' + [
                        Math.min(255, baseColor[0] + Math.round(Math.random() * 40)),
                        Math.min(255, baseColor[1] + Math.round(Math.random() * 40)),
                        Math.min(255, baseColor[2] + Math.round(Math.random() * 40))
                    ].join(',') + ')';
                }
            },
            emphasis: {
                textStyle: {
                    shadowBlur: 10,
                    shadowColor: '#333'
                }
            },
            data: data
        }]
    };
}

/**
 * 初始化评分趋势图
 */
function initRatingTrend() {
    if (typeof echarts === 'undefined') {
        console.error('ECharts库未加载，评分趋势图无法初始化');
        return;
    }

    const container = document.getElementById('rating-chart-container');
    if (!container) {
        console.log('评分趋势容器不存在');
        return;
    }
    
    // 检查容器可见性和尺寸
    const containerStyle = window.getComputedStyle(container);
    console.log("评分趋势容器可见性检查:", {
        "display": containerStyle.display,
        "visibility": containerStyle.visibility,
        "height": containerStyle.height,
        "width": containerStyle.width,
        "offsetHeight": container.offsetHeight,
        "offsetWidth": container.offsetWidth
    });
    
    // 如果容器不可见或尺寸为0，延迟渲染
    if (container.offsetHeight === 0 || container.offsetWidth === 0 || 
        containerStyle.display === 'none' || containerStyle.visibility === 'hidden') {
        console.warn("评分趋势容器尺寸为0或不可见，将延迟渲染");
        setTimeout(initRatingTrend, 500);  // 500ms后重试
        return;
    }
    
    // 使用从HTML中传递的评分趋势数据
    const trendData = window.ratingTrends || [];
    console.log("评分趋势数据:", {
        "数据类型": typeof trendData,
        "是否数组": Array.isArray(trendData),
        "数据长度": trendData ? trendData.length : 0,
        "数据样本": Array.isArray(trendData) && trendData.length > 0 ? trendData[0] : "无数据"
    });
    
    if (!trendData || trendData.length === 0) {
        console.warn('评分趋势数据为空，显示提示信息');
        container.innerHTML = '<div class="alert alert-info">暂无评分趋势数据</div>';
        return;
    }
    
    try {
        // 初始化ECharts实例
        const chart = echarts.init(container);
        window.ratingChart = chart;
        
        // 准备数据
        const dates = trendData.map(item => item.date);
        const ratings = trendData.map(item => item.rating);
        const counts = trendData.map(item => item.count);
        
        // 配置评分趋势图选项
        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                }
            },
            legend: {
                data: ['评分', '评论数']
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: dates,
                axisLabel: {
                    rotate: 45
                }
            },
            yAxis: [
                {
                    type: 'value',
                    name: '评分',
                    min: 0,
                    max: 10,
                    interval: 1,
                    axisLabel: {
                        formatter: '{value} 分'
                    }
                },
                {
                    type: 'value',
                    name: '评论数',
                    axisLabel: {
                        formatter: '{value}'
                    }
                }
            ],
            series: [
                {
                    name: '评分',
                    type: 'line',
                    data: ratings,
                    smooth: true,
                    itemStyle: {
                        color: '#e74c3c'
                    }
                },
                {
                    name: '评论数',
                    type: 'bar',
                    yAxisIndex: 1,
                    data: counts,
                    itemStyle: {
                        color: '#3498db'
                    }
                }
            ]
        };
        
        chart.setOption(option);
        console.log('评分趋势图初始化成功');
    } catch (error) {
        console.error('初始化评分趋势图时出错:', error);
        container.innerHTML = '<div class="alert alert-danger">评分趋势图渲染失败: ' + error.message + '</div>';
    }
}

/**
 * 打开豆瓣设置模态框
 */
function openDoubanSettings() {
    try {
        const modalElement = document.getElementById('doubanSettingsModal');
        if (!modalElement) {
            console.error('找不到设置模态框元素');
            return;
        }
        
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    } catch (error) {
        console.error('打开设置模态框时出错:', error);
        alert('打开设置失败，请稍后重试');
    }
}

/**
 * 保存豆瓣设置
 */
function saveDoubanSettings() {
    const form = document.getElementById('doubanSettingsForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch('/douban/settings/save/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('设置保存成功');
            bootstrap.Modal.getInstance(document.getElementById('doubanSettingsModal')).hide();
        } else {
            alert('设置保存失败: ' + (data.message || '未知错误'));
        }
    })
    .catch(error => {
        console.error('保存设置时出错:', error);
        alert('保存设置时发生错误，请稍后重试');
    });
}

/**
 * 初始化更新按钮
 */
function initUpdateButton() {
    const updateButton = document.getElementById('updateWordcloud');
    if (updateButton) {
        updateButton.addEventListener('click', function() {
            updateMovieWordcloud();
        });
    }
}

/**
 * 更新电影评论词云
 */
function updateMovieWordcloud() {
    // 获取电影ID
    const movieId = document.getElementById('movie-id').value;
    if (!movieId) {
        alert('无法获取电影ID');
        return;
    }
    
    // 显示加载状态
    const wordcloudContainer = document.getElementById('wordcloud');
    if (wordcloudContainer) {
        wordcloudContainer.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">正在更新词云数据，请稍候...</p></div>';
    }
    
    // 获取CSRF令牌
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // 发送AJAX请求
    fetch(`/douban/movie/${movieId}/update_wordcloud/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络请求失败');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // 更新成功，重新渲染词云
            if (data.wordcloud_data) {
                // 更新全局数据
                window.wordcloudData = data.wordcloud_data;
                window.commentKeywords = data.wordcloud_data;
                
                // 重新渲染词云
                initMainWordcloud();
                
                // 如果有策略词云数据，也更新它们
                if (data.strategy_data) {
                    window.strategyWordcloudData = data.strategy_data;
                    // 获取当前选中的策略
                    const strategySelector = document.getElementById('strategySelector');
                    const currentStrategy = strategySelector ? strategySelector.value : 'sequential';
                    // 重新渲染策略词云
                    renderStrategyWordcloud(currentStrategy);
                }
                
                // 显示成功消息
                alert('词云数据更新成功！');
            } else {
                wordcloudContainer.innerHTML = '<div class="alert alert-warning">更新成功，但没有获取到新的词云数据</div>';
            }
        } else {
            // 更新失败
            wordcloudContainer.innerHTML = '<div class="alert alert-danger">更新词云失败: ' + (data.message || '未知错误') + '</div>';
        }
    })
    .catch(error => {
        console.error('更新词云时出错:', error);
        if (wordcloudContainer) {
            wordcloudContainer.innerHTML = '<div class="alert alert-danger">更新词云失败: ' + error.message + '</div>';
        }
    });
} 
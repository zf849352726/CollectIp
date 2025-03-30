/**
 * 豆瓣电影详情页JavaScript
 * 用于初始化和配置评论词云和评分趋势图表
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有图表
    initCharts();
    
    // 监听窗口大小变化
    window.addEventListener('resize', handleResize);
    
    // 监听策略选择器变化
    initStrategySelector();
});

/**
 * 初始化所有图表
 */
function initCharts() {
    // 初始化主词云
    initMainWordcloud();
    
    // 初始化策略词云
    initStrategyWordcloud();
    
    // 初始化评分趋势图
    initRatingTrend();
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
        
        // 渲染对应策略的词云
        renderStrategyWordcloud(strategy);
    });
}

/**
 * 初始化主词云
 */
function initMainWordcloud() {
    const container = document.getElementById('wordcloud');
    if (!container) {
        console.log('主词云容器不存在');
        return;
    }
    
    // 使用从HTML中传递的数据
    const data = window.wordcloudData || window.commentKeywords || [];
    if (!data || data.length === 0) {
        console.log('主词云数据不存在');
        return;
    }
    
    try {
        // 初始化ECharts实例
        const chart = echarts.init(container);
        window.wordcloudChart = chart;
        
        // 配置词云选项
        const option = {
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
                        return 'rgb(' + [
                            Math.round(Math.random() * 160),
                            Math.round(Math.random() * 160),
                            Math.round(Math.random() * 160)
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
        
        chart.setOption(option);
        console.log('主词云初始化成功');
    } catch (error) {
        console.error('初始化主词云时出错:', error);
    }
}

/**
 * 初始化策略词云
 */
function initStrategyWordcloud() {
    const container = document.getElementById('strategyWordcloud');
    if (!container) return;
    
    try {
        // 初始化ECharts实例
        const chart = echarts.init(container);
        window.strategyWordcloudChart = chart;
        
        // 渲染默认策略词云
        renderStrategyWordcloud('sequential');
    } catch (error) {
        console.error('初始化策略词云时出错:', error);
    }
}

/**
 * 渲染策略词云
 */
function renderStrategyWordcloud(strategy) {
    const container = document.getElementById('strategyWordcloud');
    if (!container) return;
    
    // 从HTML中获取的策略词云数据
    const data = window.strategyWordcloudData[strategy] || [];
    
    // 如果没有数据，显示提示信息
    if (!data || data.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">暂无此策略的评论数据</div>';
        return;
    }
    
    // 清空容器内容
    container.innerHTML = '';
    
    // 重新初始化图表
    const chart = echarts.init(container);
    window.strategyWordcloudChart = chart;
    
    // 配置词云选项
    const option = {
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
                    // 为不同策略使用不同的颜色配置
                    const colors = {
                        sequential: [122, 162, 247],  // 蓝色系
                        random_pages: [250, 128, 114],  // 橙红系
                        random_interval: [50, 205, 50],  // 绿色系
                        random_block: [186, 85, 211]   // 紫色系
                    };
                    
                    const baseColor = colors[strategy] || [120, 120, 120];
                    
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
    
    chart.setOption(option);
    console.log(`策略词云 "${strategy}" 渲染成功`);
}

/**
 * 初始化评分趋势图
 */
function initRatingTrend() {
    const container = document.getElementById('rating-chart-container');
    if (!container) {
        console.log('评分趋势容器不存在');
        return;
    }
    
    // 使用从HTML中传递的评分趋势数据
    const trendData = window.ratingTrends || [];
    if (!trendData || trendData.length === 0) {
        console.log('评分趋势数据不存在');
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
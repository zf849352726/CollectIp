// 获取CSRF token的函数
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// 打开豆瓣设置模态框
function openDoubanSettings() {
    const modal = new bootstrap.Modal(document.getElementById('doubanSettingsModal'));
    modal.show();
}

// 保存豆瓣设置
function saveDoubanSettings() {
    const form = document.getElementById('doubanSettingsForm');
    const formData = new FormData(form);
    
    fetch('/douban/save_settings/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('设置已保存');
            const modal = bootstrap.Modal.getInstance(document.getElementById('doubanSettingsModal'));
            modal.hide();
        } else {
            alert('保存失败: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('发生错误，请重试');
    });
}

// 显示通知消息
function showNotification(title, message, type) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show notification-toast`;
    notification.innerHTML = `
        <strong>${title}</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.appendChild(notification);
    
    // 5秒后自动移除
    setTimeout(() => {
        notification.classList.add('fade');
        setTimeout(() => notification.remove(), 500);
    }, 5000);
}

// 获取Cookie值
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 初始化已发表状态切换按钮
function initTogglePublishedButtons() {
    console.log('初始化已发表状态切换按钮');
    
    // 获取所有已发表状态按钮
    const toggleButtons = document.querySelectorAll('.toggle-published');
    console.log(`找到 ${toggleButtons.length} 个已发表状态切换按钮`);
    
    // 为每个按钮添加点击事件监听器
    toggleButtons.forEach((button, index) => {
        console.log(`为按钮 #${index} 添加点击事件`);
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const movieId = this.getAttribute('data-id');
            const isPublished = this.getAttribute('data-published') === 'true';
            const movieTitle = this.closest('tr').querySelector('td:first-child').textContent;
            
            console.log(`点击了电影 "${movieTitle}" (ID: ${movieId}) 的状态切换按钮`);
            console.log(`当前状态: ${isPublished ? '已发表' : '未发表'}`);
            
            // 显示确认对话框
            const action = isPublished ? '取消发表' : '发表';
            if (confirm(`确定要${action}电影 "${movieTitle}" 吗？`)) {
                console.log(`用户确认了${action}操作，准备发送请求`);
                toggleMoviePublished(movieId, this);
            } else {
                console.log('用户取消了操作');
            }
        });
    });
}

// 切换电影的已发表状态
function toggleMoviePublished(movieId, buttonElement) {
    console.log(`开始处理电影ID ${movieId} 的状态切换`);
    
    // 记录按钮原始状态
    const originalHtml = buttonElement.innerHTML;
    const originalTitle = buttonElement.title;
    
    // 设置加载状态
    buttonElement.innerHTML = '⏳';
    buttonElement.title = '处理中...';
    
    // 获取CSRF token
    const csrfToken = getCSRFToken();
    console.log(`获取到CSRF token: ${csrfToken ? '成功' : '失败'}`);
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('movie_id', movieId);
    console.log('已创建FormData并添加movie_id参数');
    
    console.log(`请求URL: /douban/movies/toggle_published/`);
    console.log(`请求方法: POST`);
    console.log(`请求参数: movie_id=${movieId}`);
    
    // 发送请求到后端
    fetch('/douban/movies/toggle_published/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => {
        console.log(`收到响应，状态码: ${response.status}`);
        if (!response.ok) {
            console.error(`响应错误: ${response.status} ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('解析响应数据:', data);
        
        if (data.success) {
            // 更新按钮状态
            const newState = data.is_published;
            console.log(`更新按钮状态为: ${newState ? '已发表' : '未发表'}`);
            
            buttonElement.setAttribute('data-published', newState ? 'true' : 'false');
            buttonElement.innerHTML = newState ? '✅' : '❌';
            buttonElement.title = newState ? '已发表' : '未发表';
            
            // 显示成功消息
            showNotification('成功', data.message, 'success');
        } else {
            // 恢复按钮原始状态
            console.error('请求失败:', data.message);
            buttonElement.innerHTML = originalHtml;
            buttonElement.title = originalTitle;
            
            // 显示错误消息
            showNotification('错误', data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('请求异常:', error);
        
        // 恢复按钮原始状态
        buttonElement.innerHTML = originalHtml;
        buttonElement.title = originalTitle;
        
        showNotification('错误', '操作失败，请检查网络连接和控制台日志', 'danger');
    });
}

// 根据选择的策略显示或隐藏相应的参数输入框
function initStrategySelector() {
    // 获取所有策略选择器元素
    const strategySelectors = document.querySelectorAll('#commentStrategy');
    if (strategySelectors.length === 0) {
        console.warn('页面上没有找到策略选择器');
        return;
    }
    
    console.log(`找到 ${strategySelectors.length} 个策略选择器，开始初始化...`);
    
    // 为每个策略选择器添加事件监听并处理初始状态
    strategySelectors.forEach((selector, index) => {
        console.log(`初始化第 ${index + 1} 个策略选择器`);
        
        // 更新参数区域显示的函数
        const updateStrategyParams = function(strategy) {
            // 找到距离当前选择器最近的参数区域容器
            const paramsContainer = selector.closest('.movie-collect-area').querySelector('#strategyParams');
            if (!paramsContainer) {
                console.warn(`未找到与选择器 ${index + 1} 相关联的参数容器`);
                return;
            }
            
            // 隐藏所有参数区域
            const paramAreas = paramsContainer.querySelectorAll('[class$="-param"]');
            paramAreas.forEach(function(area) {
                area.style.display = 'none';
            });
            
            // 显示当前选择的策略参数区域
            if (strategy === 'random') {
                // 随机策略不需要额外参数
                console.log('选择了随机策略，不显示参数输入区域');
                return;
            }
            
            // 显示对应策略的参数区域
            const strategyParams = paramsContainer.querySelectorAll(`.${strategy}-param`);
            if (strategyParams.length > 0) {
                console.log(`显示策略 "${strategy}" 的 ${strategyParams.length} 个参数输入区域`);
                strategyParams.forEach(param => {
                    param.style.display = 'block';
                });
            } else {
                console.warn(`未找到策略 "${strategy}" 的参数输入区域`);
            }
        };
        
        // 监听选择器的change事件
        selector.addEventListener('change', function() {
            const strategy = this.value;
            console.log(`策略选择器 ${index + 1} 切换为: ${strategy}`);
            updateStrategyParams(strategy);
        });
        
        // 立即触发一次更新，确保页面加载时显示正确的参数区域
        const currentStrategy = selector.value;
        console.log(`触发策略选择器 ${index + 1} 的初始状态更新，当前策略: ${currentStrategy}`);
        updateStrategyParams(currentStrategy);
    });
}

// 带策略参数的电影采集函数
function crawlMovieWithStrategy() {
    console.log("crawlMovieWithStrategy 函数被调用");
    
    // 从表单获取电影名称
    const movieName = document.getElementById('movieName').value;
    console.log("电影名称:", movieName);
    
    if (!movieName) {
        alert('请输入电影名称');
        return;
    }
    
    // 从表单获取策略
    const strategy = document.getElementById('commentStrategy').value;
    console.log("采集策略:", strategy);
    
    // 获取CSRF令牌
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // 准备策略参数对象
    const strategy_params = {};
    
    // 根据不同策略添加额外参数
    switch (strategy) {
        case 'sequential':
            strategy_params.maxPages = document.getElementById('maxPages').value;
            break;
        case 'random_pages':
            strategy_params.sampleSize = document.getElementById('sampleSize').value;
            break;
        case 'random_interval':
            strategy_params.maxInterval = document.getElementById('maxInterval').value;
            break;
        case 'random_block':
            strategy_params.blockSize = document.getElementById('blockSize').value;
            break;
    }
    
    // 显示状态
    const statusEl = document.getElementById('crawlStatus');
    if (statusEl) {
        statusEl.innerHTML = '<div class="alert alert-info">正在采集中，请稍候...</div>';
    }
    
    // 准备请求数据
    const requestData = {
        movie_name: movieName,
        comment_strategy: strategy,
        strategy_params: strategy_params
    };
    
    console.log("请求数据:", JSON.stringify(requestData));
    
    // 发送请求
    fetch('/crawl_movie/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        console.log("收到响应:", response.status);
        
        if (!response.ok) {
            return response.text().then(text => {
                console.error('服务器响应错误:', text);
                throw new Error(`服务器响应错误: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log("响应数据:", data);
        
        if (data.success) {
            if (statusEl) {
                statusEl.innerHTML = '<div class="alert alert-success">采集任务已启动，请稍后查看结果</div>';
                // 3秒后自动清除状态
                setTimeout(() => {
                    statusEl.innerHTML = '';
                }, 3000);
            }
        } else {
            if (statusEl) {
                statusEl.innerHTML = `<div class="alert alert-danger">采集失败: ${data.error || '未知错误'}</div>`;
            }
        }
    })
    .catch(error => {
        console.error('采集请求失败:', error);
        if (statusEl) {
            statusEl.innerHTML = `<div class="alert alert-danger">采集请求出错: ${error.message || error}</div>`;
        }
    });
}

// 获取策略的显示名称
function getStrategyDisplayName(strategy) {
    const strategyNames = {
        'sequential': '顺序采集策略',
        'random_pages': '随机页码策略',
        'random_interval': '随机间隔策略',
        'random_block': '随机区块策略',
        'random': '随机选择策略'
    };
    
    return strategyNames[strategy] || strategy;
}

// 当DOM加载完成时执行初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM加载完成，初始化功能...');
    
    // 初始化状态切换按钮
    initTogglePublishedButtons();
    
    // 初始化策略选择器
    initStrategySelector();
});

// 添加处理会话过期的函数
function handleSessionExpired(error) {
    console.error('检测到会话可能已过期:', error);
    // 显示会话过期提示
    const notification = document.createElement('div');
    notification.className = 'alert alert-warning alert-dismissible fade show notification-toast';
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.innerHTML = `
        <strong>提示</strong> 您的会话可能已过期，3秒后将自动跳转至登录页面。
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.body.appendChild(notification);
    
    // 3秒后重定向到登录页面
    setTimeout(() => {
        window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname);
    }, 3000);
}

// 豆瓣数据采集脚本
document.addEventListener('DOMContentLoaded', function() {
    // 监听策略选择变化，显示相应的参数设置
    const strategySelect = document.getElementById('commentStrategy');
    if (strategySelect) {
        strategySelect.addEventListener('change', updateStrategyParams);
        // 初始化显示
        updateStrategyParams();
    }
});

// 更新策略参数显示
function updateStrategyParams() {
    const strategy = document.getElementById('commentStrategy').value;
    // 隐藏所有参数
    document.querySelectorAll('[class$="-param"]').forEach(el => {
        el.style.display = 'none';
    });
    
    // 显示当前策略的参数
    document.querySelectorAll(`.${strategy}-param`).forEach(el => {
        el.style.display = 'block';
    });
}

// 切换电影发布状态
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.toggle-published').forEach(button => {
        button.addEventListener('click', function() {
            const movieId = this.dataset.id;
            const isPublished = this.dataset.published === 'true';
            
            // 获取CSRF令牌
            const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            // 发送请求
            fetch(`/douban/movies/${movieId}/toggle_published/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({
                    is_published: !isPublished
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 更新按钮状态
                    this.dataset.published = (!isPublished).toString();
                    this.innerHTML = !isPublished ? '✅' : '❌';
                    this.title = !isPublished ? '已发表' : '未发表';
                } else {
                    alert('操作失败: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('发生错误，请重试');
            });
        });
    });
});

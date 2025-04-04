// 获取CSRF token的函数
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// 打开豆瓣设置模态框
function openDoubanSettings() {
    fetch('/douban/settings/', {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('crawl_interval').value = data.data.crawl_interval;
            document.getElementById('movie_count').value = data.data.movie_count;
            document.getElementById('tv_count').value = data.data.tv_count;
            const modal = new bootstrap.Modal(document.getElementById('doubanSettingsModal'));
            modal.show();
        } else {
            showNotification('错误', '加载设置失败：' + data.error, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('错误', '加载设置失败，请检查网络连接', 'danger');
    });
}

// 保存豆瓣设置
function saveDoubanSettings() {
    const formData = new FormData(document.getElementById('doubanSettingsForm'));
    
    fetch('/douban/settings/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('成功', '豆瓣设置已保存', 'success');
            const modal = bootstrap.Modal.getInstance(document.getElementById('doubanSettingsModal'));
            modal.hide();
        } else {
            showNotification('错误', '保存失败：' + data.error, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('错误', '保存设置失败，请检查网络连接', 'danger');
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
    // 尝试从不同的输入框获取电影名称，兼容不同页面
    const movieNameElement = document.getElementById('movieName');
    
    let movieName = '';
    if (movieNameElement) {
        movieName = movieNameElement.value.trim();
    }
    
    if (!movieName) {
        alert('请输入电影名称');
        return;
    }
    
    // 获取选择的策略和参数
    const strategySelector = document.getElementById('commentStrategy');
    if (!strategySelector) {
        alert('找不到策略选择器');
        return;
    }
    
    const strategy = strategySelector.value;
    const params = {};
    let paramError = null;
    
    // 根据不同策略获取参数并验证
    if (strategy === 'sequential') {
        const maxPagesElement = document.getElementById('maxPages');
        const maxPages = parseInt(maxPagesElement.value, 10);
        
        if (isNaN(maxPages) || maxPages < 1) {
            paramError = '最大页数必须是大于0的整数';
        } else if (maxPages > 50) {
            paramError = '最大页数不应超过50页';
        } else {
            params.max_pages = maxPages;
            console.log(`使用顺序采集策略，最大页数: ${params.max_pages}`);
        }
    } else if (strategy === 'random_pages') {
        const sampleSizeElement = document.getElementById('sampleSize');
        const sampleSize = parseInt(sampleSizeElement.value, 10);
        
        if (isNaN(sampleSize) || sampleSize < 1) {
            paramError = '采样页数必须是大于0的整数';
        } else if (sampleSize > 30) {
            paramError = '采样页数不应超过30页';
        } else {
            params.sample_size = sampleSize;
            console.log(`使用随机页码策略，采样页数: ${params.sample_size}`);
        }
    } else if (strategy === 'random_interval') {
        const maxIntervalElement = document.getElementById('maxInterval');
        const maxPagesElement = document.getElementById('maxPages');
        const maxInterval = parseInt(maxIntervalElement.value, 10);
        const maxPages = parseInt(maxPagesElement.value, 10);
        
        if (isNaN(maxInterval) || maxInterval < 1) {
            paramError = '最大间隔必须是大于0的整数';
        } else if (maxInterval > 20) {
            paramError = '最大间隔不应超过20页';
        } else if (isNaN(maxPages) || maxPages < 1) {
            paramError = '最大页数必须是大于0的整数';
        } else if (maxPages > 50) {
            paramError = '最大页数不应超过50页';
        } else {
            params.max_interval = maxInterval;
            params.max_pages = maxPages;
            console.log(`使用随机间隔策略，最大间隔: ${params.max_interval}, 最大页数: ${params.max_pages}`);
        }
    } else if (strategy === 'random_block') {
        const blockSizeElement = document.getElementById('blockSize');
        const blockSize = parseInt(blockSizeElement.value, 10);
        
        if (isNaN(blockSize) || blockSize < 1) {
            paramError = '区块大小必须是大于0的整数';
        } else if (blockSize > 20) {
            paramError = '区块大小不应超过20页';
        } else {
            params.block_size = blockSize;
            console.log(`使用随机区块策略，区块大小: ${params.block_size}`);
        }
    } else if (strategy === 'random') {
        // 随机策略不需要额外参数，系统会自动选择一种策略
        params.use_random_strategy = true;
        console.log('使用随机选择策略，系统将随机选择一种采集策略');
    }
    
    // 如果参数验证失败，显示错误并退出
    if (paramError) {
        alert('参数错误: ' + paramError);
        return;
    }
    
    // 获取状态元素并确保其存在
    const statusElement = document.getElementById('crawlStatus');
    if (statusElement) {
        const strategyText = getStrategyDisplayName(strategy);
        statusElement.innerHTML = `<div class="alert alert-info">
            <strong>正在采集电影:</strong> ${movieName}<br>
            <strong>采集策略:</strong> ${strategyText}<br>
            <small class="text-muted">请稍候，此过程可能需要几分钟...</small>
        </div>`;
    } else {
        console.warn('找不到crawlStatus元素，无法显示状态更新');
    }
    
    // 获取提交按钮和原始文本
    const submitButton = movieNameElement ? movieNameElement.nextElementSibling : null;
    const originalButtonText = submitButton ? submitButton.innerHTML : '';
    
    // 禁用按钮并显示加载状态
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 采集中...';
    }
    
    console.log(`发送采集请求: 电影=${movieName}, 策略=${strategy}, 参数=`, params);
    
    // 发送采集请求，包含策略参数
    fetch('/crawl_movie/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            movie_name: movieName,
            comment_strategy: strategy,
            strategy_params: params
        })
    })
    .then(response => {
        console.log(`收到响应，状态码: ${response.status}`);
        // 检查响应是否包含JSON
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        } else {
            // 如果响应不是JSON，获取文本并抛出错误
            return response.text().then(text => {
                throw new Error('服务器返回了非JSON响应，可能需要重新登录');
            });
        }
    })
    .then(data => {
        console.log('解析响应数据:', data);
        
        if (data.status === 'success' || data.success === true) {
            if (statusElement) {
                // 处理成功响应
                const successMessage = data.message || '采集已开始，请稍后查看结果';
                const movieId = data.movie_id;
                
                if (movieId) {
                    statusElement.innerHTML = `<div class="alert alert-success">
                        <strong>采集完成!</strong> ${successMessage}<br>
                        <a href="/douban/movies/${movieId}/" class="alert-link">查看电影详情</a>
                    </div>`;
                } else {
                    statusElement.innerHTML = `<div class="alert alert-success">
                        <strong>采集已开始!</strong> ${successMessage}<br>
                        <small>系统正在后台处理，请稍后刷新页面查看结果</small>
                    </div>`;
                    
                    // 10秒后自动刷新页面
                    setTimeout(() => {
                        statusElement.innerHTML += '<div class="text-center"><small>页面将在5秒后自动刷新...</small></div>';
                        setTimeout(() => {
                            window.location.reload();
                        }, 5000);
                    }, 5000);
                }
            } else {
                alert('采集请求已发送');
            }
        } else {
            if (statusElement) {
                // 处理错误响应
                const errorMessage = data.message || data.error || '未知错误';
                statusElement.innerHTML = `<div class="alert alert-warning">
                    <strong>提示:</strong> ${errorMessage}
                </div>`;
            } else {
                alert('采集请求出现问题：' + (data.message || data.error || '未知错误'));
            }
        }
    })
    .catch(error => {
        console.error('请求出错:', error);
        if (statusElement) {
            statusElement.innerHTML = `<div class="alert alert-danger">
                <strong>请求出错:</strong> ${error.message}<br>
                <small>请检查网络连接或稍后重试</small>
            </div>`;
        } else {
            alert('请求出错：' + error.message);
        }
        
        // 检查是否是会话过期错误
        if (error.message && (error.message.includes('非JSON响应') || 
            error.message.includes('登录'))) {
            handleSessionExpired(error);
        }
    })
    .finally(() => {
        // 恢复按钮状态
        if (submitButton) {
            setTimeout(() => {
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            }, 2000);
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

// 获取CSRF token的函数
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// IP采集函数
async function runOneCrawl() {
    const button = document.getElementById('runCrawlBtn');
    if (!button) {
        console.error('未找到采集按钮(ID: runCrawlBtn)');
        return;
    }

    console.log('找到采集按钮:', button);
    
    // 保存原始文本
    const originalText = button.innerHTML;
    
    // 显示加载状态 - 使用与豆瓣页面相同的加载样式
    button.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> 采集中...';
    button.disabled = true;
    
    try {
        console.log('开始执行采集请求...');
        
        const response = await fetch('/crawl_once/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json'
            }
        });
        
        console.log('采集请求响应状态:', response.status);
        
        const data = await response.json();
        console.log('采集响应数据:', data);
        
        if (data.success) {
            showNotification('成功', 'IP采集任务已启动，请稍后刷新页面查看结果', 'success');
            // 10秒后自动刷新页面
            setTimeout(() => {
                location.reload();
            }, 10000);
        } else {
            showNotification('错误', '采集请求失败: ' + (data.error || '未知错误'), 'danger');
        }
    } catch (error) {
        console.error('采集请求出错:', error);
        showNotification('错误', '网络请求失败，请稍后重试', 'danger');
    } finally {
        // 恢复按钮状态
        setTimeout(() => {
            button.innerHTML = originalText;
            button.disabled = false;
        }, 2000);
    }
}

// IP评分函数
async function runOneScore() {
    const button = document.getElementById('scoreBtn');
    if (!button) {
        console.error('未找到评分按钮(ID: scoreBtn)');
        return;
    }

    if (!confirm('确定要执行一次打分吗？')) {
        return;
    }
    
    console.log('找到评分按钮:', button);
    
    // 保存原始文本
    const originalText = button.innerHTML;
    
    // 显示加载状态 - 使用与豆瓣页面相同的加载样式
    button.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> 评分中...';
    button.disabled = true;
    
    try {
        console.log('开始执行打分请求...');
        
        const response = await fetch('/score_once/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json'
            }
        });
        
        console.log('打分请求响应状态:', response.status);
        
        const data = await response.json();
        console.log('打分响应数据:', data);
        
        if (data.success) {
            showNotification('成功', 'IP评分任务已启动，请稍后刷新页面查看结果', 'success');
            // 10秒后自动刷新页面
            setTimeout(() => {
                location.reload();
            }, 10000);
        } else {
            showNotification('错误', '评分请求失败: ' + (data.error || '未知错误'), 'danger');
        }
    } catch (error) {
        console.error('评分请求出错:', error);
        showNotification('错误', '网络请求失败，请稍后重试', 'danger');
    } finally {
        // 恢复按钮状态
        setTimeout(() => {
            button.innerHTML = originalText;
            button.disabled = false;
        }, 2000);
    }
}

// 打开设置模态框时加载当前设置
function openSettingsModal() {
    fetch('/proxy_settings/', {
        method: 'GET',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('crawler_interval').value = data.data.crawler_interval;
            document.getElementById('score_interval').value = data.data.score_interval;
            document.getElementById('min_score').value = data.data.min_score;
            const settingsModal = new bootstrap.Modal(document.getElementById('settingsModal'));
            settingsModal.show();
        } else {
            alert('加载设置失败：' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('加载设置失败');
    });
}

// 保存设置
function saveSettings() {
    const formData = new FormData(document.getElementById('settingsForm'));
    
    // 获取自动爬虫和自动评分的开关状态
    formData.append('auto_crawler', document.getElementById('auto_crawler').checked ? 'on' : 'off');
    formData.append('auto_score', document.getElementById('auto_score').checked ? 'on' : 'off');
    
    fetch('/proxy_settings/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('代理设置已保存');
            const modal = bootstrap.Modal.getInstance(document.getElementById('settingsModal'));
            modal.hide();
        } else {
            alert('保存失败：' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('保存设置失败');
    });
}

// IP池管理页面脚本
document.addEventListener('DOMContentLoaded', function() {
    console.log('IP池管理页面加载完成');
    initSearchBox();
    initTableActions();
});

// 初始化搜索框功能
function initSearchBox() {
    const searchBox = document.querySelector('.search-box input');
    if (searchBox) {
        searchBox.addEventListener('input', function() {
            const query = this.value.toLowerCase().trim();
            const rows = document.querySelectorAll('.data-table tbody tr');
            
            rows.forEach(row => {
                const server = row.querySelector('td:first-child').textContent.toLowerCase();
                if (server.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
}

// 初始化表格操作
function initTableActions() {
    // 为所有操作按钮添加点击事件
    document.querySelectorAll('.btn-icon').forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.getAttribute('title');
            const row = this.closest('tr');
            const server = row.querySelector('td:first-child').textContent;
            
            switch(action) {
                case '详情':
                    showIpDetails(server);
                    break;
                case '更新':
                    updateIp(server);
                    break;
                case '删除':
                    deleteIp(server);
                    break;
            }
        });
    });
}

// 显示IP详情
function showIpDetails(server) {
    // 获取IP详细信息
    fetch(`/ip_details/${server}/`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 创建并显示详情模态框
                const modal = new bootstrap.Modal(document.getElementById('ipDetailsModal'));
                document.getElementById('ipDetailsContent').innerHTML = `
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>IP地址：</strong>${data.data.server}</p>
                            <p><strong>国家：</strong>${data.data.country}</p>
                            <p><strong>城市：</strong>${data.data.city}</p>
                            <p><strong>运营商：</strong>${data.data.isp}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>评分：</strong>${data.data.score}</p>
                            <p><strong>延迟：</strong>${data.data.ping}ms</p>
                            <p><strong>速度：</strong>${data.data.speed}MB/s</p>
                            <p><strong>最后更新：</strong>${data.data.updated_at}</p>
                        </div>
                    </div>
                `;
                modal.show();
            } else {
                showNotification('错误', data.error || '获取详情失败', 'danger');
            }
        })
        .catch(error => {
            console.error('获取IP详情失败:', error);
            showNotification('错误', '网络请求失败', 'danger');
        });
}

// 更新IP信息
function updateIp(server) {
    const button = document.querySelector(`tr[data-server="${server}"] .btn-icon[title="更新"]`);
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
    
    fetch(`/update_ip/${server}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('成功', 'IP信息更新成功', 'success');
            setTimeout(() => location.reload(), 2000);
        } else {
            showNotification('错误', data.error || '更新失败', 'danger');
        }
    })
    .catch(error => {
        console.error('更新IP失败:', error);
        showNotification('错误', '网络请求失败', 'danger');
    })
    .finally(() => {
        button.disabled = false;
        button.innerHTML = '🔄';
    });
}

// 删除IP
function deleteIp(server) {
    if (confirm(`确定要删除IP ${server} 吗？`)) {
        fetch(`/delete_ip/${server}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('成功', 'IP删除成功', 'success');
                setTimeout(() => location.reload(), 2000);
            } else {
                showNotification('错误', data.error || '删除失败', 'danger');
            }
        })
        .catch(error => {
            console.error('删除IP失败:', error);
            showNotification('错误', '网络请求失败', 'danger');
        });
    }
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

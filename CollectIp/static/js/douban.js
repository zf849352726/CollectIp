// 获取CSRF token的函数
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// 打开豆瓣设置模态框
function openDoubanSettings() {
    fetch('/douban_settings/', {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCSRFToken(),
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
            alert('加载设置失败：' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('加载设置失败');
    });
}

// 保存豆瓣设置
function saveDoubanSettings() {
    const formData = new FormData(document.getElementById('doubanSettingsForm'));
    
    fetch('/douban_settings/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCSRFToken(),
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('豆瓣设置已保存');
            const modal = bootstrap.Modal.getInstance(document.getElementById('doubanSettingsModal'));
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

// 采集电影数据
function crawlMovie() {
    const movieName = document.getElementById('movieName').value.trim();
    const crawlButton = document.querySelector('button.btn-primary');
    
    if (!movieName) {
        alert('请输入电影名称');
        return;
    }
    
    // 禁用按钮并显示加载状态
    crawlButton.disabled = true;
    crawlButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 正在采集...';
    
    // 获取CSRF令牌
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');
    
    fetch('/crawl_movie/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            movie_name: movieName
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 显示成功消息
            showNotification('成功', `电影 "${movieName}" 数据采集任务已启动，请稍后刷新页面查看结果`, 'success');
            
            // 10秒后自动刷新页面
            setTimeout(() => {
                location.reload();
            }, 10000);
        } else {
            // 显示错误消息
            showNotification('错误', '采集请求失败: ' + (data.error || '未知错误'), 'danger');
        }
    })
    .catch(error => {
        console.error('采集请求出错:', error);
        showNotification('错误', '网络请求失败，请稍后重试', 'danger');
    })
    .finally(() => {
        // 恢复按钮状态
        setTimeout(() => {
            crawlButton.disabled = false;
            crawlButton.innerHTML = '采集数据';
        }, 2000);
    });
}

// 显示通知消息
function showNotification(title, message, type = 'info') {
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show notification-toast`;
    notification.innerHTML = `
        <strong>${title}</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 自动消失
    setTimeout(() => {
        notification.classList.remove('show');
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

// 获取CSRF token的函数
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// IP采集函数
async function runOneCrawl() {
    if (!confirm('确定要执行一次采集吗？')) {
        return;
    }
    
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
            alert('IP采集任务已启动');
        } else {
            alert('采集请求失败: ' + data.error);
        }
    } catch (error) {
        console.error('采集请求出错:', error);
        alert('采集请求出错');
    }
}

// IP评分函数
async function runOneScore() {
    if (!confirm('确定要执行一次打分吗？')) {
        return;
    }
    
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
            alert('IP评分任务已启动');
        } else {
            alert('评分请求失败: ' + data.error);
        }
    } catch (error) {
        console.error('评分请求出错:', error);
        alert('评分请求出错');
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

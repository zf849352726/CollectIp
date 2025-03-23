// 模态框控制
function openSettingsModal() {
    document.getElementById('settingsModal').style.display = 'block';
    // 获取当前设置
    fetchCurrentSettings();
}

function closeSettingsModal() {
    document.getElementById('settingsModal').style.display = 'none';
}

// 点击模态框外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('settingsModal');
    if (event.target == modal) {
        closeSettingsModal();
    }
}

// 获取当前设置
async function fetchCurrentSettings() {
    try {
        const response = await fetch('/proxy/settings/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
            throw new TypeError("返回的不是JSON数据!");
        }
        
        const data = await response.json();
        console.log('Received settings:', data); // 调试日志
        
        if (data.success) {
            document.getElementById('crawler_interval').value = data.data.crawler_interval;
            document.getElementById('score_interval').value = data.data.score_interval;
            document.getElementById('min_score').value = data.data.min_score;
        } else {
            throw new Error(data.error || '获取设置失败');
        }
    } catch (error) {
        console.error('获取设置失败:', error);
        alert('获取设置失败: ' + error.message);
    }
}

// 表单提交处理
document.getElementById('settingsForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    try {
        const response = await fetch('/proxy/settings/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Save settings response:', result); // 调试日志
        
        if (result.success) {
            alert('设置已更新');
            closeSettingsModal();
        } else {
            throw new Error(result.error || '更新失败');
        }
    } catch (error) {
        console.error('保存设置失败:', error);
        alert('保存设置失败: ' + error.message);
    }
});

// 输入验证
document.querySelectorAll('.settings-form input[type="number"]').forEach(input => {
    input.addEventListener('input', function() {
        const min = parseInt(this.getAttribute('min'));
        const max = parseInt(this.getAttribute('max'));
        const value = parseInt(this.value);
        
        if (value < min) {
            this.value = min;
        } else if (max && value > max) {
            this.value = max;
        }
    });
}); 
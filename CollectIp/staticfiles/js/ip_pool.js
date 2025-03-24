// 执行一次IP采集
async function runOneCrawl() {
    try {
        console.log('开始执行采集请求...');
        const response = await fetch('/crawl_once/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            }
        });
        
        console.log('采集请求响应状态:', response.status);
        const data = await response.json();
        
        if (data.success) {
            alert('已开始执行IP采集');
        } else {
            alert('采集失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        console.error('采集请求出错:', error);
        alert('采集请求出错: ' + error.message);
    }
}

// 执行一次IP打分
async function runOneScore() {
    try {
        console.log('开始执行打分请求...');
        const response = await fetch('/score_once/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            }
        });
        
        console.log('打分请求响应状态:', response.status);
        const data = await response.json();
        
        if (data.success) {
            alert('已开始执行IP打分');
        } else {
            alert('打分失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        console.error('打分请求出错:', error);
        alert('打分请求出错: ' + error.message);
    }
}

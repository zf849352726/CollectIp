/**
 * 日志管理页面的交互逻辑
 */
document.addEventListener('DOMContentLoaded', function() {
    // 日志类型过滤器
    const logTypeFilter = document.getElementById('logTypeFilter');
    
    // 确保Apache选项存在，如果不存在则添加
    let hasApacheOption = false;
    for (let i = 0; i < logTypeFilter.options.length; i++) {
        if (logTypeFilter.options[i].value === 'apache') {
            hasApacheOption = true;
            break;
        }
    }
    
    if (!hasApacheOption) {
        const apacheOption = document.createElement('option');
        apacheOption.value = 'apache';
        apacheOption.textContent = 'Apache服务器日志';
        logTypeFilter.appendChild(apacheOption);
    }
    
    logTypeFilter.addEventListener('change', filterLogs);
    
    // 刷新按钮
    const refreshBtn = document.getElementById('refreshLogs');
    refreshBtn.addEventListener('click', function() {
        window.location.reload();
    });
    
    // 查看日志按钮
    const viewLogBtns = document.querySelectorAll('.view-log-btn');
    viewLogBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const logPath = this.getAttribute('data-log-path');
            openLogModal(logPath);
        });
    });
    
    // 自动滚动到底部
    const autoScrollCheckbox = document.getElementById('autoScroll');
    
    // 搜索日志内容
    const searchLogBtn = document.getElementById('searchLogBtn');
    const logSearch = document.getElementById('logSearch');
    
    searchLogBtn.addEventListener('click', searchInLog);
    logSearch.addEventListener('keyup', function(event) {
        if (event.key === 'Enter') {
            searchInLog();
        }
    });
    
    // 下载日志按钮
    const downloadLogBtn = document.getElementById('downloadLogBtn');
    let currentLogPath = '';
    
    downloadLogBtn.addEventListener('click', function() {
        if (currentLogPath) {
            window.location.href = `/api/logs/download/?path=${encodeURIComponent(currentLogPath)}`;
        }
    });
    
    // 过滤日志卡片
    function filterLogs() {
        const selectedType = logTypeFilter.value;
        const logCards = document.querySelectorAll('.log-card');
        
        logCards.forEach(card => {
            const cardType = card.getAttribute('data-type');
            if (selectedType === 'all' || cardType === selectedType) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    }
    
    // 打开日志查看模态框
    function openLogModal(logPath) {
        currentLogPath = logPath;
        const logContent = document.getElementById('logContent');
        
        // 显示加载中
        logContent.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2">加载日志内容中...</p>
            </div>
        `;
        
        // 显示模态框
        const modal = new bootstrap.Modal(document.getElementById('logViewModal'));
        modal.show();
        
        // 获取日志内容
        fetch(`/api/logs/content/?path=${encodeURIComponent(logPath)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP错误! 状态: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    let logHTML = '';
                    const lines = data.content.split('\n');
                    
                    lines.forEach((line, index) => {
                        // 添加日志类型样式
                        let lineClass = '';
                        if (line.includes('ERROR') || line.includes('CRITICAL')) {
                            lineClass = 'text-danger';
                        } else if (line.includes('WARNING')) {
                            lineClass = 'text-warning';
                        } else if (line.includes('INFO')) {
                            lineClass = 'text-info';
                        } else if (line.includes('DEBUG')) {
                            lineClass = 'text-secondary';
                        }
                        
                        logHTML += `<div class="log-line ${lineClass}">${line}</div>`;
                    });
                    
                    logContent.innerHTML = logHTML;
                    
                    // 如果选中了自动滚动，则滚动到底部
                    if (autoScrollCheckbox.checked) {
                        logContent.scrollTop = logContent.scrollHeight;
                    }
                } else {
                    logContent.innerHTML = `<div class="text-danger p-3">加载日志失败: ${data.message}</div>`;
                }
            })
            .catch(error => {
                logContent.innerHTML = `<div class="text-danger p-3">加载日志错误: ${error.message}</div>`;
                console.error('日志加载错误:', error);
            });
    }
    
    // 搜索日志内容
    function searchInLog() {
        const searchTerm = logSearch.value.toLowerCase().trim();
        if (!searchTerm) return;
        
        const logLines = document.querySelectorAll('.log-line');
        let firstMatch = null;
        
        logLines.forEach(line => {
            line.classList.remove('bg-light');
            if (line.textContent.toLowerCase().includes(searchTerm)) {
                line.classList.add('bg-light');
                if (!firstMatch) {
                    firstMatch = line;
                }
            }
        });
        
        if (firstMatch) {
            firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
}); 
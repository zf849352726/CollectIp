// wechat.js - 微信公众号管理相关JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('微信公众号管理页面已加载');
    
    // 加载设置
    loadSettings();
});

// 加载设置
function loadSettings() {
    // 未来可以通过AJAX加载公众号设置
    console.log('加载公众号设置');
    
    // 模拟AJAX请求获取设置
    // fetch('/wechat_settings/')
    //    .then(response => response.json())
    //    .then(data => {
    //        if (data.success) {
    //            document.getElementById('appid').value = data.data.appid;
    //            document.getElementById('appsecret').value = data.data.appsecret;
    //            document.getElementById('token').value = data.data.token;
    //            document.getElementById('auto_sync').checked = data.data.auto_sync;
    //            document.getElementById('sync_interval').value = data.data.sync_interval;
    //        }
    //    })
    //    .catch(error => console.error('Error:', error));
}

// 打开设置模态框
function openSettingsModal() {
    // 使用全局openModal函数打开模态框
    if (window.openModal) {
        window.openModal('settingsModal');
    } else {
        // 备用方法
        const modal = new bootstrap.Modal(document.getElementById('settingsModal'));
        modal.show();
    }
}

// 保存微信公众号设置
function saveWechatSettings() {
    const formData = new FormData(document.getElementById('wechatSettingsForm'));
    
    // 获取自动同步的开关状态
    formData.append('auto_sync', document.getElementById('auto_sync').checked ? 'on' : 'off');
    
    // 模拟AJAX请求保存设置
    console.log('保存公众号设置');
    console.log('AppID:', formData.get('appid'));
    console.log('Auto Sync:', formData.get('auto_sync'));
    console.log('Sync Interval:', formData.get('sync_interval'));
    
    // 实际的AJAX请求代码
    // fetch('/wechat_settings/', {
    //     method: 'POST',
    //     body: formData,
    //     headers: {
    //         'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
    //     }
    // })
    // .then(response => response.json())
    // .then(data => {
    //     if (data.success) {
    //         alert('公众号设置已保存');
    //         const modal = bootstrap.Modal.getInstance(document.getElementById('settingsModal'));
    //         modal.hide();
    //     } else {
    //         alert('保存失败：' + data.error);
    //     }
    // })
    // .catch(error => {
    //     console.error('Error:', error);
    //     alert('保存设置失败');
    // });
    
    // 模拟保存成功关闭模态框
    alert('公众号设置已保存（模拟）');
    const modal = bootstrap.Modal.getInstance(document.getElementById('settingsModal'));
    if (modal) modal.hide();
}

// 电影合集相关功能

// 创建新电影
function createNewMovie() {
    console.log('创建新电影');
    // 实现创建新电影的逻辑
    alert('创建新电影功能将在此实现');
}

// 同步电影信息
function syncMovies() {
    console.log('同步电影信息');
    // 实现同步电影信息的逻辑
    
    // 显示加载中提示
    const loadingMessage = document.createElement('div');
    loadingMessage.className = 'alert alert-info';
    loadingMessage.textContent = '正在同步电影信息，请稍候...';
    document.querySelector('.content-body').prepend(loadingMessage);
    
    // 模拟同步过程
    setTimeout(() => {
        loadingMessage.className = 'alert alert-success';
        loadingMessage.textContent = '电影信息同步完成！';
        
        // 3秒后移除提示
        setTimeout(() => {
            loadingMessage.remove();
        }, 3000);
    }, 2000);
}

// 文章管理相关功能

// 新建图文
function createArticle() {
    console.log('新建图文');
    // 实现新建图文的逻辑
    alert('创建新图文功能将在此实现');
}

// 批量发布
function batchPublish() {
    console.log('批量发布');
    // 实现批量发布的逻辑
    alert('批量发布功能将在此实现');
}

// 编辑图文
function editArticle(articleId) {
    console.log('编辑图文: ' + articleId);
    // 实现编辑图文的逻辑
}

// 删除图文
function deleteArticle(articleId) {
    if (confirm('确定要删除这篇图文吗？此操作不可撤销')) {
        console.log('删除图文: ' + articleId);
        // 实现删除图文的逻辑
    }
}

// 预览图文
function previewArticle(articleId) {
    console.log('预览图文: ' + articleId);
    // 实现预览图文的逻辑
    window.open('/preview_article/' + articleId, '_blank');
}

// 素材库相关功能

// 上传素材
function uploadMedia() {
    console.log('上传素材');
    // 实现上传素材的逻辑
    alert('上传素材功能将在此实现');
}

// 创建文件夹
function createFolder() {
    console.log('创建文件夹');
    // 实现创建文件夹的逻辑
    const folderName = prompt('请输入文件夹名称:');
    if (folderName) {
        console.log('创建文件夹:', folderName);
        alert(`已创建文件夹: ${folderName}`);
    }
}

// 初始化表格搜索功能
document.addEventListener('DOMContentLoaded', function() {
    const searchBoxes = document.querySelectorAll('.search-box input');
    searchBoxes.forEach(searchBox => {
        searchBox.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            
            // 根据当前激活的页面执行不同的搜索逻辑
            if (document.querySelector('.menu-item.active').textContent.trim() === '电影合集') {
                // 搜索电影
                const movieCards = document.querySelectorAll('.collection-card');
                movieCards.forEach(card => {
                    const title = card.querySelector('h3').textContent.toLowerCase();
                    const desc = card.querySelector('p').textContent.toLowerCase();
                    if (title.includes(searchTerm) || desc.includes(searchTerm)) {
                        card.style.display = '';
                    } else {
                        card.style.display = 'none';
                    }
                });
            } else if (document.querySelector('.menu-item.active').textContent.trim() === '剧集合集') {
                // 搜索文章
                const rows = document.querySelectorAll('.data-table tbody tr');
                rows.forEach(row => {
                    const title = row.querySelector('td:first-child').textContent.toLowerCase();
                    if (title.includes(searchTerm)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            }
        });
    });
});

// 绑定文档中所有按钮的事件
document.querySelectorAll('.add-article button').forEach(button => {
    button.addEventListener('click', createArticle);
});

// 为文章卡片中的按钮绑定事件
document.querySelectorAll('.article-actions button').forEach(button => {
    const articleCard = button.closest('.article-card');
    const articleId = articleCard ? articleCard.dataset.id : null;
    
    if (button.title === '编辑') {
        button.addEventListener('click', () => editArticle(articleId));
    } else if (button.title === '删除') {
        button.addEventListener('click', () => deleteArticle(articleId));
    } else if (button.title === '预览') {
        button.addEventListener('click', () => previewArticle(articleId));
    }
}); 
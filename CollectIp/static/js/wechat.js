// wechat.js - 微信公众号管理相关JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('微信公众号管理页面已加载');
    
    // 加载设置
    loadSettings();
    
    // 初始化合集模态框中的保存按钮
    initCollectionModal();
    
    // 初始化删除确认模态框
    initDeleteConfirmModal();
});

// 加载设置
function loadSettings() {
    // 根据当前页面加载适当的设置
    const activeMenu = document.querySelector('.menu-item.active');
    if (!activeMenu) return;
    
    // 根据活动菜单执行相应的初始化
    if (activeMenu.textContent.includes('数据概览')) {
        // 数据概览页面初始化
        console.log('初始化数据概览页面');
    } else if (activeMenu.textContent.includes('电影合集')) {
        // 电影合集页面初始化
        console.log('初始化电影合集页面');
    }
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

// 合集管理相关功能

// 打开创建合集模态框
function openCreateCollectionModal() {
    // 重置表单
    document.getElementById('collectionForm').reset();
    document.getElementById('collection_id').value = '';
    document.getElementById('collectionModalLabel').textContent = '创建新合集';
    
    // 加载电影列表供选择
    loadMoviesForSelection([]);
    
    // 显示模态框
    const modal = new bootstrap.Modal(document.getElementById('collectionModal'));
    modal.show();
}

// 编辑合集
function editCollection(collectionId) {
    fetch(`/api/collections/${collectionId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const collection = data.data;
                
                // 填充表单数据
                document.getElementById('collection_id').value = collection.id;
                document.getElementById('collection_title').value = collection.title;
                document.getElementById('collection_type').value = collection.collection_type;
                document.getElementById('collection_description').value = collection.description || '';
                document.getElementById('collection_cover').value = collection.cover_image || '';
                document.getElementById('collection_published').checked = collection.is_published;
                
                // 更新模态框标题
                document.getElementById('collectionModalLabel').textContent = '编辑合集';
                
                // 加载电影列表并选中已关联的电影
                loadMoviesForSelection(collection.movie_ids);
                
                // 显示模态框
                const modal = new bootstrap.Modal(document.getElementById('collectionModal'));
                modal.show();
            } else {
                showNotification('错误', data.message || '获取合集信息失败', 'error');
            }
        })
        .catch(error => {
            console.error('获取合集数据失败:', error);
            showNotification('错误', '获取合集信息失败', 'error');
        });
}

// 加载电影列表供选择
function loadMoviesForSelection(selectedMovieIds = []) {
    const container = document.getElementById('movieListContainer');
    container.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-primary" role="status"></div><span class="ms-2">加载电影列表中...</span></div>';
    
    fetch('/api/movies/selection/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                container.innerHTML = '';
                
                if (data.movies.length === 0) {
                    container.innerHTML = '<div class="text-center py-3">暂无电影数据</div>';
                    return;
                }
                
                data.movies.forEach(movie => {
                    const isSelected = selectedMovieIds.includes(movie.id);
                    const movieItem = document.createElement('div');
                    movieItem.className = 'movie-list-item';
                    movieItem.innerHTML = `
                        <input type="checkbox" class="form-check-input me-2" name="movie_checkbox" value="${movie.id}" ${isSelected ? 'checked' : ''}>
                        <img src="${movie.cover_image || 'https://via.placeholder.com/50x70'}" alt="${movie.title}">
                        <div class="movie-info">
                            <div class="movie-title">${movie.title}</div>
                            <div class="movie-meta">${movie.year} | 评分: ${movie.rating}</div>
                        </div>
                    `;
                    container.appendChild(movieItem);
                });
                
                // 初始化电影搜索
                initMovieSearch();
            } else {
                container.innerHTML = `<div class="text-center py-3 text-danger">${data.message || '加载电影失败'}</div>`;
            }
        })
        .catch(error => {
            console.error('加载电影列表失败:', error);
            container.innerHTML = '<div class="text-center py-3 text-danger">加载电影列表失败</div>';
        });
}

// 初始化电影搜索功能
function initMovieSearch() {
    const searchInput = document.getElementById('movieSearchInput');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase().trim();
        const movieItems = document.querySelectorAll('.movie-list-item');
        
        movieItems.forEach(item => {
            const title = item.querySelector('.movie-title').textContent.toLowerCase();
            if (title.includes(searchTerm)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

// 初始化全选电影功能
function initSelectAllMovies() {
    const selectAllBtn = document.getElementById('selectAllMovies');
    if (!selectAllBtn) return;
    
    selectAllBtn.addEventListener('click', function() {
        const checkboxes = document.querySelectorAll('input[name="movie_checkbox"]');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);
        
        checkboxes.forEach(checkbox => {
            checkbox.checked = !allChecked;
        });
        
        this.textContent = allChecked ? '全选' : '取消全选';
    });
}

// 初始化合集模态框
function initCollectionModal() {
    // 初始化电影选择相关功能
    initMovieSearch();
    initSelectAllMovies();
    
    // 保存合集按钮点击事件
    const saveBtn = document.getElementById('saveCollection');
    if (!saveBtn) return;
    
    saveBtn.addEventListener('click', function() {
        // 表单验证
        const form = document.getElementById('collectionForm');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        // 获取表单数据
        const collectionId = document.getElementById('collection_id').value;
        const title = document.getElementById('collection_title').value;
        const collectionType = document.getElementById('collection_type').value;
        const description = document.getElementById('collection_description').value;
        const coverImage = document.getElementById('collection_cover').value;
        const isPublished = document.getElementById('collection_published').checked;
        
        // 获取选中的电影ID
        const movieCheckboxes = document.querySelectorAll('input[name="movie_checkbox"]:checked');
        const movieIds = Array.from(movieCheckboxes).map(cb => parseInt(cb.value));
        
        // 准备提交的数据
        const formData = {
            title: title,
            collection_type: collectionType,
            description: description,
            cover_image: coverImage,
            is_published: isPublished,
            movie_ids: movieIds
        };
        
        // 确定是创建还是更新
        const url = collectionId ? `/api/collections/${collectionId}/update/` : '/api/collections/create/';
        const method = 'POST';
        
        // 发送请求
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // 关闭模态框
                bootstrap.Modal.getInstance(document.getElementById('collectionModal')).hide();
                
                // 显示成功通知
                showNotification('成功', collectionId ? '合集更新成功' : '合集创建成功', 'success');
                
                // 延迟刷新页面以显示最新数据
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification('错误', data.message || '操作失败，请重试', 'error');
            }
        })
        .catch(error => {
            console.error('保存合集失败:', error);
            showNotification('错误', '保存失败，请检查网络连接后重试', 'error');
        });
    });
}

// 删除合集
function deleteCollection(collectionId) {
    // 获取合集信息用于确认
    fetch(`/api/collections/${collectionId}/`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // 设置确认对话框信息
                document.getElementById('deleteCollectionName').textContent = data.data.title;
                document.getElementById('deleteCollectionId').value = collectionId;
                
                // 显示确认对话框
                const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
                modal.show();
            } else {
                showNotification('错误', data.message || '获取合集信息失败', 'error');
            }
        })
        .catch(error => {
            console.error('获取合集信息失败:', error);
            showNotification('错误', '获取合集信息失败', 'error');
        });
}

// 初始化删除确认模态框
function initDeleteConfirmModal() {
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    if (!confirmBtn) return;
    
    confirmBtn.addEventListener('click', function() {
        const collectionId = document.getElementById('deleteCollectionId').value;
        if (!collectionId) return;
        
        fetch(`/api/collections/${collectionId}/delete/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            // 关闭确认对话框
            bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal')).hide();
            
            if (data.status === 'success') {
                showNotification('成功', '合集已成功删除', 'success');
                
                // 延迟刷新页面
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification('错误', data.message || '删除失败，请重试', 'error');
            }
        })
        .catch(error => {
            console.error('删除合集失败:', error);
            showNotification('错误', '删除失败，请检查网络连接后重试', 'error');
            
            // 关闭确认对话框
            bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal')).hide();
        });
    });
}

// 显示通知
function showNotification(title, message, type) {
    // 检查是否支持Toastify或其他通知库
    if (typeof Toastify === 'function') {
        Toastify({
            text: `${title}: ${message}`,
            duration: 3000,
            close: true,
            gravity: 'top',
            position: 'right',
            backgroundColor: type === 'success' ? '#4caf50' : '#f44336',
        }).showToast();
    } else {
        // 简单的替代方案
        alert(`${title}: ${message}`);
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
                // 搜索合集
                const collectionCards = document.querySelectorAll('.collection-card');
                collectionCards.forEach(card => {
                    const title = card.querySelector('h3').textContent.toLowerCase();
                    const desc = card.querySelector('p').textContent.toLowerCase();
                    if (title.includes(searchTerm) || desc.includes(searchTerm)) {
                        card.style.display = '';
                    } else {
                        card.style.display = 'none';
                    }
                });
            }
        });
    });
});

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
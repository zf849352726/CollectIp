// system.js - 全局系统功能JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('系统JavaScript已加载');
    
    // 加载系统设置
    loadSystemSettings();
});

// 打开系统设置模态框
function openSystemSettings() {
    // 使用Bootstrap的Modal API打开模态框
    const modal = new bootstrap.Modal(document.getElementById('systemSettingsModal'));
    modal.show();
}

// 加载系统设置
function loadSystemSettings() {
    // 未来可以通过AJAX加载系统设置
    console.log('加载系统设置');
    
    // 加载主题设置
    const theme = localStorage.getItem('theme') || 'light';
    document.getElementById('theme').value = theme;
    applyTheme(theme);
    
    // 加载语言设置
    const language = localStorage.getItem('language') || 'zh';
    document.getElementById('language').value = language;
}

// 保存系统设置
function saveSystemSettings() {
    const theme = document.getElementById('theme').value;
    const language = document.getElementById('language').value;
    
    // 保存到本地存储
    localStorage.setItem('theme', theme);
    localStorage.setItem('language', language);
    
    // 应用主题
    applyTheme(theme);
    
    // 模拟保存成功关闭模态框
    alert('系统设置已保存');
    const modal = bootstrap.Modal.getInstance(document.getElementById('systemSettingsModal'));
    if (modal) modal.hide();
}

// 应用主题
function applyTheme(theme) {
    const body = document.body;
    if (theme === 'dark') {
        body.classList.add('dark-theme');
    } else {
        body.classList.remove('dark-theme');
    }
}

// 全局函数：将Bootstrap模态框暴露给所有页面
window.openModal = function(modalId) {
    // 使用Bootstrap的Modal API打开模态框
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();
}

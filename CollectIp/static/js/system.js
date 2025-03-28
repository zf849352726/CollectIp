function openSystemSettings() {
    const systemModal = new bootstrap.Modal(document.getElementById('systemSettingsModal'));
    systemModal.show();
}

function saveSystemSettings() {
    const formData = new FormData(document.getElementById('systemSettingsForm'));
    
    fetch('/system_settings/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('系统设置已保存');
            const modal = bootstrap.Modal.getInstance(document.getElementById('systemSettingsModal'));
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

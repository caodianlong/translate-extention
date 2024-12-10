document.addEventListener('DOMContentLoaded', function() {
    // 加载保存的配置
    chrome.storage.sync.get(['apiToken', 'apiUrl'], function(result) {
        document.getElementById('apiToken').value = result.apiToken || '';
        document.getElementById('apiUrl').value = result.apiUrl || CURRENT_CONFIG.URL;
    });

    // 保存按钮点击事件
    document.getElementById('saveBtn').addEventListener('click', function() {
        const apiToken = document.getElementById('apiToken').value;
        const apiUrl = document.getElementById('apiUrl').value;

        chrome.storage.sync.set({
            apiToken: apiToken,
            apiUrl: apiUrl
        }, function() {
            showStatus('设置已保存', 'success');
        });
    });

    // 重置按钮点击事件
    document.getElementById('resetBtn').addEventListener('click', function() {
        document.getElementById('apiToken').value = '';
        document.getElementById('apiUrl').value = CURRENT_CONFIG.URL;
        showStatus('设置已重置', 'success');
    });
});

function showStatus(message, type) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = 'status-message ' + type;
    
    // 3秒后隐藏消息
    setTimeout(() => {
        status.className = 'status-message';
    }, 3000);
}
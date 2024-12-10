let apiToken = '';
let apiUrl = '';
let currentLang = 'zh';

// 初始化时加载配置
chrome.storage.sync.get(['apiToken', 'apiUrl'], function(result) {
    apiToken = result.apiToken;
    apiUrl = result.apiUrl || CURRENT_CONFIG.URL;
    
    if (!apiToken) {
        showError('请先在选项页面设置API Token');
        return;
    }
    
    loadLanguages();
});

// 加载语言列表
async function loadLanguages() {
    try {
        const response = await fetch(`${apiUrl}/supported-languages`, {
            method: 'GET',
            headers: {
                'X-API-Token': apiToken,
                'Accept': 'application/json'
            },
            mode: 'cors'
        });
        
        const languages = await response.json();
        const dropdown = document.getElementById('langsDropdown');
        
        // 过滤掉快捷按钮已有的语言
        Object.entries(languages)
            .filter(([code]) => !['zh', 'en'].includes(code))
            .sort((a, b) => a[1].name.localeCompare(b[1].name))
            .forEach(([code, lang]) => {
                const option = document.createElement('div');
                option.className = 'lang-option';
                option.dataset.lang = code;
                option.textContent = `${lang.name} (${lang.english_name})`;
                option.addEventListener('click', () => selectLanguage(code));
                dropdown.appendChild(option);
            });

        // 设置事件监听
        setupEventListeners();
            
    } catch (error) {
        console.error('加载语言列表错误:', error);
        showError('加载语言列表失败');
    }
}

function setupEventListeners() {
    // 快捷语言按钮点击事件
    document.querySelectorAll('.lang-button').forEach(button => {
        button.addEventListener('click', () => selectLanguage(button.dataset.lang));
    });

    // 更多语言按钮点击事件
    const moreButton = document.querySelector('.more-langs-btn');
    const dropdown = document.getElementById('langsDropdown');
    
    moreButton.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('show');
    });

    // 点击其他地方关闭下拉框
    document.addEventListener('click', () => {
        dropdown.classList.remove('show');
    });

    // 翻译和复制按钮事件
    document.getElementById('translateBtn').addEventListener('click', translate);
    document.getElementById('copyBtn').addEventListener('click', copyTranslation);
}

function selectLanguage(langCode) {
    // 更新当前选中的语言
    currentLang = langCode;
    
    // 更新按钮状态
    document.querySelectorAll('.lang-button').forEach(button => {
        button.classList.toggle('active', button.dataset.lang === langCode);
    });
    
    // 关闭下拉框
    document.getElementById('langsDropdown').classList.remove('show');
    
    // 如果有输入内容，自动触发翻译
    const text = document.getElementById('sourceText').value;
    if (text.trim()) {
        translate();
    }
}

async function translate() {
    const text = document.getElementById('sourceText').value;
    const translateBtn = document.getElementById('translateBtn');
    
    if (!text.trim()) {
        showError('请输入要翻译的文本');
        return;
    }
    
    try {
        translateBtn.disabled = true;
        translateBtn.textContent = '翻译中...';
        
        const response = await fetch(`${apiUrl}/translate`, {
            method: 'POST',
            headers: {
                'X-API-Token': apiToken,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            mode: 'cors',
            body: JSON.stringify({
                text: text,
                targetLanguage: currentLang
            })
        });
        
        const result = await response.json();
        document.getElementById('translationResult').textContent = 
            result.TranslationList[0].Translation;
    } catch (error) {
        console.error('翻译错误:', error);
        showError('翻译失败');
    } finally {
        translateBtn.disabled = false;
        translateBtn.textContent = '翻译';
    }
}

function copyTranslation() {
    const translationResult = document.getElementById('translationResult').textContent;
    if (translationResult && translationResult !== '翻译结果将在这里显示') {
        navigator.clipboard.writeText(translationResult).then(() => {
            const copyBtn = document.getElementById('copyBtn');
            const originalText = copyBtn.textContent;
            copyBtn.textContent = '已复制！';
            setTimeout(() => {
                copyBtn.textContent = originalText;
            }, 2000);
        }).catch(err => {
            showError('复制失败');
        });
    }
}

function showError(message) {
    const errorElement = document.getElementById('errorMessage');
    errorElement.textContent = message;
    errorElement.style.display = 'block';
    setTimeout(() => {
        errorElement.style.display = 'none';
    }, 3000);
}
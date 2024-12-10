const CONFIG = {
    DEFAULT_API: {
        URL: 'http://129.226.181.190:6890',
        HOST_PERMISSION: 'http://129.226.181.190:6890/*'
    },
    // 可以添加其他环境的配置
    PROD_API: {
        URL: 'https://api.production.com',
        HOST_PERMISSION: 'https://api.production.com/*'
    }
};

// 当前使用的配置
const CURRENT_CONFIG = CONFIG.DEFAULT_API;
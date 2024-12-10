import os
import json
import logging
import datetime
from flask import Flask, request, jsonify
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress

from volcengine.ApiInfo import ApiInfo
from volcengine.Credentials import Credentials
from volcengine.ServiceInfo import ServiceInfo
from volcengine.base.Service import Service

# 支持的语言列表
LANGUAGE_CONFIG = {
    'zh': {'name': '中文(简体)', 'english_name': 'Chinese (simplified)'},
    'en': {'name': '英语', 'english_name': 'English'},
    'es': {'name': '西班牙语', 'english_name': 'Spanish'}, 
    'ar': {'name': '阿拉伯语', 'english_name': 'Arabic'},
    'pt': {'name': '葡萄牙语', 'english_name': 'Portuguese'},
    'ru': {'name': '俄语', 'english_name': 'Russian'},
    'ja': {'name': '日语', 'english_name': 'Japanese'},
    'fr': {'name': '法语', 'english_name': 'French'},
    'th': {'name': '泰语', 'english_name': 'Thai'}
}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载配置
def load_config():
    config_path = os.path.expanduser('~/.volc/config')
    try:
        with open(config_path) as f:
            config = json.load(f)
            # 验证必要的配置项
            if not all(k in config for k in ['ak', 'sk', 'tokens']):
                raise KeyError("Missing required config items (ak, sk, tokens)")
            if not isinstance(config['tokens'], list):
                raise ValueError("Tokens must be a list")
            return config
    except (FileNotFoundError, KeyError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to load config from {config_path}: {str(e)}")
        raise RuntimeError(f"Failed to load config: {str(e)}")

# 加载配置
config = load_config()
k_access_key = config['ak']
k_secret_key = config['sk']
VALID_TOKENS = set(config['tokens'])  # 转换为set以提高查询效率

# 初始化火山翻译服务
k_service_info = ServiceInfo(
    'translate.volcengineapi.com',
    {'Content-Type': 'application/json'},
    Credentials(k_access_key, k_secret_key, 'translate', 'cn-north-1'),
    5,
    5
)
k_query = {
    'Action': 'TranslateText',
    'Version': '2020-06-01'
}
k_api_info = {
    'translate': ApiInfo('POST', '/', k_query, {}, {})
}
service = Service(k_service_info, k_api_info)

# 启动web服务
app = Flask(__name__)

# 初始化限流器
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# 初始化压缩
Compress(app)

def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-API-Token')
            
        if not token:
            logger.warning("No X-API-Token provided in request headers")
            return jsonify({'error': 'X-API-Token is missing'}), 401
            
        if token not in VALID_TOKENS:
            logger.warning(f"Invalid token attempted: {token}")
            return jsonify({'error': 'Invalid token'}), 403
            
        return f(*args, **kwargs)
    return decorated

def validate_language(target_lang):
    """
    验证目标语言是否在支持的语言列表中
    """
    if target_lang not in LANGUAGE_CONFIG:
        return False, "不支持的目标语言代码"
    return True, None

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat()
    })

@app.route('/admin/reload-config', methods=['POST'])
@require_token
def reload_config():
    """重新加载配置"""
    try:
        global config, VALID_TOKENS, k_access_key, k_secret_key, service
        
        # 重新加载配置
        config = load_config()
        VALID_TOKENS = set(config['tokens'])
        k_access_key = config['ak']
        k_secret_key = config['sk']
        
        # 重新初始化翻译服务
        k_service_info = ServiceInfo(
            'translate.volcengineapi.com',
            {'Content-Type': 'application/json'},
            Credentials(k_access_key, k_secret_key, 'translate', 'cn-north-1'),
            5,
            5
        )
        service = Service(k_service_info, k_api_info)
        
        logger.info("Configuration reloaded successfully")
        return jsonify({'status': 'success', 'message': 'Configuration reloaded'})
    except Exception as e:
        logger.error(f"Failed to reload config: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to reload config: {str(e)}'}), 500

@app.route('/translate', methods=['POST'])
@require_token
@limiter.limit("100/minute")  # 针对翻译接口的特定限流
def translate():
    try:
        # 获取请求内容
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'Invalid JSON'}), 400
            
        # 获取必要参数
        text = request_data.get('text')
        target_language = request_data.get('targetLanguage', '').lower()

        # 参数验证
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        if not target_language:
            return jsonify({'error': 'No target language specified'}), 400
            
        # 验证语言对
        is_valid, error_message = validate_language(target_language)
        if not is_valid:
            return jsonify({'error': error_message}), 400        
            
        logger.info(f"Received translation request - text: {text}, target language: {target_language}")

        # 准备翻译请求
        body = {
            'TargetLanguage': target_language,
            'TextList': [text],
        }
        
        # 调用翻译服务
        res = service.json('translate', {}, json.dumps(body))
        result = json.loads(res)
        
        logger.info(f"Translation completed successfully")
        return jsonify(result)
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in request")
        return jsonify({'error': 'Invalid JSON format'}), 400
        
    except Exception as e:
        logger.error(f"Error during translation: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/supported-languages', methods=['GET'])
@require_token
@limiter.limit("100/minute")
def get_supported_languages():
    """
    获取支持的语言列表
    """
    return jsonify(LANGUAGE_CONFIG)

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_error(e):
    return jsonify({'error': 'Rate limit exceeded'}), 429
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
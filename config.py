"""
MalgeunTube 설정 파일
환경별 설정을 관리합니다.
"""
import os
from datetime import timedelta

# 기본 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """기본 설정 클래스"""
    # 시크릿 키 - 환경변수에서 로드
    # 개발 환경에서는 고정된 개발용 키 사용, 프로덕션에서는 반드시 환경변수 설정 필요
    _default_dev_key = 'dev-secret-key-for-development-only-change-in-production'
    SECRET_KEY = os.environ.get('SECRET_KEY') or _default_dev_key
    
    # 데이터 디렉토리 설정
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    DOWNLOAD_DIR = os.path.join(BASE_DIR, 'downloads')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'avatars')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    
    # 파일 업로드 설정
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 데이터베이스 설정
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(BASE_DIR, 'data', 'malgeuntube.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 캐싱 설정
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300  # 5분
    CACHE_VIDEO_INFO_TIMEOUT = 3600  # 1시간
    CACHE_SEARCH_TIMEOUT = 900  # 15분
    CACHE_CHANNEL_TIMEOUT = 1800  # 30분
    
    # Rate Limiting 설정
    RATELIMIT_ENABLED = True
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_STORAGE_URL = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"
    RATELIMIT_HEADERS_ENABLED = True
    
    # API Rate Limits
    RATELIMIT_SEARCH = "10 per minute"
    RATELIMIT_DOWNLOAD = "5 per minute"
    RATELIMIT_API_DEFAULT = "30 per minute"
    
    # 로깅 설정
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_FILE_BACKUP_COUNT = 5
    
    # 세션 설정
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    
    @staticmethod
    def init_app(app):
        """애플리케이션 초기화 시 호출되는 메서드"""
        # 필요한 디렉토리 생성
        for directory in [Config.DATA_DIR, Config.DOWNLOAD_DIR, 
                         Config.UPLOAD_FOLDER, Config.LOGS_DIR]:
            if not os.path.exists(directory):
                os.makedirs(directory)


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    
    # 개발 환경에서는 캐시 시간 단축
    CACHE_DEFAULT_TIMEOUT = 60
    CACHE_VIDEO_INFO_TIMEOUT = 300
    CACHE_SEARCH_TIMEOUT = 60
    
    # Rate Limiting 완화
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False
    
    # 프로덕션에서는 반드시 환경변수에서 시크릿 키 로드
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # 캐시 타입 변경 가능 (Redis 등)
    # CACHE_TYPE = 'redis'
    # CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # 프로덕션 환경 체크
        if not cls.SECRET_KEY:
            raise ValueError("프로덕션 환경에서는 SECRET_KEY 환경변수가 필요합니다.")


class TestingConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    DEBUG = True
    
    # 테스트용 데이터베이스 (인메모리)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # 캐시 비활성화
    CACHE_TYPE = 'NullCache'
    
    # Rate Limiting 비활성화
    RATELIMIT_ENABLED = False
    
    # 테스트용 시크릿 키
    SECRET_KEY = 'test-secret-key-for-testing-only'


# 환경별 설정 매핑
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """현재 환경에 맞는 설정 객체 반환"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

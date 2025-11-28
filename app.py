"""
MalgeunTube - 광고 없는 깨끗한 유튜브 경험
"""
import os
import json
import random
import uuid
import glob
import re
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file, after_this_request
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import yt_dlp

# 환경변수 로드
load_dotenv()

# Flask 확장 모듈 임포트
try:
    from flask_sqlalchemy import SQLAlchemy
    from flask_caching import Cache
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    EXTENSIONS_AVAILABLE = True
except ImportError:
    EXTENSIONS_AVAILABLE = False

# 설정 로드
from config import get_config

# Flask 앱 초기화
app = Flask(__name__)
config_obj = get_config()
app.config.from_object(config_obj)
config_obj.init_app(app)

# 시크릿 키는 config에서 이미 설정됨 - 별도 설정 불필요

# ============== 로깅 설정 ==============

def setup_logging():
    """애플리케이션 로깅 설정"""
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    log_dir = app.config.get('LOGS_DIR', 'logs')
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 파일 핸들러 (로테이션)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'malgeuntube.log'),
        maxBytes=app.config.get('LOG_FILE_MAX_BYTES', 10 * 1024 * 1024),
        backupCount=app.config.get('LOG_FILE_BACKUP_COUNT', 5),
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    
    # 앱 로거 설정
    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)
    
    app.logger.info("MalgeunTube 애플리케이션 시작")

setup_logging()

# ============== Flask 확장 초기화 ==============

# 캐싱 설정
cache = Cache(app, config={
    'CACHE_TYPE': app.config.get('CACHE_TYPE', 'SimpleCache'),
    'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
})

# Rate Limiting 설정
if app.config.get('RATELIMIT_ENABLED', True):
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', '200 per day')],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
        strategy=app.config.get('RATELIMIT_STRATEGY', 'fixed-window')
    )
else:
    # Rate limiting 비활성화 시 더미 limiter
    class DummyLimiter:
        def limit(self, limit_value):
            def decorator(f):
                return f
            return decorator
    limiter = DummyLimiter()

# ============== 디렉토리 및 파일 설정 ==============

DATA_DIR = app.config.get('DATA_DIR')
DOWNLOAD_DIR = app.config.get('DOWNLOAD_DIR')
UPLOAD_FOLDER = app.config.get('UPLOAD_FOLDER')
ALLOWED_EXTENSIONS = app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'webp'})

HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')
CHANNELS_FILE = os.path.join(DATA_DIR, 'channels.json')
PLAYLISTS_FILE = os.path.join(DATA_DIR, 'playlists.json')
PROFILES_FILE = os.path.join(DATA_DIR, 'profiles.json')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 필요한 디렉토리 생성
for directory in [DATA_DIR, DOWNLOAD_DIR, UPLOAD_FOLDER]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# ============== 다운로드 관리 ==============

# 다운로드 진행률 및 작업 추적
download_progress = {}
download_tasks = {}  # {download_id: Future}
executor = ThreadPoolExecutor(max_workers=3)  # 최대 3개 동시 다운로드

# yt-dlp 공통 설정 (봇 방지 우회)
def get_ydl_base_opts():
    """yt-dlp 기본 옵션 반환 (봇 방지 우회 포함)"""
    return {
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============== 데이터 관리 함수 ==============

def load_json(filepath):
    """JSON 파일 로드"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except json.JSONDecodeError as e:
            app.logger.error(f"Error decoding JSON from {filepath}: {e}")
            return []
        except Exception as e:
            app.logger.error(f"Error loading JSON from {filepath}: {e}")
            return []
    return []

# ... (rest of json functions) ...

# (Remove download_task and replace api_download and add serve_download)

def progress_hook(d, download_id):
    """yt-dlp 다운로드 진행률 콜백"""
    if d['status'] == 'downloading':
        try:
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)

            if total > 0:
                progress = (downloaded / total) * 100
                download_progress[download_id]['progress'] = round(progress, 1)
                download_progress[download_id]['status'] = 'downloading'

                # 속도와 ETA 정보도 저장
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                if speed:
                    download_progress[download_id]['speed'] = f"{speed / 1024 / 1024:.1f} MB/s"
                if eta:
                    download_progress[download_id]['eta'] = f"{eta}초"
        except:
            pass
    elif d['status'] == 'finished':
        download_progress[download_id]['status'] = 'processing'
        download_progress[download_id]['progress'] = 100

def download_video_task(video_id, download_type, quality, download_id):
    """백그라운드에서 실행되는 다운로드 작업"""
    try:
        download_progress[download_id] = {
            'status': 'starting',
            'progress': 0,
            'filename': None,
            'error': None,
            'title': None
        }

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        file_id = str(uuid.uuid4())

        ydl_opts = get_ydl_base_opts()
        ydl_opts.update({
            'outtmpl': os.path.join(DOWNLOAD_DIR, f'{file_id}.%(ext)s'),
            'progress_hooks': [lambda d: progress_hook(d, download_id)],
        })

        if download_type == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': quality if quality else '192',
                }],
            })
        else:
            if quality == 'best':
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            else:
                try:
                    height = int(quality)
                    ydl_opts['format'] = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
                except:
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            
            # Find the downloaded file
            files = glob.glob(os.path.join(DOWNLOAD_DIR, f'{file_id}.*'))
            if not files:
                download_progress[download_id]['status'] = 'error'
                download_progress[download_id]['error'] = 'Download failed: File not found'
                return

            filename = os.path.basename(files[0])
            title = info.get('title', 'video')
            
            download_progress[download_id]['status'] = 'completed'
            download_progress[download_id]['progress'] = 100
            download_progress[download_id]['filename'] = filename
            download_progress[download_id]['title'] = title

    except Exception as e:
        download_progress[download_id]['status'] = 'error'
        download_progress[download_id]['error'] = str(e)
        app.logger.error(f"Download task error: {e}")

@app.route('/api/download', methods=['POST'])
@limiter.limit(app.config.get('RATELIMIT_DOWNLOAD', '5 per minute'))
def api_download():
    """다운로드 시작 API (Rate limited: 분당 5회)"""
    data = request.get_json()
    video_id = data.get('video_id')
    download_type = data.get('type', 'video')
    quality = data.get('quality', 'best')

    if not video_id:
        return jsonify({'success': False, 'message': 'Video ID is required'})

    # 다운로드 ID 생성
    download_id = str(uuid.uuid4())
    
    app.logger.info(f"Starting download for video: {video_id}, type: {download_type}")

    # ThreadPoolExecutor를 사용하여 다운로드 시작
    future = executor.submit(download_video_task, video_id, download_type, quality, download_id)
    download_tasks[download_id] = future

    return jsonify({
        'success': True,
        'download_id': download_id,
        'message': '다운로드가 시작되었습니다'
    })

@app.route('/api/download/progress/<download_id>')
def api_download_progress(download_id):
    """다운로드 진행률 조회"""
    if download_id not in download_progress:
        return jsonify({'success': False, 'message': 'Download not found'})

    progress_data = download_progress[download_id]

    # 완료된 다운로드는 URL 포함
    if progress_data['status'] == 'completed':
        progress_data['download_url'] = url_for(
            'serve_download',
            filename=progress_data['filename'],
            title=progress_data['title']
        )

    return jsonify({
        'success': True,
        **progress_data
    })

@app.route('/api/download/cancel/<download_id>', methods=['POST'])
def api_download_cancel(download_id):
    """다운로드 취소 API"""
    if download_id not in download_progress:
        return jsonify({'success': False, 'message': 'Download not found'})
    
    # 작업 취소 시도
    if download_id in download_tasks:
        future = download_tasks[download_id]
        if not future.done():
            future.cancel()
            download_progress[download_id]['status'] = 'cancelled'
            app.logger.info(f"Download cancelled: {download_id}")
            return jsonify({'success': True, 'message': '다운로드가 취소되었습니다'})
    
    # 이미 완료되었거나 취소할 수 없는 경우
    return jsonify({'success': False, 'message': '다운로드를 취소할 수 없습니다'})

@app.route('/download/<filename>')
def serve_download(filename):
    """다운로드 파일 제공 (Path Traversal 방지)"""
    try:
        # Path Traversal 방지: secure_filename 사용
        safe_filename = secure_filename(filename)
        if not safe_filename:
            app.logger.warning(f"Invalid filename requested: {filename}")
            return "Invalid filename", 400
        
        title = request.args.get('title', 'video')
        file_path = os.path.join(DOWNLOAD_DIR, safe_filename)
        
        # 경로 검증: 파일이 DOWNLOAD_DIR 내에 있는지 확인
        real_path = os.path.realpath(file_path)
        real_download_dir = os.path.realpath(DOWNLOAD_DIR)
        if not real_path.startswith(real_download_dir):
            app.logger.warning(f"Path traversal attempt detected: {filename}")
            return "Access denied", 403
        
        if not os.path.exists(file_path):
            return "File not found", 404
            
        # 확장자 추출
        _, ext = os.path.splitext(safe_filename)
        download_filename = secure_filename(f"{title}{ext}")
        
        # 다운로드 후 파일 정리
        @after_this_request
        def remove_file(response):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    app.logger.debug(f"Downloaded file removed: {safe_filename}")
            except Exception as e:
                app.logger.error(f"Error removing file: {e}")
            return response
            
        return send_file(
            file_path, 
            as_attachment=True, 
            download_name=download_filename
        )
    except Exception as e:
        app.logger.error(f"Error serving download: {e}")
        return str(e), 500

def save_json(filepath, data):
    """JSON 파일 저장"""
    try:
        # 디렉토리가 존재하는지 확인
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        app.logger.debug(f"Successfully saved JSON to {filepath}")
    except Exception as e:
        app.logger.error(f"Error saving JSON to {filepath}: {e}")
        raise

# ============== 프로필 관리 함수 ==============

def load_profiles():
    return load_json(PROFILES_FILE)

def save_profiles(profiles):
    save_json(PROFILES_FILE, profiles)

def get_profile(profile_id):
    profiles = load_profiles()
    for p in profiles:
        if p['id'] == profile_id:
            return p
    return None

def get_data_path(file_type):
    profile_id = session.get('profile_id')
    if not profile_id:
        # Fallback to default files if no profile selected (shouldn't happen in main app)
        if file_type == 'history': return HISTORY_FILE
        if file_type == 'channels': return CHANNELS_FILE
        if file_type == 'playlists': return PLAYLISTS_FILE
    
    # Profile specific paths
    if file_type == 'history': return os.path.join(DATA_DIR, f'history_{profile_id}.json')
    if file_type == 'channels': return os.path.join(DATA_DIR, f'channels_{profile_id}.json')
    if file_type == 'playlists': return os.path.join(DATA_DIR, f'playlists_{profile_id}.json')
    return None

# ============== 전역 에러 핸들러 ==============

@app.errorhandler(Exception)
def handle_exception(e):
    """전역 예외 핸들러"""
    # API 요청인 경우 JSON 응답 반환
    if request.path.startswith('/api/'):
        app.logger.error(f"API Error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'서버 오류: {str(e)}'
        }), 500
    # 일반 페이지 요청은 기본 에러 처리
    raise e

@app.errorhandler(404)
def not_found(e):
    """404 에러 핸들러"""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': '요청한 API를 찾을 수 없습니다.'}), 404
    if os.path.exists(os.path.join(app.template_folder, '404.html')):
        return render_template('404.html'), 404
    else:
        return str(e), 404

@app.errorhandler(500)
def internal_error(e):
    """500 에러 핸들러"""
    app.logger.error(f"Internal Server Error: {str(e)}", exc_info=True)
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': '내부 서버 오류가 발생했습니다.'}), 500
    return str(e), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """Rate Limit 에러 핸들러"""
    app.logger.warning(f"Rate limit exceeded: {request.remote_addr} - {request.path}")
    return jsonify({
        'success': False,
        'message': '요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.',
        'retry_after': e.description
    }), 429

# ============== 프로필 라우트 ==============

@app.route('/profiles')
def profiles_view():
    profiles = load_profiles()
    current_profile_id = session.get('profile_id')
    current_profile = get_profile(current_profile_id) if current_profile_id else None
    return render_template('profiles.html', profiles=profiles, current_profile=current_profile)

@app.route('/api/profile/create', methods=['POST'])
def create_profile():
    """새 프로필 생성"""
    try:
        app.logger.info("Profile creation started")
        app.logger.debug(f"Request method: {request.method}")
        app.logger.debug(f"Request content type: {request.content_type}")

        name = request.form.get('name')
        app.logger.debug(f"Profile name: {name}")

        if not name:
            app.logger.warning("Profile creation: No name provided")
            return jsonify({'success': False, 'message': '이름을 입력해주세요.'})

        avatar_path = '/static/avatars/default.svg'
        if 'avatar' in request.files:
            file = request.files['avatar']
            app.logger.debug(f"Avatar file: {file.filename}")
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                app.logger.debug(f"Saving avatar to: {filepath}")
                file.save(filepath)
                avatar_path = f"/static/avatars/{unique_filename}"

        new_profile = {
            'id': str(uuid.uuid4()),
            'name': name,
            'avatar': avatar_path,
            'created_at': datetime.now().isoformat()
        }
        app.logger.info(f"New profile created: {new_profile.get('id')}")

        profiles = load_profiles()
        app.logger.debug(f"Existing profiles count: {len(profiles)}")
        profiles.append(new_profile)
        save_profiles(profiles)
        app.logger.info("Profile saved successfully")

        return jsonify({'success': True, 'profile': new_profile})
    except Exception as e:
        app.logger.error(f"Error creating profile: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'프로필 생성 중 오류 발생: {str(e)}'})

@app.route('/api/profile/switch', methods=['POST'])
def switch_profile():
    try:
        data = request.get_json()
        profile_id = data.get('profile_id')

        if get_profile(profile_id):
            session['profile_id'] = profile_id
            return jsonify({'success': True})

        return jsonify({'success': False, 'message': '프로필을 찾을 수 없습니다.'})
    except Exception as e:
        app.logger.error(f"Error switching profile: {e}")
        return jsonify({'success': False, 'message': f'프로필 전환 중 오류 발생: {str(e)}'})

@app.route('/api/profile/delete', methods=['POST'])
def delete_profile():
    try:
        data = request.get_json()
        profile_id = data.get('profile_id')

        profiles = load_profiles()
        profiles = [p for p in profiles if p['id'] != profile_id]
        save_profiles(profiles)

        # 데이터 파일 삭제
        try:
            for ftype in ['history', 'channels', 'playlists']:
                path = os.path.join(DATA_DIR, f'{ftype}_{profile_id}.json')
                if os.path.exists(path):
                    os.remove(path)
        except Exception as file_error:
            app.logger.warning(f"Error deleting profile data files: {file_error}")

        if session.get('profile_id') == profile_id:
            session.pop('profile_id', None)

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error deleting profile: {e}")
        return jsonify({'success': False, 'message': f'프로필 삭제 중 오류 발생: {str(e)}'})

@app.before_request
def check_profile():
    # Static resources and specific routes don't need profile check
    # Check by path (URL) not endpoint (function name)
    if (request.path.startswith('/static/') or
        request.path.startswith('/api/profile') or
        request.path == '/profiles' or
        request.endpoint == 'static'):
        return

    # If no profile in session, redirect to profiles page
    if not session.get('profile_id'):
        return redirect(url_for('profiles_view'))
    
    # Pass current profile to templates
    if request.endpoint: # Only for view functions
        profile = get_profile(session['profile_id'])
        # If session has ID but profile deleted, force logout
        if not profile: 
            session.pop('profile_id', None)
            return redirect(url_for('profiles_view'))
        app.jinja_env.globals['current_profile'] = profile

def load_history():
    return load_json(get_data_path('history'))

def save_history(history):
    save_json(get_data_path('history'), history)

def add_to_history(video_info):
    history = load_history()
    history = [h for h in history if h.get('id') != video_info.get('id')]
    video_info['watched_at'] = datetime.now().isoformat()
    history.insert(0, video_info)
    history = history[:100]
    save_history(history)

def load_channels():
    return load_json(get_data_path('channels'))

def save_channels(channels):
    save_json(get_data_path('channels'), channels)

def add_channel(channel_info):
    channels = load_channels()
    if not any(c.get('channel_id') == channel_info.get('channel_id') for c in channels):
        channel_info['added_at'] = datetime.now().isoformat()
        channels.insert(0, channel_info)
        save_channels(channels)
        return True
    return False

def remove_channel(channel_id):
    channels = load_channels()
    channels = [c for c in channels if c.get('channel_id') != channel_id]
    save_channels(channels)

def is_channel_subscribed(channel_id):
    channels = load_channels()
    return any(c.get('channel_id') == channel_id for c in channels)

def load_playlists():
    return load_json(get_data_path('playlists'))

def save_playlists(playlists):
    save_json(get_data_path('playlists'), playlists)

def create_playlist(name):
    playlists = load_playlists()
    playlist_id = f"pl_{int(datetime.now().timestamp())}"
    new_playlist = {
        'id': playlist_id,
        'name': name,
        'videos': [],
        'created_at': datetime.now().isoformat()
    }
    playlists.append(new_playlist)
    save_playlists(playlists)
    return playlist_id

def add_to_playlist(playlist_id, video_info):
    playlists = load_playlists()
    for pl in playlists:
        if pl['id'] == playlist_id:
            if not any(v.get('id') == video_info.get('id') for v in pl['videos']):
                pl['videos'].append(video_info)
                save_playlists(playlists)
                return True
    return False

def remove_from_playlist(playlist_id, video_id):
    playlists = load_playlists()
    for pl in playlists:
        if pl['id'] == playlist_id:
            pl['videos'] = [v for v in pl['videos'] if v.get('id') != video_id]
            save_playlists(playlists)
            return True
    return False

def delete_playlist(playlist_id):
    playlists = load_playlists()
    playlists = [pl for pl in playlists if pl['id'] != playlist_id]
    save_playlists(playlists)

# ============== 설정 관리 ==============

# 지원하는 국가 목록
SUPPORTED_COUNTRIES = {
    'KR': '한국',
    'US': '미국',
    'JP': '일본',
    'GB': '영국',
    'DE': '독일',
    'FR': '프랑스',
    'CA': '캐나다',
    'AU': '호주',
    'IN': '인도',
    'BR': '브라질'
}

def load_settings():
    """사용자 설정 로드"""
    settings_file = os.path.join(DATA_DIR, f'settings_{session.get("profile_id", "default")}.json')
    settings = load_json(settings_file)
    if isinstance(settings, list):
        # 기존 데이터가 리스트인 경우 딕셔너리로 변환
        return {'country': 'KR'}
    return settings if settings else {'country': 'KR'}

def save_settings(settings):
    """사용자 설정 저장"""
    settings_file = os.path.join(DATA_DIR, f'settings_{session.get("profile_id", "default")}.json')
    save_json(settings_file, settings)

def get_country_setting():
    """현재 국가 설정 가져오기"""
    settings = load_settings()
    return settings.get('country', 'KR')

# ============== 나중에 볼 영상 관리 ==============

def load_watch_later():
    watch_later_file = os.path.join(DATA_DIR, f'watch_later_{session.get("profile_id", "default")}.json')
    return load_json(watch_later_file)

def save_watch_later(videos):
    watch_later_file = os.path.join(DATA_DIR, f'watch_later_{session.get("profile_id", "default")}.json')
    save_json(watch_later_file, videos)

def add_to_watch_later(video_info):
    videos = load_watch_later()
    # 중복 체크
    if not any(v.get('id') == video_info.get('id') for v in videos):
        video_info['added_at'] = datetime.now().isoformat()
        videos.insert(0, video_info)  # 맨 앞에 추가
        save_watch_later(videos)
        return True
    return False

def remove_from_watch_later(video_id):
    videos = load_watch_later()
    videos = [v for v in videos if v.get('id') != video_id]
    save_watch_later(videos)
    return True

def is_in_watch_later(video_id):
    videos = load_watch_later()
    return any(v.get('id') == video_id for v in videos)

# ============== 시청 진행률 관리 ==============

def load_watch_progress():
    progress_file = os.path.join(DATA_DIR, f'progress_{session.get("profile_id", "default")}.json')
    return load_json(progress_file)

def save_watch_progress(progress_data):
    progress_file = os.path.join(DATA_DIR, f'progress_{session.get("profile_id", "default")}.json')
    save_json(progress_file, progress_data)

def update_progress(video_id, current_time, duration):
    progress_data = load_watch_progress()

    # 진행률 계산 (5% 미만이면 저장 안 함, 95% 이상이면 완료로 표시)
    if duration > 0:
        percentage = (current_time / duration) * 100

        if percentage < 5:
            # 너무 초반이면 저장 안 함
            return
        elif percentage >= 95:
            # 거의 끝까지 봤으면 완료로 표시하고 제거
            progress_data = [p for p in progress_data if p.get('video_id') != video_id]
        else:
            # 기존 데이터 찾기
            found = False
            for p in progress_data:
                if p.get('video_id') == video_id:
                    p['current_time'] = current_time
                    p['duration'] = duration
                    p['percentage'] = round(percentage, 2)
                    p['updated_at'] = datetime.now().isoformat()
                    found = True
                    break

            if not found:
                progress_data.append({
                    'video_id': video_id,
                    'current_time': current_time,
                    'duration': duration,
                    'percentage': round(percentage, 2),
                    'updated_at': datetime.now().isoformat()
                })

    save_watch_progress(progress_data)

def get_progress(video_id):
    progress_data = load_watch_progress()
    for p in progress_data:
        if p.get('video_id') == video_id:
            return p
    return None

# ============== 검색 기록 관리 ==============

def load_search_history():
    """검색 기록 로드"""
    search_history_file = os.path.join(DATA_DIR, f'search_history_{session.get("profile_id", "default")}.json')
    return load_json(search_history_file)

def save_search_history(history):
    """검색 기록 저장"""
    search_history_file = os.path.join(DATA_DIR, f'search_history_{session.get("profile_id", "default")}.json')
    save_json(search_history_file, history)

def save_search_query(query):
    """검색 쿼리를 기록에 저장"""
    if not query or len(query.strip()) < 2:
        return
    
    history = load_search_history()
    
    # 중복 제거 (같은 검색어는 최신으로 업데이트)
    history = [h for h in history if h.get('query', '').lower() != query.lower()]
    
    # 새 검색어 추가
    history.insert(0, {
        'query': query.strip(),
        'searched_at': datetime.now().isoformat()
    })
    
    # 최대 50개까지만 유지
    history = history[:50]
    
    save_search_history(history)

def get_search_suggestions(query):
    """검색어 자동완성 제안"""
    if not query or len(query) < 2:
        return []
    
    history = load_search_history()
    query_lower = query.lower()
    
    suggestions = []
    for h in history:
        search_query = h.get('query', '')
        if search_query.lower().startswith(query_lower):
            suggestions.append(search_query)
    
    return suggestions[:10]  # 최대 10개

# ============== YouTube 데이터 함수 ==============

@cache.memoize(timeout=3600)  # 1시간 캐시
def get_video_info_cached(video_url):
    """비디오 정보 가져오기 (캐시됨) - is_subscribed 제외"""
    ydl_opts = get_ydl_base_opts()
    ydl_opts['extract_flat'] = False

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            formats = []
            if info.get('formats'):
                for f in info['formats']:
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                        formats.append({
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'resolution': f.get('resolution', 'unknown'),
                            'filesize': f.get('filesize'),
                            'url': f.get('url'),
                            'quality': f.get('height', 0)
                        })
            
            formats.sort(key=lambda x: x.get('quality', 0), reverse=True)
            channel_id = info.get('channel_id') or info.get('uploader_id', '')
            
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'description': info.get('description', '')[:500],
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'view_count': info.get('view_count'),
                'like_count': info.get('like_count'),
                'channel': info.get('channel') or info.get('uploader'),
                'channel_id': channel_id,
                'channel_url': info.get('channel_url') or f"https://www.youtube.com/channel/{channel_id}",
                'upload_date': info.get('upload_date'),
                'formats': formats[:10],
                'url': info.get('url'),
                'webpage_url': info.get('webpage_url'),
            }
    except Exception as e:
        app.logger.error(f"Error getting video info: {e}")
        return {'error': str(e)}

def get_video_info(video_url):
    """비디오 정보 가져오기 (구독 상태 포함)"""
    video_info = get_video_info_cached(video_url)
    if 'error' not in video_info:
        video_info['is_subscribed'] = is_channel_subscribed(video_info.get('channel_id', ''))
    return video_info

def get_playlist_info(playlist_url):
    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        'extract_flat': True,
        'ignoreerrors': True,
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
            
            videos = []
            if info and 'entries' in info:
                for idx, entry in enumerate(info['entries']):
                    if entry:
                        videos.append({
                            'id': entry.get('id'),
                            'title': entry.get('title'),
                            'thumbnail': entry.get('thumbnail') or f"https://img.youtube.com/vi/{entry.get('id')}/mqdefault.jpg",
                            'duration': entry.get('duration'),
                            'channel': entry.get('channel') or entry.get('uploader'),
                            'index': idx
                        })
            
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'description': info.get('description', ''),
                'thumbnail': info.get('thumbnail'),
                'channel': info.get('channel') or info.get('uploader'),
                'video_count': len(videos),
                'videos': videos
            }
    except Exception as e:
        return {'error': str(e)}

def get_channel_videos(channel_url, max_videos=100):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlistend': max_videos,
    }
    
    try:
        if '/channel/' in channel_url or '/@' in channel_url:
            if not channel_url.endswith('/videos'):
                channel_url = channel_url.rstrip('/') + '/videos'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            
            videos = []
            if info and 'entries' in info:
                for entry in info['entries'][:max_videos]:
                    if entry:
                        videos.append({
                            'id': entry.get('id'),
                            'title': entry.get('title'),
                            'thumbnail': entry.get('thumbnail') or f"https://img.youtube.com/vi/{entry.get('id')}/mqdefault.jpg",
                            'duration': entry.get('duration'),
                            'view_count': entry.get('view_count'),
                        })
            
            return {
                'channel': info.get('channel') or info.get('uploader'),
                'channel_id': info.get('channel_id') or info.get('uploader_id'),
                'videos': videos
            }
    except Exception as e:
        return {'error': str(e)}

def get_related_videos(video_id, max_results=12):
    ydl_opts = get_ydl_base_opts()
    ydl_opts['extract_flat'] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            title = video_info.get('title', '')
            channel = video_info.get('channel', '')
            search_query = f"{title[:30]} {channel}"
            results = ydl.extract_info(f"ytsearch{max_results}:{search_query}", download=False)
            
            videos = []
            if results and 'entries' in results:
                for entry in results['entries']:
                    if entry and entry.get('id') != video_id:
                        videos.append({
                            'id': entry.get('id'),
                            'title': entry.get('title'),
                            'thumbnail': entry.get('thumbnail') or f"https://img.youtube.com/vi/{entry.get('id')}/mqdefault.jpg",
                            'duration': entry.get('duration'),
                            'channel': entry.get('channel') or entry.get('uploader'),
                            'view_count': entry.get('view_count'),
                        })
            
            return videos[:max_results]
    except Exception as e:
        app.logger.error(f"Error getting related videos: {e}")
        return []

@cache.memoize(timeout=900)  # 15분 캐시
def search_youtube(query, max_results=20):
    """YouTube 검색 (캐시됨)"""
    ydl_opts = get_ydl_base_opts()
    ydl_opts['extract_flat'] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            
            videos = []
            if results and 'entries' in results:
                for entry in results['entries']:
                    if entry:
                        videos.append({
                            'id': entry.get('id'),
                            'title': entry.get('title'),
                            'thumbnail': entry.get('thumbnail') or f"https://img.youtube.com/vi/{entry.get('id')}/mqdefault.jpg",
                            'duration': entry.get('duration'),
                            'channel': entry.get('channel') or entry.get('uploader'),
                            'channel_id': entry.get('channel_id') or entry.get('uploader_id'),
                            'view_count': entry.get('view_count'),
                        })
            return videos
    except Exception as e:
        app.logger.error(f"Error searching YouTube: {e}")
        return {'error': str(e)}

def get_trending_videos(max_results=20, country=None):
    """트렌딩 영상 가져오기 (trending 페이지 대신 인기 검색어 사용)"""
    if country is None:
        country = get_country_setting()
    
    ydl_opts = get_ydl_base_opts()
    ydl_opts.update({
        'extract_flat': True,
        'playlistend': max_results,
        'geo_bypass_country': country,
    })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # trending 페이지 대신 인기 검색어로 대체
            popular_queries = ['music', 'gaming', 'news', 'sports', 'entertainment']
            query = random.choice(popular_queries)
            results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

            videos = []
            if results and 'entries' in results:
                for entry in results['entries'][:max_results]:
                    if entry:
                        videos.append({
                            'id': entry.get('id'),
                            'title': entry.get('title'),
                            'thumbnail': entry.get('thumbnail') or f"https://img.youtube.com/vi/{entry.get('id')}/mqdefault.jpg",
                            'duration': entry.get('duration'),
                            'channel': entry.get('channel') or entry.get('uploader'),
                            'view_count': entry.get('view_count'),
                        })
            return videos
    except:
        return []

# ============== 라우트 ==============

@app.route('/favicon.ico')
def favicon():
    """Favicon 제공"""
    return send_file(
        os.path.join(app.static_folder, 'icons', 'icon.svg'),
        mimetype='image/svg+xml'
    )

@app.route('/')
def index():
    history = load_history()[:8]
    channels = load_channels()[:6]
    trending = get_trending_videos(8)

    # 시청 기록 기반 추천 영상
    recommended = []
    if history:
        # 최근 시청한 영상들에서 랜덤으로 선택
        import random
        sample_videos = random.sample(history[:5], min(2, len(history[:5])))
        for video in sample_videos:
            related = get_related_videos(video.get('id'), max_results=6)
            recommended.extend(related)

        # 중복 제거 및 셔플
        seen_ids = set()
        unique_recommended = []
        for video in recommended:
            if video.get('id') not in seen_ids and video.get('id') not in [h.get('id') for h in history]:
                seen_ids.add(video.get('id'))
                unique_recommended.append(video)

        random.shuffle(unique_recommended)
        recommended = unique_recommended[:12]

    return render_template('index.html', history=history, channels=channels, trending=trending, recommended=recommended)

@app.route('/watch')
def watch():
    video_url = request.args.get('v')
    playlist_id = request.args.get('list')
    playlist_index = request.args.get('index', 0, type=int)
    
    if not video_url:
        return redirect(url_for('index'))
    
    if not video_url.startswith('http'):
        video_url = f"https://www.youtube.com/watch?v={video_url}"
    
    video_info = get_video_info(video_url)
    
    playlist_info = None
    if playlist_id:
        if playlist_id.startswith('pl_'):
            playlists = load_playlists()
            for pl in playlists:
                if pl['id'] == playlist_id:
                    playlist_info = pl
                    playlist_info['is_custom'] = True
                    break
        else:
            playlist_info = get_playlist_info(f"https://www.youtube.com/playlist?list={playlist_id}")
            if playlist_info and 'error' not in playlist_info:
                playlist_info['is_custom'] = False
    
    related_videos = []
    if 'error' not in video_info:
        related_videos = get_related_videos(video_info['id'])
        add_to_history({
            'id': video_info.get('id'),
            'title': video_info.get('title'),
            'thumbnail': video_info.get('thumbnail'),
            'channel': video_info.get('channel'),
            'channel_id': video_info.get('channel_id'),
            'duration': video_info.get('duration')
        })
    
    user_playlists = load_playlists()
    
    return render_template('watch.html', 
                         video=video_info, 
                         playlist=playlist_info,
                         playlist_index=playlist_index,
                         related_videos=related_videos,
                         user_playlists=user_playlists)

@app.route('/search')
@limiter.limit(app.config.get('RATELIMIT_SEARCH', '10 per minute'))
def search():
    """검색 페이지 (Rate limited)"""
    query = request.args.get('q', '')
    results = []
    search_history = load_search_history()
    
    if query:
        # 검색 기록 저장
        save_search_query(query)
        
        results = search_youtube(query, max_results=30)
        if isinstance(results, list):
            for video in results:
                if video.get('channel_id'):
                    video['is_subscribed'] = is_channel_subscribed(video['channel_id'])
    
    user_playlists = load_playlists()
    return render_template('search.html', query=query, results=results, 
                         user_playlists=user_playlists, search_history=search_history)

@app.route('/history')
def history():
    history_data = load_history()
    return render_template('history.html', history=history_data)

@app.route('/watch-later')
def watch_later_page():
    videos = load_watch_later()
    return render_template('watch_later.html', videos=videos)

@app.route('/stats')
def stats_page():
    return render_template('stats.html')

@app.route('/playlist/<playlist_id>')
def playlist_view(playlist_id):
    if playlist_id.startswith('pl_'):
        playlists = load_playlists()
        playlist_info = None
        for pl in playlists:
            if pl['id'] == playlist_id:
                playlist_info = pl
                playlist_info['is_custom'] = True
                break
        if not playlist_info:
            return redirect(url_for('index'))
    else:
        playlist_info = get_playlist_info(f"https://www.youtube.com/playlist?list={playlist_id}")
        if playlist_info and 'error' not in playlist_info:
            playlist_info['is_custom'] = False
    
    return render_template('playlist.html', playlist=playlist_info)

@app.route('/playlists')
def playlists():
    user_playlists = load_playlists()
    return render_template('playlists.html', playlists=user_playlists)

@app.route('/channels')
def channels():
    subscribed_channels = load_channels()
    return render_template('channels.html', channels=subscribed_channels)

@app.route('/channel/<channel_id>')
def channel_detail(channel_id):
    channel_url = f"https://www.youtube.com/channel/{channel_id}"
    channel_info = get_channel_videos(channel_url)
    
    if 'error' in channel_info:
        return render_template('channel_detail.html', channel=None, error=channel_info['error'])
    
    channel_info['channel_id'] = channel_id
    channel_info['is_subscribed'] = is_channel_subscribed(channel_id)
    
    return render_template('channel_detail.html', channel=channel_info)

@app.route('/feed')
def feed():
    channels = load_channels()
    all_videos = []
    
    for channel in channels[:15]:  # 더 많은 채널에서 가져오기
        channel_url = channel.get('channel_url', '')
        if channel_url:
            videos = get_channel_videos(channel_url, max_videos=10)  # 채널당 더 많은 영상
            if 'error' not in videos:
                for video in videos.get('videos', []):
                    video['channel'] = channel.get('name')
                    video['channel_id'] = channel.get('channel_id')
                    all_videos.append(video)
    
    random.shuffle(all_videos)
    
    return render_template('feed.html', videos=all_videos[:60], channels=channels)  # 더 많은 영상 표시

# ============== API 엔드포인트 ==============

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    save_history([])
    return jsonify({'success': True})

@app.route('/api/channel/subscribe', methods=['POST'])
def subscribe_channel():
    data = request.get_json()
    channel_info = {
        'channel_id': data.get('channel_id'),
        'name': data.get('name'),
        'channel_url': data.get('channel_url'),
        'thumbnail': data.get('thumbnail', '')
    }
    success = add_channel(channel_info)
    return jsonify({'success': success})

@app.route('/api/channel/unsubscribe', methods=['POST'])
def unsubscribe_channel():
    data = request.get_json()
    channel_id = data.get('channel_id')
    remove_channel(channel_id)
    return jsonify({'success': True})

@app.route('/api/playlist/create', methods=['POST'])
def api_create_playlist():
    data = request.get_json()
    name = data.get('name', '새 플레이리스트')
    playlist_id = create_playlist(name)
    return jsonify({'success': True, 'playlist_id': playlist_id})

@app.route('/api/playlist/<playlist_id>/add', methods=['POST'])
def api_add_to_playlist(playlist_id):
    try:
        data = request.get_json()
        app.logger.debug(f"Adding to playlist {playlist_id}")
        app.logger.debug(f"Request data: {data}")

        video_info = {
            'id': data.get('video_id'),
            'title': data.get('title'),
            'thumbnail': data.get('thumbnail'),
            'duration': data.get('duration'),
            'channel': data.get('channel')
        }
        app.logger.debug(f"Video info: {video_info}")

        success = add_to_playlist(playlist_id, video_info)
        app.logger.debug(f"Add result: {success}")

        if success:
            return jsonify({'success': True, 'message': '플레이리스트에 추가되었습니다.'})
        else:
            return jsonify({'success': False, 'message': '이미 플레이리스트에 있거나 추가할 수 없습니다.'})
    except Exception as e:
        app.logger.error(f"Error adding to playlist: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'오류 발생: {str(e)}'})

@app.route('/api/playlist/<playlist_id>/remove', methods=['POST'])
def api_remove_from_playlist(playlist_id):
    data = request.get_json()
    video_id = data.get('video_id')
    success = remove_from_playlist(playlist_id, video_id)
    return jsonify({'success': success})

@app.route('/api/playlist/<playlist_id>/delete', methods=['POST'])
def api_delete_playlist(playlist_id):
    delete_playlist(playlist_id)
    return jsonify({'success': True})

@app.route('/api/playlist/<playlist_id>/reorder', methods=['POST'])
def api_reorder_playlist(playlist_id):
    """플레이리스트 영상 순서 변경"""
    try:
        data = request.get_json()
        video_ids = data.get('video_ids', [])  # 새로운 순서의 video_id 배열

        playlists = load_playlists()
        for pl in playlists:
            if pl['id'] == playlist_id:
                # 기존 영상들을 딕셔너리로 변환 (빠른 검색)
                video_dict = {v.get('id'): v for v in pl['videos']}

                # 새로운 순서로 재배열
                new_videos = []
                for vid in video_ids:
                    if vid in video_dict:
                        new_videos.append(video_dict[vid])

                pl['videos'] = new_videos
                save_playlists(playlists)
                return jsonify({'success': True, 'message': '순서가 변경되었습니다'})

        return jsonify({'success': False, 'message': '플레이리스트를 찾을 수 없습니다'})
    except Exception as e:
        app.logger.error(f"Error reordering playlist: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/playlist/<playlist_id>/move', methods=['POST'])
def api_move_video_in_playlist(playlist_id):
    """플레이리스트 내 영상을 특정 위치로 이동"""
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        direction = data.get('direction')  # 'up', 'down', 'top', 'bottom'

        playlists = load_playlists()
        for pl in playlists:
            if pl['id'] == playlist_id:
                videos = pl['videos']

                # 현재 인덱스 찾기
                current_index = None
                for i, v in enumerate(videos):
                    if v.get('id') == video_id:
                        current_index = i
                        break

                if current_index is None:
                    return jsonify({'success': False, 'message': '영상을 찾을 수 없습니다'})

                # 이동 처리
                video = videos.pop(current_index)

                if direction == 'up' and current_index > 0:
                    videos.insert(current_index - 1, video)
                elif direction == 'down' and current_index < len(videos):
                    videos.insert(current_index + 1, video)
                elif direction == 'top':
                    videos.insert(0, video)
                elif direction == 'bottom':
                    videos.append(video)
                else:
                    videos.insert(current_index, video)  # 변경 없음

                pl['videos'] = videos
                save_playlists(playlists)
                return jsonify({'success': True, 'message': '이동되었습니다'})

        return jsonify({'success': False, 'message': '플레이리스트를 찾을 수 없습니다'})
    except Exception as e:
        app.logger.error(f"Error moving video: {e}")
        return jsonify({'success': False, 'message': str(e)})

# ============== 나중에 볼 영상 API ==============

@app.route('/api/watch-later/add', methods=['POST'])
def api_add_watch_later():
    try:
        data = request.get_json()
        video_info = {
            'id': data.get('video_id'),
            'title': data.get('title'),
            'thumbnail': data.get('thumbnail'),
            'duration': data.get('duration'),
            'channel': data.get('channel'),
            'channel_id': data.get('channel_id')
        }

        success = add_to_watch_later(video_info)
        if success:
            return jsonify({'success': True, 'message': '나중에 볼 영상에 추가되었습니다'})
        else:
            return jsonify({'success': False, 'message': '이미 추가된 영상입니다'})
    except Exception as e:
        app.logger.error(f"Error adding to watch later: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/watch-later/remove', methods=['POST'])
def api_remove_watch_later():
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        remove_from_watch_later(video_id)
        return jsonify({'success': True, 'message': '나중에 볼 영상에서 제거되었습니다'})
    except Exception as e:
        app.logger.error(f"Error removing from watch later: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/watch-later/check/<video_id>', methods=['GET'])
def api_check_watch_later(video_id):
    is_added = is_in_watch_later(video_id)
    return jsonify({'is_added': is_added})

# ============== 시청 진행률 API ==============

@app.route('/api/progress/update', methods=['POST'])
def api_update_progress():
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        current_time = data.get('current_time', 0)
        duration = data.get('duration', 0)

        update_progress(video_id, current_time, duration)
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error updating progress: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/progress/<video_id>', methods=['GET'])
def api_get_progress(video_id):
    progress = get_progress(video_id)
    return jsonify({'progress': progress})

# ============== 시청 통계 API ==============

@app.route('/api/stats', methods=['GET'])
def api_get_stats():
    try:
        history = load_history()
        channels = load_channels()

        # 오늘, 이번 주, 이번 달 시청 시간 계산
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        today_time = 0
        week_time = 0
        month_time = 0

        channel_counts = {}

        for video in history:
            watched_at = video.get('watched_at')
            if watched_at:
                try:
                    watched_date = datetime.fromisoformat(watched_at)
                    duration = video.get('duration', 0)

                    if watched_date >= today_start:
                        today_time += duration
                    if watched_date >= week_start:
                        week_time += duration
                    if watched_date >= month_start:
                        month_time += duration

                    # 채널별 시청 횟수
                    channel = video.get('channel', 'Unknown')
                    channel_counts[channel] = channel_counts.get(channel, 0) + 1
                except:
                    pass

        # Top 5 채널
        top_channels = sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        stats = {
            'today_minutes': round(today_time / 60, 1),
            'week_minutes': round(week_time / 60, 1),
            'month_minutes': round(month_time / 60, 1),
            'total_videos': len(history),
            'total_channels': len(channels),
            'top_channels': [{'name': ch, 'count': cnt} for ch, cnt in top_channels]
        }

        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        app.logger.error(f"Error getting stats: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/channel/<channel_id>/videos', methods=['GET'])
def api_get_channel_videos(channel_id):
    """채널의 더 많은 영상을 가져오는 API"""
    try:
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 20, type=int)

        channel_url = f"https://www.youtube.com/channel/{channel_id}"

        # 더 많은 영상 로드 (최대 100개)
        channel_info = get_channel_videos(channel_url, max_videos=min(offset + limit, 100))

        if 'error' in channel_info:
            return jsonify({'success': False, 'error': channel_info['error']})

        # offset부터 limit개만큼 잘라서 반환
        videos = channel_info.get('videos', [])[offset:offset + limit]
        has_more = len(channel_info.get('videos', [])) > offset + limit

        return jsonify({
            'success': True,
            'videos': videos,
            'has_more': has_more,
            'total': len(channel_info.get('videos', []))
        })
    except Exception as e:
        app.logger.error(f"Error loading more videos: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/search', methods=['GET'])
@limiter.limit(app.config.get('RATELIMIT_SEARCH', '10 per minute'))
def api_search():
    """검색 API (Rate limited: 분당 10회)"""
    try:
        query = request.args.get('q', '')
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 20, type=int)

        if not query:
            return jsonify({'success': False, 'error': 'Query is required'})

        app.logger.debug(f"API Search: {query}, offset: {offset}, limit: {limit}")

        # 더 많은 결과 요청 (최대 50개까지)
        max_results = min(offset + limit, 50)
        results = search_youtube(query, max_results=max_results)

        if isinstance(results, dict) and 'error' in results:
            return jsonify({'success': False, 'error': results['error']})

        # offset부터 limit개만큼 잘라서 반환
        videos = results[offset:offset + limit] if isinstance(results, list) else []

        # 구독 정보 추가
        for video in videos:
            if video.get('channel_id'):
                video['is_subscribed'] = is_channel_subscribed(video['channel_id'])

        has_more = len(results) > offset + limit and len(results) < 50

        return jsonify({
            'success': True,
            'videos': videos,
            'has_more': has_more,
            'total': len(results)
        })
    except Exception as e:
        app.logger.error(f"Error in API search: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recommended', methods=['GET'])
def api_recommended():
    """추천 영상을 더 가져오는 API"""
    try:
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 12, type=int)

        app.logger.debug(f"API Recommended: offset: {offset}, limit: {limit}")

        history = load_history()

        if not history:
            return jsonify({'success': False, 'error': 'No watch history'})

        # 시청 기록에서 더 많은 샘플 선택
        import random
        sample_count = min(3, len(history[:10]))
        sample_videos = random.sample(history[:10], sample_count)

        all_recommended = []
        for video in sample_videos:
            related = get_related_videos(video.get('id'), max_results=10)
            all_recommended.extend(related)

        # 중복 제거
        seen_ids = set([h.get('id') for h in history])
        unique_recommended = []
        for video in all_recommended:
            if video.get('id') not in seen_ids:
                seen_ids.add(video.get('id'))
                unique_recommended.append(video)

        # 랜덤 셔플
        random.shuffle(unique_recommended)

        # offset부터 limit개만큼 반환
        videos = unique_recommended[offset:offset + limit]
        has_more = len(unique_recommended) > offset + limit

        return jsonify({
            'success': True,
            'videos': videos,
            'has_more': has_more,
            'total': len(unique_recommended)
        })
    except Exception as e:
        app.logger.error(f"Error in API recommended: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/search/suggestions', methods=['GET'])
def api_search_suggestions():
    """검색어 자동완성 API"""
    query = request.args.get('q', '')
    suggestions = get_search_suggestions(query)
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/search/history', methods=['GET'])
def api_search_history():
    """검색 기록 API"""
    history = load_search_history()
    return jsonify({'success': True, 'history': history[:20]})

@app.route('/api/search/history/clear', methods=['POST'])
def api_clear_search_history():
    """검색 기록 삭제 API"""
    save_search_history([])
    return jsonify({'success': True, 'message': '검색 기록이 삭제되었습니다'})

# ============== 설정 API ==============

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """사용자 설정 조회 API"""
    try:
        settings = load_settings()
        return jsonify({
            'success': True,
            'settings': settings,
            'countries': SUPPORTED_COUNTRIES
        })
    except Exception as e:
        app.logger.error(f"Error getting settings: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    """사용자 설정 저장 API"""
    try:
        data = request.get_json()
        settings = load_settings()
        
        # 국가 설정 업데이트
        if 'country' in data:
            country = data['country']
            if country in SUPPORTED_COUNTRIES:
                settings['country'] = country
            else:
                return jsonify({'success': False, 'message': '지원하지 않는 국가입니다.'})
        
        save_settings(settings)
        return jsonify({'success': True, 'message': '설정이 저장되었습니다.', 'settings': settings})
    except Exception as e:
        app.logger.error(f"Error saving settings: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/settings/country', methods=['GET'])
def api_get_country():
    """현재 국가 설정 조회 API"""
    country = get_country_setting()
    return jsonify({
        'success': True,
        'country': country,
        'country_name': SUPPORTED_COUNTRIES.get(country, country)
    })

# ============== 템플릿 필터 ==============

@app.template_filter('duration')
def format_duration(seconds):
    if not seconds:
        return '0:00'
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f'{hours}:{minutes:02d}:{secs:02d}'
    return f'{minutes}:{secs:02d}'

@app.template_filter('views')
def format_views(count):
    if not count:
        return '0'
    if count >= 1000000:
        return f'{count/1000000:.1f}M'
    if count >= 1000:
        return f'{count/1000:.1f}K'
    return str(count)

@app.template_filter('timeago')
def format_timeago(iso_string):
    if not iso_string:
        return ''
    try:
        dt = datetime.fromisoformat(iso_string)
        diff = datetime.now() - dt
        if diff.days > 30:
            return f'{diff.days // 30}개월 전'
        elif diff.days > 0:
            return f'{diff.days}일 전'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600}시간 전'
        elif diff.seconds > 60:
            return f'{diff.seconds // 60}분 전'
        else:
            return '방금 전'
    except:
        return ''

if __name__ == '__main__':
    app.run(debug=True, port=5000)
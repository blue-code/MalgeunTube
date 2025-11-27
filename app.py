from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file, after_this_request
from werkzeug.utils import secure_filename
import yt_dlp
import json
import os
import random
import threading
import uuid
import glob
from datetime import datetime
from functools import lru_cache

app = Flask(__name__)
app.secret_key = 'adfree-tube-secret-key-2024'

# 데이터 디렉토리 설정
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
HISTORY_FILE = os.path.join(DATA_DIR, 'history.json') # Default/Legacy
CHANNELS_FILE = os.path.join(DATA_DIR, 'channels.json') # Default/Legacy
PLAYLISTS_FILE = os.path.join(DATA_DIR, 'playlists.json') # Default/Legacy
PROFILES_FILE = os.path.join(DATA_DIR, 'profiles.json')
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'avatars')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============== 데이터 관리 함수 ==============

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {filepath}: {e}")
            return []
        except Exception as e:
            print(f"Error loading JSON from {filepath}: {e}")
            return []
    return []

# ... (rest of json functions) ...

# (Remove download_task and replace api_download and add serve_download)

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json()
    video_id = data.get('video_id')
    download_type = data.get('type', 'video')
    quality = data.get('quality', 'best')
    
    if not video_id:
        return jsonify({'success': False, 'message': 'Video ID is required'})
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    file_id = str(uuid.uuid4())
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': os.path.join(DOWNLOAD_DIR, f'{file_id}.%(ext)s'),
        }
        
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
            # yt-dlp might change extension (e.g. mkv -> mp4 or webm -> mp3)
            # We look for files starting with the file_id
            files = glob.glob(os.path.join(DOWNLOAD_DIR, f'{file_id}.*'))
            if not files:
                return jsonify({'success': False, 'message': 'Download failed: File not found'})
            
            filename = os.path.basename(files[0])
            title = info.get('title', 'video')
            
            return jsonify({
                'success': True, 
                'download_url': url_for('serve_download', filename=filename, title=title)
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/download/<filename>')
def serve_download(filename):
    try:
        title = request.args.get('title', 'video')
        file_path = os.path.join(DOWNLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            return "File not found", 404
            
        # Get original extension
        _, ext = os.path.splitext(filename)
        safe_filename = f"{title}{ext}"
        
        # Simple cleanup after request (optional, works on some WSGI servers)
        @after_this_request
        def remove_file(response):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Error removing file: {e}")
            return response
            
        return send_file(
            file_path, 
            as_attachment=True, 
            download_name=safe_filename
        )
    except Exception as e:
        return str(e), 500

def save_json(filepath, data):
    try:
        # 디렉토리가 존재하는지 확인
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved JSON to {filepath}")
    except Exception as e:
        print(f"Error saving JSON to {filepath}: {e}")
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
    # API 요청인 경우 JSON 응답 반환
    if request.path.startswith('/api/'):
        print(f"=== Global exception handler for API ===")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'서버 오류: {str(e)}'
        }), 500
    # 일반 페이지 요청은 기본 에러 처리
    raise e

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': '요청한 API를 찾을 수 없습니다.'}), 404
    return render_template('404.html'), 404 if os.path.exists(os.path.join(app.template_folder, '404.html')) else (str(e), 404)

@app.errorhandler(500)
def internal_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': '내부 서버 오류가 발생했습니다.'}), 500
    return str(e), 500

# ============== 프로필 라우트 ==============

@app.route('/profiles')
def profiles_view():
    profiles = load_profiles()
    current_profile_id = session.get('profile_id')
    current_profile = get_profile(current_profile_id) if current_profile_id else None
    return render_template('profiles.html', profiles=profiles, current_profile=current_profile)

@app.route('/api/profile/create', methods=['POST'])
def create_profile():
    try:
        print("=== Profile creation started ===")
        print(f"Request method: {request.method}")
        print(f"Request content type: {request.content_type}")

        name = request.form.get('name')
        print(f"Profile name: {name}")

        if not name:
            print("Error: No name provided")
            return jsonify({'success': False, 'message': '이름을 입력해주세요.'})

        avatar_path = '/static/avatars/default.svg'
        if 'avatar' in request.files:
            file = request.files['avatar']
            print(f"Avatar file: {file.filename}")
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                print(f"Saving avatar to: {filepath}")
                file.save(filepath)
                avatar_path = f"/static/avatars/{unique_filename}"

        new_profile = {
            'id': str(uuid.uuid4()),
            'name': name,
            'avatar': avatar_path,
            'created_at': datetime.now().isoformat()
        }
        print(f"New profile created: {new_profile}")

        profiles = load_profiles()
        print(f"Existing profiles count: {len(profiles)}")
        profiles.append(new_profile)
        save_profiles(profiles)
        print("Profile saved successfully")

        return jsonify({'success': True, 'profile': new_profile})
    except Exception as e:
        print(f"=== Error creating profile ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()
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
        print(f"Error switching profile: {e}")
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
            print(f"Error deleting profile data files: {file_error}")

        if session.get('profile_id') == profile_id:
            session.pop('profile_id', None)

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting profile: {e}")
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

# ============== YouTube 데이터 함수 ==============

def get_video_info(video_url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
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
                'is_subscribed': is_channel_subscribed(channel_id)
            }
    except Exception as e:
        return {'error': str(e)}

def get_playlist_info(playlist_url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'ignoreerrors': True,
    }
    
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

def get_channel_videos(channel_url, max_videos=30):
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
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    
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
        return []

def search_youtube(query, max_results=20):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }
    
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
        return {'error': str(e)}

def get_trending_videos(max_results=20):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'playlistend': max_results,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info("https://www.youtube.com/feed/trending", download=False)
            
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

@app.route('/')
def index():
    history = load_history()[:8]
    channels = load_channels()[:6]
    trending = get_trending_videos(8)
    return render_template('index.html', history=history, channels=channels, trending=trending)

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
def search():
    query = request.args.get('q', '')
    results = []
    if query:
        results = search_youtube(query)
        if isinstance(results, list):
            for video in results:
                if video.get('channel_id'):
                    video['is_subscribed'] = is_channel_subscribed(video['channel_id'])
    
    user_playlists = load_playlists()
    return render_template('search.html', query=query, results=results, user_playlists=user_playlists)

@app.route('/history')
def history():
    history_data = load_history()
    return render_template('history.html', history=history_data)

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
    
    for channel in channels[:10]:
        channel_url = channel.get('channel_url', '')
        if channel_url:
            videos = get_channel_videos(channel_url, max_videos=5)
            if 'error' not in videos:
                for video in videos.get('videos', []):
                    video['channel'] = channel.get('name')
                    video['channel_id'] = channel.get('channel_id')
                    all_videos.append(video)
    
    random.shuffle(all_videos)
    
    return render_template('feed.html', videos=all_videos[:30], channels=channels)

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
    data = request.get_json()
    video_info = {
        'id': data.get('video_id'),
        'title': data.get('title'),
        'thumbnail': data.get('thumbnail'),
        'duration': data.get('duration'),
        'channel': data.get('channel')
    }
    success = add_to_playlist(playlist_id, video_info)
    return jsonify({'success': success})

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
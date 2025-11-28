"""
MalgeunTube JSON to SQLite 마이그레이션 유틸리티
기존 JSON 데이터를 SQLite 데이터베이스로 마이그레이션합니다.
"""
import os
import json
from datetime import datetime

from models import (
    db, Profile, History, Channel, Playlist, 
    PlaylistVideo, WatchLater, WatchProgress, SearchHistory
)


def load_json_file(filepath):
    """JSON 파일 로드"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            print(f"  ⚠️ JSON 로드 실패: {filepath} - {e}")
            return []
    return []


def parse_datetime(dt_str):
    """ISO 형식 문자열을 datetime으로 변환"""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return datetime.utcnow()


def migrate_profiles(data_dir):
    """프로필 마이그레이션"""
    print("\n📁 프로필 마이그레이션 중...")
    profiles_file = os.path.join(data_dir, 'profiles.json')
    profiles_data = load_json_file(profiles_file)
    
    migrated = 0
    for p in profiles_data:
        if not Profile.query.get(p.get('id')):
            profile = Profile(
                id=p.get('id'),
                name=p.get('name'),
                avatar=p.get('avatar', '/static/avatars/default.svg'),
                created_at=parse_datetime(p.get('created_at'))
            )
            db.session.add(profile)
            migrated += 1
    
    db.session.commit()
    print(f"  ✅ {migrated}개 프로필 마이그레이션 완료")
    return profiles_data


def migrate_history(data_dir, profiles):
    """시청 기록 마이그레이션"""
    print("\n📺 시청 기록 마이그레이션 중...")
    migrated = 0
    
    for profile in profiles:
        profile_id = profile.get('id')
        history_file = os.path.join(data_dir, f'history_{profile_id}.json')
        
        # 레거시 파일 체크
        if not os.path.exists(history_file):
            history_file = os.path.join(data_dir, 'history.json')
        
        history_data = load_json_file(history_file)
        
        for h in history_data:
            video_id = h.get('id')
            if video_id:
                # 중복 체크
                existing = History.query.filter_by(
                    profile_id=profile_id, 
                    video_id=video_id
                ).first()
                
                if not existing:
                    history = History(
                        profile_id=profile_id,
                        video_id=video_id,
                        title=h.get('title'),
                        thumbnail=h.get('thumbnail'),
                        channel=h.get('channel'),
                        channel_id=h.get('channel_id'),
                        duration=h.get('duration'),
                        watched_at=parse_datetime(h.get('watched_at'))
                    )
                    db.session.add(history)
                    migrated += 1
    
    db.session.commit()
    print(f"  ✅ {migrated}개 시청 기록 마이그레이션 완료")


def migrate_channels(data_dir, profiles):
    """구독 채널 마이그레이션"""
    print("\n📡 구독 채널 마이그레이션 중...")
    migrated = 0
    
    for profile in profiles:
        profile_id = profile.get('id')
        channels_file = os.path.join(data_dir, f'channels_{profile_id}.json')
        
        # 레거시 파일 체크
        if not os.path.exists(channels_file):
            channels_file = os.path.join(data_dir, 'channels.json')
        
        channels_data = load_json_file(channels_file)
        
        for c in channels_data:
            channel_id = c.get('channel_id')
            if channel_id:
                # 중복 체크
                existing = Channel.query.filter_by(
                    profile_id=profile_id, 
                    channel_id=channel_id
                ).first()
                
                if not existing:
                    channel = Channel(
                        profile_id=profile_id,
                        channel_id=channel_id,
                        name=c.get('name'),
                        channel_url=c.get('channel_url'),
                        thumbnail=c.get('thumbnail'),
                        added_at=parse_datetime(c.get('added_at'))
                    )
                    db.session.add(channel)
                    migrated += 1
    
    db.session.commit()
    print(f"  ✅ {migrated}개 구독 채널 마이그레이션 완료")


def migrate_playlists(data_dir, profiles):
    """플레이리스트 마이그레이션"""
    print("\n🎵 플레이리스트 마이그레이션 중...")
    migrated_playlists = 0
    migrated_videos = 0
    
    for profile in profiles:
        profile_id = profile.get('id')
        playlists_file = os.path.join(data_dir, f'playlists_{profile_id}.json')
        
        # 레거시 파일 체크
        if not os.path.exists(playlists_file):
            playlists_file = os.path.join(data_dir, 'playlists.json')
        
        playlists_data = load_json_file(playlists_file)
        
        for pl in playlists_data:
            playlist_id = pl.get('id')
            
            if playlist_id and not Playlist.query.get(playlist_id):
                playlist = Playlist(
                    id=playlist_id,
                    profile_id=profile_id,
                    name=pl.get('name'),
                    created_at=parse_datetime(pl.get('created_at'))
                )
                db.session.add(playlist)
                migrated_playlists += 1
                
                # 플레이리스트 영상들 마이그레이션
                videos = pl.get('videos', [])
                for idx, v in enumerate(videos):
                    video_id = v.get('id')
                    if video_id:
                        playlist_video = PlaylistVideo(
                            playlist_id=playlist_id,
                            video_id=video_id,
                            title=v.get('title'),
                            thumbnail=v.get('thumbnail'),
                            duration=v.get('duration'),
                            channel=v.get('channel'),
                            position=idx
                        )
                        db.session.add(playlist_video)
                        migrated_videos += 1
    
    db.session.commit()
    print(f"  ✅ {migrated_playlists}개 플레이리스트, {migrated_videos}개 영상 마이그레이션 완료")


def migrate_watch_later(data_dir, profiles):
    """나중에 볼 영상 마이그레이션"""
    print("\n⏰ 나중에 볼 영상 마이그레이션 중...")
    migrated = 0
    
    for profile in profiles:
        profile_id = profile.get('id')
        watch_later_file = os.path.join(data_dir, f'watch_later_{profile_id}.json')
        watch_later_data = load_json_file(watch_later_file)
        
        for wl in watch_later_data:
            video_id = wl.get('id')
            if video_id:
                existing = WatchLater.query.filter_by(
                    profile_id=profile_id, 
                    video_id=video_id
                ).first()
                
                if not existing:
                    watch_later = WatchLater(
                        profile_id=profile_id,
                        video_id=video_id,
                        title=wl.get('title'),
                        thumbnail=wl.get('thumbnail'),
                        duration=wl.get('duration'),
                        channel=wl.get('channel'),
                        channel_id=wl.get('channel_id'),
                        added_at=parse_datetime(wl.get('added_at'))
                    )
                    db.session.add(watch_later)
                    migrated += 1
    
    db.session.commit()
    print(f"  ✅ {migrated}개 나중에 볼 영상 마이그레이션 완료")


def migrate_watch_progress(data_dir, profiles):
    """시청 진행률 마이그레이션"""
    print("\n📊 시청 진행률 마이그레이션 중...")
    migrated = 0
    
    for profile in profiles:
        profile_id = profile.get('id')
        progress_file = os.path.join(data_dir, f'progress_{profile_id}.json')
        progress_data = load_json_file(progress_file)
        
        for p in progress_data:
            video_id = p.get('video_id')
            if video_id:
                existing = WatchProgress.query.filter_by(
                    profile_id=profile_id, 
                    video_id=video_id
                ).first()
                
                if not existing:
                    progress = WatchProgress(
                        profile_id=profile_id,
                        video_id=video_id,
                        current_time=p.get('current_time', 0),
                        duration=p.get('duration', 0),
                        percentage=p.get('percentage', 0),
                        updated_at=parse_datetime(p.get('updated_at'))
                    )
                    db.session.add(progress)
                    migrated += 1
    
    db.session.commit()
    print(f"  ✅ {migrated}개 시청 진행률 마이그레이션 완료")


def migrate_all(app, data_dir=None):
    """모든 데이터 마이그레이션 실행"""
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    
    print("=" * 50)
    print("🚀 MalgeunTube 데이터 마이그레이션 시작")
    print("=" * 50)
    print(f"📂 데이터 디렉토리: {data_dir}")
    
    with app.app_context():
        # 테이블 생성
        db.create_all()
        
        # 프로필 마이그레이션
        profiles = migrate_profiles(data_dir)
        
        if profiles:
            # 나머지 데이터 마이그레이션
            migrate_history(data_dir, profiles)
            migrate_channels(data_dir, profiles)
            migrate_playlists(data_dir, profiles)
            migrate_watch_later(data_dir, profiles)
            migrate_watch_progress(data_dir, profiles)
        else:
            print("\n⚠️ 마이그레이션할 프로필이 없습니다.")
    
    print("\n" + "=" * 50)
    print("✅ 데이터 마이그레이션 완료!")
    print("=" * 50)


if __name__ == '__main__':
    # 독립 실행 시
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from flask import Flask
    from config import get_config
    
    app = Flask(__name__)
    config_obj = get_config()
    app.config.from_object(config_obj)
    
    from models import db
    db.init_app(app)
    
    migrate_all(app)

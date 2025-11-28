"""
MalgeunTube 데이터베이스 모델
SQLAlchemy를 사용한 데이터 모델 정의
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Profile(db.Model):
    """사용자 프로필 모델"""
    __tablename__ = 'profiles'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    avatar = db.Column(db.String(255), default='/static/avatars/default.svg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 관계 설정
    history = db.relationship('History', backref='profile', lazy='dynamic', cascade='all, delete-orphan')
    channels = db.relationship('Channel', backref='profile', lazy='dynamic', cascade='all, delete-orphan')
    playlists = db.relationship('Playlist', backref='profile', lazy='dynamic', cascade='all, delete-orphan')
    watch_later = db.relationship('WatchLater', backref='profile', lazy='dynamic', cascade='all, delete-orphan')
    watch_progress = db.relationship('WatchProgress', backref='profile', lazy='dynamic', cascade='all, delete-orphan')
    search_history = db.relationship('SearchHistory', backref='profile', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'avatar': self.avatar,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class History(db.Model):
    """시청 기록 모델"""
    __tablename__ = 'history'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.String(36), db.ForeignKey('profiles.id'), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(255))
    thumbnail = db.Column(db.String(255))
    channel = db.Column(db.String(100))
    channel_id = db.Column(db.String(50))
    duration = db.Column(db.Integer)
    watched_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_history_profile_video', 'profile_id', 'video_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.video_id,
            'title': self.title,
            'thumbnail': self.thumbnail,
            'channel': self.channel,
            'channel_id': self.channel_id,
            'duration': self.duration,
            'watched_at': self.watched_at.isoformat() if self.watched_at else None
        }


class Channel(db.Model):
    """구독 채널 모델"""
    __tablename__ = 'channels'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.String(36), db.ForeignKey('profiles.id'), nullable=False)
    channel_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100))
    channel_url = db.Column(db.String(255))
    thumbnail = db.Column(db.String(255))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('profile_id', 'channel_id', name='unique_profile_channel'),
    )
    
    def to_dict(self):
        return {
            'channel_id': self.channel_id,
            'name': self.name,
            'channel_url': self.channel_url,
            'thumbnail': self.thumbnail,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }


class Playlist(db.Model):
    """플레이리스트 모델"""
    __tablename__ = 'playlists'
    
    id = db.Column(db.String(36), primary_key=True)
    profile_id = db.Column(db.String(36), db.ForeignKey('profiles.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 플레이리스트 내 영상들
    videos = db.relationship('PlaylistVideo', backref='playlist', lazy='dynamic', 
                            cascade='all, delete-orphan', order_by='PlaylistVideo.position')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'videos': [v.to_dict() for v in self.videos.order_by(PlaylistVideo.position).all()],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PlaylistVideo(db.Model):
    """플레이리스트 내 영상 모델"""
    __tablename__ = 'playlist_videos'
    
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.String(36), db.ForeignKey('playlists.id'), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(255))
    thumbnail = db.Column(db.String(255))
    duration = db.Column(db.Integer)
    channel = db.Column(db.String(100))
    position = db.Column(db.Integer, default=0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('playlist_id', 'video_id', name='unique_playlist_video'),
    )
    
    def to_dict(self):
        return {
            'id': self.video_id,
            'title': self.title,
            'thumbnail': self.thumbnail,
            'duration': self.duration,
            'channel': self.channel
        }


class WatchLater(db.Model):
    """나중에 볼 영상 모델"""
    __tablename__ = 'watch_later'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.String(36), db.ForeignKey('profiles.id'), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(255))
    thumbnail = db.Column(db.String(255))
    duration = db.Column(db.Integer)
    channel = db.Column(db.String(100))
    channel_id = db.Column(db.String(50))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('profile_id', 'video_id', name='unique_watch_later'),
    )
    
    def to_dict(self):
        return {
            'id': self.video_id,
            'title': self.title,
            'thumbnail': self.thumbnail,
            'duration': self.duration,
            'channel': self.channel,
            'channel_id': self.channel_id,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }


class WatchProgress(db.Model):
    """시청 진행률 모델"""
    __tablename__ = 'watch_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.String(36), db.ForeignKey('profiles.id'), nullable=False)
    video_id = db.Column(db.String(20), nullable=False)
    current_time = db.Column(db.Float, default=0)
    duration = db.Column(db.Float, default=0)
    percentage = db.Column(db.Float, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('profile_id', 'video_id', name='unique_watch_progress'),
    )
    
    def to_dict(self):
        return {
            'video_id': self.video_id,
            'current_time': self.current_time,
            'duration': self.duration,
            'percentage': self.percentage,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SearchHistory(db.Model):
    """검색 기록 모델"""
    __tablename__ = 'search_history'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.String(36), db.ForeignKey('profiles.id'), nullable=False)
    query = db.Column(db.String(255), nullable=False)
    searched_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_search_history_profile', 'profile_id', 'searched_at'),
    )
    
    def to_dict(self):
        return {
            'query': self.query,
            'searched_at': self.searched_at.isoformat() if self.searched_at else None
        }


def init_db(app):
    """데이터베이스 초기화"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

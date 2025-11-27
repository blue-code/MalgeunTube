"""
플레이리스트 추가 기능 테스트
"""
import json
import os

DATA_DIR = 'data'

# 프로필 로드
profiles = []
profiles_file = os.path.join(DATA_DIR, 'profiles.json')
if os.path.exists(profiles_file):
    with open(profiles_file, 'r', encoding='utf-8') as f:
        profiles = json.load(f)

print("=== 프로필 목록 ===")
for profile in profiles:
    print(f"ID: {profile['id']}")
    print(f"Name: {profile['name']}")
    
    # 해당 프로필의 플레이리스트 확인
    playlist_file = os.path.join(DATA_DIR, f"playlists_{profile['id']}.json")
    if os.path.exists(playlist_file):
        with open(playlist_file, 'r', encoding='utf-8') as f:
            playlists = json.load(f)
        
        print(f"\n플레이리스트 개수: {len(playlists)}")
        for pl in playlists:
            print(f"\n  - {pl['name']} (ID: {pl['id']})")
            print(f"    영상 개수: {len(pl['videos'])}")
            for i, video in enumerate(pl['videos'], 1):
                print(f"    {i}. ID: {video.get('id')} | Title: {video.get('title')[:50]}")
                if video.get('id') is None:
                    print(f"       ⚠️  WARNING: Video ID is None!")
    print("-" * 80)

print("\n=== 테스트 결과 ===")
print("위에서 'Video ID is None' 경고가 있다면 플레이리스트 추가가 실패한 것입니다.")
print("수정 후에는 video_id가 제대로 저장되어야 합니다.")


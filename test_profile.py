"""
프로필 생성 기능 테스트 스크립트
"""
import json
import os
from datetime import datetime
import uuid

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
PROFILES_FILE = os.path.join(DATA_DIR, 'profiles.json')

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

def save_json(filepath, data):
    try:
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Successfully saved JSON to {filepath}")
    except Exception as e:
        print(f"Error saving JSON to {filepath}: {e}")
        raise

def test_profile_creation():
    print("=== Testing Profile Creation ===")

    # 테스트 프로필 생성
    new_profile = {
        'id': str(uuid.uuid4()),
        'name': 'Test User',
        'avatar': '/static/avatars/default.svg',
        'created_at': datetime.now().isoformat()
    }

    print(f"New profile: {new_profile}")

    # 기존 프로필 로드
    profiles = load_json(PROFILES_FILE)
    print(f"Existing profiles: {profiles}")

    # 프로필 추가
    profiles.append(new_profile)

    # 저장
    save_json(PROFILES_FILE, profiles)

    # 다시 로드해서 확인
    loaded_profiles = load_json(PROFILES_FILE)
    print(f"Loaded profiles after save: {loaded_profiles}")

    print("\n=== Test Complete ===")
    return True

if __name__ == '__main__':
    try:
        test_profile_creation()
        print("\n✅ Test PASSED!")
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()


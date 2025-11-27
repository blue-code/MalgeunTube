"""
프로필 생성 API 테스트
"""
import requests
import time

# 서버 시작 대기
print("서버 연결 대기 중...")
time.sleep(2)

# 서버 상태 확인
try:
    response = requests.get('http://localhost:5000/profiles')
    print(f"✅ 서버 연결 성공! (Status: {response.status_code})")
except Exception as e:
    print(f"❌ 서버 연결 실패: {e}")
    exit(1)

# 프로필 생성 테스트
print("\n프로필 생성 API 테스트...")

data = {
    'name': 'API Test User'
}

try:
    response = requests.post('http://localhost:5000/api/profile/create', data=data)

    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")

    if 'application/json' in response.headers.get('Content-Type', ''):
        json_data = response.json()
        print(f"\n✅ JSON 응답 성공!")
        print(f"Response Data: {json_data}")

        if json_data.get('success'):
            print(f"\n🎉 프로필 생성 성공!")
            print(f"Profile ID: {json_data.get('profile', {}).get('id')}")
            print(f"Profile Name: {json_data.get('profile', {}).get('name')}")
        else:
            print(f"\n❌ 프로필 생성 실패: {json_data.get('message')}")
    else:
        print(f"\n❌ JSON이 아닌 응답 받음!")
        print(f"Response Text (first 500 chars):\n{response.text[:500]}")

except Exception as e:
    print(f"\n❌ API 호출 실패: {e}")
    import traceback
    traceback.print_exc()


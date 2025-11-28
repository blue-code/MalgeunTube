# YouTube 봇 방지 문제 해결

## 문제점
YouTube에서 봇 방지 메커니즘이 작동하여 다음과 같은 오류가 발생했습니다:
```
ERROR: [youtube] Sign in to confirm you're not a bot. This helps protect our community.
ERROR: [youtube:tab] trending: The channel/playlist does not exist and the URL redirected to youtube.com home page
```

## 적용된 해결책

### 1. yt-dlp 업그레이드
- **이전 버전**: 2024.8.6
- **현재 버전**: 2025.11.12
- 최신 버전은 YouTube의 변경사항에 대한 수정사항을 포함합니다.

### 2. 봇 방지 우회 설정 추가
`app.py`에 다음 설정을 추가했습니다:

```python
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
```

### 3. 모든 YouTube API 호출에 적용
다음 함수들이 업데이트되었습니다:
- `get_video_info_cached()` - 비디오 정보 가져오기
- `get_playlist_info()` - 플레이리스트 정보
- `get_related_videos()` - 관련 영상
- `search_youtube()` - 검색
- `get_trending_videos()` - 트렌딩 영상
- `download_video_task()` - 다운로드

### 4. Trending 페이지 대체
Trending 페이지는 봇 방지가 특히 엄격하므로 인기 검색어를 사용하는 방식으로 변경:
```python
popular_queries = ['music', 'gaming', 'news', 'sports', 'entertainment']
query = random.choice(popular_queries)
results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
```

## 추가 권장사항

### 1. 쿠키 파일 사용 (선택사항)
더 안정적인 접근을 위해 YouTube 쿠키를 사용할 수 있습니다:

1. 브라우저 확장 프로그램으로 YouTube 쿠키 추출 (예: "Get cookies.txt LOCALLY")
2. `cookies.txt` 파일을 프로젝트 루트에 저장
3. `get_ydl_base_opts()`에 다음 추가:
   ```python
   'cookiefile': 'cookies.txt',
   ```

### 2. 요청 간격 조절
너무 많은 요청을 보내지 않도록 주의하세요:
- 캐시 사용 (이미 적용됨)
- Rate limiting (이미 적용됨)
- 필요시 time.sleep() 추가

### 3. 정기적인 yt-dlp 업데이트
YouTube는 자주 변경되므로 yt-dlp를 정기적으로 업데이트하세요:
```bash
pip install --upgrade yt-dlp
```

## 테스트
다음 명령으로 서버를 재시작하고 테스트하세요:
```bash
python app.py
```

모든 기능이 정상 작동해야 합니다:
- ✅ 비디오 검색
- ✅ 비디오 재생
- ✅ 관련 영상
- ✅ 다운로드
- ✅ 트렌딩 (인기 검색어 기반)

## 문제 지속 시
1. yt-dlp 버전 확인: `pip show yt-dlp`
2. 최신 버전으로 업데이트: `pip install --upgrade yt-dlp`
3. 캐시 초기화: 브라우저에서 Ctrl+Shift+R
4. 쿠키 파일 사용 고려


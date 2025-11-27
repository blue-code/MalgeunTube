# 🎬 MalgeunTube (맑은튜브)

광고 없이 깨끗하게 YouTube를 시청하고, 다운로드까지 가능한 웹 애플리케이션입니다.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ 주요 기능

- 🚫 **광고 없는 재생** - 깨끗하게 영상 시청
- 📥 **영상/음원 다운로드** - 원하는 화질(4K/1080p 등)의 영상이나 고음질 MP3 추출 다운로드
- 👤 **프로필 관리** - 여러 프로필을 생성하여 개인별 시청 기록, 구독, 플레이리스트 분리 관리
- 🎵 **강력한 플레이리스트** - 나만의 플레이리스트 생성, YouTube 플레이리스트 가져오기
- ⭐ **채널 구독(즐겨찾기)** - 로그인 없이 좋아하는 채널 구독 및 피드 확인
- ⚙️ **화질 자동 설정** - 선호하는 화질(Best, 1080p, Data Saver 등) 고정 기능
- 🎯 **검색 및 추천** - 유튜브 검색 및 관련 영상/인기 급상승 영상 제공
- ⚡ **재생 속도 조절** - 0.5x ~ 2x 속도 조절
- 🌙 **다크/라이트 모드** - 눈이 편한 테마 스위칭
- 📱 **반응형 디자인** - 모바일/태블릿/PC 완벽 지원
- 📝 **시청 기록** - 로컬에 안전하게 저장되는 시청 내역

## 📁 프로젝트 구조

```
MalgeunTube/
├── app.py                 # Flask 메인 애플리케이션
├── requirements.txt       # 의존성 패키지 목록
├── setup.bat             # Windows 간편 설치 스크립트
├── run.bat               # Windows 간편 실행 스크립트
├── README.md             # 프로젝트 설명서
├── .gitignore            # Git 제외 파일 목록
├── templates/            # HTML 템플릿 (UI)
│   ├── base.html         # 기본 레이아웃 (설정 모달 포함)
│   ├── index.html        # 메인 (인기 급상승)
│   ├── watch.html        # 영상 시청 (플레이어, 다운로드)
│   ├── search.html       # 검색 결과
│   ├── playlist.html     # 플레이리스트 상세
│   ├── playlists.html    # 내 플레이리스트 목록
│   └── ...
├── static/               # 정적 리소스
│   ├── css/style.css     # 스타일시트
│   └── js/main.js        # 클라이언트 로직
├── data/                 # 사용자 데이터 (JSON DB)
│   ├── profiles.json     # 프로필 목록
│   ├── history.json      # 시청 기록 (기본/레거시)
│   ├── channels.json     # 구독 채널 목록 (기본/레거시)
│   ├── playlists.json    # 사용자 플레이리스트 (기본/레거시)
│   ├── history_{profile_id}.json   # 프로필별 시청 기록
│   ├── channels_{profile_id}.json  # 프로필별 구독 채널
│   └── playlists_{profile_id}.json # 프로필별 플레이리스트
└── downloads/            # 다운로드 임시 저장소
```

## 🚀 설치 방법

### 요구사항

- Python 3.8 이상
- pip (Python 패키지 관리자)

### Windows

1. 프로젝트 폴더로 이동합니다.
2. `setup.bat` 파일을 실행하여 필요한 패키지를 설치합니다.
3. `run.bat` 파일을 실행하여 서버를 시작합니다.
4. 브라우저가 자동으로 열리거나 `http://localhost:5000`으로 접속합니다.

### Linux / macOS

```bash
# 1. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 애플리케이션 실행
python app.py
```

## 💻 사용 방법

### 0. 프로필 생성 및 관리 👤
- 첫 실행 시 `/profiles` 페이지에서 **프로필을 생성**하세요.
- 가족 구성원마다 별도의 프로필을 만들어 각자의 시청 기록과 구독을 관리할 수 있습니다.
- 프로필마다 독립적인 시청 기록, 채널 구독, 플레이리스트가 저장됩니다.
- 언제든지 프로필을 전환하거나 삭제할 수 있습니다.

### 1. 영상 시청 및 검색
- 메인 화면에서 바로 **인기 급상승 영상**을 확인할 수 있습니다.
- 상단 검색창에 검색어 또는 YouTube URL을 입력하세요.
- 플레이리스트 URL을 입력하면 해당 리스트를 그대로 가져옵니다.

### 2. 다운로드 기능 📥
- 영상 재생 화면 하단의 **다운로드 버튼**을 클릭하세요.
- **비디오 탭**: 최고 화질, 1080p, 720p 등 원하는 해상도를 선택하여 MP4로 다운로드.
- **오디오 탭**: 고음질(320k), 일반(192k) 등을 선택하여 MP3로 추출 다운로드.

### 3. 플레이리스트 관리 🎵
- 검색 결과나 재생 화면에서 `+` 버튼을 눌러 **나만의 플레이리스트**에 영상을 추가하세요.
- '리스트' 메뉴에서 생성한 목록을 관리하고 연속 재생할 수 있습니다.

### 4. 채널 구독 ⭐
- 마음에 드는 채널은 '즐겨찾기(별표)' 버튼을 눌러 구독하세요.
- '피드' 메뉴에서 구독한 채널의 최신 영상을 모아볼 수 있습니다.

### 5. 설정 ⚙️
- 상단 메뉴의 ⚙️(설정) 아이콘을 눌러 **기본 화질**을 설정하세요.
- 설정한 화질에 맞춰 영상이 자동으로 재생됩니다.

## ⌨️ 키보드 단축키

| 키 | 기능 |
|---|---|
| `Space` / `K` | 재생/일시정지 |
| `←` / `J` | 5초 뒤로 |
| `→` / `L` | 5초 앞으로 |
| `↑` | 볼륨 높이기 |
| `↓` | 볼륨 낮추기 |
| `F` | 전체화면 |
| `M` | 음소거 |

## 🛠️ 기술 스택

- **Backend**: Python, Flask
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Core Engine**: yt-dlp (YouTube Data & Stream Extraction)
- **Data Storage**: JSON-based Local Storage (No SQL required)

## ⚠️ 주의사항

1. **개인 사용 목적으로만 사용하세요.**
2. 이 프로젝트는 학습 및 연구 목적으로 개발되었습니다.
3. 대량의 영상 다운로드나 과도한 트래픽 유발은 YouTube에 의해 IP가 차단될 수 있습니다.
4. 저작권이 있는 콘텐츠를 무단으로 배포하거나 상업적으로 이용하는 것은 불법입니다.

## 📄 라이선스

MIT License

---

Made with ❤️ by MalgeunTube Team
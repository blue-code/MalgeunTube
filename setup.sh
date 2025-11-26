#!/bin/bash

echo "🎬 AdFree Tube 설치를 시작합니다..."

# 가상환경 생성
python3 -m venv venv
echo "✅ 가상환경 생성 완료"

# 가상환경 활성화
source venv/bin/activate
echo "✅ 가상환경 활성화 완료"

# 의존성 설치
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ 의존성 설치 완료"

# 디렉토리 생성
mkdir -p static/css static/js templates data
echo "✅ 디렉토리 생성 완료"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 설치가 완료되었습니다!"
echo ""
echo "실행 방법:"
echo "  1. source venv/bin/activate"
echo "  2. python app.py"
echo "  3. 브라우저에서 http://localhost:5000 접속"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
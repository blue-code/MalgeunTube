/**
 * Touch Gestures for Video Player
 * 터치 제스처 기능 - 모바일 사용자 경험 개선
 */

(function() {
    'use strict';

    // ============== 설정 ==============
    var CONFIG = {
        // 더블 탭 설정
        DOUBLE_TAP_DELAY: 300,           // 더블 탭 인식 시간 (ms)
        SEEK_TIME: 10,                   // 더블 탭 시 이동 시간 (초)
        
        // 스와이프 설정
        SWIPE_THRESHOLD: 30,             // 스와이프 인식 최소 거리 (px)
        VERTICAL_SWIPE_SENSITIVITY: 150, // 세로 스와이프 감도 (높을수록 덜 민감)
        HORIZONTAL_SWIPE_SENSITIVITY: 2, // 가로 스와이프 감도 (초/100px)
        
        // 핀치 줌 설정
        PINCH_THRESHOLD: 50,             // 핀치 인식 최소 거리 변화 (px)
        
        // 영역 분할 비율
        LEFT_ZONE_RATIO: 0.33,           // 왼쪽 영역 (0-33%)
        RIGHT_ZONE_RATIO: 0.67           // 오른쪽 영역 (67-100%)
    };

    // ============== 상태 변수 ==============
    var state = {
        lastTap: 0,
        lastTapX: 0,
        lastTapY: 0,
        touchStartX: 0,
        touchStartY: 0,
        touchStartTime: 0,
        initialVolume: 1,
        initialBrightness: 1,
        initialTime: 0,
        isSwiping: false,
        swipeDirection: null,
        pinchStartDistance: 0,
        isPinching: false,
        brightnessFilter: null
    };

    // ============== 유틸리티 함수 ==============
    
    /**
     * 시간 포맷팅 (초 -> MM:SS 또는 HH:MM:SS)
     */
    function formatTime(seconds) {
        var absSeconds = Math.abs(seconds);
        var sign = seconds < 0 ? '-' : '+';
        var h = Math.floor(absSeconds / 3600);
        var m = Math.floor((absSeconds % 3600) / 60);
        var s = Math.floor(absSeconds % 60);
        
        if (h > 0) {
            return sign + h + ':' + (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
        }
        return sign + m + ':' + (s < 10 ? '0' : '') + s;
    }

    /**
     * 터치 위치의 영역 판별 (left, center, right)
     */
    function getTouchZone(x, width) {
        var ratio = x / width;
        if (ratio < CONFIG.LEFT_ZONE_RATIO) {
            return 'left';
        } else if (ratio > CONFIG.RIGHT_ZONE_RATIO) {
            return 'right';
        }
        return 'center';
    }

    /**
     * 두 터치 포인트 사이의 거리 계산
     */
    function getTouchDistance(touches) {
        if (touches.length < 2) return 0;
        var dx = touches[0].clientX - touches[1].clientX;
        var dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    // ============== UI 오버레이 생성 ==============
    
    /**
     * 제스처 오버레이 컨테이너 생성
     */
    function createGestureOverlay(wrapper) {
        // 메인 오버레이
        var overlay = document.createElement('div');
        overlay.className = 'gesture-overlay';
        overlay.id = 'gesture-overlay';
        
        // 더블 탭 피드백 (왼쪽)
        var leftFeedback = document.createElement('div');
        leftFeedback.className = 'double-tap-feedback left';
        leftFeedback.id = 'double-tap-left';
        leftFeedback.innerHTML = '<div class="ripple"></div><div class="icon">◀◀<span class="seek-text">10초</span></div>';
        
        // 더블 탭 피드백 (오른쪽)
        var rightFeedback = document.createElement('div');
        rightFeedback.className = 'double-tap-feedback right';
        rightFeedback.id = 'double-tap-right';
        rightFeedback.innerHTML = '<div class="ripple"></div><div class="icon"><span class="seek-text">10초</span>▶▶</div>';
        
        // 더블 탭 피드백 (중앙)
        var centerFeedback = document.createElement('div');
        centerFeedback.className = 'double-tap-feedback center';
        centerFeedback.id = 'double-tap-center';
        centerFeedback.innerHTML = '<div class="icon play-pause-icon">⏸</div>';
        
        // 볼륨/밝기 조절 인디케이터
        var controlIndicator = document.createElement('div');
        controlIndicator.className = 'control-indicator';
        controlIndicator.id = 'control-indicator';
        controlIndicator.innerHTML = '<div class="indicator-icon"></div><div class="indicator-bar"><div class="indicator-fill"></div></div><div class="indicator-text"></div>';
        
        // 탐색 시간 표시
        var seekIndicator = document.createElement('div');
        seekIndicator.className = 'seek-indicator';
        seekIndicator.id = 'seek-indicator';
        seekIndicator.innerHTML = '<div class="seek-time"></div><div class="seek-preview"></div>';
        
        overlay.appendChild(leftFeedback);
        overlay.appendChild(rightFeedback);
        overlay.appendChild(centerFeedback);
        overlay.appendChild(controlIndicator);
        overlay.appendChild(seekIndicator);
        
        wrapper.appendChild(overlay);
        
        return overlay;
    }

    // ============== 더블 탭 처리 ==============
    
    /**
     * 더블 탭 피드백 표시
     */
    function showDoubleTapFeedback(zone, player) {
        var feedbackId = 'double-tap-' + zone;
        var feedback = document.getElementById(feedbackId);
        
        if (!feedback) return;
        
        // 중앙 탭인 경우 아이콘 업데이트
        if (zone === 'center') {
            var icon = feedback.querySelector('.play-pause-icon');
            if (icon) {
                icon.textContent = player.paused ? '▶' : '⏸';
            }
        }
        
        // 애니메이션 클래스 추가
        feedback.classList.add('active');
        
        // 애니메이션 종료 후 클래스 제거
        setTimeout(function() {
            feedback.classList.remove('active');
        }, 500);
    }

    /**
     * 더블 탭 동작 실행
     */
    function handleDoubleTap(zone, player) {
        if (!player) return;
        
        switch (zone) {
            case 'left':
                player.currentTime = Math.max(0, player.currentTime - CONFIG.SEEK_TIME);
                showToast('-' + CONFIG.SEEK_TIME + '초');
                break;
            case 'right':
                player.currentTime = Math.min(player.duration, player.currentTime + CONFIG.SEEK_TIME);
                showToast('+' + CONFIG.SEEK_TIME + '초');
                break;
            case 'center':
                if (player.paused) {
                    player.play();
                } else {
                    player.pause();
                }
                break;
        }
        
        showDoubleTapFeedback(zone, player);
    }

    // ============== 스와이프 처리 ==============
    
    /**
     * 볼륨/밝기 인디케이터 표시
     */
    function showControlIndicator(type, value) {
        var indicator = document.getElementById('control-indicator');
        if (!indicator) return;
        
        var iconEl = indicator.querySelector('.indicator-icon');
        var fillEl = indicator.querySelector('.indicator-fill');
        var textEl = indicator.querySelector('.indicator-text');
        
        indicator.className = 'control-indicator active ' + type;
        
        if (type === 'volume') {
            if (value === 0) {
                iconEl.textContent = '🔇';
            } else if (value < 0.5) {
                iconEl.textContent = '🔉';
            } else {
                iconEl.textContent = '🔊';
            }
            textEl.textContent = Math.round(value * 100) + '%';
        } else if (type === 'brightness') {
            if (value < 0.3) {
                iconEl.textContent = '🌙';
            } else if (value < 0.7) {
                iconEl.textContent = '☀️';
            } else {
                iconEl.textContent = '🔆';
            }
            textEl.textContent = Math.round(value * 100) + '%';
        }
        
        fillEl.style.height = (value * 100) + '%';
    }

    /**
     * 인디케이터 숨기기
     */
    function hideControlIndicator() {
        var indicator = document.getElementById('control-indicator');
        if (indicator) {
            indicator.classList.remove('active');
        }
    }

    /**
     * 탐색 인디케이터 표시
     */
    function showSeekIndicator(seekTime, currentTime, duration) {
        var indicator = document.getElementById('seek-indicator');
        if (!indicator) return;
        
        var timeEl = indicator.querySelector('.seek-time');
        var previewEl = indicator.querySelector('.seek-preview');
        
        indicator.classList.add('active');
        
        var newTime = currentTime + seekTime;
        newTime = Math.max(0, Math.min(duration, newTime));
        
        timeEl.textContent = formatTime(seekTime);
        
        // 미리보기 시간 표시
        var h = Math.floor(newTime / 3600);
        var m = Math.floor((newTime % 3600) / 60);
        var s = Math.floor(newTime % 60);
        var timeStr = h > 0 
            ? h + ':' + (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s
            : m + ':' + (s < 10 ? '0' : '') + s;
        previewEl.textContent = timeStr;
    }

    /**
     * 탐색 인디케이터 숨기기
     */
    function hideSeekIndicator() {
        var indicator = document.getElementById('seek-indicator');
        if (indicator) {
            indicator.classList.remove('active');
        }
    }

    /**
     * 화면 밝기 조절 (CSS 필터 사용)
     */
    function setBrightness(value, wrapper) {
        if (!state.brightnessFilter) {
            state.brightnessFilter = document.createElement('div');
            state.brightnessFilter.className = 'brightness-filter';
            wrapper.appendChild(state.brightnessFilter);
        }
        
        // 밝기 값: 0 = 어둡게, 1 = 원본, 밝기는 최대 1까지
        var darkness = 1 - value;
        state.brightnessFilter.style.opacity = darkness;
    }

    /**
     * 세로 스와이프 처리 (볼륨/밝기)
     */
    function handleVerticalSwipe(deltaY, zone, player, wrapper) {
        var change = -deltaY / CONFIG.VERTICAL_SWIPE_SENSITIVITY;
        
        if (zone === 'right') {
            // 볼륨 조절
            var newVolume = state.initialVolume + change;
            newVolume = Math.max(0, Math.min(1, newVolume));
            player.volume = newVolume;
            showControlIndicator('volume', newVolume);
        } else if (zone === 'left') {
            // 밝기 조절
            var newBrightness = state.initialBrightness + change;
            newBrightness = Math.max(0, Math.min(1, newBrightness));
            setBrightness(newBrightness, wrapper);
            showControlIndicator('brightness', newBrightness);
        }
    }

    /**
     * 가로 스와이프 처리 (탐색)
     */
    function handleHorizontalSwipe(deltaX, player) {
        var seekTime = (deltaX / 100) * CONFIG.HORIZONTAL_SWIPE_SENSITIVITY;
        showSeekIndicator(seekTime, state.initialTime, player.duration);
        return seekTime;
    }

    // ============== 핀치 줌 처리 ==============
    
    /**
     * 전체화면 토글
     */
    function toggleFullscreen(player) {
        if (document.fullscreenElement) {
            document.exitFullscreen().catch(function() {});
        } else if (player) {
            var wrapper = player.closest('.video-wrapper');
            if (wrapper && wrapper.requestFullscreen) {
                wrapper.requestFullscreen().catch(function() {
                    // wrapper 전체화면 실패 시 비디오 전체화면 시도
                    if (player.requestFullscreen) {
                        player.requestFullscreen().catch(function() {});
                    }
                });
            } else if (player.requestFullscreen) {
                player.requestFullscreen().catch(function() {});
            }
        }
    }

    // ============== 이벤트 핸들러 ==============
    
    /**
     * 터치 시작
     */
    function onTouchStart(e, player, wrapper) {
        // 두 손가락 터치 (핀치 시작)
        if (e.touches.length === 2) {
            state.isPinching = true;
            state.pinchStartDistance = getTouchDistance(e.touches);
            return;
        }
        
        if (e.touches.length !== 1) return;
        
        var touch = e.touches[0];
        state.touchStartX = touch.clientX;
        state.touchStartY = touch.clientY;
        state.touchStartTime = Date.now();
        state.initialVolume = player.volume;
        state.initialTime = player.currentTime;
        state.isSwiping = false;
        state.swipeDirection = null;
        
        // 밝기 값 초기화 (brightness filter opacity에서 역산)
        if (state.brightnessFilter) {
            state.initialBrightness = 1 - parseFloat(state.brightnessFilter.style.opacity || 0);
        } else {
            state.initialBrightness = 1;
        }
    }

    /**
     * 터치 이동
     */
    function onTouchMove(e, player, wrapper) {
        // 핀치 중
        if (state.isPinching && e.touches.length === 2) {
            e.preventDefault();
            return;
        }
        
        if (e.touches.length !== 1) return;
        
        var touch = e.touches[0];
        var deltaX = touch.clientX - state.touchStartX;
        var deltaY = touch.clientY - state.touchStartY;
        var absDeltaX = Math.abs(deltaX);
        var absDeltaY = Math.abs(deltaY);
        
        // 스와이프 방향 결정 (한 번만)
        if (!state.swipeDirection && (absDeltaX > CONFIG.SWIPE_THRESHOLD || absDeltaY > CONFIG.SWIPE_THRESHOLD)) {
            state.swipeDirection = absDeltaX > absDeltaY ? 'horizontal' : 'vertical';
            state.isSwiping = true;
        }
        
        if (!state.isSwiping) return;
        
        e.preventDefault();
        
        var rect = wrapper.getBoundingClientRect();
        var zone = getTouchZone(state.touchStartX - rect.left, rect.width);
        
        if (state.swipeDirection === 'vertical') {
            handleVerticalSwipe(deltaY, zone, player, wrapper);
        } else if (state.swipeDirection === 'horizontal') {
            handleHorizontalSwipe(deltaX, player);
        }
    }

    /**
     * 터치 종료
     */
    function onTouchEnd(e, player, wrapper) {
        // 핀치 종료
        if (state.isPinching) {
            if (e.touches.length < 2) {
                var endDistance = e.touches.length === 1 
                    ? getTouchDistance([e.touches[0], e.changedTouches[0]])
                    : getTouchDistance(e.changedTouches);
                
                var pinchDelta = endDistance - state.pinchStartDistance;
                
                if (Math.abs(pinchDelta) > CONFIG.PINCH_THRESHOLD) {
                    if (pinchDelta > 0) {
                        // 핀치 아웃 - 전체화면 진입
                        if (!document.fullscreenElement) {
                            toggleFullscreen(player);
                            showToast('전체화면');
                        }
                    } else {
                        // 핀치 인 - 전체화면 종료
                        if (document.fullscreenElement) {
                            toggleFullscreen(player);
                            showToast('전체화면 종료');
                        }
                    }
                }
                
                state.isPinching = false;
                state.pinchStartDistance = 0;
            }
            return;
        }
        
        // 스와이프 종료 처리
        if (state.isSwiping) {
            if (state.swipeDirection === 'horizontal') {
                // 탐색 적용
                var touch = e.changedTouches[0];
                var deltaX = touch.clientX - state.touchStartX;
                var seekTime = (deltaX / 100) * CONFIG.HORIZONTAL_SWIPE_SENSITIVITY;
                var newTime = state.initialTime + seekTime;
                player.currentTime = Math.max(0, Math.min(player.duration, newTime));
                
                if (Math.abs(seekTime) >= 1) {
                    showToast(formatTime(seekTime));
                }
            }
            
            hideControlIndicator();
            hideSeekIndicator();
            state.isSwiping = false;
            state.swipeDirection = null;
            return;
        }
        
        // 더블 탭 감지
        var now = Date.now();
        var touch = e.changedTouches[0];
        var rect = wrapper.getBoundingClientRect();
        var x = touch.clientX - rect.left;
        var y = touch.clientY - rect.top;
        
        var timeSinceLastTap = now - state.lastTap;
        var distFromLastTap = Math.sqrt(
            Math.pow(x - state.lastTapX, 2) + 
            Math.pow(y - state.lastTapY, 2)
        );
        
        if (timeSinceLastTap < CONFIG.DOUBLE_TAP_DELAY && distFromLastTap < 50) {
            // 더블 탭 감지됨
            var zone = getTouchZone(x, rect.width);
            handleDoubleTap(zone, player);
            
            // 상태 리셋
            state.lastTap = 0;
            state.lastTapX = 0;
            state.lastTapY = 0;
        } else {
            // 첫 번째 탭
            state.lastTap = now;
            state.lastTapX = x;
            state.lastTapY = y;
        }
    }

    // ============== 초기화 ==============
    
    /**
     * 터치 제스처 초기화
     */
    function initTouchGestures() {
        var wrapper = document.getElementById('video-wrapper');
        var player = document.getElementById('video-player');
        
        if (!wrapper || !player) {
            // 플레이어가 없으면 초기화하지 않음
            return;
        }
        
        // 터치 지원 여부 확인
        if (!('ontouchstart' in window)) {
            return;
        }
        
        // 오버레이 생성
        createGestureOverlay(wrapper);
        
        // 이벤트 리스너 등록
        wrapper.addEventListener('touchstart', function(e) {
            onTouchStart(e, player, wrapper);
        }, { passive: true });
        
        wrapper.addEventListener('touchmove', function(e) {
            onTouchMove(e, player, wrapper);
        }, { passive: false });
        
        wrapper.addEventListener('touchend', function(e) {
            onTouchEnd(e, player, wrapper);
        }, { passive: true });
        
        wrapper.addEventListener('touchcancel', function() {
            state.isSwiping = false;
            state.swipeDirection = null;
            state.isPinching = false;
            hideControlIndicator();
            hideSeekIndicator();
        }, { passive: true });
        
        console.log('🎮 터치 제스처 초기화 완료');
    }

    // DOM 로드 후 초기화
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTouchGestures);
    } else {
        initTouchGestures();
    }

    // 전역 설정 노출 (감도 조절 가능)
    window.TouchGestureConfig = CONFIG;

})();

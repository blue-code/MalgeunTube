// 테마 관리
var themeToggle = document.getElementById('theme-toggle');
var html = document.documentElement;

var savedTheme = localStorage.getItem('theme') || 'dark';
html.setAttribute('data-theme', savedTheme);

if (themeToggle) {
    themeToggle.addEventListener('click', function() {
        var currentTheme = html.getAttribute('data-theme');
        var newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    });
}

// 모바일 메뉴 토글
var menuToggle = document.getElementById('menu-toggle');
var navLinks = document.getElementById('nav-links');
var navOverlay = document.getElementById('nav-overlay');

if (menuToggle) {
    menuToggle.addEventListener('click', function() {
        navLinks.classList.toggle('show');
        navOverlay.classList.toggle('show');
    });
}

if (navOverlay) {
    navOverlay.addEventListener('click', function() {
        navLinks.classList.remove('show');
        navOverlay.classList.remove('show');
    });
}

// 이미지 로딩 에러 처리
var images = document.querySelectorAll('img');
for (var i = 0; i < images.length; i++) {
    images[i].addEventListener('error', function() {
        this.style.backgroundColor = '#333';
        this.alt = '';
    });
}

// Toast 알림
function showToast(message, duration) {
    duration = duration || 2000;
    var toast = document.getElementById('toast');
    if (toast) {
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(function() {
            toast.classList.remove('show');
        }, duration);
    }
}

// 키보드 단축키 도움말
console.log('\n🎬 MalgeunTube 키보드 단축키:\n' +
    '━━━━━━━━━━━━━━━━━━━━━━━━━━\n' +
    'Space / K  : 재생/일시정지\n' +
    '← / J      : 5초 뒤로\n' +
    '→ / L      : 5초 앞으로\n' +
    '↑          : 볼륨 높이기\n' +
    '↓          : 볼륨 낮추기\n' +
    'F          : 전체화면\n' +
    'M          : 음소거\n' +
    '━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

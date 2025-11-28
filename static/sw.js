/**
 * MalgeunTube Service Worker
 * 오프라인 지원 및 캐싱 전략
 */

const CACHE_NAME = 'malgeuntube-v1';
const STATIC_CACHE_NAME = 'malgeuntube-static-v1';
const DYNAMIC_CACHE_NAME = 'malgeuntube-dynamic-v1';

// 정적 리소스 캐시 목록
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/manifest.json'
];

// 캐시 전략 설정
const CACHE_STRATEGIES = {
    // 정적 리소스: Cache First
    static: [
        '/static/css/',
        '/static/js/',
        '/static/icons/',
        '/static/avatars/'
    ],
    // API 요청: Network First
    networkFirst: [
        '/api/',
        '/search',
        '/watch'
    ],
    // 이미지: Cache First with Network Fallback
    images: [
        'https://img.youtube.com/',
        'https://i.ytimg.com/'
    ]
};

// 서비스 워커 설치
self.addEventListener('install', (event) => {
    console.log('[SW] Installing Service Worker...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[SW] Installation complete');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Installation failed:', error);
            })
    );
});

// 서비스 워커 활성화
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating Service Worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => {
                            return name.startsWith('malgeuntube-') && 
                                   name !== STATIC_CACHE_NAME && 
                                   name !== DYNAMIC_CACHE_NAME;
                        })
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[SW] Activation complete');
                return self.clients.claim();
            })
    );
});

// 요청 가로채기 및 캐시 전략 적용
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // 비디오 스트리밍 요청은 캐시하지 않음
    if (url.pathname.includes('/watch') && event.request.headers.get('range')) {
        return;
    }
    
    // 정적 리소스: Cache First
    if (isStaticAsset(url)) {
        event.respondWith(cacheFirst(event.request));
        return;
    }
    
    // YouTube 이미지: Stale While Revalidate
    if (isYouTubeImage(url)) {
        event.respondWith(staleWhileRevalidate(event.request));
        return;
    }
    
    // API 및 동적 페이지: Network First
    if (isNetworkFirstRequest(url)) {
        event.respondWith(networkFirst(event.request));
        return;
    }
    
    // 기본: Network First
    event.respondWith(networkFirst(event.request));
});

// 캐시 전략: Cache First
async function cacheFirst(request) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.error('[SW] Cache First failed:', error);
        return new Response('Offline', { status: 503 });
    }
}

// 캐시 전략: Network First
async function networkFirst(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // 오프라인 폴백
        if (request.mode === 'navigate') {
            return caches.match('/');
        }
        
        return new Response('Offline', { status: 503 });
    }
}

// 캐시 전략: Stale While Revalidate
async function staleWhileRevalidate(request) {
    const cache = await caches.open(DYNAMIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    const fetchPromise = fetch(request)
        .then((networkResponse) => {
            if (networkResponse.ok) {
                cache.put(request, networkResponse.clone());
            }
            return networkResponse;
        })
        .catch(() => cachedResponse);
    
    return cachedResponse || fetchPromise;
}

// 헬퍼 함수들
function isStaticAsset(url) {
    return CACHE_STRATEGIES.static.some(path => url.pathname.startsWith(path));
}

function isNetworkFirstRequest(url) {
    return CACHE_STRATEGIES.networkFirst.some(path => url.pathname.startsWith(path));
}

function isYouTubeImage(url) {
    return CACHE_STRATEGIES.images.some(domain => url.href.startsWith(domain));
}

// 푸시 알림 (향후 확장)
self.addEventListener('push', (event) => {
    if (!event.data) return;
    
    const data = event.data.json();
    
    event.waitUntil(
        self.registration.showNotification(data.title || 'MalgeunTube', {
            body: data.body || '',
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/icon-72x72.png',
            data: data.url || '/'
        })
    );
});

// 알림 클릭 처리
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    event.waitUntil(
        clients.openWindow(event.notification.data || '/')
    );
});

// 백그라운드 동기화 (향후 확장)
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-watch-progress') {
        event.waitUntil(syncWatchProgress());
    }
});

async function syncWatchProgress() {
    // 오프라인에서 저장된 시청 진행률을 서버에 동기화
    console.log('[SW] Syncing watch progress...');
}

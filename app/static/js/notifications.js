const publicVapidKey = 'BEWyGqMWafmjeAy4CHHd2iUAeTlpE7kxSh3GDa6NyMeZ3e3_363xUdx-5mw1yl9l_6bMsBi7EyhUCyNZB1NvR1c';

document.addEventListener('DOMContentLoaded', () => {
    const enableBtn = document.getElementById('enable-notifications-btn');

    // Detect iOS
    function isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
            (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    // Detect if running as installed PWA
    function isPWA() {
        return window.matchMedia('(display-mode: standalone)').matches ||
            window.navigator.standalone === true;
    }

    // Check if push is supported
    function isPushSupported() {
        return 'serviceWorker' in navigator &&
            'PushManager' in window &&
            'Notification' in window;
    }

    function checkNotificationPermission() {
        // For iOS Safari, only show if PWA and iOS 16.4+
        if (isIOS()) {
            if (!isPWA()) {
                console.log('iOS: Please add to Home Screen for notifications');
                if (enableBtn) {
                    enableBtn.textContent = 'أضف للشاشة الرئيسية للإشعارات';
                    enableBtn.classList.remove('hidden');
                    enableBtn.disabled = true;
                }
                return;
            }
        }

        if (!isPushSupported()) {
            console.log('Push notifications not supported');
            if (enableBtn) enableBtn.classList.add('hidden');
            return;
        }

        if (Notification.permission === 'default') {
            if (enableBtn) {
                enableBtn.classList.remove('hidden');
                enableBtn.disabled = false;
                enableBtn.addEventListener('click', async function () {
                    try {
                        const permission = await Notification.requestPermission();
                        if (permission === 'granted') {
                            console.log('Notification permission granted.');
                            enableBtn.classList.add('hidden');
                            await registerServiceWorker();
                        } else {
                            console.log('Notification permission denied');
                        }
                    } catch (err) {
                        console.error('Permission request failed:', err);
                    }
                });
            }
        } else if (Notification.permission === 'granted') {
            if (enableBtn) enableBtn.classList.add('hidden');
            registerServiceWorker();
        } else {
            console.log('Notification permission denied.');
            if (enableBtn) {
                enableBtn.classList.remove('hidden');
                enableBtn.textContent = 'الإشعارات محظورة - غير الإعدادات';
                enableBtn.disabled = true;
            }
        }
    }

    // Initial check
    checkNotificationPermission();

    async function registerServiceWorker() {
        if (!('serviceWorker' in navigator)) {
            console.log('Service Worker not supported');
            return;
        }

        try {
            // Use scope for better compatibility
            const registration = await navigator.serviceWorker.register('/sw.js', {
                scope: '/'
            });
            console.log('Service Worker Registered:', registration.scope);

            // Wait for the service worker to be ready
            await navigator.serviceWorker.ready;
            console.log('Service Worker is ready');

            // Subscribe to push notifications
            await subscribeUser(registration);
        } catch (error) {
            console.error('Service Worker Registration Failed:', error);
        }
    }

    async function subscribeUser(registration) {
        if (!('PushManager' in window)) {
            console.log('PushManager not supported');
            return;
        }

        try {
            // Check for existing subscription first
            let subscription = await registration.pushManager.getSubscription();

            if (!subscription) {
                // Create new subscription
                subscription = await registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(publicVapidKey)
                });
                console.log('New push subscription created');
            } else {
                console.log('Using existing push subscription');
            }

            console.log('User is subscribed:', subscription.endpoint);

            // Send subscription to server
            const response = await fetch('/subscribe', {
                method: 'POST',
                body: JSON.stringify(subscription),
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                console.log('Subscription sent to server successfully');
            } else {
                console.error('Failed to send subscription to server:', response.status);
            }
        } catch (err) {
            console.error('Failed to subscribe the user:', err);
            // Handle specific errors
            if (err.name === 'NotAllowedError') {
                console.log('Permission was denied');
            } else if (err.name === 'AbortError') {
                console.log('Subscription was aborted');
            }
        }
    }

    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    // Poll for unread notifications count
    async function checkUnreadNotifications() {
        const isLoggedIn = document.body.getAttribute('data-user-logged-in') === 'true';
        if (!isLoggedIn) return;

        try {
            const response = await fetch('/api/notifications/unread-count');
            if (response.ok) {
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.indexOf("application/json") !== -1) {
                    const data = await response.json();
                    const badge = document.getElementById('notification-badge');

                    if (badge) {
                        if (data.count > 0) {
                            badge.textContent = data.count;
                            badge.classList.remove('hidden');
                        } else {
                            badge.classList.add('hidden');
                        }
                    }
                }
            }
        } catch (error) {
            console.error('Error fetching unread count:', error);
        }
    }

    setInterval(checkUnreadNotifications, 30000);
    checkUnreadNotifications();
});


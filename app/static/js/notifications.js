const publicVapidKey = 'BEWyGqMWafmjeAy4CHHd2iUAeTlpE7kxSh3GDa6NyMeZ3e3_363xUdx-5mw1yl9l_6bMsBi7EyhUCyNZB1NvR1c';

document.addEventListener('DOMContentLoaded', () => {
    // Check permission status and show button if needed
    const enableBtn = document.getElementById('enable-notifications-btn');

    function checkNotificationPermission() {
        if (!('Notification' in window)) {
            console.log('This browser does not support desktop notification');
            return;
        }

        if (Notification.permission === 'default') {
            // Permission not asked yet, show button
            if (enableBtn) {
                enableBtn.classList.remove('hidden');
                enableBtn.addEventListener('click', function () {
                    Notification.requestPermission().then(function (permission) {
                        if (permission === 'granted') {
                            console.log('Notification permission granted.');
                            enableBtn.classList.add('hidden');
                            registerServiceWorker();
                        }
                    });
                });
            }
        } else if (Notification.permission === 'granted') {
            // Already granted, ensure SW is registered
            if (enableBtn) enableBtn.classList.add('hidden');
            registerServiceWorker();
        } else {
            // Denied
            console.log('Notification permission denied.');
            if (enableBtn) enableBtn.classList.remove('hidden'); // Show button to let user know they can try again (though browser might block it)
        }
    }

    // Initial check
    checkNotificationPermission();

    async function registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/sw.js');
                console.log('Service Worker Registered');

                // Subscribe to push notifications
                await subscribeUser(registration);
            } catch (error) {
                console.error('Service Worker Registration Failed:', error);
            }
        }
    }

    async function subscribeUser(registration) {
        if (!('PushManager' in window)) return;

        try {
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(publicVapidKey)
            });

            console.log('User is subscribed:', subscription);

            // Send subscription to server
            await fetch('/subscribe', {
                method: 'POST',
                body: JSON.stringify(subscription),
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        } catch (err) {
            console.log('Failed to subscribe the user: ', err);
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
        try {
            const response = await fetch('/api/notifications/unread-count');
            if (response.ok) {
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
        } catch (error) {
            console.error('Error fetching unread count:', error);
        }
    }

    setInterval(checkUnreadNotifications, 30000); // Check every 30 seconds
    checkUnreadNotifications(); // Initial check
});

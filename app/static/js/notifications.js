const publicVapidKey = 'BEWyGqMWafmjeAy4CHHd2iUAeTlpE7kxSh3GDa6NyMeZ3e3_363xUdx-5mw1yl9l_6bMsBi7EyhUCyNZB1NvR1c';

async function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        try {
            const register = await navigator.serviceWorker.register('/sw.js', {
                scope: '/'
            });
            console.log('✅ Service Worker Registered successfully');
            return register;
        } catch (e) {
            console.error('❌ Service Worker Registration Failed:', e);
            return null;
        }
    } else {
        console.warn('⚠️ Service Workers are not supported in this browser');
        return null;
    }
}

async function subscribeUser() {
    if (!('serviceWorker' in navigator)) {
        console.error('❌ Service Worker not supported');
        return;
    }

    if (!('PushManager' in window)) {
        console.error('❌ Push notifications not supported');
        return;
    }

    try {
        const register = await navigator.serviceWorker.ready;
        console.log('🔄 Service Worker is ready');

        // Check if already subscribed
        const existingSubscription = await register.pushManager.getSubscription();
        if (existingSubscription) {
            console.log('✅ User already has an active subscription');
            await sendSubscriptionToBackend(existingSubscription);
            return;
        }

        console.log('🔔 Subscribing user to push notifications...');
        const subscription = await register.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicVapidKey)
        });

        console.log('✅ User subscribed successfully:', subscription);
        await sendSubscriptionToBackend(subscription);
        console.log('✅ Subscription sent to server');
    } catch (e) {
        console.error('❌ Failed to subscribe user:', e);
        if (e.name === 'NotAllowedError') {
            console.warn('⚠️ User denied notification permission');
        }
    }
}

async function sendSubscriptionToBackend(subscription) {
    try {
        const response = await fetch('/subscribe', {
            method: 'POST',
            body: JSON.stringify(subscription),
            headers: {
                'content-type': 'application/json'
            }
        });

        if (response.ok) {
            console.log('✅ Subscription saved to backend');
        } else {
            console.error('❌ Backend rejected subscription:', response.status);
        }
    } catch (e) {
        console.error('❌ Failed to send subscription to backend:', e);
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

// Polling for unread notifications
async function checkUnreadNotifications() {
    if (!document.getElementById('notification-badge')) return;

    try {
        const response = await fetch('/api/notifications/unread-count');
        if (response.ok) {
            const data = await response.json();
            updateNotificationBadge(data.count);
        }
    } catch (e) {
        console.error('Failed to check unread notifications:', e);
    }
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notification-badge');
    const bellIcon = document.querySelector('.fa-bell');

    if (count > 0) {
        if (badge) {
            badge.textContent = count;
            badge.style.display = 'flex';
            badge.classList.remove('hidden');
        } else if (bellIcon) {
            // Create badge if it doesn't exist
            const newBadge = document.createElement('span');
            newBadge.id = 'notification-badge';
            newBadge.className = 'absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center';
            newBadge.textContent = count;
            bellIcon.parentElement.appendChild(newBadge);
        }
    } else {
        if (badge) {
            badge.style.display = 'none';
            badge.classList.add('hidden');
        }
    }
}

// Initialize when page loads
console.log('🚀 Initializing Push Notifications...');

registerServiceWorker().then((registration) => {
    if (!registration) {
        console.error('❌ Could not register service worker');
        return;
    }

    // Start polling every 30 seconds
    setInterval(checkUnreadNotifications, 30000);
    checkUnreadNotifications(); // Initial check

    console.log('🔍 Checking notification permission:', Notification.permission);

    // Ask for permission if not granted
    if (Notification.permission === 'default') {
        console.log('🔔 Requesting notification permission...');
        Notification.requestPermission().then(permission => {
            console.log('📬 Permission result:', permission);
            if (permission === 'granted') {
                console.log('✅ Notification permission granted');
                subscribeUser();
            } else {
                console.warn('⚠️ Notification permission denied or dismissed');
            }
        });
    } else if (Notification.permission === 'granted') {
        console.log('✅ Notification permission already granted');
        // Always try to subscribe/sync with backend on load
        subscribeUser();
    } else {
        console.warn('⚠️ Notifications blocked by user');
    }
});

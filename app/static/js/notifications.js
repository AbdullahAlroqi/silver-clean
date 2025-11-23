const publicVapidKey = 'BEWyGqMWafmjeAy4CHHd2iUAeTlpE7kxSh3GDa6NyMeZ3e3_363xUdx-5mw1yl9l_6bMsBi7EyhUCyNZB1NvR1c';

async function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        try {
            const register = await navigator.serviceWorker.register('/static/sw.js', {
                scope: '/'
            });
            console.log('Service Worker Registered');
            return register;
        } catch (e) {
            console.error('Service Worker Failed', e);
        }
    }
}

async function subscribeUser() {
    if (!('serviceWorker' in navigator)) return;

    const register = await navigator.serviceWorker.ready;

    // Check if already subscribed
    const existingSubscription = await register.pushManager.getSubscription();
    if (existingSubscription) {
        console.log('User is already subscribed');
        await sendSubscriptionToBackend(existingSubscription);
        return;
    }

    try {
        const subscription = await register.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(publicVapidKey)
        });
        console.log('User Subscribed');
        await sendSubscriptionToBackend(subscription);
    } catch (e) {
        console.error('Failed to subscribe the user: ', e);
    }
}

async function sendSubscriptionToBackend(subscription) {
    await fetch('/subscribe', {
        method: 'POST',
        body: JSON.stringify(subscription),
        headers: {
            'content-type': 'application/json'
        }
    });
    console.log('Subscription sent to backend');
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

// Initialize
registerServiceWorker().then(() => {
    // Ask for permission if not granted
    if (Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                subscribeUser();
            }
        });
    } else if (Notification.permission === 'granted') {
        subscribeUser();
    }
});

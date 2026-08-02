const publicVapidKey = document.querySelector('meta[name="vapid-public-key"]')?.content?.trim() || '';

document.addEventListener('DOMContentLoaded', () => {
    const floatingButton = document.getElementById('enable-notifications-btn');
    const dashboardButtons = [...document.querySelectorAll('[data-enable-notifications]')];
    const dashboardCards = [...document.querySelectorAll('[data-notification-card]')];
    const statusElements = [...document.querySelectorAll('[data-notification-status]')];
    let activationRunning = false;

    function isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
            (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    function isPWA() {
        return window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
    }

    function setStatus(message, state = 'info') {
        dashboardCards.forEach(card => card.classList.remove('hidden'));
        statusElements.forEach(element => {
            element.textContent = message;
            element.classList.remove('text-gray-300', 'text-green-300', 'text-red-300', 'text-amber-300');
            element.classList.add({success: 'text-green-300', error: 'text-red-300', warning: 'text-amber-300'}[state] || 'text-gray-300');
        });
    }

    function setButtons({visible = true, disabled = false, label = 'تفعيل الإشعارات'} = {}) {
        if (floatingButton) {
            floatingButton.classList.toggle('hidden', !visible);
            floatingButton.disabled = disabled;
            const labelElement = floatingButton.querySelector('span');
            if (labelElement) labelElement.textContent = label;
        }
        dashboardButtons.forEach(button => {
            button.disabled = disabled;
            const labelElement = button.querySelector('[data-notification-label]');
            if (labelElement) labelElement.textContent = label;
        });
    }

    function supportError() {
        if (!window.isSecureContext) return 'الإشعارات تحتاج اتصال HTTPS آمن';
        if (!publicVapidKey) return 'مفتاح الإشعارات غير مضبوط على الخادم';
        if (!('serviceWorker' in navigator)) return 'المتصفح لا يدعم Service Worker';
        if (!('PushManager' in window) || !('Notification' in window)) return 'هذا المتصفح لا يدعم إشعارات Push';
        if (isIOS() && !isPWA()) return 'أضف الموقع للشاشة الرئيسية ثم افتحه من الأيقونة';
        return null;
    }

    async function activateNotifications(background = false) {
        if (activationRunning) return;
        const error = supportError();
        if (error) {
            setStatus(error, 'error');
            setButtons({visible: true, disabled: true, label: 'تعذر تفعيل الإشعارات'});
            return;
        }
        if (Notification.permission === 'denied') {
            setStatus('الإشعارات محظورة. فعّلها من إعدادات الهاتف ثم أعد فتح التطبيق.', 'error');
            setButtons({visible: true, disabled: true, label: 'الإشعارات محظورة'});
            return;
        }

        activationRunning = true;
        // Registration is deliberately silent. Do not flash a connecting card
        // while navigating or after the user presses the activation button.
        setButtons({visible: false, disabled: true});
        dashboardCards.forEach(card => card.classList.add('hidden'));
        try {
            if (Notification.permission !== 'granted') {
                const permission = await Notification.requestPermission();
                if (permission !== 'granted') throw new Error('لم يتم السماح بالإشعارات');
            }
            const registration = await navigator.serviceWorker.register('/sw.js', {scope: '/'});
            await navigator.serviceWorker.ready;
            const subscription = await ensureSubscription(registration);
            await saveSubscription(subscription);
            setStatus('الإشعارات مفعلة على هذا الهاتف', 'success');
            setButtons({visible: false, disabled: false, label: 'الإشعارات مفعلة'});
            dashboardCards.forEach(card => card.classList.add('hidden'));
        } catch (error) {
            console.error('Push activation failed:', error);
            setStatus(error.message || 'فشل ربط الهاتف بالإشعارات', 'error');
            setButtons({visible: true, disabled: false, label: 'إعادة محاولة التفعيل'});
        } finally {
            activationRunning = false;
        }
    }

    async function ensureSubscription(registration) {
        let subscription = await registration.pushManager.getSubscription();
        const expectedKey = urlBase64ToUint8Array(publicVapidKey);
        if (subscription?.options?.applicationServerKey) {
            const currentKey = new Uint8Array(subscription.options.applicationServerKey);
            const matches = currentKey.length === expectedKey.length && currentKey.every((value, index) => value === expectedKey[index]);
            if (!matches) {
                await subscription.unsubscribe();
                subscription = null;
            }
        }
        if (!subscription) {
            subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: expectedKey
            });
        }
        return subscription;
    }

    async function saveSubscription(subscription) {
        const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
        const response = await fetch('/subscribe', {
            method: 'POST',
            body: JSON.stringify(subscription),
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf}
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok || result.status === 'ignored') {
            throw new Error(result.message || `فشل حفظ اشتراك الهاتف (${response.status})`);
        }
    }

    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        return Uint8Array.from(window.atob(base64), character => character.charCodeAt(0));
    }

    async function initializeNotifications() {
        const error = supportError();
        if (error) {
            setStatus(error, 'error');
            setButtons({visible: true, disabled: true, label: 'تعذر تفعيل الإشعارات'});
            return;
        }
        if (Notification.permission === 'denied') {
            setStatus('الإشعارات محظورة من إعدادات الهاتف', 'error');
            setButtons({visible: true, disabled: true, label: 'الإشعارات محظورة'});
            return;
        }
        if (Notification.permission === 'granted') {
            // Permission alone is not enough: register and save the subscription.
            await activateNotifications(true);
        } else {
            setStatus('اضغط لتفعيل الإشعارات على هذا الهاتف', 'warning');
            setButtons({visible: true, disabled: false});
        }
    }

    if (floatingButton) floatingButton.addEventListener('click', () => activateNotifications(false));
    dashboardButtons.forEach(button => button.addEventListener('click', () => activateNotifications(false)));
    initializeNotifications();

    async function checkUnreadNotifications() {
        if (document.body.getAttribute('data-user-logged-in') !== 'true') return;
        try {
            const response = await fetch('/api/notifications/unread-count');
            if (!response.ok) return;
            const data = await response.json();
            const badge = document.getElementById('notification-badge');
            if (!badge) return;
            badge.textContent = data.count || '';
            badge.classList.toggle('hidden', !data.count);
        } catch (error) {
            console.error('Unread notification check failed:', error);
        }
    }
    checkUnreadNotifications();
    setInterval(checkUnreadNotifications, 30000);
});

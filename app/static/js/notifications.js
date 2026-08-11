const publicVapidKey = document.querySelector('meta[name="vapid-public-key"]')?.content?.trim() || '';

document.addEventListener('DOMContentLoaded', () => {
    const floatingButton = document.getElementById('enable-notifications-btn');
    const dashboardButtons = [...document.querySelectorAll('[data-enable-notifications]')];
    const dashboardCards = [...document.querySelectorAll('[data-notification-card]')];
    const statusElements = [...document.querySelectorAll('[data-notification-status]')];
    const titleElements = [...document.querySelectorAll('[data-notification-title]')];
    const iconElements = [...document.querySelectorAll('[data-notification-icon]')];
    const postBookingCard = document.querySelector('[data-post-booking-notification-card]');
    const postBookingButton = document.querySelector('[data-post-booking-enable-notifications]');
    const browserSettings = document.querySelector('[data-browser-notification-settings]');
    const browserStatus = document.querySelector('[data-browser-notification-status]');
    const browserButton = document.querySelector('[data-browser-enable-notifications]');
    let activationRunning = false;

    function isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
            (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    function isPWA() {
        return window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
    }

    function isAndroid() {
        return /Android/i.test(navigator.userAgent);
    }

    function currentPermission() {
        return 'Notification' in window ? Notification.permission : 'unsupported';
    }

    function reportDeviceStatus() {
        const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
        fetch('/api/notifications/device-status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
            body: JSON.stringify({installed: isPWA(), permission: currentPermission()}),
            keepalive: true
        }).catch(() => {});
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
            button.classList.toggle('hidden', !visible);
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
        return null;
    }

    async function activateNotifications(background = false, allowAndroidBrowser = false) {
        if (activationRunning) return;
        if (!isPWA() && !(allowAndroidBrowser && isAndroid())) {
            dashboardCards.forEach(card => card.classList.add('hidden'));
            setButtons({visible: false, disabled: true});
            return;
        }
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
            if (postBookingCard) postBookingCard.classList.add('hidden');
            if (browserStatus) browserStatus.textContent = 'الإشعارات مفعّلة على هذا الجهاز.';
            if (browserButton) browserButton.classList.add('hidden');
            reportDeviceStatus();
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
        // Notification activation belongs to the installed app only. Browsers
        // continue to show the separate installation UI, but never this card.
        if (!isPWA()) {
            dashboardCards.forEach(card => card.classList.add('hidden'));
            setButtons({visible: false, disabled: true});
        } else if (postBookingCard && currentPermission() !== 'granted') {
            postBookingCard.classList.remove('hidden');
        }

        reportDeviceStatus();

        if (browserSettings) {
            if (isPWA()) {
                browserStatus.textContent = currentPermission() === 'granted'
                    ? 'الإشعارات مفعّلة داخل التطبيق.'
                    : 'يمكنك تفعيل الإشعارات داخل التطبيق من الزر أدناه.';
                browserButton.classList.toggle('hidden', currentPermission() === 'granted');
            } else if (isAndroid()) {
                browserStatus.textContent = currentPermission() === 'granted'
                    ? 'الإشعارات مفعّلة على هذا المتصفح.'
                    : 'يمكنك تفعيل الإشعارات من هنا دون ظهور بطاقة مزعجة في بقية الصفحات.';
                browserButton.classList.toggle('hidden', currentPermission() === 'granted');
            } else {
                browserStatus.textContent = 'على iPhone: ثبّت التطبيق على الشاشة الرئيسية أولًا، ثم فعّل الإشعارات من داخله.';
                browserButton.classList.add('hidden');
            }
        }

        if (!isPWA()) return;

        if (isIOS() && !isPWA()) {
            // Safari on iPhone cannot receive Web Push until the site is added
            // to the Home Screen. Show installation guidance, not an error or
            // notification activation UI.
            titleElements.forEach(element => element.textContent = 'تثبيت التطبيق على iPhone');
            iconElements.forEach(element => {
                element.className = 'fas fa-mobile-screen-button text-white text-2xl';
            });
            setStatus('من Safari اضغط أيقونة المشاركة، ثم اختر «إضافة إلى الشاشة الرئيسية»، وبعدها افتح التطبيق من الأيقونة.', 'info');
            setButtons({visible: false, disabled: true});
            return;
        }
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
    if (postBookingButton) postBookingButton.addEventListener('click', () => activateNotifications(false));
    if (browserButton) browserButton.addEventListener('click', () => activateNotifications(false, true));
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

(function () {
    const path = window.location.pathname.replace(/\/+$/, '');
    let config = null;

    if (path === '/customer/book') {
        config = { flow: 'booking', page: 'حجز خدمة', step: 'اختيار الموقع' };
    } else if (/^\/customer\/subscription\/\d+\/book$/.test(path)) {
        config = { flow: 'subscription_wash', page: 'حجز غسلة اشتراك', step: 'اختيار الموقع' };
    } else if (/^\/customer\/subscribe\/\d+\/details$/.test(path)) {
        config = { flow: 'subscription', page: 'بيانات الاشتراك', step: 'اختيار المركبة والمنطقة' };
    } else if (path === '/customer/subscribe') {
        config = { flow: 'subscription', page: 'اختيار باقة اشتراك', step: 'اختيار الباقة' };
    } else if (/^\/customer\/polishing\/\d+\/request$/.test(path)) {
        config = { flow: 'polishing', page: 'طلب التلميع', step: 'بيانات الطلب' };
    } else if (path === '/customer/polishing') {
        config = { flow: 'polishing', page: 'اختيار باقة تلميع', step: 'اختيار الباقة' };
    } else if (path === '/customer/gift/wash') {
        config = { flow: 'gift_wash', page: 'إهداء غسلة', step: 'بيانات الهدية' };
    } else if (path === '/customer/gift/subscription') {
        config = { flow: 'gift_subscription', page: 'إهداء اشتراك', step: 'بيانات الهدية' };
    } else if (path === '/customer/gift/polishing') {
        config = { flow: 'gift_polishing', page: 'إهداء تلميع', step: 'بيانات الهدية' };
    }

    if (!config) return;

    const storageKey = 'checkout_token_' + config.flow;
    let token = localStorage.getItem(storageKey)
        || (window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : '');
    if (token) localStorage.setItem(storageKey, token);
    let timer = null;

    function collectFormData() {
        const result = {};
        document.querySelectorAll('form').forEach((form) => {
            new FormData(form).forEach((value, key) => {
                if (key === 'csrf_token' || key === 'checkout_token') return;
                if (Object.prototype.hasOwnProperty.call(result, key)) {
                    result[key] = Array.isArray(result[key])
                        ? result[key].concat(String(value))
                        : [result[key], String(value)];
                } else {
                    result[key] = String(value);
                }
            });
        });
        const totalElement = document.getElementById('review-total');
        if (totalElement) {
            const total = parseFloat(totalElement.textContent.replace(/[^\d.]/g, ''));
            if (!Number.isNaN(total)) result.estimated_total = total;
        }
        const packageMatch = path.match(/^\/customer\/(?:subscribe|polishing)\/(\d+)/);
        if (packageMatch) result.package_id = packageMatch[1];
        const subscriptionMatch = path.match(/^\/customer\/subscription\/(\d+)\/book$/);
        if (subscriptionMatch) result.subscription_id = subscriptionMatch[1];
        return result;
    }

    function ensureTokenFields() {
        document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form) => {
            let input = form.querySelector('input[name="checkout_token"]');
            if (!input) {
                input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'checkout_token';
                form.appendChild(input);
            }
            input.value = token;
        });
    }

    function sendProgress() {
        const csrf = document.querySelector('meta[name="csrf-token"]');
        fetch('/customer/api/checkout-progress', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf ? csrf.content : ''
            },
            body: JSON.stringify({
                token: token,
                flow_type: config.flow,
                page_name: config.page,
                step_name: config.step,
                form_data: collectFormData()
            }),
            keepalive: true
        })
            .then((response) => response.ok ? response.json() : null)
            .then((data) => {
                if (!data || !data.token) return;
                token = data.token;
                localStorage.setItem(storageKey, token);
                ensureTokenFields();
            })
            .catch(() => {});
    }

    function scheduleProgress() {
        window.clearTimeout(timer);
        timer = window.setTimeout(sendProgress, 600);
    }

    document.addEventListener('change', scheduleProgress);
    document.addEventListener('input', scheduleProgress);
    document.addEventListener('checkout:step', (event) => {
        if (event.detail && event.detail.step) config.step = event.detail.step;
        sendProgress();
    });
    document.addEventListener('submit', ensureTokenFields);

    ensureTokenFields();
    sendProgress();
})();

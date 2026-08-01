(function () {
    const loader = document.getElementById('site-loader');
    if (!loader) return;

    const storageKey = 'silver-clean-opening-loader-shown';
    try {
        if (window.sessionStorage.getItem(storageKey) === '1') {
            loader.remove();
            return;
        }
        window.sessionStorage.setItem(storageKey, '1');
    } catch (error) {
        // If storage is unavailable, retain the safe one-page loader behavior.
    }

    let removed = false;
    function hideLoader() {
        if (removed) return;
        removed = true;
        loader.classList.add('is-hidden');
        window.setTimeout(() => loader.remove(), 250);
    }

    if (document.readyState === 'complete') {
        hideLoader();
    } else {
        window.addEventListener('load', hideLoader, { once: true });
    }

    // Never let a failed third-party resource leave the interface covered.
    window.setTimeout(hideLoader, 5000);
})();

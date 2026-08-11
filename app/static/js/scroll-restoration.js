(function () {
    if ('scrollRestoration' in history) {
        history.scrollRestoration = 'manual';
    }

    window.addEventListener('pageshow', function () {
        document.body.classList.remove('admin-sidebar-open');

        if (!window.location.search) return;

        window.requestAnimationFrame(function () {
            const innerScroller = document.querySelector('.customer-app, .content');
            if (innerScroller) {
                innerScroller.scrollTop = 0;
            }

            const pageScroller = document.scrollingElement || document.documentElement;
            pageScroller.scrollTop = 0;
        });
    });
})();

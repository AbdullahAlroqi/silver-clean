(function () {
    function normalizeAdminCards() {
        const main = document.querySelector('.admin-main');
        if (!main) return;

        main.querySelectorAll('.bg-primary, article[class*="bg-"], section[class*="bg-"]').forEach(function (card) {
            if (card.closest('[class*="fixed"][class*="inset-0"]')) return;
            card.classList.add('admin-ui-card');

            Array.from(card.children).forEach(function (child) {
                if (child.matches('.flex.justify-between, .flex.items-center.justify-between, .flex.justify-end')) {
                    child.classList.add('admin-ui-card-row');
                }
                if (child.matches('.flex.justify-end, .flex.gap-2, .flex.gap-3')) {
                    const hasControl = child.querySelector('button, a, form');
                    if (hasControl) child.classList.add('admin-ui-card-actions');
                }
            });
        });

        Array.from(main.children).forEach(function (element) {
            if (element.matches('.flex.justify-between, .flex.items-center.justify-between')) {
                element.classList.add('admin-ui-page-header');
            }
        });
    }

    function makeTablesResponsive() {
        document.querySelectorAll('.admin-main table').forEach(function (table) {
            if (table.dataset.mobileTable === 'scroll') return;
            const headers = Array.from(table.querySelectorAll('thead th')).map(function (header) {
                return header.textContent.trim();
            });
            if (headers.length < 2) return;
            table.classList.add('admin-responsive-table');
            table.querySelectorAll('tbody tr').forEach(function (row) {
                Array.from(row.children).forEach(function (cell, index) {
                    if (cell.tagName === 'TD' && !cell.hasAttribute('colspan')) {
                        cell.dataset.label = headers[index] || '';
                    }
                });
            });
        });
    }

    function enhanceSidebarSections() {
        const headings = Array.from(document.querySelectorAll('.sidebar-section-title'));
        headings.forEach(function (heading, headingIndex) {
            const items = [];
            let element = heading.nextElementSibling;
            while (element && !element.classList.contains('sidebar-section-title')) {
                if (element.matches('a, p, div')) items.push(element);
                element = element.nextElementSibling;
            }

            const active = items.some(function (item) {
                if (!item.matches('a[href]')) return false;
                const path = new URL(item.href, window.location.origin).pathname.replace(/\/$/, '');
                const current = window.location.pathname.replace(/\/$/, '');
                return path === current;
            });
            const storageKey = 'admin-sidebar-section-' + headingIndex;
            let expanded = active || headingIndex === 0;
            try {
                const saved = window.localStorage.getItem(storageKey);
                if (saved !== null && !active) expanded = saved === '1';
            } catch (error) {}

            function render() {
                heading.setAttribute('aria-expanded', expanded ? 'true' : 'false');
                items.forEach(function (item) {
                    item.classList.toggle('sidebar-section-collapsed', !expanded);
                });
            }

            heading.setAttribute('role', 'button');
            heading.setAttribute('tabindex', '0');
            heading.addEventListener('click', function () {
                expanded = !expanded;
                try { window.localStorage.setItem(storageKey, expanded ? '1' : '0'); } catch (error) {}
                render();
            });
            heading.addEventListener('keydown', function (event) {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    heading.click();
                }
            });
            render();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            normalizeAdminCards();
            makeTablesResponsive();
            enhanceSidebarSections();
        }, {once: true});
    } else {
        normalizeAdminCards();
        makeTablesResponsive();
        enhanceSidebarSections();
    }
})();

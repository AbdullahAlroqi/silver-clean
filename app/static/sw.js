self.addEventListener('install', (event) => {
  console.log('Service Worker installing.');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('Service Worker activating.');
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});

self.addEventListener('push', function (event) {
  console.log('Push notification received:', event);

  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      console.error('Failed to parse push data:', e);
      data = { title: 'Silver Clean', body: event.data.text() };
    }
  }

  const title = data.title || 'Silver Clean';
  const options = {
    body: data.body || 'إشعار جديد',
    icon: '/static/images/logo.png',
    badge: '/static/images/logo.png',
    vibrate: [200, 100, 200],
    tag: 'silver-clean-notification',
    requireInteraction: true,
    data: {
      url: data.url || '/',
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'view',
        title: 'عرض',
        icon: '/static/images/logo.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', function (event) {
  console.log('Notification clicked:', event);
  event.notification.close();

  const urlToOpen = event.notification.data.url || '/';

  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    }).then(function (clientList) {
      // Check if there is already a window open with the target URL
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      // If not, open a new window
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

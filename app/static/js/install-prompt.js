// Install Prompt for Add to Home Screen (PWA)
let deferredPrompt;
let installButton;
let installBanner;

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    installButton = document.getElementById('install-app-btn');
    installBanner = document.getElementById('install-banner');

    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true) {
        console.log('App is already installed');
        return;
    }

    // Check if user already dismissed the banner
    const dismissed = localStorage.getItem('install-prompt-dismissed');
    if (dismissed === 'true') {
        return;
    }

    // Show install banner after a delay (better UX)
    setTimeout(() => {
        if (installBanner && !deferredPrompt) {
            installBanner.style.display = 'flex';
        }
    }, 3000); // Show after 3 seconds
});

// Capture the install prompt event
window.addEventListener('beforeinstallprompt', (e) => {
    console.log('beforeinstallprompt event fired');

    // Prevent the default browser install prompt
    e.preventDefault();

    // Store the event for later use
    deferredPrompt = e;

    // Show our custom install UI
    if (installBanner) {
        installBanner.style.display = 'flex';
    }

    if (installButton) {
        installButton.style.display = 'flex';
    }
});

// Handle install button click
function installApp() {
    if (!deferredPrompt) {
        console.log('No deferred prompt available');

        // For iOS devices (Safari doesn't support beforeinstallprompt)
        if (isIOS()) {
            showIOSInstructions();
        }
        return;
    }

    // Hide the banner
    if (installBanner) {
        installBanner.style.display = 'none';
    }

    // Show the install prompt
    deferredPrompt.prompt();

    // Wait for the user's response
    deferredPrompt.userChoice.then((choiceResult) => {
        if (choiceResult.outcome === 'accepted') {
            console.log('User accepted the install prompt');
        } else {
            console.log('User dismissed the install prompt');
        }

        // Clear the deferred prompt
        deferredPrompt = null;
    });
}

// Dismiss the install banner
function dismissInstallBanner() {
    if (installBanner) {
        installBanner.style.display = 'none';
    }

    // Save dismissal preference
    localStorage.setItem('install-prompt-dismissed', 'true');
}

// Check if device is iOS
function isIOS() {
    const userAgent = window.navigator.userAgent.toLowerCase();
    return /iphone|ipad|ipod/.test(userAgent);
}

// Show instructions for iOS users
function showIOSInstructions() {
    const modal = document.createElement('div');
    modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
    padding: 20px;
    animation: fadeIn 0.3s ease;
  `;

    const content = document.createElement('div');
    content.style.cssText = `
    background: linear-gradient(135deg, #1F1F1F 0%, #2D2D2D 100%);
    border-radius: 20px;
    padding: 30px;
    max-width: 400px;
    width: 100%;
    text-align: center;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.1);
  `;

    content.innerHTML = `
    <h2 style="color: #4DA8DA; margin-bottom: 20px; font-size: 24px; font-weight: bold;">
      <i class="fas fa-mobile-alt" style="margin-left: 10px;"></i>
      إضافة إلى الشاشة الرئيسية
    </h2>
    <p style="color: #fff; margin-bottom: 20px; line-height: 1.6; font-size: 16px;">
      لتثبيت التطبيق على جهاز iOS:
    </p>
    <ol style="color: #D8D8D8; text-align: right; margin: 0 auto 20px; max-width: 300px; line-height: 2;">
      <li>اضغط على زر المشاركة <i class="fas fa-share" style="color: #4DA8DA;"></i> في Safari</li>
      <li>اسحب للأسفل واختر "إضافة إلى الشاشة الرئيسية"</li>
      <li>اضغط "إضافة" في الزاوية العلوية</li>
    </ol>
    <button onclick="this.parentElement.parentElement.remove()" 
      style="
        background: linear-gradient(135deg, #4DA8DA 0%, #3B8AB8 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 10px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        transition: transform 0.2s;
        width: 100%;
      "
      onmouseover="this.style.transform='scale(1.05)'"
      onmouseout="this.style.transform='scale(1)'"
    >
      فهمت
    </button>
  `;

    modal.appendChild(content);
    document.body.appendChild(modal);

    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// Listen for successful app installation
window.addEventListener('appinstalled', () => {
    console.log('PWA was installed successfully');

    // Hide install UI
    if (installBanner) {
        installBanner.style.display = 'none';
    }

    if (installButton) {
        installButton.style.display = 'none';
    }

    // Show success message
    showSuccessMessage();
});

// Show success message after installation
function showSuccessMessage() {
    const message = document.createElement('div');
    message.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(135deg, #10B981 0%, #059669 100%);
    color: white;
    padding: 16px 30px;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(16, 185, 129, 0.4);
    z-index: 10000;
    font-size: 16px;
    font-weight: bold;
    animation: slideDown 0.5s ease;
  `;

    message.innerHTML = `
    <i class="fas fa-check-circle" style="margin-left: 8px;"></i>
    تم تثبيت التطبيق بنجاح!
  `;

    document.body.appendChild(message);

    // Remove after 3 seconds
    setTimeout(() => {
        message.style.animation = 'slideUp 0.5s ease';
        setTimeout(() => message.remove(), 500);
    }, 3000);
}

// CSS Animations
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  @keyframes slideDown {
    from {
      opacity: 0;
      transform: translateX(-50%) translateY(-20px);
    }
    to {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }
  
  @keyframes slideUp {
    from {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
    to {
      opacity: 0;
      transform: translateX(-50%) translateY(-20px);
    }
  }
  
  @keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
  }
`;
document.head.appendChild(style);

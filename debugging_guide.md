# دليل تشخيص وإصلاح مشكلة عدم إرسال البريد الإلكتروني (OTP) في بيئة الإنتاج

بما أن النظام يعمل محلياً ويستخدم `Flask-Mail` مع `ProtonMail` أو `Gmail` (بناءً على الإعدادات)، فإن المشكلة غالباً تتعلق إما بإعدادات السيرفر (Firewall/Ports) أو متغيرات البيئة.

## 1. التشخيص الأولي (Diagnostic Steps)

### أ. التحقق من متغيرات البيئة (Environment Variables)
في بيئة الإنتاج (Linux VPS)، متغيرات البيئة التي تضعها في ملف `.env` قد لا يتم قراءتها تلقائياً بواسطة Gunicorn أو Systemd إلا إذا تم إعدادها صراحة.

**خطوات التحقق:**
1. ادخل على السيرفر عبر SSH.
2. إذا كنت تستخدم **Systemd** لتشغيل Gunicorn، تأكد من ملف الخدمة:
   ```bash
   sudo cat /etc/systemd/system/silver_clean.service  # أو اسم الخدمة الخاص بك
   ```
   يجب أن يحتوي على خطوط `Environment` أو `EnvironmentFile=/path/to/.env`.

3. إذا كنت تعتمد على `.env` فقط، تأكد من أن الكود يقوم بتحميلها فعلياً (تأكدنا من وجود `load_dotenv()` في `config.py`، وهذا جيد).

### ب. فحص الاتصال بالمنافذ (Port Connectivity)
أغلب مزودي الخدمات السحابية (DigitalOcean, AWS, Google Cloud, Vultr) يقومون بحظر المنفذ **25** و أحياناً **587/465** بشكل افتراضي لمنع السبام.

**اختبار الاتصال من داخل السيرفر:**
```bash
# جرب الاتصال بمنفذ 587 (TLS)
telnet smtp.gmail.com 587
# أو
nc -v smtp.gmail.com 587
```
- إذا ظهر `Connected`، فالمنفذ مفتوح.
- إذا ظهر `Connection timed out`، فالمنفذ محظور من قبل الاستضافة (Hostinger/DigitalOcean) أو الفايروال (UFW).

### ج. مراجعة سجلات الخطأ (Logs)
بما أن الإرسال يتم في `Thread` منفصل (كما رأينا في `email.py`)، فإن الأخطاء قد لا تظهر في الرد المباشر للطلب (HTTP 500)، بل تظهر في سجلات التطبيق فقط.

```bash
# عرض سجلات خدمة Gunicorn
sudo journalctl -u silver_clean -n 100 --no-pager
# أو ملف الخطأ إذا تم تحديده
tail -f /var/log/gunicorn/error.log
```
ابحث عن رسائل مثل: `ConnectionRefusedError` أو `SMTPAuthenticationError`.

---

## 2. الأسباب الشائعة والحلول

### السبب 1: حظر المنافذ (Blocked SMTP Ports) - الأكثر شيوعاً 🔴
- **المشكلة:** Hostinger ومعظم الاستضافات تحظر منافذ SMTP الخارجية (25, 465, 587) افتراضياً.
- **الحل:** يجب عليك التواصل مع الدعم الفني لطلب فتح منافذ SMTP أو استخدام منفذ بديل إذا كان متاحاً (غالباً 587).
- **بديل:** استخدام خدمة API مثل SendGrid أو Mailgun بدلاً من SMTP المباشر، حيث تعمل عبر HTTP (Port 80/443) ولا تتأثر بحظر SMTP.

### السبب 2: مصادقة Google / الأمان (Less Secure Apps)
- **المشكلة:** إذا كنت تستخدم Gmail، فإن Google تمنع تسجيل الدخول بكلمة المرور العادية من سيرفرات غير معروفة.
- **الحل:**
    1. تأكد من تفعيل "2-Step Verification" في حساب Gmail.
    2. أنشئ "App Password" خاص للسيرفر:
       - Google Account -> Security -> 2-Step Verification -> App passwords.
    3. استبدل كلمة المرور في متغيرات البيئة `MAIL_PASSWORD` بكلمة مرور التطبيق (16 حرفاً).

### السبب 3: عدم تطابق متغيرات البيئة
- **المشكلة:** السيرفر يقرأ قيم افتراضية لأن ملف `.env` غير موجود أو غير مقروء.
- **الحل:** تأكد من وجود ملف `.env` في المسار الصحيح على السيرفر وأن المستخدم (مثلاً `www-data` أو `root`) يملك صلاحية قراءته.

---

## 3. إعدادات الإنتاج الموصى بها (Best Practices)

### أ. استخدم App Passwords أو API
بدلاً من كلمة مرور الإيميل الحقيقية، استخدم App Password دائماً. الأفضل استخدام خدمة بريد متخصصة (Transactional Email Service) مثل Amazon SES أو SendGrid أو Postmark لتجنب مشاكل الحظر والوصول للسبام.

### ب. إعدادات Logging للإيميل
لتشخيص المشكلة بدقة، أضف إعدادات Logging خاصة بـ Flask-Mail في `app/__init__.py` أو عند تهيئة التطبيق:

```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    if app.config['MAIL_SERVER']:
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()
        mail_handler = logging.StreamHandler()
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)
```

### ج. إعداد Firewall (UFW)
تأكد من السماح بالاتصالات الخارجية (Outgoing) إذا كنت تستخدم سياسة حظر صارمة.
```bash
sudo ufw allow out 587/tcp
```

---

## ملخص خطوات الحل المقترحة لك الآن:

1. **جرب الاتصال بـ SMTP من السيرفر** باستخدام `telnet` أو `nc`. إذا فشل، تواصل مع استضافتك لفتح المنفذ.
2. **تأكد من `App Password`**: إذا كنت تستخدم Gmail، تأكد أنك تستخدم كلمة مرور تطبيق وليس كلمتك الشخصية.
3. **راجع ملف `.env` على السيرفر**: تأكد أن `MAIL_USERNAME` و `MAIL_PASSWORD` و `MAIL_SERVER` صحيحة.
4. **شاهد السجلات (Logs)** أثناء محاولة التسجيل لتعرف رسالة الخطأ الدقيقة (`journalctl -f`).

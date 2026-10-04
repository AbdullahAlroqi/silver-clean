# خطوات النشر — إصلاحات التقارير + دعم تطبيق الأندرويد

الكوميت: `2a8544e` على `main`
السيرفر: Hostinger VPS — `https://silvc.cloud`

**لا يحتاج ترحيل قاعدة بيانات.** لم تُضف أعمدة ولا جداول، فلا `flask db upgrade`.

---

## 1. الدخول للسيرفر والنسخ الاحتياطي

```bash
ssh root@<ip-السيرفر>
cd /path/to/your/project      # عدّل للمسار الفعلي، غالباً /var/www/silver-clean
```

خذ نسخة من قاعدة البيانات قبل أي شيء:

```bash
cp instance/silver_clean.db ~/silver_clean-$(date +%F-%H%M).db
ls -la ~/silver_clean-*.db
```

واعرف اسم الخدمة إن لم تكن متأكداً:

```bash
systemctl list-units --type=service | grep -iE "silver|gunicorn|flask"
```

---

## 2. سحب التحديث

```bash
git fetch origin
git log --oneline HEAD..origin/main      # اطّلع على ما سيُسحب
git pull origin main
```

**إن اشتكى git من تعديلات محلية على السيرفر**، فلا تستخدم `reset --hard` قبل أن
ترى ما ستفقده:

```bash
git status
git diff
```

ثم إن كانت التعديلات غير مهمة:

```bash
git stash          # تبقى محفوظة ويمكن استرجاعها بـ git stash pop
git pull origin main
```

---

## 3. التحقق من وصول الملفات

```bash
ls -la app/mobile_api.py app/utils/revenue.py
grep -n "mobile_api" app/__init__.py
```

يجب أن تظهر الثلاثة. الملفات المطلوبة:

| الملف | السبب |
|---|---|
| `app/mobile_api.py` | **جديد** — مسارات تطبيق الأندرويد |
| `app/utils/revenue.py` | **جديد** — حساب الإيرادات الموحّد |
| `app/__init__.py` | تسجيل الـ blueprint |
| `app/admin/routes.py` | إصلاحات التقارير |
| `app/employee/routes.py` | إصلاح إحصائيات الموظف |
| `app/static/js/notifications.js` | إخفاء إشعارات الويب داخل التطبيق |
| `app/static/js/install-prompt.js` | إخفاء دعوة التثبيت داخل التطبيق |

---

## 4. إعادة التشغيل

```bash
sudo systemctl restart silver     # استبدل الاسم إن كان مختلفاً
sudo systemctl status silver --no-pager
```

إعادة التشغيل ضرورية: Gunicorn يحتفظ بنسخة قديمة من القوالب وملفات بايثون
في الذاكرة.

---

## 5. التحقق بعد النشر

### مسارات تطبيق الأندرويد

```bash
curl https://silvc.cloud/api/mobile/session
```

**المتوقع:** `{"authenticated":false}`
**إن رجع 404** فالكود القديم ما زال يعمل — راجع الخطوة 4.

```bash
curl "https://silvc.cloud/api/mobile/notifications?since_id=0"
```

**المتوقع:** `{"authenticated":false,"notifications":[]}`

```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"latitude":24.7,"longitude":46.6}' \
     -w " [%{http_code}]\n" \
     https://silvc.cloud/api/mobile/location
```

**المتوقع:** `{"status":"unauthenticated"} [401]`
لو رجع 400 مع رسالة CSRF فالإعفاء لم يُطبّق — تأكد أن `app/mobile_api.py` وصل.

### صفحات التقارير

سجّل دخول كأدمن وافتح، وتأكد أن كل صفحة ترجع 200 ولا 500:

- `/admin/` — الشاشة الرئيسية
- `/admin/reports`
- `/admin/management-reports`
- `/admin/locations`
- `/admin/services`
- `/admin/seasons`

وللتأكد أن إصلاح المدخلات التالفة عمل — كان يعطي 500 قبل الإصلاح:

```
/admin/reports?from_date=abc&to_date=2026-09-30
```

**المتوقع:** الصفحة تفتح طبيعياً بفترة افتراضية.

### التحقق من التوازن

في `/admin/reports` يجب أن:

- النقدي + الشبكة = إيرادات الخدمات + إيرادات المنتجات
- مجموع صفوف «أداء المدن» = الإيرادات الكلية

### سجل الأخطاء

```bash
sudo journalctl -u silver -n 60 --no-pager
```

---

## 6. التراجع إن حدث خطأ

```bash
git reset --hard c71332f
sudo systemctl restart silver
```

واستعادة قاعدة البيانات إن لزم:

```bash
cp ~/silver_clean-<الوقت>.db instance/silver_clean.db
sudo systemctl restart silver
```

---

## ملاحظات

**`SECURE_COOKIES`** — أضفت هذا المتغير في `config.py`. **لا تضفه إلى `.env` على
السيرفر.** الافتراضي `true` وهو الصحيح لأن السيرفر على https؛ وضعه `false`
يجعل كوكي الجلسة غير آمن.

**`seed_demo_reports.py`** — سكربت يضيف بيانات تجربة، وصل مع هذا الكوميت.
**لا تشغّله على السيرفر** — سيضيف حجوزات وهمية لقاعدة البيانات الحقيقية.
هو للتجربة المحلية فقط، ويُحذف بـ `--remove`.

**البيانات الوهمية المحلية** التي أضفناها موجودة في قاعدة بيانات جهازك فقط
(`instance/` مستثنى من git)، ولن تصل للسيرفر.

**تطبيق الأندرويد** غير موجود في هذا المستودع — مشروعه في
`C:\Users\abdullah\Desktop\Test\APK` على جهازك. لا يحتاج نشراً على السيرفر.

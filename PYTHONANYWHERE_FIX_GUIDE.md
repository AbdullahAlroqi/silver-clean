# خطوات إصلاح خطأ 500 على PythonAnywhere

## المشكلة المحددة
خطأ 500 Internal Server Error يحدث بسبب محاولة الوصول إلى جدول `site_settings` غير الموجود في قاعدة البيانات.

## الحل المطبق محليًا
✓ تم إضافة معالجة الأخطاء في `app/__init__.py` للدالة `inject_settings()`

## الخطوات المطلوبة على PythonAnywhere

### 1. رفع الملف المحدث
قم برفع الملف التالي إلى PythonAnywhere:
- `app/__init__.py` (تم تحديثه محليًا)

يمكنك رفعه عبر:
- **الطريقة الأولى**: استخدم واجهة الملفات (Files) في PythonAnywhere
- **الطريقة الثانية**: استخدم Git إذا كان المشروع متصل بمستودع

### 2. تطبيق ترحيلات قاعدة البيانات
افتح Bash Console في PythonAnywhere ونفذ الأوامر التالية:

```bash
# الانتقال إلى مجلد المشروع
cd ~/alasadi12380.pythonanywhere.com

# تفعيل البيئة الافتراضية
source .venv/bin/activate

# تطبيق الترحيلات
flask db upgrade
```

### 3. إعادة تشغيل التطبيق
1. اذهب إلى صفحة **Web** في لوحة تحكم PythonAnywhere
2. اضغط على زر **Reload alasadi12380.pythonanywhere.com**
3. انتظر حتى يتم إعادة التشغيل

### 4. اختبار التطبيق
افتح المتصفح واذهب إلى:
```
https://alasadi12380.pythonanywhere.com/
```

يجب أن تعمل الصفحة الرئيسية الآن بدون خطأ 500 ✓

## ملاحظات مهمة

- ✓ **الحماية من الأخطاء**: حتى إذا فشل تطبيق الترحيلات، التطبيق لن يتعطل (سيعمل بدون إعدادات الموقع فقط)
- ✓ **السجلات (Logs)**: إذا استمر الخطأ، تحقق من سجلات الأخطاء في PythonAnywhere عبر:
  - Web → Log files → Error log

## استكشاف الأخطاء

إذا استمر خطأ 500 بعد تطبيق الإصلاح:

1. **تحقق من سجل الأخطاء**:
   - اذهب إلى Web → Log files → Error log
   - ابحث عن السطر الأخير للخطأ

2. **تحقق من الترحيلات**:
   ```bash
   flask db current
   ```
   يجب أن يظهر: `add_tiktok_url (head)`

3. **تحقق من وجود الجدول**:
   ```bash
   flask shell
   >>> from app.models import SiteSettings
   >>> SiteSettings.query.first()
   ```

## اتصل بي
إذا واجهت أي مشاكل، أرسل لي:
- محتوى Error log
- ناتج `flask db current`

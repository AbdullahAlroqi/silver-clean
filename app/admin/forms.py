from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, FloatField, IntegerField, SelectField, TextAreaField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, Optional

class EmployeeForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    phone = StringField('رقم الجوال', validators=[DataRequired(), Length(min=10, max=15)])
    password = PasswordField('كلمة المرور', validators=[Optional()])
    role = SelectField('الدور', choices=[('employee', 'موظف'), ('supervisor', 'مشرف')], default='employee')
    neighborhoods = SelectMultipleField('الأحياء المسندة (للموظفين)', coerce=int)
    supervisor_cities = SelectMultipleField('المدن المسندة (للمشرفين)', coerce=int)
    supervisor_neighborhoods = SelectMultipleField('الأحياء المسندة (للمشرفين)', coerce=int)
    submit = SubmitField('حفظ')

class ServiceForm(FlaskForm):
    name_ar = StringField('الاسم (عربي)', validators=[DataRequired()])
    name_en = StringField('الاسم (إنجليزي)', validators=[DataRequired()])
    price = FloatField('السعر', validators=[DataRequired()])
    duration = IntegerField('المدة (دقيقة)', validators=[DataRequired()])
    description = TextAreaField('الوصف')
    submit = SubmitField('حفظ')

class VehicleSizeForm(FlaskForm):
    name_ar = StringField('الاسم (عربي)', validators=[DataRequired()])
    name_en = StringField('الاسم (إنجليزي)', validators=[DataRequired()])
    price_adjustment = FloatField('تعديل السعر (ريال)', validators=[DataRequired()])
    is_active = BooleanField('مفعل', default=True)
    submit = SubmitField('حفظ')

class CityForm(FlaskForm):
    name_ar = StringField('الاسم (عربي)', validators=[DataRequired()])
    name_en = StringField('الاسم (إنجليزي)', validators=[DataRequired()])
    is_active = BooleanField('مفعل')
    submit = SubmitField('حفظ')

class NeighborhoodForm(FlaskForm):
    city_id = SelectField('المدينة', coerce=int, validators=[DataRequired()])
    name_ar = StringField('الاسم (عربي)', validators=[DataRequired()])
    name_en = StringField('الاسم (إنجليزي)', validators=[DataRequired()])
    is_active = BooleanField('مفعل')
    submit = SubmitField('حفظ')

class SubscriptionPackageForm(FlaskForm):
    name_ar = StringField('الاسم بالعربية', validators=[DataRequired()])
    name_en = StringField('Name (English)', validators=[DataRequired()])
    price = StringField('السعر', validators=[DataRequired()])
    wash_count = StringField('عدد الغسلات', validators=[DataRequired()])
    duration_days = StringField('مدة الاشتراك (بالأيام)', validators=[DataRequired()])
    description = StringField('الوصف')
    is_active = BooleanField('مفعّل', default=True)
    submit = SubmitField('حفظ')

class ProductForm(FlaskForm):
    name_ar = StringField('الاسم بالعربية', validators=[DataRequired()])
    name_en = StringField('Name (English)', validators=[DataRequired()])
    price = StringField('السعر', validators=[DataRequired()])
    stock_quantity = IntegerField('الكمية المتوفرة', validators=[Optional()], default=0)
    image = FileField('صورة المنتج', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'الصور فقط!')])
    submit = SubmitField('حفظ')

class SiteSettingsForm(FlaskForm):
    site_name = StringField('Site Name', validators=[DataRequired()])
    logo = FileField('Logo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    primary_color = StringField('Primary Color')
    accent_color = StringField('Accent Color')
    whatsapp_number = StringField('WhatsApp Number')
    facebook_url = StringField('Facebook URL')
    twitter_url = StringField('Twitter URL')
    instagram_url = StringField('Instagram URL')
    tiktok_url = StringField('TikTok URL')
    terms_content = TextAreaField('Terms and Conditions')
    submit = SubmitField('Save Settings')

class NotificationForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    user_id = SelectField('Recipient', coerce=int) # 0 for All
    submit = SubmitField('Send Notification')

class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional()])
    submit = SubmitField('Save Admin')

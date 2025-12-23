from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length
from app.models import User

class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم أو رقم الجوال', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    remember_me = BooleanField('تذكرني')
    submit = SubmitField('تسجيل الدخول')

class RegistrationForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    phone = StringField('رقم الجوال', validators=[DataRequired(), Length(min=10, max=15)])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('تسجيل جديد')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('اسم المستخدم هذا مستخدم بالفعل.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('البريد الإلكتروني هذا مستخدم بالفعل.')

    def validate_phone(self, phone):
        # Convert Arabic numerals to English
        arabic_numerals = '٠١٢٣٤٥٦٧٨٩'
        english_numerals = '0123456789'
        translation_table = str.maketrans(arabic_numerals, english_numerals)
        converted_phone = phone.data.translate(translation_table).strip()
        
        # Update the field data with converted value
        phone.data = converted_phone
        
        # Check if phone already exists
        user = User.query.filter_by(phone=converted_phone).first()
        if user:
            raise ValidationError('رقم الجوال هذا مستخدم بالفعل.')

class ResetPasswordRequestForm(FlaskForm):
    identifier = StringField('البريد الإلكتروني أو رقم الجوال', validators=[DataRequired()])
    submit = SubmitField('إرسال رمز التحقق')

class ResetCodeForm(FlaskForm):
    code = StringField('رمز التحقق', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('تحقق')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('كلمة المرور الجديدة', validators=[DataRequired()])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('تغيير كلمة المرور')

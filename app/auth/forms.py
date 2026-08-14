from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length
from app.models import User
from app.utils.phone import normalize_saudi_phone

class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم أو رقم الجوال', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    remember_me = BooleanField('تذكرني')
    submit = SubmitField('تسجيل الدخول')

class RegistrationForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    phone = StringField('رقم الجوال', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired(), Length(min=8, message='كلمة المرور يجب أن تكون 8 أحرف على الأقل')])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])

    def validate_password(self, password):
        import re
        if not re.search(r"[a-z]", password.data) or not re.search(r"[A-Z]", password.data) or not re.search(r"[0-9]", password.data):
            raise ValidationError('كلمة المرور يجب أن تحتوي على أحرف صغيرة وكبيرة وأرقام.')
    
    referral_code = StringField('كود الإحالة (اختياري)')  # Optional referral code
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
        try:
            converted_phone = normalize_saudi_phone(phone.data)
        except ValueError as error:
            raise ValidationError(str(error))
        phone.data = converted_phone
        user = User.query.filter_by(phone=converted_phone).first()
        if user:
            raise ValidationError('رقم الجوال هذا مستخدم بالفعل.')
        return
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

class UpdatePhoneForm(FlaskForm):
    phone = StringField('رقم الجوال الصحيح', validators=[DataRequired()])
    submit = SubmitField('حفظ رقم الجوال')

    def validate_phone(self, phone):
        try:
            phone.data = normalize_saudi_phone(phone.data)
        except ValueError as error:
            raise ValidationError(str(error))
        owner = User.query.filter_by(phone=phone.data).first()
        from flask_login import current_user
        if owner and owner.id != current_user.id:
            raise ValidationError('رقم الجوال مرتبط بحساب آخر.')


class ResetCodeForm(FlaskForm):
    code = StringField('رمز التحقق', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('تحقق')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('كلمة المرور الجديدة', validators=[DataRequired(), Length(min=8, message='كلمة المرور يجب أن تكون 8 أحرف على الأقل')])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('تغيير كلمة المرور')

    def validate_password(self, password):
        import re
        if not re.search(r"[a-z]", password.data) or not re.search(r"[A-Z]", password.data) or not re.search(r"[0-9]", password.data):
             raise ValidationError('كلمة المرور يجب أن تحتوي على أحرف صغيرة وكبيرة وأرقام.')

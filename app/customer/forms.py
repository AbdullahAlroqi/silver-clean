from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TimeField, SubmitField, PasswordField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo
from app.models import Vehicle, Service, City, Neighborhood

class VehicleForm(FlaskForm):
    brand = SelectField('نوع السيارة', choices=[
        ('Toyota', 'تويوتا'), ('Hyundai', 'هيونداي'), ('Ford', 'فورد'), 
        ('Nissan', 'نيسان'), ('Chevrolet', 'شيفروليه'), ('Honda', 'هوندا'), 
        ('Kia', 'كيا'), ('Mazda', 'مازدا'), ('Lexus', 'لكزس'), 
        ('Mercedes', 'مرسيدس'), ('BMW', 'بي إم دبليو'), ('Audi', 'أودي'),
        ('GMC', 'جي إم سي'), ('Dodge', 'دودج'), ('Jeep', 'جيب'),
        ('Other', 'أخرى')
    ], validators=[DataRequired()])
    vehicle_size = SelectField('حجم السيارة', coerce=int, validators=[DataRequired()])
    plate_number = StringField('رقم اللوحة', validators=[DataRequired()])
    submit = SubmitField('حفظ')

class BookingForm(FlaskForm):
    vehicle_id = SelectField('السيارة', coerce=int, validators=[DataRequired()])
    service_id = SelectField('الخدمة', coerce=int, validators=[DataRequired()])
    city_id = SelectField('المدينة', coerce=lambda x: int(x) if x else None)
    neighborhood_id = SelectField('الحي', coerce=int, validators=[DataRequired()])
    date = DateField('التاريخ', validators=[DataRequired()])
    time = TimeField('الوقت', validators=[DataRequired()])
    submit = SubmitField('حجز')

class EditProfileForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    email = StringField('البريد الإلكتروني', validators=[DataRequired()])
    phone = StringField('رقم الجوال', validators=[DataRequired()])
    submit_profile = SubmitField('حفظ التغييرات')

    def validate_username(self, username):
        from flask_login import current_user
        from app.models import User
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('اسم المستخدم هذا مستخدم بالفعل.')

    def validate_email(self, email):
        from flask_login import current_user
        from app.models import User
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('البريد الإلكتروني هذا مستخدم بالفعل.')

    def validate_phone(self, phone):
        from flask_login import current_user
        from app.models import User
        # Basic phone validation/conversion logic should be here if needed
        if phone.data != current_user.phone:
            user = User.query.filter_by(phone=phone.data).first()
            if user:
                raise ValidationError('رقم الجوال هذا مستخدم بالفعل.')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('كلمة المرور الحالية', validators=[DataRequired()])
    new_password = PasswordField('كلمة المرور الجديدة', validators=[DataRequired()])
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('new_password')])
    submit_password = SubmitField('تغيير كلمة المرور')

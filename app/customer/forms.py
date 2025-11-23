from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TimeField, SubmitField
from wtforms.validators import DataRequired
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

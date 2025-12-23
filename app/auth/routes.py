from flask import render_template, redirect, url_for, flash, request
from urllib.parse import urlparse
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetCodeForm, ResetPasswordForm
from app.models import User

def convert_arabic_to_english_numerals(text):
    """Convert Arabic numerals to English numerals"""
    arabic_numerals = '٠١٢٣٤٥٦٧٨٩'
    english_numerals = '0123456789'
    translation_table = str.maketrans(arabic_numerals, english_numerals)
    return text.translate(translation_table)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role in ['admin', 'supervisor']:
            return redirect(url_for('admin.index'))
        elif current_user.role == 'employee':
            return redirect(url_for('employee.index'))
        else:
            return redirect(url_for('customer.index'))
            
    form = LoginForm()
    if form.validate_on_submit():
        # Convert Arabic numerals to English in login username (could be phone)
        username_or_phone = convert_arabic_to_english_numerals(form.username.data)
        user = User.query.filter((User.username == username_or_phone) | (User.phone == username_or_phone)).first()
        if user is None or not user.check_password(form.password.data):
            flash('اسم المستخدم أو كلمة المرور غير صحيحة')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            if user.role in ['admin', 'supervisor']:
                next_page = url_for('admin.index')
            elif user.role == 'employee':
                next_page = url_for('employee.index')
            else:
                next_page = url_for('customer.index')
        return redirect(next_page)
        
    return render_template('auth/login.html', title='تسجيل الدخول', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Convert Arabic numerals to English before processing
        phone = convert_arabic_to_english_numerals(form.phone.data.strip())
        
        # Check if phone number already exists
        existing_phone = User.query.filter_by(phone=phone).first()
        if existing_phone:
            flash('رقم الهاتف مستخدم بالفعل. الرجاء استخدام رقم هاتف آخر.', 'error')
            return render_template('auth/register.html', title='التسجيل', form=form)
        
        # Check if username already exists
        existing_username = User.query.filter_by(username=form.username.data).first()
        if existing_username:
            flash('اسم المستخدم موجود بالفعل. الرجاء اختيار اسم مستخدم آخر.', 'error')
            return render_template('auth/register.html', title='التسجيل', form=form)
        
        # Check if email already exists
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('البريد الإلكتروني مستخدم بالفعل. الرجاء استخدام بريد آخر.', 'error')
            return render_template('auth/register.html', title='التسجيل', form=form)
        
        # Create user with converted phone number
        user = User(username=form.username.data, email=form.email.data, phone=phone, role='customer')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('تم التسجيل بنجاح! يمكنك الآن تسجيل الدخول.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='التسجيل', form=form)

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        identifier = convert_arabic_to_english_numerals(form.identifier.data.strip())
        
        # Determine if input is email or phone matching
        user = User.query.filter((User.email == identifier) | (User.phone == identifier)).first()
            
        if user:
            import random
            import string
            from datetime import datetime, timedelta
            from app.auth.email import send_password_reset_email
            
            # Generate 6-digit code
            code = ''.join(random.choices(string.digits, k=6))
            user.reset_code = code
            user.reset_code_expiration = datetime.utcnow() + timedelta(minutes=15)
            db.session.commit()
            
            send_password_reset_email(user, code)
            
            # Mask email for display
            if '@' in user.email:
                local, domain = user.email.split('@')
                if len(local) > 2:
                    masked_local = local[:2] + '*' * (len(local) - 2)
                else:
                    masked_local = local
                masked_email = f"{masked_local}@{domain}"
            else:
                masked_email = user.email
            
            # Store email in session to verify later
            from flask import session
            session['reset_email'] = user.email
            session['masked_email'] = masked_email
            
            flash(f'تم إرسال رمز التحقق إلى: {masked_email}')
            return redirect(url_for('auth.verify_code'))
        else:
            flash('البيانات المدخلة غير مسجلة لدينا.', 'error')
    return render_template('auth/reset_request.html', title='استعادة كلمة المرور', form=form)

@bp.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    from flask import session
    email = session.get('reset_email')
    masked_email = session.get('masked_email', email)
    
    if not email:
        return redirect(url_for('auth.reset_password_request'))
        
    form = ResetCodeForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        from datetime import datetime
        if user and user.reset_code == form.code.data and user.reset_code_expiration > datetime.utcnow():
            session['reset_verified'] = True
            return redirect(url_for('auth.reset_password'))
        else:
            flash('رمز التحقق غير صحيح أو منتهي الصلاحية.', 'error')
            
    return render_template('auth/verify_code.html', title='التحقق من الرمز', form=form, masked_email=masked_email)

@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    from flask import session
    if not session.get('reset_verified'):
        return redirect(url_for('auth.reset_password_request'))
        
    email = session.get('reset_email')
    if not email:
        return redirect(url_for('auth.reset_password_request'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(form.password.data)
            user.reset_code = None
            user.reset_code_expiration = None
            db.session.commit()
            
            # Clear session
            session.pop('reset_email', None)
            session.pop('reset_verified', None)
            
            flash('تم تغيير كلمة المرور بنجاح.')
            return redirect(url_for('auth.login'))
            
    return render_template('auth/reset_password.html', title='تغيير كلمة المرور', form=form)

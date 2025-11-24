from flask import render_template, redirect, url_for, flash, request
from urllib.parse import urlparse
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User

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
        user = User.query.filter((User.username == form.username.data) | (User.phone == form.username.data)).first()
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
        # Check if phone number already exists
        existing_phone = User.query.filter_by(phone=form.phone.data).first()
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
        
        user = User(username=form.username.data, email=form.email.data, phone=form.phone.data, role='customer')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('تم التسجيل بنجاح! يمكنك الآن تسجيل الدخول.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='التسجيل', form=form)

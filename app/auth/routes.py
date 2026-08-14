from flask import render_template, redirect, url_for, flash, request
from urllib.parse import urlparse
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetCodeForm, ResetPasswordForm, UpdatePhoneForm
from app.models import User
from app.limiter import limiter
from app.utils.phone import normalize_phone_identifier, normalize_saudi_phone

def maintenance_mode_enabled():
    from app.models import SiteSettings
    return bool(getattr(SiteSettings.get_settings(), 'maintenance_mode', False))

def get_post_login_redirect(user):
    if maintenance_mode_enabled() and user.role in ['admin', 'supervisor', 'site_supervisor']:
        return url_for('admin.settings')
    if user.role in ['admin', 'supervisor', 'site_supervisor']:
        return url_for('admin.index')
    if user.role == 'employee':
        return url_for('employee.index')
    return url_for('customer.index')

def convert_arabic_to_english_numerals(text):
    """Convert Arabic numerals to English numerals"""
    arabic_numerals = '٠١٢٣٤٥٦٧٨٩'
    english_numerals = '0123456789'
    translation_table = str.maketrans(arabic_numerals, english_numerals)
    return text.translate(translation_table)

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(get_post_login_redirect(current_user))
            
    form = LoginForm()
    if form.validate_on_submit():
        # Convert Arabic numerals to English in login username (could be phone)
        username_or_phone = normalize_phone_identifier(form.username.data)
        user = User.query.filter((User.username == username_or_phone) | (User.phone == username_or_phone)).first()
        if user is None or not user.check_password(form.password.data):
            flash('اسم المستخدم أو كلمة المرور غير صحيحة')
            return redirect(url_for('auth.login'))
        
        # Check if user is banned
        if user.is_banned:
            flash('تم حظر حسابك بشكل نهائي. للتواصل مع الإدارة يرجى الاتصال بالدعم.', 'error')
            return redirect(url_for('auth.login'))
        
        # Always remember user for 1 year (especially important for PWA)
        login_user(user, remember=True)
        if user.phone_needs_update:
            return redirect(url_for('auth.update_phone'))
        
        next_page = request.args.get('next')
        if maintenance_mode_enabled() and user.role in ['admin', 'supervisor', 'site_supervisor']:
            next_page = url_for('admin.settings')
        elif not next_page or urlparse(next_page).netloc != '':
            next_page = get_post_login_redirect(user)
        return redirect(next_page)
        
    return render_template('auth/login.html', title='تسجيل الدخول', form=form)

@bp.route('/update-phone', methods=['GET', 'POST'])
def update_phone():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    if not current_user.phone_needs_update:
        return redirect(get_post_login_redirect(current_user))
    form = UpdatePhoneForm()
    if form.validate_on_submit():
        current_user.phone = form.phone.data
        current_user.phone_needs_update = False
        current_user.original_phone = None
        db.session.commit()
        flash('تم تحديث رقم الجوال بنجاح.', 'success')
        return redirect(get_post_login_redirect(current_user))
    return render_template('auth/update_phone.html', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    
    # Pre-fill referral code from URL parameter ?ref=SILVC****
    if request.method == 'GET' and request.args.get('ref'):
        form.referral_code.data = request.args.get('ref')
    
    if form.validate_on_submit():
        # Convert Arabic numerals to English before processing
        phone = normalize_saudi_phone(form.phone.data)
        
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
        
        # Check if phone or email is banned
        banned_user = User.query.filter(
            User.is_banned == True,
            db.or_(User.phone == phone, User.email == form.email.data)
        ).first()
        if banned_user:
            flash('لا يمكن التسجيل بهذا الرقم أو البريد الإلكتروني. تم حظر الحساب المرتبط بهذه البيانات.', 'error')
            return render_template('auth/register.html', title='التسجيل', form=form)
        
        # Create user with converted phone number and auto-generated referral code
        user = User(
            username=form.username.data, 
            email=form.email.data, 
            phone=phone, 
            role='customer',
            referral_code=User.generate_referral_code()
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # Get user.id before commit
        
        # Process referral code if provided
        referral_input = form.referral_code.data.strip().upper() if form.referral_code.data else ''
        if referral_input:
            from app.models import ReferralRecord, DiscountCode
            
            # First check if it's an influencer code (which is a DiscountCode with is_influencer=True)
            influencer = DiscountCode.query.filter_by(code=referral_input, is_influencer=True, is_active=True).first()
            if influencer:
                influencer.used_count += 1
                user.referred_by = None  # Influencer codes don't link to a referring user
                user.used_influencer_code_id = influencer.id  # Track for 1st wash loyalty point
            else:
                # Check if it's a valid user referral code
                referrer = User.query.filter_by(referral_code=referral_input).first()
                if referrer and referrer.id != user.id:
                    user.referred_by = referrer.id
                    # Create referral record
                    name_prefix = form.username.data[:3].upper() if form.username.data else '???'
                    record = ReferralRecord(
                        referrer_id=referrer.id,
                        referred_user_id=user.id,
                        name_prefix=name_prefix
                    )
                    db.session.add(record)
        
        db.session.commit()
        flash('تم التسجيل بنجاح! يمكنك الآن تسجيل الدخول.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='التسجيل', form=form)

@bp.route('/reset_password_request', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        identifier = normalize_phone_identifier(form.identifier.data)
        
        # Determine if input is email or phone matching
        user = User.query.filter((User.email == identifier) | (User.phone == identifier)).first()
            
        if user:
            import secrets
            import string
            from datetime import datetime, timedelta
            from app.auth.email import send_password_reset_email
            
            # Generate 6-digit code securely
            code = ''.join(secrets.choice(string.digits) for _ in range(6))
            user.reset_code = code
            user.reset_code_expiration = datetime.utcnow() + timedelta(minutes=15)
            db.session.commit()
            
            if not send_password_reset_email(user, code):
                user.reset_code = None
                user.reset_code_expiration = None
                db.session.commit()
                flash('تعذر إرسال رمز الاستعادة حاليًا. تحقق من البريد ثم حاول مرة أخرى.', 'error')
                return render_template('auth/reset_request.html', title='استعادة كلمة المرور', form=form), 503
            
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

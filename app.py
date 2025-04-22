#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixltpro - نظام بلاغات الدعم الفني - تطبيق Flask مع SQLite
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect  # إضافة حماية CSRF
from flask_wtf import FlaskForm  # استيراد FlaskForm
from wtforms import StringField, PasswordField, BooleanField, validators  # استيراد حقول النموذج
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os

# إنشاء تطبيق Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'مفتاح_سري_للغاية')

# إعداد اتصال SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'fixltpro.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# إنشاء حماية CSRF
csrf = CSRFProtect(app)

# إنشاء قاعدة البيانات
db = SQLAlchemy(app)

# تعريف نماذج قاعدة البيانات
class User(db.Model):
    """نموذج المستخدم"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # admin, employee, maintenance
    email = db.Column(db.String(100))  # إضافة حقل البريد الإلكتروني
    phone = db.Column(db.String(20))  # إضافة حقل رقم الهاتف
    
    tickets_created = db.relationship('Ticket', backref='creator', lazy='dynamic', 
                                     foreign_keys='Ticket.created_by_id')
    tickets_assigned = db.relationship('Ticket', backref='assignee', lazy='dynamic',
                                      foreign_keys='Ticket.assigned_to_id')
    
    @property
    def password(self):
        raise AttributeError('كلمة المرور غير قابلة للقراءة')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)


class TicketPriority(db.Model):
    """نموذج أولوية البلاغ"""
    __tablename__ = 'priorities'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    response_time = db.Column(db.Integer)  # وقت الاستجابة بالساعات
    color = db.Column(db.String(7))  # لون HTML مثل #FF0000
    
    tickets = db.relationship('Ticket', backref='priority', lazy='dynamic')


class TicketStatus(db.Model):
    """نموذج حالة البلاغ"""
    __tablename__ = 'statuses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    
    tickets = db.relationship('Ticket', backref='status', lazy='dynamic')


class Category(db.Model):
    """نموذج تصنيف البلاغ"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    tickets = db.relationship('Ticket', backref='category', lazy='dynamic')


class Ticket(db.Model):
    """نموذج البلاغ"""
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    priority_id = db.Column(db.Integer, db.ForeignKey('priorities.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('statuses.id'), nullable=False)
    
    comments = db.relationship('Comment', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')
    
    def is_overdue(self):
        """التحقق مما إذا كان البلاغ متأخراً"""
        if not self.due_date:
            return False
        return datetime.utcnow() > self.due_date


class Comment(db.Model):
    """نموذج التعليقات على البلاغات"""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    user = db.relationship('User', backref='comments')


# تعريف نموذج تسجيل الدخول
class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[validators.DataRequired()])
    password = PasswordField('كلمة المرور', validators=[validators.DataRequired()])
    remember = BooleanField('تذكرني')


# مزخرفات للتحقق من تسجيل الدخول والصلاحيات
def login_required(user_type=None):
    """التحقق من تسجيل الدخول والصلاحيات"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                flash('يرجى تسجيل الدخول أولاً', 'error')
                return redirect(url_for('login'))
            
            user = User.query.get(session['user_id'])
            if not user:
                session.pop('user_id', None)
                flash('يرجى تسجيل الدخول مرة أخرى', 'error')
                return redirect(url_for('login'))
            
            if user_type and user.user_type != user_type and user.user_type != 'admin':
                flash('ليس لديك صلاحية للوصول إلى هذه الصفحة', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return wrapped
    return decorator


def calculate_due_date(priority_id):
    """حساب الموعد النهائي بناءً على الأولوية"""
    priority = TicketPriority.query.get(priority_id)
    if not priority:
        return None
    
    return datetime.utcnow() + timedelta(hours=priority.response_time)


def get_current_user():
    """الحصول على المستخدم الحالي"""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


# مسارات التطبيق
@app.route('/')
def index():
    """الصفحة الرئيسية"""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user.user_type == 'maintenance':
            return redirect(url_for('maintenance_dashboard'))
        else:
            return redirect(url_for('create_ticket'))
    
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول"""
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember.data
        
        user = User.query.filter_by(username=username).first()
        if user and user.verify_password(password):
            session['user_id'] = user.id
            
            # إذا اختار المستخدم "تذكرني"، نضبط مدة الجلسة
            if remember:
                # تعيين مدة انتهاء الجلسة (30 يوم)
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)
            
            flash(f'مرحباً بك {user.name}!', 'success')
            return redirect(url_for('index'))
        
        flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')
    
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    """تسجيل الخروج"""
    session.pop('user_id', None)
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required()
def profile():
    """صفحة الملف الشخصي للمستخدم"""
    user = get_current_user()
    
    if request.method == 'POST':
        # تحديث بيانات المستخدم
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # تحقق من كلمة المرور الحالية إذا كان المستخدم يريد تغييرها
        if current_password:
            if not user.verify_password(current_password):
                flash('كلمة المرور الحالية غير صحيحة', 'danger')
                return redirect(url_for('profile'))
            
            if new_password != confirm_password:
                flash('كلمات المرور غير متطابقة', 'danger')
                return redirect(url_for('profile'))
            
            user.password = new_password
            flash('تم تغيير كلمة المرور بنجاح', 'success')
        
        # تحديث البيانات الأخرى
        user.name = name
        user.email = email
        user.phone = phone
        
        db.session.commit()
        flash('تم تحديث الملف الشخصي بنجاح', 'success')
        return redirect(url_for('profile'))
    
    # إحصائيات للعرض في الملف الشخصي
    stats = {}
    if user.user_type == 'employee':
        stats = {
            'created_tickets': user.tickets_created.count(),
            'active_tickets': user.tickets_created.join(TicketStatus).filter(TicketStatus.name != 'مغلق').count(),
            'resolved_tickets': user.tickets_created.join(TicketStatus).filter(TicketStatus.name == 'مكتمل').count()
        }
    elif user.user_type == 'maintenance':
        stats = {
            'assigned_tickets': user.tickets_assigned.count(),
            'active_tickets': user.tickets_assigned.join(TicketStatus).filter(TicketStatus.name != 'مغلق').count(),
            'resolved_tickets': user.tickets_assigned.join(TicketStatus).filter(TicketStatus.name == 'مكتمل').count(),
            'overdue_tickets': sum(1 for ticket in user.tickets_assigned if ticket.is_overdue())
        }
    elif user.user_type == 'admin':
        stats = {
            'total_tickets': Ticket.query.count(),
            'active_tickets': Ticket.query.join(TicketStatus).filter(TicketStatus.name != 'مغلق').count(),
            'users_count': User.query.count(),
            'categories_count': Category.query.count()
        }
    
    return render_template('profile.html', user=user, stats=stats)


@app.route('/reset_password_request')
def reset_password_request():
    """صفحة طلب إعادة تعيين كلمة المرور"""
    flash('وظيفة استعادة كلمة المرور غير متاحة حالياً', 'info')
    return redirect(url_for('login'))


# تحديث التطبيق لتفعيل الجلسات الدائمة
@app.before_request
def make_session_permanent():
    if session.get('user_id') and not session.get('permanent', False):
        session.permanent = True
        app.permanent_session_lifetime = timedelta(days=1)  # الافتراضي يوم واحد


@app.route('/admin/assign/<int:ticket_id>', methods=['POST'])
@login_required('admin')
def assign_ticket(ticket_id):
    """تعيين بلاغ لفني صيانة"""
    ticket = Ticket.query.get_or_404(ticket_id)
    maintenance_id = request.form.get('maintenance_id', type=int)
    
    if not maintenance_id:
        flash('يرجى اختيار فني صيانة', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    maintenance_user = User.query.filter_by(id=maintenance_id, user_type='maintenance').first()
    if not maintenance_user:
        flash('فني الصيانة غير موجود', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    # تعيين البلاغ للفني
    ticket.assigned_to_id = maintenance_id
    
    # تغيير حالة البلاغ إلى قيد المعالجة
    in_progress_status = TicketStatus.query.filter_by(name='قيد المعالجة').first()
    if in_progress_status:
        ticket.status_id = in_progress_status.id
    
    db.session.commit()
    
    flash('تم تعيين البلاغ بنجاح', 'success')
    return redirect(url_for('view_ticket', ticket_id=ticket_id))


@app.route('/ticket/create', methods=['GET', 'POST'])
@login_required('employee')
def create_ticket():
    """صفحة إنشاء بلاغ جديد للموظف"""
    categories = Category.query.all()
    priorities = TicketPriority.query.all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category_id = request.form.get('category_id', type=int)
        priority_id = request.form.get('priority_id', type=int)
        
        if not all([title, description, category_id, priority_id]):
            flash('يرجى ملء جميع الحقول', 'error')
            return render_template('create_ticket.html', categories=categories, priorities=priorities)
        
        # الحصول على حالة "جديد"
        new_status = TicketStatus.query.filter_by(name='جديد').first()
        if not new_status:
            flash('خطأ في النظام: حالة "جديد" غير موجودة', 'error')
            return render_template('create_ticket.html', categories=categories, priorities=priorities)
        
        # إنشاء البلاغ الجديد
        ticket = Ticket(
            title=title,
            description=description,
            created_by_id=session['user_id'],
            category_id=category_id,
            priority_id=priority_id,
            status_id=new_status.id,
            due_date=calculate_due_date(priority_id)
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        flash('تم إنشاء البلاغ بنجاح', 'success')
        return redirect(url_for('view_ticket', ticket_id=ticket.id))
    
    return render_template('create_ticket.html', categories=categories, priorities=priorities)


@app.route('/ticket/<int:ticket_id>')
@login_required()
def view_ticket(ticket_id):
    """عرض تفاصيل البلاغ"""
    ticket = Ticket.query.get_or_404(ticket_id)
    current_user = get_current_user()
    
    # التحقق من الصلاحيات - يمكن للمدير ولفني الصيانة المسؤول وللموظف صاحب البلاغ عرضه
    if (current_user.user_type != 'admin' and
        current_user.id != ticket.created_by_id and
        (current_user.user_type != 'maintenance' or current_user.id != ticket.assigned_to_id)):
        flash('ليس لديك صلاحية لعرض هذا البلاغ', 'error')
        return redirect(url_for('index'))
    
    # الحصول على التعليقات
    comments = ticket.comments.order_by(Comment.created_at).all()
    
    # الحصول على فنيي الصيانة للتعيين (للمدير فقط)
    maintenance_staff = []
    if current_user.user_type == 'admin':
        maintenance_staff = User.query.filter_by(user_type='maintenance').all()
    
    # الحصول على الحالات المتاحة لتحديث الحالة
    statuses = TicketStatus.query.all()
    
    return render_template(
        'view_ticket.html',
        ticket=ticket,
        comments=comments,
        maintenance_staff=maintenance_staff,
        statuses=statuses
    )


@app.route('/ticket/<int:ticket_id>/comment', methods=['POST'])
@login_required()
def add_comment(ticket_id):
    """إضافة تعليق على بلاغ"""
    ticket = Ticket.query.get_or_404(ticket_id)
    content = request.form.get('content')
    
    if not content:
        flash('يرجى كتابة تعليق', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    comment = Comment(
        content=content,
        ticket_id=ticket_id,
        user_id=session['user_id']
    )
    
    db.session.add(comment)
    db.session.commit()
    
    flash('تم إضافة التعليق بنجاح', 'success')
    return redirect(url_for('view_ticket', ticket_id=ticket_id))


@app.route('/ticket/<int:ticket_id>/status', methods=['POST'])
@login_required()
def change_status(ticket_id):
    """تغيير حالة البلاغ"""
    ticket = Ticket.query.get_or_404(ticket_id)
    current_user = get_current_user()
    
    # التحقق من الصلاحيات - يمكن للمدير ولفني الصيانة المسؤول تغيير الحالة
    if (current_user.user_type != 'admin' and
        (current_user.user_type != 'maintenance' or current_user.id != ticket.assigned_to_id)):
        flash('ليس لديك صلاحية لتغيير حالة هذا البلاغ', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    status_id = request.form.get('status_id', type=int)
    if not status_id:
        flash('يرجى اختيار حالة', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    # تحديث حالة البلاغ
    ticket.status_id = status_id
    db.session.commit()
    
    flash('تم تغيير حالة البلاغ بنجاح', 'success')
    return redirect(url_for('view_ticket', ticket_id=ticket_id))


@app.route('/maintenance/dashboard')
@login_required('maintenance')
def maintenance_dashboard():
    """لوحة تحكم فني الصيانة لعرض البلاغات المسندة إليه"""
    current_user = get_current_user()
    
    # البلاغات المسندة
    assigned_tickets = Ticket.query.filter_by(assigned_to_id=current_user.id).all()
    
    # تصنيف البلاغات حسب الحالة
    new_tickets = []
    in_progress_tickets = []
    completed_tickets = []
    
    for ticket in assigned_tickets:
        if ticket.status.name == 'جديد':
            new_tickets.append(ticket)
        elif ticket.status.name == 'قيد المعالجة':
            in_progress_tickets.append(ticket)
        elif ticket.status.name == 'مكتمل':
            completed_tickets.append(ticket)
    
    return render_template(
        'maintenance_dashboard.html',
        new_tickets=new_tickets,
        in_progress_tickets=in_progress_tickets,
        completed_tickets=completed_tickets,
        total_assigned=len(assigned_tickets)
    )


@app.route('/setup')
def setup_database():
    """إعداد قاعدة البيانات وإنشاء البيانات الأولية"""
    # إنشاء الجداول
    db.create_all()
    
    # التحقق مما إذا كانت البيانات موجودة بالفعل
    if User.query.count() > 0:
        flash('تم إعداد قاعدة البيانات مسبقاً', 'info')
        return redirect(url_for('index'))
    
    # إنشاء المستخدمين
    admin = User(username='admin', name='مدير النظام', user_type='admin', email='admin@fixltpro.com', phone='0500000000')
    admin.password = 'admin123'
    
    employee1 = User(username='employee1', name='موظف الاستقبال', user_type='employee', email='employee@fixltpro.com', phone='0500000001')
    employee1.password = 'emp123'
    
    maintenance1 = User(username='maintenance1', name='فني الصيانة 1', user_type='maintenance', email='maint1@fixltpro.com', phone='0500000002')
    maintenance1.password = 'mtn123'
    
    maintenance2 = User(username='maintenance2', name='فني الصيانة 2', user_type='maintenance', email='maint2@fixltpro.com', phone='0500000003')
    maintenance2.password = 'mtn123'
    
    db.session.add_all([admin, employee1, maintenance1, maintenance2])
    
    # إنشاء الأولويات
    high_priority = TicketPriority(name='عالية', response_time=24, color='#FF0000')
    medium_priority = TicketPriority(name='متوسطة', response_time=72, color='#FFAA00')
    low_priority = TicketPriority(name='منخفضة', response_time=120, color='#00AA00')
    
    db.session.add_all([high_priority, medium_priority, low_priority])
    
    # إنشاء الحالات
    new_status = TicketStatus(name='جديد')
    in_progress = TicketStatus(name='قيد المعالجة')
    completed = TicketStatus(name='مكتمل')
    closed = TicketStatus(name='مغلق')
    
    db.session.add_all([new_status, in_progress, completed, closed])
    
    # إنشاء التصنيفات
    hardware = Category(name='أجهزة الحاسب')
    network = Category(name='شبكات')
    software = Category(name='برمجيات')
    other = Category(name='أخرى')
    
    db.session.add_all([hardware, network, software, other])
    
    # حفظ التغييرات
    db.session.commit()
    
    # إنشاء بعض البلاغات التجريبية
    ticket1 = Ticket(
        title='جهاز لا يعمل',
        description='جهاز الحاسب في قسم المحاسبة لا يعمل بشكل صحيح',
        created_by_id=employee1.id,
        category_id=hardware.id,
        priority_id=high_priority.id,
        status_id=new_status.id,
        due_date=datetime.utcnow() + timedelta(hours=24)
    )
    
    ticket2 = Ticket(
        title='انقطاع في الشبكة',
        description='شبكة الإنترنت غير متوفرة في الطابق الثاني',
        created_by_id=employee1.id,
        category_id=network.id,
        priority_id=medium_priority.id,
        status_id=new_status.id,
        due_date=datetime.utcnow() + timedelta(hours=72)
    )
    
    db.session.add_all([ticket1, ticket2])
    db.session.commit()
    
    flash('تم إعداد قاعدة البيانات بنجاح', 'success')
    return redirect(url_for('index'))


# إضافة دالة لتوفير المستخدم الحالي في قوالب الصفحات
@app.context_processor
def inject_user():
    return dict(get_current_user=get_current_user)


# إضافة دالة لتوفير متغير now في قوالب الصفحات
@app.context_processor
def inject_now():
    return dict(now=datetime.now())


# إضافة مسارات إدارة المستخدمين
@app.route('/admin/users')
@login_required('admin')
def admin_users():
    """صفحة إدارة المستخدمين للمدير"""
    users = User.query.all()
    return render_template('admin_users.html', users=users, current_user=get_current_user())


@app.route('/admin/users/add', methods=['POST'])
@login_required('admin')
def admin_add_user():
    """إضافة مستخدم جديد"""
    username = request.form.get('username')
    name = request.form.get('name')
    password = request.form.get('password')
    user_type = request.form.get('user_type')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')
    
    # التحقق من عدم وجود اسم مستخدم مكرر
    if User.query.filter_by(username=username).first():
        flash('اسم المستخدم موجود بالفعل', 'error')
        return redirect(url_for('admin_users'))
    
    # إنشاء مستخدم جديد
    user = User(username=username, name=name, user_type=user_type, email=email, phone=phone)
    user.password = password
    
    db.session.add(user)
    db.session.commit()
    
    flash('تم إضافة المستخدم بنجاح', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/edit', methods=['POST'])
@login_required('admin')
def admin_edit_user():
    """تعديل بيانات مستخدم"""
    user_id = request.form.get('user_id', type=int)
    username = request.form.get('username')
    name = request.form.get('name')
    password = request.form.get('password')
    user_type = request.form.get('user_type')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')
    
    user = User.query.get_or_404(user_id)
    
    # التحقق من عدم وجود اسم مستخدم مكرر
    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != user_id:
        flash('اسم المستخدم موجود بالفعل', 'error')
        return redirect(url_for('admin_users'))
    
    # تحديث بيانات المستخدم
    user.username = username
    user.name = name
    user.user_type = user_type
    user.email = email
    user.phone = phone
    
    # تحديث كلمة المرور إذا تم إدخالها
    if password:
        user.password = password
    
    db.session.commit()
    
    flash('تم تحديث بيانات المستخدم بنجاح', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/delete', methods=['POST'])
@login_required('admin')
def admin_delete_user():
    """حذف مستخدم"""
    user_id = request.form.get('user_id', type=int)
    current_user = get_current_user()
    
    # لا يمكن للمستخدم حذف نفسه
    if current_user.id == user_id:
        flash('لا يمكنك حذف حسابك الخاص', 'error')
        return redirect(url_for('admin_users'))
    
    user = User.query.get_or_404(user_id)
    
    # حذف المستخدم
    db.session.delete(user)
    db.session.commit()
    
    flash('تم حذف المستخدم بنجاح', 'success')
    return redirect(url_for('admin_users'))


# تحديث مسار admin_dashboard ليدعم مرشح التصنيف
@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    """لوحة تحكم الإدارة لعرض جميع البلاغات وتوزيعها حسب الأهمية"""
    priority_filter = request.args.get('priority', type=int)
    status_filter = request.args.get('status', type=int)
    category_filter = request.args.get('category', type=int)
    
    tickets_query = Ticket.query
    
    if priority_filter:
        tickets_query = tickets_query.filter_by(priority_id=priority_filter)
    
    if status_filter:
        tickets_query = tickets_query.filter_by(status_id=status_filter)
        
    if category_filter:
        tickets_query = tickets_query.filter_by(category_id=category_filter)
    
    tickets = tickets_query.order_by(Ticket.created_at.desc()).all()
    
    # إحصائيات البلاغات
    total_tickets = Ticket.query.count()
    open_tickets = Ticket.query.join(TicketStatus).filter(TicketStatus.name != 'مغلق').count()
    high_priority = Ticket.query.filter_by(priority_id=1).count()  # نفترض أن الأولوية العالية هي 1
    completed_tickets = Ticket.query.join(TicketStatus).filter(TicketStatus.name == 'مكتمل').count()
    
    # الحصول على قوائم التصفية
    priorities = TicketPriority.query.all()
    statuses = TicketStatus.query.all()
    categories = Category.query.all()
    
    # تجميع ألوان الأولويات
    priority_colors = {}
    for priority in priorities:
        if priority.name == 'عالية':
            priority_colors['high'] = priority.color or '#e74a3b'
        elif priority.name == 'متوسطة':
            priority_colors['medium'] = priority.color or '#f6c23e'
        elif priority.name == 'منخفضة':
            priority_colors['low'] = priority.color or '#1cc88a'
    
    return render_template(
        'admin_dashboard.html',
        tickets=tickets,
        priorities=priorities,
        statuses=statuses,
        categories=categories,
        current_priority=priority_filter,
        current_status=status_filter,
        current_category=category_filter,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        high_priority=high_priority,
        completed_tickets=completed_tickets,
        priority_colors=priority_colors
    )


@app.route('/admin/tickets/edit', methods=['POST'])
@login_required('admin')
def admin_edit_ticket():
    """تعديل بيانات البلاغ"""
    ticket_id = request.form.get('ticket_id', type=int)
    title = request.form.get('title')
    description = request.form.get('description')
    category_id = request.form.get('category_id', type=int)
    priority_id = request.form.get('priority_id', type=int)
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # تحديث بيانات البلاغ
    ticket.title = title
    ticket.description = description
    ticket.category_id = category_id
    
    # إذا تغيرت الأولوية، نعيد حساب الموعد النهائي
    if ticket.priority_id != priority_id:
        ticket.priority_id = priority_id
        ticket.due_date = calculate_due_date(priority_id)
    
    db.session.commit()
    
    # إضافة تعليق تلقائي عن التعديل
    comment = Comment(
        content=f'تم تعديل بيانات البلاغ بواسطة {get_current_user().name}',
        ticket_id=ticket_id,
        user_id=session['user_id']
    )
    db.session.add(comment)
    db.session.commit()
    
    flash('تم تحديث البلاغ بنجاح', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/tickets/delete', methods=['POST'])
@login_required('admin')
def admin_delete_ticket():
    """حذف البلاغ"""
    ticket_id = request.form.get('ticket_id', type=int)
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # حذف البلاغ (سيحذف جميع التعليقات تلقائيًا بسبب cascade)
    db.session.delete(ticket)
    db.session.commit()
    
    flash('تم حذف البلاغ بنجاح', 'success')
    return redirect(url_for('admin_dashboard'))


#-------------------------
# مسارات إدارة التصنيفات
#-------------------------
@app.route('/admin/categories')
@login_required('admin')
def admin_categories():
    """صفحة إدارة التصنيفات"""
    categories = Category.query.all()
    
    # تحضير بيانات التصنيفات بتنسيق JSON لاستخدامها في JavaScript
    categories_json = []
    for category in categories:
        categories_json.append({
            'id': category.id,
            'name': category.name,
            'tickets_count': category.tickets.count()
        })
    
    # تحويل البيانات إلى سلسلة JSON
    import json
    categories_json_str = json.dumps(categories_json)
    
    return render_template('admin_categories.html', 
                          categories=categories,
                          categories_json=categories_json_str)

@app.route('/admin/categories/add', methods=['POST'])
@login_required('admin')
def admin_add_category():
    """إضافة تصنيف جديد"""
    name = request.form.get('name')
    
    # التحقق من عدم وجود تصنيف بنفس الاسم
    if Category.query.filter_by(name=name).first():
        flash('التصنيف موجود بالفعل', 'error')
        return redirect(url_for('admin_categories'))
    
    # إنشاء تصنيف جديد
    category = Category(name=name)
    db.session.add(category)
    db.session.commit()
    
    flash('تم إضافة التصنيف بنجاح', 'success')
    return redirect(url_for('admin_categories'))


@app.route('/admin/categories/edit', methods=['POST'])
@login_required('admin')
def admin_edit_category():
    """تعديل تصنيف"""
    category_id = request.form.get('category_id', type=int)
    name = request.form.get('name')
    
    category = Category.query.get_or_404(category_id)
    
    # التحقق من عدم وجود تصنيف آخر بنفس الاسم
    existing_category = Category.query.filter_by(name=name).first()
    if existing_category and existing_category.id != category_id:
        flash('يوجد تصنيف آخر بنفس الاسم', 'error')
        return redirect(url_for('admin_categories'))
    
    # تحديث اسم التصنيف
    category.name = name
    db.session.commit()
    
    flash('تم تحديث التصنيف بنجاح', 'success')
    return redirect(url_for('admin_categories'))


@app.route('/admin/categories/delete', methods=['POST'])
@login_required('admin')
def admin_delete_category():
    """حذف تصنيف"""
    category_id = request.form.get('category_id', type=int)
    replacement_category_id = request.form.get('replacement_category_id', type=int)
    
    category = Category.query.get_or_404(category_id)
    
    # إذا كان التصنيف يحتوي على بلاغات، يجب تحديد تصنيف بديل
    if category.tickets.count() > 0:
        if not replacement_category_id:
            flash('يجب تحديد تصنيف بديل لنقل البلاغات الحالية إليه', 'error')
            return redirect(url_for('admin_categories'))
        
        replacement_category = Category.query.get_or_404(replacement_category_id)
        
        # نقل البلاغات إلى التصنيف البديل
        # تعديل هنا: نستخدم التحديث المباشر بدلاً من الحلقة
        Ticket.query.filter_by(category_id=category_id).update({'category_id': replacement_category_id})
        db.session.flush()  # تنفيذ عمليات التحديث قبل الحذف
    
    # حذف التصنيف
    db.session.delete(category)
    db.session.commit()
    
    flash('تم حذف التصنيف بنجاح', 'success')
    return redirect(url_for('admin_categories'))

#-------------------------
# مسارات تقارير النظام
#-------------------------
@app.route('/admin/report')
@login_required('admin')
def admin_report():
    """صفحة تقارير النظام"""
    # استقبال مرشحات التقرير
    date_range = request.args.get('date_range', type=int, default=30)  # الافتراضي 30 يوم
    selected_category = request.args.get('category', type=int)
    selected_user = request.args.get('user', type=int)
    selected_priority = request.args.get('priority', type=int)
    
    # تحديد تاريخ بداية التقرير
    start_date = datetime.utcnow() - timedelta(days=date_range)
    
    # استعلام البلاغات حسب المرشحات
    tickets_query = Ticket.query.filter(Ticket.created_at >= start_date)
    
    if selected_category:
        tickets_query = tickets_query.filter_by(category_id=selected_category)
    
    if selected_user:
        tickets_query = tickets_query.filter(
            db.or_(
                Ticket.created_by_id == selected_user,
                Ticket.assigned_to_id == selected_user
            )
        )
    
    if selected_priority:
        tickets_query = tickets_query.filter_by(priority_id=selected_priority)
    
    tickets = tickets_query.all()
    
    # جلب الفلاتر لعرضها في الواجهة
    categories = Category.query.all()
    users = User.query.all()
    priorities = TicketPriority.query.all()
    statuses = TicketStatus.query.all()
    
    # البيانات المستخدمة في الرسوم البيانية
    report_data = generate_report_data(tickets, date_range, statuses, categories)
    
    return render_template(
        'admin_report.html',
        date_range=date_range,
        selected_category=selected_category,
        selected_user=selected_user,
        selected_priority=selected_priority,
        categories=categories,
        users=users,
        priorities=priorities,
        report_data=report_data
    )

def generate_report_data(tickets, date_range, statuses, categories):
    """توليد بيانات التقرير من البلاغات"""
    # الإحصائيات الأساسية
    total_tickets = len(tickets)
    completed_tickets = sum(1 for ticket in tickets if ticket.status.name == 'مكتمل')
    overdue_tickets = sum(1 for ticket in tickets if ticket.is_overdue())
    
    # حساب معدل الإكمال
    completion_rate = 0 if total_tickets == 0 else round((completed_tickets / total_tickets) * 100)
    
    # حساب متوسط وقت الاستجابة (بالساعات)
    response_times = [ticket.priority.response_time for ticket in tickets]
    avg_response_time = 0 if len(response_times) == 0 else round(sum(response_times) / len(response_times), 1)
    
    # حساب معدل التأخير
    open_tickets = sum(1 for ticket in tickets if ticket.status.name != 'مغلق')
    overdue_rate = 0 if open_tickets == 0 else round((overdue_tickets / open_tickets) * 100)
    
    # بيانات الرسم البياني للحالات
    status_names = [status.name for status in statuses]
    status_counts = []
    for status in statuses:
        count = sum(1 for ticket in tickets if ticket.status_id == status.id)
        status_counts.append(count)
    
    # بيانات الرسم البياني للتصنيفات
    category_names = [category.name for category in categories]
    category_counts = []
    for category in categories:
        count = sum(1 for ticket in tickets if ticket.category_id == category.id)
        category_counts.append(count)
    
    # إنشاء البيانات الزمنية للبلاغات
    timeline_labels, timeline_counts = generate_timeline_data(tickets, date_range)
    
    # بيانات أداء فنيي الصيانة
    technicians = generate_technician_performance(tickets)
    
    return {
        'total_tickets': total_tickets,
        'completed_tickets': completed_tickets,
        'completion_rate': completion_rate,
        'avg_response_time': avg_response_time,
        'overdue_tickets': overdue_tickets,
        'overdue_rate': overdue_rate,
        'status_names': status_names,
        'status_counts': status_counts,
        'category_names': category_names,
        'category_counts': category_counts,
        'timeline_labels': timeline_labels,
        'timeline_counts': timeline_counts,
        'technicians': technicians
    }


def generate_timeline_data(tickets, date_range):
    """توليد بيانات الجدول الزمني للبلاغات"""
    today = datetime.utcnow().date()
    
    # تحديد نوع المخطط الزمني بناءً على الفترة المختارة
    if date_range <= 30:
        # عرض كل يوم
        days = [today - timedelta(days=i) for i in range(date_range)]
        days.reverse()
        labels = [day.strftime('%Y-%m-%d') for day in days]
        
        counts = []
        for day in days:
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            count = sum(1 for ticket in tickets if day_start <= ticket.created_at <= day_end)
            counts.append(count)
    else:
        # عرض كل أسبوع
        weeks = date_range // 7
        if date_range % 7 > 0:
            weeks += 1
            
        week_dates = [today - timedelta(days=i*7) for i in range(weeks)]
        week_dates.reverse()
        
        labels = [f"أسبوع {i+1}" for i in range(len(week_dates))]
        
        counts = []
        for i, week_date in enumerate(week_dates):
            week_start = datetime.combine(week_date - timedelta(days=6), datetime.min.time())
            week_end = datetime.combine(week_date, datetime.max.time())
            count = sum(1 for ticket in tickets if week_start <= ticket.created_at <= week_end)
            counts.append(count)
    
    return labels, counts


def generate_technician_performance(tickets):
    """توليد بيانات أداء فنيي الصيانة"""
    # جمع البلاغات حسب الفني
    tech_data = {}
    
    # الفنيون الذين لديهم بلاغات مسندة
    maintenance_users = User.query.filter_by(user_type='maintenance').all()
    
    for user in maintenance_users:
        tech_data[user.id] = {
            'name': user.name,
            'assigned': 0,
            'completed': 0,
            'overdue': 0,
            'response_times': []
        }
    
    # حساب الإحصائيات لكل فني
    for ticket in tickets:
        if ticket.assigned_to_id and ticket.assigned_to_id in tech_data:
            tech_id = ticket.assigned_to_id
            tech_data[tech_id]['assigned'] += 1
            
            if ticket.status.name == 'مكتمل':
                tech_data[tech_id]['completed'] += 1
            
            if ticket.is_overdue():
                tech_data[tech_id]['overdue'] += 1
                
            tech_data[tech_id]['response_times'].append(ticket.priority.response_time)
    
    # تحويل البيانات إلى قائمة وحساب المعدلات
    technicians = []
    for tech_id, data in tech_data.items():
        if data['assigned'] > 0:
            # حساب معدل الإكمال
            completion_rate = 0 if data['assigned'] == 0 else round((data['completed'] / data['assigned']) * 100)
            
            # حساب متوسط وقت الاستجابة
            avg_response_time = 0 if len(data['response_times']) == 0 else round(sum(data['response_times']) / len(data['response_times']), 1)
            
            # حساب تقييم الأداء (مقياس من 1 إلى 5)
            # يعتمد على معدل الإكمال (50%)، نسبة البلاغات المتأخرة (30%)، وقت الاستجابة (20%)
            completion_score = completion_rate / 20  # 5 نقاط كحد أقصى
            
            overdue_rate = 0 if data['assigned'] == 0 else (data['overdue'] / data['assigned'])
            overdue_score = 3 - (overdue_rate * 3)  # 3 نقاط كحد أقصى
            
            response_score = 2 if avg_response_time == 0 else min(2, 2 * (48 / max(24, avg_response_time)))  # 2 نقاط كحد أقصى
            
            performance_rating = round(completion_score + overdue_score + response_score, 1)
            
            technicians.append({
                'name': data['name'],
                'assigned': data['assigned'],
                'completed': data['completed'],
                'completion_rate': completion_rate,
                'avg_response_time': avg_response_time,
                'overdue': data['overdue'],
                'performance_rating': performance_rating
            })
    
    # ترتيب الفنيين حسب التقييم
    technicians.sort(key=lambda x: x['performance_rating'], reverse=True)
    
    return technicians


# مسار صفحة بلاغاتي للموظفين
@app.route('/my_tickets')
@login_required('employee')
def my_tickets():
    """صفحة البلاغات الخاصة بالموظف"""
    current_user = get_current_user()
    
    # الحصول على البلاغات التي أنشأها الموظف
    tickets = Ticket.query.filter_by(created_by_id=current_user.id).order_by(Ticket.created_at.desc()).all()
    
    # تصنيف البلاغات حسب الحالة
    open_tickets = []
    in_progress_tickets = []
    completed_tickets = []
    
    for ticket in tickets:
        if ticket.status.name == 'جديد':
            open_tickets.append(ticket)
        elif ticket.status.name == 'قيد المعالجة':
            in_progress_tickets.append(ticket)
        elif ticket.status.name == 'مكتمل':
            completed_tickets.append(ticket)
    
    return render_template(
        'my_tickets.html',
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        completed_tickets=completed_tickets,
        total_tickets=len(tickets)
    )


@app.route('/maintenance/reports')
@login_required('maintenance')
def maintenance_reports():
    """صفحة تقارير فني الصيانة"""
    current_user = get_current_user()
    
    # الحصول على جميع البلاغات المسندة للفني
    assigned_tickets = Ticket.query.filter_by(assigned_to_id=current_user.id).all()
    
    # إجمالي البلاغات المسندة
    total_assigned = len(assigned_tickets)
    
    # تصنيف البلاغات حسب الحالة
    new_tickets = []
    in_progress_tickets = []
    completed_tickets = []
    overdue_tickets = []
    
    for ticket in assigned_tickets:
        if ticket.status.name == 'جديد':
            new_tickets.append(ticket)
        elif ticket.status.name == 'قيد المعالجة':
            in_progress_tickets.append(ticket)
        elif ticket.status.name == 'مكتمل':
            completed_tickets.append(ticket)
        
        if ticket.is_overdue():
            overdue_tickets.append(ticket)
    
    # إحصائيات الحالات
    new_count = len(new_tickets)
    in_progress_count = len(in_progress_tickets)
    completed_count = len(completed_tickets)
    overdue_count = len(overdue_tickets)
    
    # حساب معدل الإكمال
    completion_rate = 0
    if total_assigned > 0:
        completion_rate = round((completed_count / total_assigned) * 100)
    
    # حساب متوسط وقت الاستجابة
    avg_response_time = 0
    if total_assigned > 0:
        response_times = []
        for ticket in assigned_tickets:
            if ticket.status.name == 'مكتمل':
                # حساب المدة بين إنشاء التذكرة وإكمالها بالساعات
                duration = (ticket.updated_at - ticket.created_at).total_seconds() / 3600
                response_times.append(duration)
        
        if response_times:
            avg_response_time = round(sum(response_times) / len(response_times), 1)
    
    # إحصائيات البلاغات حسب الأولوية
    priority_stats = []
    priorities = TicketPriority.query.all()
    
    for priority in priorities:
        count = sum(1 for ticket in assigned_tickets if ticket.priority_id == priority.id)
        if count > 0:
            priority_stats.append({
                'name': priority.name,
                'count': count,
                'color': priority.color or f'#{hash(priority.name) % 0xffffff:06x}'
            })
    
    # إحصائيات البلاغات حسب القسم
    category_stats = []
    categories = Category.query.all()
    
    for category in categories:
        count = sum(1 for ticket in assigned_tickets if ticket.category_id == category.id)
        if count > 0:
            category_stats.append({
                'name': category.name,
                'count': count
            })
    
    # أحدث البلاغات المكتملة (آخر 5)
    recent_completed = sorted(
        completed_tickets, 
        key=lambda x: x.updated_at, 
        reverse=True
    )[:5]
    
    # بدلاً من تحويل البيانات إلى JSON، نرسلها مباشرة كقوائم كائنات
    return render_template(
        'maintenance_reports.html',
        total_assigned=total_assigned,
        new_count=new_count,
        in_progress_count=in_progress_count,
        completed_count=completed_count,
        overdue_count=overdue_count,
        completion_rate=completion_rate,
        avg_response_time=avg_response_time,
        priority_stats_raw=priority_stats,  # إرسال البيانات الأصلية
        category_stats_raw=category_stats,  # إرسال البيانات الأصلية
        recent_completed=recent_completed
    )

# تشغيل التطبيق
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
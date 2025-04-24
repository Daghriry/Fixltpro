#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixltpro - نظام بلاغات الدعم الفني - تطبيق Flask مع SQLite
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, send_from_directory, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect  # إضافة حماية CSRF
from flask_wtf import FlaskForm  # استيراد FlaskForm
from wtforms import StringField, PasswordField, BooleanField, validators  # استيراد حقول النموذج
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
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


# إعداد مسار المرفقات
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 ميجابايت كحد أقصى

# الامتدادات المسموح بها
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

def allowed_file(filename):
    """التحقق من امتداد الملف"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    subcategories = db.relationship('SubCategory', backref='parent_category', lazy='dynamic', cascade='all, delete-orphan')

class SubCategory(db.Model):
    """نموذج التصنيف الفرعي للبلاغ"""
    __tablename__ = 'subcategories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    tickets = db.relationship('Ticket', backref='subcategory', lazy='dynamic')


class Department(db.Model):
    """نموذج الإدارات"""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # العلاقة مع الأقسام
    sections = db.relationship('Section', backref='department', lazy='dynamic', cascade='all, delete-orphan')
    tickets = db.relationship('Ticket', backref='department', lazy='dynamic')


class Section(db.Model):
    """نموذج الأقسام"""
    __tablename__ = 'sections'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    
    tickets = db.relationship('Ticket', backref='section', lazy='dynamic')
    

class Ticket(db.Model):
    """نموذج البلاغ"""
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))  # جعلها اختيارية
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    subcategory_id = db.Column(db.Integer, db.ForeignKey('subcategories.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'))
    priority_id = db.Column(db.Integer, db.ForeignKey('priorities.id'), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('statuses.id'), nullable=False)
    
    comments = db.relationship('Comment', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')


    def is_overdue(self):
        """التحقق مما إذا كان البلاغ متأخراً"""
        if not self.due_date:
            return False
        return datetime.utcnow() > self.due_date


class Attachment(db.Model):
    """نموذج المرفقات"""
    __tablename__ = 'attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))  # نوع الملف (صورة، PDF، إلخ)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # إضافة علاقة مع المستخدم الذي قام برفع الملف
    
    # إضافة علاقة مع المستخدم
    user = db.relationship('User', backref='attachments')


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



@app.route('/')
def index():
    """الصفحة الرئيسية"""
    # التحقق من وجود جداول قاعدة البيانات
    try:
        if User.query.count() == 0:
            # قاعدة البيانات موجودة لكن فارغة، إعادة توجيه إلى الإعداد
            return redirect(url_for('setup_page'))
    except:
        # خطأ يعني عدم وجود جداول في قاعدة البيانات
        session.clear()  # حذف بيانات الجلسة
        return redirect(url_for('setup_page'))
        
    # في حالة وجود جلسة تسجيل دخول
    if 'user_id' in session:
        try:
            user = User.query.get(session['user_id'])
            if user:  # تأكد من أن المستخدم موجود
                if user.user_type == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user.user_type == 'maintenance':
                    return redirect(url_for('maintenance_dashboard'))
                else:
                    return redirect(url_for('create_ticket'))
            else:
                # المستخدم غير موجود، مسح الجلسة
                session.clear()
        except:
            # خطأ في الاستعلام، مسح الجلسة
            session.clear()
            
    # إعادة توجيه إلى صفحة تسجيل الدخول
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
    departments = Department.query.all()
    priorities = TicketPriority.query.all()
    
    # الحصول على قائمة فنيي الصيانة لعرضها في القائمة المنسدلة
    maintenance_staff = User.query.filter_by(user_type='maintenance').all()
    
    if request.method == 'POST':
        description = request.form.get('description')
        category_id = request.form.get('category_id', type=int)
        subcategory_id = request.form.get('subcategory_id')
        department_id = request.form.get('department_id')
        section_id = request.form.get('section_id')
        priority_id = request.form.get('priority_id', type=int)
        assigned_to_id = request.form.get('assigned_to_id')  # معرف فني الصيانة المعين
        
        # تحويل القيم إلى None إذا كانت '0' أو فارغة
        if subcategory_id in ['0', '', None]:
            subcategory_id = None
        else:
            subcategory_id = int(subcategory_id)
            
        if department_id in ['0', '', None]:
            department_id = None
        else:
            department_id = int(department_id)
            
        if section_id in ['0', '', None]:
            section_id = None
        else:
            section_id = int(section_id)
            
        if assigned_to_id in ['0', '', None]:
            assigned_to_id = None
        else:
            assigned_to_id = int(assigned_to_id)
        
        if not all([description, category_id, priority_id]):
            flash('يرجى ملء جميع الحقول المطلوبة', 'error')
            return render_template('create_ticket.html', 
                                  categories=categories, 
                                  priorities=priorities, 
                                  departments=departments,
                                  maintenance_staff=maintenance_staff)
        
        # الحصول على حالة "جديد" أو "قيد المعالجة" حسب ما إذا تم تعيين فني أم لا
        if assigned_to_id:
            # إذا تم تعيين فني، نجعل حالة البلاغ "قيد المعالجة"
            status = TicketStatus.query.filter_by(name='قيد المعالجة').first()
        else:
            # إذا لم يتم تعيين فني، نجعل حالة البلاغ "جديد"
            status = TicketStatus.query.filter_by(name='جديد').first()
            
        if not status:
            flash('خطأ في النظام: حالة البلاغ غير موجودة', 'error')
            return render_template('create_ticket.html', 
                                  categories=categories, 
                                  priorities=priorities, 
                                  departments=departments,
                                  maintenance_staff=maintenance_staff)
        
        # إنشاء عنوان افتراضي للبلاغ إذا لم يتم توفيره
        auto_title = f"{Category.query.get(category_id).name}"
        if subcategory_id:
            auto_title += f" - {SubCategory.query.get(subcategory_id).name}"
        if department_id:
            auto_title += f" - {Department.query.get(department_id).name}"
            if section_id:
                auto_title += f" - {Section.query.get(section_id).name}"
        
        # إنشاء البلاغ الجديد
        ticket = Ticket(
            title=auto_title,  # استخدام العنوان الافتراضي المنشأ تلقائيًا
            description=description,
            created_by_id=session['user_id'],
            category_id=category_id,
            subcategory_id=subcategory_id,
            department_id=department_id,
            section_id=section_id,
            priority_id=priority_id,
            assigned_to_id=assigned_to_id,  # تعيين الفني المسؤول
            status_id=status.id,
            due_date=calculate_due_date(priority_id)
        )
        
        db.session.add(ticket)
        db.session.flush()  # للحصول على معرف البلاغ
        
        # معالجة المرفقات
        uploaded_files = request.files.getlist('attachments')
        if uploaded_files:
            upload_dir = os.path.join(basedir, 'uploads')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            for file in uploaded_files[:5]:  # الحد الأقصى 5 ملفات
                if file and file.filename:
                    # إنشاء اسم ملف فريد
                    filename = secure_filename(file.filename)
                    unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    
                    # حفظ الملف
                    file.save(file_path)
                    
                    # إنشاء سجل المرفق مع إضافة معرف المستخدم
                    attachment = Attachment(
                        filename=filename,
                        file_path=file_path,
                        file_type=file.content_type,
                        ticket_id=ticket.id,
                        user_id=session['user_id']  # إضافة معرف المستخدم الحالي
                    )
                    db.session.add(attachment)
        
        # إذا تم تعيين فني، أضف تعليق تلقائي يشير إلى ذلك
        if assigned_to_id:
            tech_name = User.query.get(assigned_to_id).name
            comment = Comment(
                content=f"تم تعيين البلاغ إلى {tech_name} عند إنشاء البلاغ.",
                ticket_id=ticket.id,
                user_id=session['user_id']
            )
            db.session.add(comment)
        
        db.session.commit()
        
        flash('تم إنشاء البلاغ بنجاح', 'success')
        
        # إعادة التوجيه مع تعليمات لمنع تخزين البيانات في المتصفح
        response = make_response(redirect(url_for('view_ticket', ticket_id=ticket.id)))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        
        # تعيين كوكي لمسح البيانات بعد الانتقال
        response.set_cookie('clear_form', 'true', max_age=60)
        
        return response
    
    # في حالة طلب GET، تأكد من تقديم نموذج نظيف
    response = make_response(render_template('create_ticket.html', 
                          categories=categories, 
                          priorities=priorities, 
                          departments=departments,
                          maintenance_staff=maintenance_staff))
    
    # إضافة ترويسات التحكم بالتخزين المؤقت
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    
    return response


@app.route('/search_ticket')
@login_required()
def search_ticket():
    """البحث عن بلاغ برقم البلاغ والانتقال إليه مباشرة"""
    ticket_id = request.args.get('ticket_id', '')
    
    # التحقق من صحة رقم البلاغ
    if not ticket_id.isdigit():
        flash('الرجاء إدخال رقم بلاغ صحيح', 'error')
        return redirect(request.referrer or url_for('index'))
    
    # محاولة العثور على البلاغ
    ticket = Ticket.query.get(int(ticket_id))
    
    if not ticket:
        flash(f'لم يتم العثور على بلاغ برقم {ticket_id}', 'error')
        return redirect(request.referrer or url_for('index'))
    
    # الانتقال مباشرة إلى صفحة البلاغ
    return redirect(url_for('view_ticket', ticket_id=ticket.id))

@app.route('/ticket/<int:ticket_id>')
@login_required()
def view_ticket(ticket_id):
    """عرض تفاصيل البلاغ"""
    ticket = Ticket.query.get_or_404(ticket_id)
    current_user = get_current_user()
    
    # لا نحتاج للتحقق من الصلاحيات - أي مستخدم يمكنه الوصول للبلاغات
    
    # الحصول على التعليقات
    comments = ticket.comments.order_by(Comment.created_at).all()
    
    # الحصول على المرفقات
    attachments = ticket.attachments.order_by(Attachment.upload_date.desc()).all()
    
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
        attachments=attachments,
        maintenance_staff=maintenance_staff,
        statuses=statuses
    )

# تعديل مسار إضافة تعليق لدعم المرفقات أيضاً
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
    db.session.flush()  # للحصول على معرف التعليق
    
    # معالجة المرفقات للتعليق
    uploaded_files = request.files.getlist('comment_attachments')
    if uploaded_files:
        upload_dir = os.path.join(basedir, 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        for file in uploaded_files[:2]:  # الحد الأقصى 2 ملفات للتعليق
            if file and file.filename:
                # إنشاء اسم ملف فريد
                filename = secure_filename(file.filename)
                unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_comment_{comment.id}_{filename}"
                file_path = os.path.join(upload_dir, unique_filename)
                
                # حفظ الملف
                file.save(file_path)
                
                # تحديث محتوى التعليق لتضمين إشارة للمرفق
                comment.content += f"\n\n[مرفق: {filename}]"
                
                # إنشاء سجل المرفق مرتبط بالبلاغ وإضافة معرف المستخدم
                attachment = Attachment(
                    filename=filename,
                    file_path=file_path,
                    file_type=file.content_type,
                    ticket_id=ticket_id,
                    user_id=session['user_id']  # إضافة معرف المستخدم الحالي
                )
                db.session.add(attachment)
    
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
def setup_page():
    """صفحة إعداد قاعدة البيانات"""
    # مسح أي جلسة سابقة لتجنب الأخطاء
    session.clear()
    
    # التحقق مما إذا كانت قاعدة البيانات مهيأة بالفعل
    try:
        if User.query.count() > 0:
            flash('تم إعداد قاعدة البيانات مسبقاً', 'info')
            return redirect(url_for('login'))
    except:
        # تجاهل الخطأ - إنه متوقع إذا لم تكن الجداول موجودة بعد
        pass
    
    # عرض صفحة الإعداد
    return render_template('setup_page.html')


def setup_api():
    """واجهة برمجة التطبيقات لإعداد قاعدة البيانات"""
    try:
        # مسح أي جلسة سابقة
        session.clear()
        
        # التحقق مما إذا كانت البيانات موجودة بالفعل
        try:
            if User.query.count() > 0:
                return jsonify({'status': 'info', 'message': 'تم إعداد قاعدة البيانات مسبقاً'})
        except:
            # تجاهل الخطأ - هذا متوقع إذا لم تكن الجداول موجودة
            pass
        
        # إعادة إنشاء قاعدة البيانات
        try:
            db.drop_all()  # حذف جميع الجداول القديمة إن وجدت
        except:
            pass  # تجاهل الخطأ إذا لم تكن هناك جداول لحذفها
            
        db.create_all()  # إنشاء الجداول من جديد
        
        # إنشاء مجلد التحميلات إذا لم يكن موجودًا
        upload_dir = os.path.join(basedir, 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # إنشاء المستخدمين
        admin = User(username='admin', name='مدير النظام', user_type='admin', email='admin@fixltpro.com', phone='0500000000')
        admin.password = 'admin123'
        
        employee1 = User(username='employee1', name='موظف الاستقبال', user_type='employee', email='employee@fixltpro.com', phone='0500000001')
        employee1.password = 'employee1'
        
        maintenance1 = User(username='maintenance1', name='فني الصيانة 1', user_type='maintenance', email='maint1@fixltpro.com', phone='0500000002')
        maintenance1.password = 'maintenance1'
        
        maintenance2 = User(username='maintenance2', name='فني الصيانة 2', user_type='maintenance', email='maint2@fixltpro.com', phone='0500000003')
        maintenance2.password = 'maintenance2'
        
        db.session.add_all([admin, employee1, maintenance1, maintenance2])
        db.session.flush()
        
        # إنشاء الأولويات
        high_priority = TicketPriority(name='عالية', response_time=24, color='#FF0000')
        medium_priority = TicketPriority(name='متوسطة', response_time=72, color='#FFAA00')
        low_priority = TicketPriority(name='منخفضة', response_time=120, color='#00AA00')
        
        db.session.add_all([high_priority, medium_priority, low_priority])
        db.session.flush()
        
        # إنشاء الحالات
        new_status = TicketStatus(name='جديد')
        in_progress = TicketStatus(name='قيد المعالجة')
        completed = TicketStatus(name='مكتمل')
        closed = TicketStatus(name='مغلق')
        
        db.session.add_all([new_status, in_progress, completed, closed])
        db.session.flush()
        
        # إنشاء التصنيفات
        hardware = Category(name='أجهزة الحاسب')
        network = Category(name='شبكات')
        software = Category(name='برمجيات')
        other = Category(name='أخرى')
        
        db.session.add_all([hardware, network, software, other])
        db.session.flush()
        
        # إنشاء التصنيفات الفرعية
        hardware_subcats = [
            SubCategory(name='أجهزة الحاسب المكتبية', category_id=hardware.id),
            SubCategory(name='أجهزة الحاسب المحمولة', category_id=hardware.id),
            SubCategory(name='الطابعات', category_id=hardware.id),
            SubCategory(name='أجهزة العرض', category_id=hardware.id)
        ]
        
        network_subcats = [
            SubCategory(name='الإنترنت', category_id=network.id),
            SubCategory(name='الشبكة الداخلية', category_id=network.id),
            SubCategory(name='نقاط الوصول اللاسلكية', category_id=network.id)
        ]
        
        software_subcats = [
            SubCategory(name='نظام التشغيل', category_id=software.id),
            SubCategory(name='برامج المكتب', category_id=software.id),
            SubCategory(name='تطبيقات المؤسسة', category_id=software.id),
            SubCategory(name='البرامج المضادة للفيروسات', category_id=software.id)
        ]
        
        db.session.add_all(hardware_subcats + network_subcats + software_subcats)
        db.session.flush()
        
        # إنشاء الإدارات
        dept1 = Department(name='الإدارة العامة')
        dept2 = Department(name='الموارد البشرية')
        dept3 = Department(name='المالية')
        dept4 = Department(name='تقنية المعلومات')
        
        db.session.add_all([dept1, dept2, dept3, dept4])
        db.session.flush()
        
        # إنشاء الأقسام
        sections = [
            Section(name='مكتب المدير العام', department_id=dept1.id),
            Section(name='العلاقات العامة', department_id=dept1.id),
            Section(name='التوظيف', department_id=dept2.id),
            Section(name='التطوير الوظيفي', department_id=dept2.id),
            Section(name='المحاسبة', department_id=dept3.id),
            Section(name='المشتريات', department_id=dept3.id),
            Section(name='الدعم الفني', department_id=dept4.id),
            Section(name='البنية التحتية', department_id=dept4.id),
            Section(name='تطوير البرمجيات', department_id=dept4.id)
        ]
        
        db.session.add_all(sections)
        db.session.flush()
        
        # حفظ التغييرات
        db.session.commit()
        
        # إنشاء بعض البلاغات التجريبية
        ticket1 = Ticket(
            title='جهاز لا يعمل',
            description='جهاز الحاسب في قسم المحاسبة لا يعمل بشكل صحيح',
            created_by_id=employee1.id,
            category_id=hardware.id,
            subcategory_id=hardware_subcats[0].id,  # أجهزة الحاسب المكتبية
            department_id=dept3.id,  # المالية
            section_id=sections[4].id,  # المحاسبة
            priority_id=high_priority.id,
            status_id=new_status.id,
            due_date=datetime.utcnow() + timedelta(hours=24)
        )
        
        ticket2 = Ticket(
            title='انقطاع في الشبكة',
            description='شبكة الإنترنت غير متوفرة في الطابق الثاني',
            created_by_id=employee1.id,
            category_id=network.id,
            subcategory_id=network_subcats[0].id,  # الإنترنت
            department_id=dept4.id,  # تقنية المعلومات
            section_id=sections[7].id,  # البنية التحتية
            priority_id=medium_priority.id,
            status_id=new_status.id,
            due_date=datetime.utcnow() + timedelta(hours=72)
        )
        
        db.session.add_all([ticket1, ticket2])
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'تم إعداد قاعدة البيانات بنجاح'})
        
    except Exception as e:
        app.logger.error(f"خطأ في إعداد قاعدة البيانات: {str(e)}")
        return jsonify({'status': 'error', 'message': f'حدث خطأ أثناء إعداد قاعدة البيانات: {str(e)}'})


@app.context_processor
def inject_common_data():
    """إضافة بيانات مشتركة إلى جميع القوالب"""
    try:
        # نحاول الحصول على البيانات من قاعدة البيانات
        data = {
            'get_current_user': get_current_user,
            'now': datetime.now()
        }
        
        # التحقق من طريق المتصفح - إذا كان مسار الإعداد، لا نحتاج لبيانات قاعدة البيانات
        if request.path != '/setup' and request.path != '/setup_api':
            data['categories'] = Category.query.all()
            data['departments'] = Department.query.all()
        
        return data
    except:
        # في حالة وجود خطأ (مثل عدم وجود الجداول)، نعيد فقط البيانات الأساسية
        return {
            'get_current_user': get_current_user,
            'now': datetime.now(),
            'categories': [],
            'departments': []
        }


@app.route('/setup_api', methods=['POST'])
@csrf.exempt  # إعفاء هذا المسار من حماية CSRF
def setup_api_route():
    """مسار واجهة برمجة التطبيقات لإعداد قاعدة البيانات"""
    return setup_api()

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

@app.route('/ticket/<int:ticket_id>/upload', methods=['POST'])
@login_required()
def upload_attachment(ticket_id):
    """رفع مرفق جديد للبلاغ"""
    ticket = Ticket.query.get_or_404(ticket_id)
    current_user = get_current_user()
    
    # التحقق من صلاحية الوصول للبلاغ
    if (current_user.user_type != 'admin' and
        current_user.id != ticket.created_by_id and
        (current_user.user_type != 'maintenance' or current_user.id != ticket.assigned_to_id)):
        flash('ليس لديك صلاحية لإضافة مرفقات لهذا البلاغ', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    # التحقق من وجود ملف في الطلب
    if 'attachment' not in request.files:
        flash('لم يتم تحديد ملف', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    file = request.files['attachment']
    
    # التحقق من اختيار ملف
    if file.filename == '':
        flash('لم يتم اختيار ملف', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    # التحقق من صلاحية امتداد الملف
    if not allowed_file(file.filename):
        flash('امتداد الملف غير مسموح به', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    
    # تأمين اسم الملف
    original_filename = file.filename
    filename = secure_filename(original_filename)
    
    # إنشاء اسم فريد للملف المخزن
    import uuid
    stored_filename = f"{uuid.uuid4()}_{filename}"
    
    # حفظ الملف
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
    file.save(file_path)
    
    # إنشاء سجل للمرفق في قاعدة البيانات
    attachment = Attachment(
        filename=original_filename,
        stored_filename=stored_filename,
        file_type=file.content_type,
        file_size=os.path.getsize(file_path),
        ticket_id=ticket_id,
        user_id=current_user.id
    )
    
    db.session.add(attachment)
    db.session.commit()
    
    # إضافة تعليق تلقائي عن إضافة المرفق
    comment = Comment(
        content=f'تم إضافة مرفق: {original_filename}',
        ticket_id=ticket_id,
        user_id=current_user.id
    )
    db.session.add(comment)
    db.session.commit()
    
    flash('تم رفع المرفق بنجاح', 'success')
    return redirect(url_for('view_ticket', ticket_id=ticket_id))


@app.route('/attachments/<int:attachment_id>/download')
@login_required()
def download_attachment(attachment_id):
    """تحميل المرفق"""
    return view_attachment(attachment_id)  # تحويل مباشر إلى مسار المعاينة مع إضافة معلمة download=true

# Route للحصول على التصنيفات الفرعية
@app.route('/api/subcategories/<int:category_id>')
@login_required()
def get_subcategories(category_id):
    """الحصول على التصنيفات الفرعية لتصنيف معين"""
    subcategories = SubCategory.query.filter_by(category_id=category_id).all()
    
    # تحويل الكائنات إلى قائمة للتمثيل JSON
    subcategories_list = []
    for subcategory in subcategories:
        subcategories_list.append({
            'id': subcategory.id,
            'name': subcategory.name
        })
    
    return jsonify({'subcategories': subcategories_list})

# Route للحصول على الأقسام
@app.route('/api/sections/<int:department_id>')
@login_required()
def get_sections(department_id):
    """الحصول على الأقسام لإدارة معينة"""
    sections = Section.query.filter_by(department_id=department_id).all()
    
    # تحويل الكائنات إلى قائمة للتمثيل JSON
    sections_list = []
    for section in sections:
        sections_list.append({
            'id': section.id,
            'name': section.name
        })
    
    return jsonify({'sections': sections_list})

# مسار إضافة التصنيف الفرعي
@app.route('/admin/subcategories/add', methods=['POST'])
@login_required('admin')
def admin_add_subcategory():
    """إضافة تصنيف فرعي جديد"""
    category_id = request.form.get('category_id', type=int)
    name = request.form.get('name')
    
    # التحقق من وجود التصنيف الرئيسي
    category = Category.query.get_or_404(category_id)
    
    # التحقق من عدم وجود تصنيف فرعي بنفس الاسم للتصنيف الرئيسي نفسه
    existing_subcategory = SubCategory.query.filter_by(name=name, category_id=category_id).first()
    if existing_subcategory:
        flash('التصنيف الفرعي موجود بالفعل', 'error')
        return redirect(url_for('admin_categories'))
    
    # إنشاء تصنيف فرعي جديد
    subcategory = SubCategory(name=name, category_id=category_id)
    db.session.add(subcategory)
    db.session.commit()
    
    flash('تم إضافة التصنيف الفرعي بنجاح', 'success')
    return redirect(url_for('admin_categories'))

# مسار تعديل التصنيف الفرعي
@app.route('/admin/subcategories/edit', methods=['POST'])
@login_required('admin')
def admin_edit_subcategory():
    """تعديل تصنيف فرعي"""
    subcategory_id = request.form.get('subcategory_id', type=int)
    name = request.form.get('name')
    
    subcategory = SubCategory.query.get_or_404(subcategory_id)
    
    # التحقق من عدم وجود تصنيف فرعي آخر بنفس الاسم للتصنيف الرئيسي نفسه
    existing_subcategory = SubCategory.query.filter_by(name=name, category_id=subcategory.category_id).first()
    if existing_subcategory and existing_subcategory.id != subcategory_id:
        flash('يوجد تصنيف فرعي آخر بنفس الاسم', 'error')
        return redirect(url_for('admin_categories'))
    
    # تحديث اسم التصنيف الفرعي
    subcategory.name = name
    db.session.commit()
    
    flash('تم تحديث التصنيف الفرعي بنجاح', 'success')
    return redirect(url_for('admin_categories'))

# مسار حذف التصنيف الفرعي
@app.route('/admin/subcategories/delete', methods=['POST'])
@login_required('admin')
def admin_delete_subcategory():
    """حذف تصنيف فرعي"""
    subcategory_id = request.form.get('subcategory_id', type=int)
    
    subcategory = SubCategory.query.get_or_404(subcategory_id)
    
    # نقل البلاغات من التصنيف الفرعي إلى التصنيف الرئيسي
    if subcategory.tickets.count() > 0:
        Ticket.query.filter_by(subcategory_id=subcategory_id).update({'subcategory_id': None})
        db.session.flush()
    
    # حذف التصنيف الفرعي
    db.session.delete(subcategory)
    db.session.commit()
    
    flash('تم حذف التصنيف الفرعي بنجاح', 'success')
    return redirect(url_for('admin_categories'))

# مسار صفحة إدارة الإدارات
@app.route('/admin/departments')
@login_required('admin')
def admin_departments():
    """صفحة إدارة الإدارات"""
    departments = Department.query.all()
    
    # تحضير بيانات الإدارات بتنسيق JSON لاستخدامها في الرسم البياني
    departments_data = []
    for department in departments:
        departments_data.append({
            'id': department.id,
            'name': department.name,
            'tickets_count': department.tickets.count(),
            'sections_count': department.sections.count()
        })
    
    # تحويل البيانات إلى سلسلة JSON
    import json
    departments_json_str = json.dumps(departments_data)
    
    return render_template('admin_departments.html', 
                          departments=departments,
                          departments_data=departments_data,
                          departments_json=departments_json_str)

# مسار إضافة إدارة جديدة
@app.route('/admin/departments/add', methods=['POST'])
@login_required('admin')
def admin_add_department():
    """إضافة إدارة جديدة"""
    name = request.form.get('name')
    
    # التحقق من عدم وجود إدارة بنفس الاسم
    if Department.query.filter_by(name=name).first():
        flash('الإدارة موجودة بالفعل', 'error')
        return redirect(url_for('admin_departments'))
    
    # إنشاء إدارة جديدة
    department = Department(name=name)
    db.session.add(department)
    db.session.commit()
    
    flash('تم إضافة الإدارة بنجاح', 'success')
    return redirect(url_for('admin_departments'))

# مسار تعديل إدارة
@app.route('/admin/departments/edit', methods=['POST'])
@login_required('admin')
def admin_edit_department():
    """تعديل إدارة"""
    department_id = request.form.get('department_id', type=int)
    name = request.form.get('name')
    
    department = Department.query.get_or_404(department_id)
    
    # التحقق من عدم وجود إدارة أخرى بنفس الاسم
    existing_department = Department.query.filter_by(name=name).first()
    if existing_department and existing_department.id != department_id:
        flash('يوجد إدارة أخرى بنفس الاسم', 'error')
        return redirect(url_for('admin_departments'))
    
    # تحديث اسم الإدارة
    department.name = name
    db.session.commit()
    
    flash('تم تحديث الإدارة بنجاح', 'success')
    return redirect(url_for('admin_departments'))

# مسار حذف إدارة
@app.route('/admin/departments/delete', methods=['POST'])
@login_required('admin')
def admin_delete_department():
    """حذف إدارة"""
    department_id = request.form.get('department_id', type=int)
    
    department = Department.query.get_or_404(department_id)
    
    # حذف الإدارة (سيتم حذف جميع الأقسام والبلاغات المرتبطة بها تلقائيًا بسبب cascade)
    db.session.delete(department)
    db.session.commit()
    
    flash('تم حذف الإدارة بنجاح', 'success')
    return redirect(url_for('admin_departments'))

# مسار إضافة قسم
@app.route('/admin/sections/add', methods=['POST'])
@login_required('admin')
def admin_add_section():
    """إضافة قسم جديد"""
    department_id = request.form.get('department_id', type=int)
    name = request.form.get('name')
    
    # التحقق من وجود الإدارة
    department = Department.query.get_or_404(department_id)
    
    # التحقق من عدم وجود قسم بنفس الاسم للإدارة نفسها
    existing_section = Section.query.filter_by(name=name, department_id=department_id).first()
    if existing_section:
        flash('القسم موجود بالفعل', 'error')
        return redirect(url_for('admin_departments'))
    
    # إنشاء قسم جديد
    section = Section(name=name, department_id=department_id)
    db.session.add(section)
    db.session.commit()
    
    flash('تم إضافة القسم بنجاح', 'success')
    return redirect(url_for('admin_departments'))

# مسار تعديل قسم
@app.route('/admin/sections/edit', methods=['POST'])
@login_required('admin')
def admin_edit_section():
    """تعديل قسم"""
    section_id = request.form.get('section_id', type=int)
    name = request.form.get('name')
    
    section = Section.query.get_or_404(section_id)
    
    # التحقق من عدم وجود قسم آخر بنفس الاسم للإدارة نفسها
    existing_section = Section.query.filter_by(name=name, department_id=section.department_id).first()
    if existing_section and existing_section.id != section_id:
        flash('يوجد قسم آخر بنفس الاسم', 'error')
        return redirect(url_for('admin_departments'))
    
    # تحديث اسم القسم
    section.name = name
    db.session.commit()
    
    flash('تم تحديث القسم بنجاح', 'success')
    return redirect(url_for('admin_departments'))

# مسار حذف قسم
@app.route('/admin/sections/delete', methods=['POST'])
@login_required('admin')
def admin_delete_section():
    """حذف قسم"""
    section_id = request.form.get('section_id', type=int)
    
    section = Section.query.get_or_404(section_id)
    
    # نقل البلاغات من القسم إلى الإدارة الرئيسية
    if section.tickets.count() > 0:
        for ticket in section.tickets:
            ticket.section_id = None
        db.session.flush()
    
    # حذف القسم
    db.session.delete(section)
    db.session.commit()
    
    flash('تم حذف القسم بنجاح', 'success')
    return redirect(url_for('admin_departments'))

# مسار عرض المرفق
@app.route('/attachments/<int:attachment_id>')
@login_required()
def view_attachment(attachment_id):
    """عرض المرفق"""
    attachment = Attachment.query.get_or_404(attachment_id)
    ticket = Ticket.query.get(attachment.ticket_id)
    current_user = get_current_user()
    
    # التحقق من الصلاحيات - يمكن للمدير ولفني الصيانة المسؤول وللموظف صاحب البلاغ عرض المرفقات
    if (current_user.user_type != 'admin' and
        current_user.id != ticket.created_by_id and
        (current_user.user_type != 'maintenance' or current_user.id != ticket.assigned_to_id)):
        flash('ليس لديك صلاحية لعرض هذا المرفق', 'error')
        return redirect(url_for('index'))
    
    # التحقق مما إذا كان المستخدم يريد تحميل الملف أو معاينته
    download = request.args.get('download', 'false') == 'true'
    
    try:
        # إرسال الملف
        return send_file(
            attachment.file_path,
            as_attachment=download,  # True للتحميل، False للمعاينة
            download_name=attachment.filename if download else None,
            mimetype=attachment.file_type
        )
    except Exception as e:
        app.logger.error(f"Error serving attachment: {str(e)}")
        flash('حدث خطأ أثناء محاولة عرض المرفق', 'error')
        return redirect(url_for('view_ticket', ticket_id=ticket.id))


@app.route('/attachment/<int:attachment_id>/delete', methods=['POST'])
@login_required()
def delete_attachment(attachment_id):
    """حذف المرفق"""
    attachment = Attachment.query.get_or_404(attachment_id)
    current_user = get_current_user()
    
    # التحقق من صلاحية حذف المرفق (المدير أو الشخص الذي قام برفع الملف)
    if current_user.user_type != 'admin' and current_user.id != attachment.user_id:
        flash('ليس لديك صلاحية لحذف هذا المرفق', 'error')
        return redirect(url_for('view_ticket', ticket_id=attachment.ticket_id))
    
    # حذف الملف من النظام
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment.stored_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        app.logger.error(f"خطأ في حذف الملف: {str(e)}")
    
    # حذف المرفق من قاعدة البيانات
    ticket_id = attachment.ticket_id
    filename = attachment.filename
    
    db.session.delete(attachment)
    db.session.commit()
    
    # إضافة تعليق تلقائي عن حذف المرفق
    comment = Comment(
        content=f'تم حذف مرفق: {filename}',
        ticket_id=ticket_id,
        user_id=current_user.id
    )
    db.session.add(comment)
    db.session.commit()
    
    flash('تم حذف المرفق بنجاح', 'success')
    return redirect(url_for('view_ticket', ticket_id=ticket_id))




# تشغيل التطبيق
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
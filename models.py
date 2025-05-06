"""
models.py - نماذج قاعدة البيانات لنظام Fixltpro للدعم الفني
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# إنشاء كائن قاعدة البيانات
db = SQLAlchemy()

class User(db.Model):
    """نموذج المستخدم"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # admin, employee, maintenance
    email = db.Column(db.String(100))  # حقل البريد الإلكتروني
    phone = db.Column(db.String(20))  # حقل رقم الهاتف
    
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
    is_custom = db.Column(db.Boolean, default=False)  # هل هذه أولوية بوقت محدد؟
    
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


class Beneficiary(db.Model):
    """نموذج المستفيد"""
    __tablename__ = 'beneficiaries'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # إضافة علاقة مع البلاغات
    tickets = db.relationship('Ticket', backref='beneficiary', lazy='dynamic')


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
    beneficiary_id = db.Column(db.Integer, db.ForeignKey('beneficiaries.id'))  # حقل المستفيد
    
    comments = db.relationship('Comment', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')
    attachments = db.relationship('Attachment', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')
    contact_method = db.Column(db.String(50), nullable=True)

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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # المستخدم الذي قام برفع الملف
    
    # العلاقة مع المستخدم
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
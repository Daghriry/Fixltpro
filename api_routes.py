"""
api_routes.py - واجهات برمجة التطبيقات لنظام Fixltpro
"""

from flask import Blueprint, jsonify, request, session
from models import db, Department, Section, Category, SubCategory, Ticket, User, Beneficiary, Comment
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timedelta

# إنشاء Blueprint للواجهات البرمجية
api = Blueprint('api', __name__)

# إنشاء كائن CSRF للحماية
csrf = CSRFProtect()

# إعفاء بعض المسارات API من حماية CSRF
@api.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,X-CSRFToken')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

# API لجلب الأقسام التابعة لإدارة معينة
@api.route('/sections/<int:department_id>', methods=['GET'])
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

# API لجلب التصنيفات الفرعية لتصنيف معين
@api.route('/subcategories/<int:category_id>', methods=['GET'])
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

# API للبحث عن المستفيدين
@api.route('/beneficiaries/search', methods=['GET'])
def search_beneficiaries():
    """البحث عن المستفيدين للاستخدام في الواجهة"""
    search_term = request.args.get('term', '')
    
    if not search_term:
        return jsonify([])
    
    # البحث عن المستفيدين الذين يطابق اسمهم مصطلح البحث
    beneficiaries = Beneficiary.query.filter(Beneficiary.name.like(f'%{search_term}%')).limit(10).all()
    
    # إرجاع النتائج بتنسيق مناسب لـ autocomplete
    results = []
    for beneficiary in beneficiaries:
        results.append({
            'id': beneficiary.id,
            'value': beneficiary.name,
            'label': f"{beneficiary.name} {f'- {beneficiary.phone}' if beneficiary.phone else ''}"
        })
    
    return jsonify(results)

# API لإضافة مستفيد جديد
@api.route('/beneficiaries/add', methods=['POST'])
@csrf.exempt
def add_beneficiary():
    """إضافة مستفيد جديد"""
    data = request.json
    
    if not data or not data.get('name'):
        return jsonify({'status': 'error', 'message': 'يرجى إدخال اسم المستفيد'}), 400
    
    beneficiary = Beneficiary(
        name=data.get('name'),
        phone=data.get('phone', '')
    )
    
    db.session.add(beneficiary)
    db.session.commit()
    
    return jsonify({
        'status': 'success', 
        'message': 'تم إضافة المستفيد بنجاح',
        'beneficiary': {
            'id': beneficiary.id,
            'name': beneficiary.name
        }
    })

# API لإضافة إدارة جديدة
@api.route('/departments/add', methods=['POST'])
@csrf.exempt
def add_department():
    """إضافة إدارة جديدة"""
    data = request.json
    
    if not data or not data.get('name'):
        return jsonify({'status': 'error', 'message': 'يرجى إدخال اسم الإدارة'}), 400
    
    # التحقق من عدم وجود إدارة بنفس الاسم
    existing_department = Department.query.filter_by(name=data.get('name')).first()
    if existing_department:
        return jsonify({'status': 'error', 'message': 'الإدارة موجودة بالفعل'}), 400
    
    department = Department(
        name=data.get('name')
    )
    
    db.session.add(department)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'تم إضافة الإدارة بنجاح',
        'department': {
            'id': department.id,
            'name': department.name
        }
    })

# API لإضافة قسم جديد
@api.route('/sections/add', methods=['POST'])
@csrf.exempt
def add_section():
    """إضافة قسم جديد"""
    data = request.json
    
    if not data or not data.get('name') or not data.get('department_id'):
        return jsonify({'status': 'error', 'message': 'يرجى إدخال اسم القسم والإدارة التابع لها'}), 400
    
    department_id = data.get('department_id')
    name = data.get('name')
    
    # التحقق من وجود الإدارة
    department = Department.query.get(department_id)
    if not department:
        return jsonify({'status': 'error', 'message': 'الإدارة غير موجودة'}), 404
    
    # التحقق من عدم وجود قسم بنفس الاسم في نفس الإدارة
    existing_section = Section.query.filter_by(name=name, department_id=department_id).first()
    if existing_section:
        return jsonify({'status': 'error', 'message': 'القسم موجود بالفعل في هذه الإدارة'}), 400
    
    section = Section(
        name=name,
        department_id=department_id
    )
    
    db.session.add(section)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'تم إضافة القسم بنجاح',
        'section': {
            'id': section.id,
            'name': section.name
        }
    })

# API لإضافة تصنيف جديد
@api.route('/categories/add', methods=['POST'])
@csrf.exempt
def add_category():
    """إضافة تصنيف جديد"""
    data = request.json
    
    if not data or not data.get('name'):
        return jsonify({'status': 'error', 'message': 'يرجى إدخال اسم التصنيف'}), 400
    
    name = data.get('name')
    
    # التحقق من عدم وجود تصنيف بنفس الاسم
    existing_category = Category.query.filter_by(name=name).first()
    if existing_category:
        return jsonify({'status': 'error', 'message': 'التصنيف موجود بالفعل'}), 400
    
    category = Category(
        name=name
    )
    
    db.session.add(category)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'تم إضافة التصنيف بنجاح',
        'category': {
            'id': category.id,
            'name': category.name
        }
    })

# API لإضافة تصنيف فرعي جديد
@api.route('/subcategories/add', methods=['POST'])
@csrf.exempt
def add_subcategory():
    """إضافة تصنيف فرعي جديد"""
    data = request.json
    
    if not data or not data.get('name') or not data.get('category_id'):
        return jsonify({'status': 'error', 'message': 'يرجى إدخال اسم التصنيف الفرعي والتصنيف التابع له'}), 400
    
    category_id = data.get('category_id')
    name = data.get('name')
    
    # التحقق من وجود التصنيف
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'status': 'error', 'message': 'التصنيف غير موجود'}), 404
    
    # التحقق من عدم وجود تصنيف فرعي بنفس الاسم في نفس التصنيف
    existing_subcategory = SubCategory.query.filter_by(name=name, category_id=category_id).first()
    if existing_subcategory:
        return jsonify({'status': 'error', 'message': 'التصنيف الفرعي موجود بالفعل في هذا التصنيف'}), 400
    
    subcategory = SubCategory(
        name=name,
        category_id=category_id
    )
    
    db.session.add(subcategory)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'تم إضافة التصنيف الفرعي بنجاح',
        'subcategory': {
            'id': subcategory.id,
            'name': subcategory.name
        }
    })

# API لإضافة تعليق عند إرسال رسالة واتساب
@api.route('/add_whatsapp_comment', methods=['POST'])
@csrf.exempt
def add_whatsapp_comment():
    """إضافة تعليق عند إرسال رسالة واتساب"""
    data = request.json
    user_id = session.get('user_id')
    
    if not data or not data.get('ticket_id') or not data.get('tech_name') or not user_id:
        return jsonify({'status': 'error', 'message': 'بيانات غير كاملة'}), 400
    
    ticket_id = data.get('ticket_id')
    tech_name = data.get('tech_name')
    
    # التحقق من وجود البلاغ
    ticket = Ticket.query.get(ticket_id)
    if not ticket:
        return jsonify({'status': 'error', 'message': 'البلاغ غير موجود'}), 404
    
    # إنشاء تعليق جديد
    comment = Comment(
        content=f"تم إرسال تنبيه عبر واتساب إلى {tech_name} عن البلاغ.",
        ticket_id=ticket_id,
        user_id=user_id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'تم إضافة التعليق بنجاح'
    })
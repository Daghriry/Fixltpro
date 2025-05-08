"""
maintenance_routes.py - مسارات Flask لنموذج الصيانة الإلكتروني
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify, make_response
from models import db, Ticket, User, Attachment, Comment, TicketStatus
from datetime import datetime
import base64
import io
import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
from functools import wraps
import arabic_reshaper
from bidi.algorithm import get_display
from fpdf import FPDF

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

def get_current_user():
    """الحصول على المستخدم الحالي"""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def add_maintenance_routes(app):
    """
    إضافة مسارات نموذج الصيانة الإلكتروني إلى تطبيق Flask
    
    Args:
        app: تطبيق Flask
    """
    
    @app.route('/ticket/<int:ticket_id>/maintenance_form', methods=['GET'])
    @login_required()
    def electronic_maintenance_form(ticket_id):
        """عرض صفحة نموذج الصيانة الإلكتروني"""
        # التحقق من وجود البلاغ
        ticket = Ticket.query.get_or_404(ticket_id)
        current_user = get_current_user()
        
        # التحقق من صلاحية الوصول للبلاغ
        if (current_user.user_type != 'admin' and 
            current_user.id != ticket.assigned_to_id and 
            current_user.id != ticket.created_by_id):
            flash('ليس لديك صلاحية للوصول إلى هذا النموذج', 'error')
            return redirect(url_for('view_ticket', ticket_id=ticket_id))
        
        # جلب آخر تعليق من الفني المسؤول عن البلاغ
        technician_comment = None
        if ticket.assigned_to_id:
            latest_comment = Comment.query.filter_by(
                ticket_id=ticket_id,
                user_id=ticket.assigned_to_id
            ).order_by(Comment.created_at.desc()).first()
            
            if latest_comment:
                technician_comment = latest_comment.content
        
        # عرض صفحة النموذج
        return render_template('maintenance_form.html', 
                              ticket=ticket, 
                              technician_comment=technician_comment,
                              current_user=current_user)
    
    
    @app.route('/ticket/<int:ticket_id>/save_maintenance_form', methods=['POST'])
    @login_required()
    def save_maintenance_form(ticket_id):
        """حفظ نموذج الصيانة وإنشاء ملف PDF"""
        ticket = Ticket.query.get_or_404(ticket_id)
        current_user = get_current_user()
        
        # التحقق من صلاحية الوصول
        if (current_user.user_type != 'admin' and 
            current_user.id != ticket.assigned_to_id and 
            current_user.id != ticket.created_by_id):
            flash('ليس لديك صلاحية لحفظ هذا النموذج', 'error')
            return redirect(url_for('view_ticket', ticket_id=ticket_id))
        
        # استخراج البيانات من النموذج
        problem_solved = request.form.get('problem_solved') == 'yes'
        problem_reasons = request.form.get('problem_reasons', '')
        signature_data = request.form.get('signature_data', '')
        
        # الحصول على آخر تعليق من الفني المسؤول عن البلاغ
        technician_comment = None
        if ticket.assigned_to_id:
            latest_comment = Comment.query.filter_by(
                ticket_id=ticket_id,
                user_id=ticket.assigned_to_id
            ).order_by(Comment.created_at.desc()).first()
            
            if latest_comment:
                technician_comment = latest_comment.content
        
        # إنشاء ملف PDF يتضمن التوقيع
        pdf_file_path = create_maintenance_form_pdf_with_signature(
            ticket_id, 
            problem_solved, 
            problem_reasons,
            technician_comment,
            signature_data
        )
        
        # إضافة تعليق بشأن إكمال النموذج
        comment_content = "تم تعبئة نموذج الصيانة الإلكتروني. "
        if problem_solved:
            comment_content += "تم حل المشكلة بنجاح."
            
            # تحديث حالة البلاغ إلى "مكتمل" إذا تم حل المشكلة
            completed_status = TicketStatus.query.filter_by(name='مكتمل').first()
            if completed_status:
                ticket.status_id = completed_status.id
        else:
            comment_content += f"لم يتم حل المشكلة."
            if problem_reasons:
                comment_content += f" ملاحظات: {problem_reasons}"
        
        # إضافة التعليق
        comment = Comment(
            content=comment_content,
            ticket_id=ticket_id,
            user_id=current_user.id
        )
        
        db.session.add(comment)
        
        # حفظ ملف PDF كمرفق للبلاغ
        if pdf_file_path:
            attachment = Attachment(
                filename=f"نموذج صيانة - بلاغ {ticket.id}.pdf",
                file_path=pdf_file_path,
                file_type='application/pdf',
                ticket_id=ticket_id,
                user_id=current_user.id
            )
            db.session.add(attachment)
        
        # حفظ التغييرات
        db.session.commit()
        
        flash('تم حفظ نموذج الصيانة بنجاح وإرفاقه بالبلاغ', 'success')
        return redirect(url_for('view_ticket', ticket_id=ticket_id))
    

    def create_maintenance_form_pdf_with_signature(ticket_id, problem_solved, problem_reasons, technician_comment, signature_data):
        """إنشاء ملف PDF لنموذج الصيانة بتصميم متطابق مع صفحة الويب في صفحة واحدة فقط"""
        ticket = Ticket.query.get_or_404(ticket_id)
        
        # إنشاء ملف PDF جديد
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # إضافة الخطوط
        basedir = os.path.abspath(os.path.dirname(__file__))
        pdf.add_font('Arial', '', os.path.join(basedir, 'static/fonts/arial.ttf'), uni=True)
        pdf.add_font('Arial', 'B', os.path.join(basedir, 'static/fonts/arialbd.ttf'), uni=True)
        
        # دالة مساعدة للكتابة بالعربية
        def arabic_text(text, rtl=True):
            if not text:
                return ""
            if rtl:
                reshaped_text = arabic_reshaper.reshape(str(text))
                return get_display(reshaped_text)
            return str(text)
        
        # تعيين ألوان التصميم
        header_background = (24, 116, 205)  # لون أزرق للعناوين
        primary_color = (24, 116, 205)     # لون أزرق للعناصر المهمة
        text_color = (0, 0, 0)             # لون أسود للنصوص
        input_bg = (248, 248, 248)         # لون رمادي فاتح لخلفية المدخلات
        border_color = (200, 200, 200)     # لون رمادي للحدود
        success_color = (46, 139, 87)      # لون أخضر لخيار "نعم"
        danger_color = (220, 20, 60)       # لون أحمر لخيار "لا"
        
        # تحديد الهوامش للتأكد من أن كل شيء يظهر في صفحة واحدة
        pdf.set_margins(10, 10, 10)
        
        # ----- 1. ترويسة النموذج (تم تعديلها) -----
        # لا توجد خلفية زرقاء للترويسة (تم إزالتها)
        
        # رقم البلاغ في الجهة اليسرى
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(0, 0, 0)  # تم تغيير لون النص إلى الأسود
        pdf.set_xy(10, 10)
        pdf.cell(30, 8, arabic_text(f'رقم البلاغ: {ticket.id}'), 0, 0, 'L')
        
        # اسم الجهة في الجهة اليمنى
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(140, 10)
        pdf.cell(60, 6, arabic_text('المملكة العربية السعودية'), 0, 1, 'R')
        pdf.set_xy(140, 15)
        pdf.cell(60, 5, arabic_text('وزارة الداخلية'), 0, 1, 'R')
        pdf.set_font('Arial', '', 8)
        pdf.set_xy(140, 20)
        pdf.cell(60, 4, arabic_text('المديرية العامة للسجون'), 0, 1, 'R')
        pdf.set_xy(140, 24)
        pdf.cell(60, 4, arabic_text('مديرية السجون بمنطقة جازان'), 0, 1, 'R')
        pdf.set_xy(140, 28)
        pdf.cell(60, 4, arabic_text('إدارة التقنية والذكاء الإصطناعي'), 0, 1, 'R')
        pdf.set_xy(140, 32)
        pdf.cell(60, 4, arabic_text('شعبة الدعم الفني'), 0, 1, 'R')
        
        # إضافة الشعار في وسط الترويسة
        logo_path = os.path.join(basedir, 'static/images/moi_logo.png')
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=95, y=15, w=20)
        
        # عنوان النموذج أسفل الشعار
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(primary_color[0], primary_color[1], primary_color[2])  # لون أزرق للعنوان
        pdf.set_xy(60, 37)  # تم تعديل موضع العنوان ليكون أسفل الشعار
        pdf.cell(90, 10, arabic_text('نموذج طلب صيانة الدعم الفني'), 0, 0, 'C')
        
        # ----- 2. معلومات مقدم الطلب -----
        current_y = 50  # تم زيادة القيمة لإعطاء مساحة كافية بعد الترويسة
        
        # عنوان القسم
        pdf.set_fill_color(header_background[0], header_background[1], header_background[2])
        pdf.rect(10, current_y, 190, 8, 'F')
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, current_y)
        pdf.cell(190, 8, arabic_text('بيانات مقدم الطلب'), 0, 1, 'C')
        
        # باقي الكود كما هو
        # محتوى القسم
        pdf.set_text_color(text_color[0], text_color[1], text_color[2])
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(10, current_y + 8, 190, 20, 'F')
        
        # الاسم
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(160, current_y + 10)
        pdf.cell(30, 6, arabic_text('الاسم:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(20, current_y + 10)
        pdf.cell(140, 6, arabic_text(ticket.beneficiary.name if ticket.beneficiary else 'غير محدد'), 0, 0, 'R')
        
        # الإدارة/القسم
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(160, current_y + 15)
        pdf.cell(30, 6, arabic_text('الإدارة/القسم:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(20, current_y + 15)
        
        # بناء نص الإدارة/القسم
        department_section = ""
        if ticket.department:
            department_section = ticket.department.name
            if ticket.section:
                department_section += f" / {ticket.section.name}"
        else:
            department_section = "غير محدد"
        
        pdf.cell(140, 6, arabic_text(department_section), 0, 0, 'R')
        
        # رقم الجوال
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(160, current_y + 20)
        pdf.cell(30, 6, arabic_text('رقم الجوال:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(20, current_y + 20)
        beneficiary_phone = ticket.beneficiary.phone if ticket.beneficiary and ticket.beneficiary.phone else 'غير محدد'
        pdf.cell(140, 6, arabic_text(beneficiary_phone), 0, 0, 'R')
        
        # ----- 3. معلومات البلاغ -----
        current_y += 33  # بداية القسم الجديد
        
        # عنوان القسم
        pdf.set_fill_color(header_background[0], header_background[1], header_background[2])
        pdf.rect(10, current_y, 190, 8, 'F')
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, current_y)
        pdf.cell(190, 8, arabic_text('معلومات البلاغ'), 0, 1, 'C')
        
        # محتوى القسم
        pdf.set_text_color(text_color[0], text_color[1], text_color[2])
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(10, current_y + 8, 190, 20, 'F')
        
        # تاريخ البلاغ
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(160, current_y + 10)
        pdf.cell(30, 6, arabic_text('تاريخ البلاغ:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(20, current_y + 10)
        pdf.cell(140, 6, arabic_text(ticket.created_at.strftime('%Y/%m/%d')), 0, 0, 'R')
        
        # الأولوية
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(160, current_y + 15)
        pdf.cell(30, 6, arabic_text('الأولوية:'), 0, 0, 'R')
        
        # لون خلفية الأولوية حسب نوعها
        priority_name = ticket.priority.name
        if priority_name == 'عالية':
            pdf.set_fill_color(255, 200, 200)  # لون خلفية أحمر فاتح للأولوية العالية
            pdf.set_text_color(200, 0, 0)      # لون نص أحمر للأولوية العالية
        elif priority_name == 'متوسطة':
            pdf.set_fill_color(255, 235, 200)  # لون خلفية برتقالي فاتح للأولوية المتوسطة
            pdf.set_text_color(200, 100, 0)    # لون نص برتقالي للأولوية المتوسطة
        else:
            pdf.set_fill_color(200, 255, 200)  # لون خلفية أخضر فاتح للأولوية المنخفضة
            pdf.set_text_color(0, 150, 0)      # لون نص أخضر للأولوية المنخفضة
        
        # مستطيل الأولوية
        pdf.rect(120, current_y + 15, 30, 6, 'F')
        pdf.set_xy(120, current_y + 15)
        pdf.cell(30, 6, arabic_text(priority_name), 0, 0, 'C')
        
        # إعادة لون النص للون الأصلي
        pdf.set_text_color(text_color[0], text_color[1], text_color[2])
        
        # طريقة استلام البلاغ
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(160, current_y + 20)
        pdf.cell(30, 6, arabic_text('طريقة استلام البلاغ:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(20, current_y + 20)
        pdf.cell(140, 6, arabic_text(ticket.contact_method if ticket.contact_method else 'حضور شخصي'), 0, 0, 'R')
        
        # ----- 4. تصنيف العطل -----
        current_y += 33  # بداية القسم الجديد
        
        # عنوان القسم
        pdf.set_fill_color(header_background[0], header_background[1], header_background[2])
        pdf.rect(10, current_y, 190, 8, 'F')
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, current_y)
        pdf.cell(190, 8, arabic_text('تصنيف العطل'), 0, 1, 'C')
        
        # محتوى القسم
        pdf.set_text_color(text_color[0], text_color[1], text_color[2])
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(10, current_y + 8, 190, 20, 'F')
        
        # تصنيفات العطل في صفين (يمين ويسار)
        categories = [
            {'name': 'أجهزة الحاسب', 'match': 'أجهزة', 'x': 160, 'y': current_y + 12},
            {'name': 'البرمجيات', 'match': 'برمجيات', 'x': 160, 'y': current_y + 18},
            {'name': 'الشبكات', 'match': 'شبكات', 'x': 160, 'y': current_y + 24},
            {'name': 'الطابعات', 'match': 'طابعات', 'x': 80, 'y': current_y + 12},
            {'name': 'أخرى', 'match': 'أخرى', 'x': 80, 'y': current_y + 18}
        ]
        
        # رسم مربعات الاختيار والنصوص
        for category in categories:
            # مربع الاختيار
            pdf.set_draw_color(border_color[0], border_color[1], border_color[2])
            pdf.rect(category['x'] - 20, category['y'], 4, 4, 'D')
            
            # وضع علامة إذا كان التصنيف مطابق
            if ticket.category and category['match'].lower() in ticket.category.name.lower():
                pdf.set_fill_color(primary_color[0], primary_color[1], primary_color[2])
                pdf.rect(category['x'] - 20, category['y'], 4, 4, 'F')
                pdf.set_text_color(255, 255, 255)
                pdf.set_xy(category['x'] - 20, category['y'] - 0.5)
                pdf.set_font('Arial', 'B', 6)
                pdf.cell(4, 4, "✓", 0, 0, 'C')
            
            # نص التصنيف
            pdf.set_text_color(text_color[0], text_color[1], text_color[2])
            pdf.set_font('Arial', '', 10)
            pdf.set_xy(category['x'] - 25, category['y'] - 1)
            pdf.cell(60, 6, arabic_text(category['name']), 0, 0, 'R')
            
            # في حالة "أخرى"، يمكن إضافة التصنيف الفرعي
            if category['match'] == 'أخرى' and ticket.category and 'أخرى' in ticket.category.name.lower() and ticket.subcategory:
                pdf.set_xy(70, category['y'] - 1)
                pdf.cell(5, 6, arabic_text(f"({ticket.subcategory.name})"), 0, 0, 'R')
        
        # ----- 5. وصف المشكلة -----
        current_y += 30  # بداية القسم الجديد
        
        # عنوان القسم
        pdf.set_fill_color(header_background[0], header_background[1], header_background[2])
        pdf.rect(10, current_y, 190, 8, 'F')
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, current_y)
        pdf.cell(190, 8, arabic_text('وصف المشكلة'), 0, 1, 'C')
        
        # تحديد ارتفاع محتوى الوصف بشكل ديناميكي بناءً على طول النص
        description_text = ticket.description if ticket.description else "لا يوجد وصف للمشكلة"
        description_height = max(20, min(35, 5 * (len(description_text) // 80 + 1)))  # تقدير ارتفاع النص (على الأقل 20 وحد أقصى 35)
        
        # مربع محتوى الوصف (بارتفاع ديناميكي)
        pdf.set_text_color(text_color[0], text_color[1], text_color[2])
        pdf.set_fill_color(input_bg[0], input_bg[1], input_bg[2])
        pdf.rect(10, current_y + 8, 190, description_height, 'F')
        
        # نص الوصف
        pdf.set_xy(15, current_y + 10)
        pdf.set_font('Arial', '', 10)
        
        if ticket.description:
            # تقسيم النص إلى أسطر وعرضه بشكل مناسب
            pdf.multi_cell(180, 5, arabic_text(description_text), 0, 'R')
        else:
            pdf.set_text_color(150, 150, 150)
            pdf.cell(180, 10, arabic_text('لا يوجد وصف للمشكلة'), 0, 0, 'C')
        
        # ----- 6. تقرير فني الصيانة -----
        current_y += description_height + 12  # بداية القسم الجديد (بعد قسم الوصف)
        
        # عنوان القسم
        pdf.set_fill_color(header_background[0], header_background[1], header_background[2])
        pdf.rect(10, current_y, 190, 8, 'F')
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, current_y)
        pdf.cell(190, 8, arabic_text('تقرير فني الصيانة'), 0, 1, 'C')
        
        # تحديد ارتفاع محتوى التقرير بشكل ديناميكي بناءً على طول النص
        report_text = technician_comment if technician_comment else "لا يوجد تقرير فني حتى الآن"
        report_height = max(20, min(35, 5 * (len(report_text) // 80 + 1)))  # تقدير ارتفاع النص (على الأقل 20 وحد أقصى 35)
        
        # مربع محتوى التقرير (بارتفاع ديناميكي)
        pdf.set_text_color(text_color[0], text_color[1], text_color[2])
        pdf.set_fill_color(input_bg[0], input_bg[1], input_bg[2])
        pdf.rect(10, current_y + 8, 190, report_height, 'F')
        
        # نص التقرير
        pdf.set_xy(15, current_y + 10)
        pdf.set_font('Arial', '', 10)
        
        if technician_comment:
            # عرض التقرير بشكل كامل
            pdf.multi_cell(180, 5, arabic_text(report_text), 0, 'R')
        else:
            pdf.set_text_color(150, 150, 150)
            pdf.cell(180, 10, arabic_text('لا يوجد تقرير فني حتى الآن'), 0, 0, 'C')
        
        # ----- 7. نتيجة الصيانة -----
        current_y += report_height + 12  # بداية القسم الجديد (بعد قسم التقرير)
        
        # عنوان القسم
        pdf.set_fill_color(header_background[0], header_background[1], header_background[2])
        pdf.rect(10, current_y, 190, 8, 'F')
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(10, current_y)
        pdf.cell(190, 8, arabic_text('نتيجة الصيانة'), 0, 1, 'C')
        
        # محتوى نتيجة الصيانة
        pdf.set_text_color(text_color[0], text_color[1], text_color[2])
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(10, current_y + 8, 190, 18, 'F')
        
        # عنوان "هل تم حل المشكلة؟"
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(170, current_y + 12)
        pdf.cell(20, 6, arabic_text('هل تم حل المشكلة؟'), 0, 0, 'R')
        
        # مربع اختيار "نعم"
        pdf.set_draw_color(border_color[0], border_color[1], border_color[2])
        pdf.rect(140, current_y + 13, 4, 4, 'D')
        
        # ملء المربع إذا كان الاختيار "نعم"
        if problem_solved:
            pdf.set_fill_color(success_color[0], success_color[1], success_color[2])
            pdf.rect(140, current_y + 13, 4, 4, 'F')
        
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(125, current_y + 12)
        pdf.cell(15, 6, arabic_text('نعم'), 0, 0, 'R')
        
        # مربع اختيار "لا"
        pdf.rect(120, current_y + 13, 4, 4, 'D')
        
        # ملء المربع إذا كان الاختيار "لا"
        if not problem_solved:
            pdf.set_fill_color(danger_color[0], danger_color[1], danger_color[2])
            pdf.rect(120, current_y + 13, 4, 4, 'F')
        
        pdf.set_xy(105, current_y + 12)
        pdf.cell(15, 6, arabic_text('لا'), 0, 0, 'R')
        
        # إضافة الملاحظات إذا وجدت
        if problem_reasons:
            pdf.set_font('Arial', 'B', 10)
            pdf.set_xy(100, current_y + 12)
            
            if not problem_solved:
                pdf.cell(20, 6, arabic_text('سبب عدم الحل:'), 0, 0, 'R')
            else:
                pdf.cell(20, 6, arabic_text('ملاحظات:'), 0, 0, 'R')
            
            # محتوى الملاحظات
            pdf.set_font('Arial', '', 9)
            pdf.set_xy(15, current_y + 12)
            
            # تقصير النص إذا كان طويلاً
            notes = problem_reasons
            if len(notes) > 80:
                notes = notes[:77] + "..."
            
            pdf.cell(80, 6, arabic_text(notes), 0, 0, 'R')
        
        # ----- 8. قسم التوقيعات -----
        current_y += 30  # بداية القسم الجديد
        
        # رسم خط فاصل
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, current_y, 200, current_y)
        
        # توقيعات الفني ومقدم الطلب
        
        # الفني المسؤول
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(180, current_y + 4)  # تم تحريك الموضع إلى اليسار قليلاً
        pdf.cell(20, 6, arabic_text('الفني المسؤول:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(105, current_y + 4)  # تم تحريك الموضع إلى اليسار قليلاً
        pdf.cell(75, 6, arabic_text(ticket.assignee.name if ticket.assignee else '_________________'), 0, 0, 'R')
        
        # مقدم الطلب
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(100, current_y + 4)  # تم تحريك الموضع إلى اليسار قليلاً
        pdf.cell(20, 6, arabic_text('مقدم الطلب:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(20, current_y + 4)  # تم تحريك الموضع إلى اليسار قليلاً
        pdf.cell(80, 6, arabic_text(ticket.beneficiary.name if ticket.beneficiary else '_________________'), 0, 0, 'R')
        
        # التاريخ
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(180, current_y + 12)  # تم تحريك الموضع إلى اليسار قليلاً
        pdf.cell(10, 6, arabic_text('التاريخ:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(130, current_y + 12)  # تم تحريك الموضع إلى اليسار قليلاً
        current_date = datetime.now().strftime('%Y/%m/%d')
        pdf.cell(50, 6, arabic_text(current_date), 0, 0, 'R')
        
        # توقيع مقدم الطلب
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(150, current_y + 20)  # تم تحريك الموضع إلى اليسار قليلاً
        pdf.cell(30, 6, arabic_text('توقيع مقدم الطلب:'), 0, 0, 'R')
        
        # رسم مربع للتوقيع
        signature_x = 90  # تم تحريك الموضع إلى اليسار قليلاً
        signature_width = 85
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(signature_x, current_y + 25, signature_width, 15, 'D')
        
        # إضافة التوقيع إذا كان موجوداً
        if signature_data and signature_data.startswith('data:image/png;base64,'):
            try:
                # معالجة التوقيع
                signature_base64 = signature_data.replace('data:image/png;base64,', '')
                signature_bytes = base64.b64decode(signature_base64)
                
                # حفظ التوقيع بشكل مؤقت
                temp_signature_path = os.path.join(basedir, 'uploads', f'temp_signature_{uuid.uuid4()}.png')
                with open(temp_signature_path, 'wb') as temp_file:
                    temp_file.write(signature_bytes)
                
                # إضافة صورة التوقيع داخل المربع
                pdf.image(temp_signature_path, x=signature_x + 5, y=current_y + 26, w=signature_width - 10, h=13)
                
                # حذف الملف المؤقت
                os.remove(temp_signature_path)
                
            except Exception as e:
                # إذا حدث خطأ في معالجة التوقيع
                pdf.set_text_color(150, 150, 150)
                pdf.set_font('Arial', '', 9)
                pdf.set_xy(signature_x, current_y + 25)
                pdf.cell(signature_width, 6, arabic_text('لا يوجد توقيع'), 0, 0, 'C')
        else:
            # إذا لم يكن هناك توقيع
            pdf.set_text_color(150, 150, 150)
            pdf.set_font('Arial', '', 9)
            pdf.set_xy(signature_x, current_y + 25)
            pdf.cell(signature_width, 6, arabic_text('لا يوجد توقيع'), 0, 0, 'C')
        
        # إعادة لون النص الأصلي
        pdf.set_text_color(text_color[0], text_color[1], text_color[2])
        
        # ----- حفظ الملف -----
        basedir = os.path.abspath(os.path.dirname(__file__))
        pdf_folder = os.path.join(basedir, 'uploads')
        
        # التأكد من وجود المجلد
        if not os.path.exists(pdf_folder):
            os.makedirs(pdf_folder)
        
        # إنشاء اسم فريد للملف
        filename = f"maintenance_form_{ticket_id}_{uuid.uuid4().hex}.pdf"
        file_path = os.path.join(pdf_folder, filename)
        
        # حفظ الملف
        pdf.output(file_path)
        
        return file_path

    def save_signature_image(ticket_id, signature_data, user_id):
        """حفظ صورة التوقيع وإرجاع المسار"""
        try:
            # معالجة بيانات التوقيع
            signature_base64 = signature_data.replace('data:image/png;base64,', '')
            signature_bytes = base64.b64decode(signature_base64)
            
            # إنشاء اسم فريد للملف
            filename = f"signature_{ticket_id}_{uuid.uuid4().hex}.png"
            secure_name = secure_filename(filename)
            
            # المسار الكامل للملف
            basedir = os.path.abspath(os.path.dirname(__file__))
            upload_folder = os.path.join(basedir, 'uploads')
            file_path = os.path.join(upload_folder, secure_name)
            
            # التأكد من وجود مجلد التحميلات
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            # حفظ الصورة
            img = Image.open(io.BytesIO(signature_bytes))
            img.save(file_path)
            
            # إضافة المرفق إلى قاعدة البيانات
            attachment = Attachment(
                filename=f"توقيع نموذج الصيانة - بلاغ {ticket_id}",
                file_path=file_path,
                file_type='image/png',
                ticket_id=ticket_id,
                user_id=user_id,
                attachment_type='signature'  # تمييز المرفق كنوع توقيع
            )
            
            db.session.add(attachment)
            db.session.flush()  # للحصول على معرف المرفق
            
            return file_path
            
        except Exception as e:
            app.logger.error(f"خطأ في حفظ التوقيع: {str(e)}")
            return None
    
    
    def create_maintenance_pdf(ticket_id, problem_solved, problem_reasons, technician_comment=None):
        """إنشاء ملف PDF لنموذج الصيانة"""
        ticket = Ticket.query.get_or_404(ticket_id)
        
        # إنشاء ملف PDF جديد
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # إضافة الخطوط
        basedir = os.path.abspath(os.path.dirname(__file__))
        pdf.add_font('Arial', '', os.path.join(basedir, 'static/fonts/arial.ttf'), uni=True)
        pdf.add_font('Arial', 'B', os.path.join(basedir, 'static/fonts/arialbd.ttf'), uni=True)
        
        # دالة مساعدة للكتابة بالعربية
        def arabic_text(text, rtl=True):
            if not text:
                return ""
            if rtl:
                reshaped_text = arabic_reshaper.reshape(str(text))
                return get_display(reshaped_text)
            return str(text)
        
        # تحديد الألوان المستخدمة
        header_color = (0, 73, 144)  # أزرق غامق
        subheader_color = (0, 112, 192)  # أزرق فاتح
        
        # إنشاء النموذج بنفس الأسلوب القديم
        # الترويسة
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(header_color[0], header_color[1], header_color[2])
        pdf.set_xy(110, 10)
        pdf.cell(90, 6, arabic_text('المملكة العربية السعودية'), 0, 1, 'R')
        pdf.set_xy(110, 16)
        pdf.cell(90, 6, arabic_text('وزارة الداخلية'), 0, 1, 'R')
        pdf.set_xy(110, 22)
        pdf.set_font('Arial', '', 12)
        pdf.cell(90, 6, arabic_text('المديرية العامة للسجون'), 0, 1, 'R')
        pdf.set_xy(110, 28)
        pdf.cell(90, 6, arabic_text('مديرية السجون بمنطقة جازان'), 0, 1, 'R')
        
        # الشعار
        logo_path = os.path.join(basedir, 'static/images/moi_logo.png')
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=85, y=10, w=30)
        
        # رقم البلاغ والتاريخ
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(10, 15)
        pdf.cell(60, 6, arabic_text(f'رقم البلاغ: {ticket.id}'), 0, 1, 'L')
        
        current_date = datetime.now().strftime('%Y/%m/%d')
        pdf.set_xy(10, 25)
        pdf.cell(60, 6, arabic_text(f'التاريخ: {current_date}'), 0, 1, 'L')
        
        # عنوان النموذج
        pdf.set_y(45)
        pdf.set_font('Arial', 'B', 18)
        pdf.set_text_color(header_color[0], header_color[1], header_color[2])
        pdf.cell(0, 10, arabic_text('نموذج طلب صيانة الدعم الفني'), 0, 1, 'C')
        
        # توحيد حجم خط رؤوس الجداول
        header_font_size = 12
        
        # معلومات مقدم الطلب
        pdf.set_y(60)
        pdf.set_fill_color(header_color[0], header_color[1], header_color[2])
        pdf.set_text_color(255, 255, 255)
        pdf.rect(10, pdf.get_y(), 190, 8, 'F')
        pdf.set_font('Arial', 'B', header_font_size)
        pdf.cell(190, 8, arabic_text('بيانات مقدم الطلب'), 0, 1, 'C')
        
        # إعادة تعيين لون النص
        pdf.set_text_color(0, 0, 0)
        
        # إطار معلومات مقدم الطلب
        y_position = pdf.get_y()
        pdf.rect(10, y_position, 190, 25)
        
        # معلومات مقدم الطلب
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(150, y_position + 2)
        pdf.cell(40, 6, arabic_text('الاسم:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(10, y_position + 2)
        pdf.cell(140, 6, arabic_text(ticket.beneficiary.name if ticket.beneficiary else '______________________'), 0, 1, 'R')
        
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(150, y_position + 10)
        pdf.cell(40, 6, arabic_text('الإدارة/القسم:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(10, y_position + 10)
        department_name = ticket.department.name if ticket.department else '_____________'
        section_name = ticket.section.name if ticket.section else '_____________'
        pdf.cell(140, 6, arabic_text(f'{department_name} / {section_name}'), 0, 1, 'R')
        
        pdf.set_font('Arial', 'B', 10)
        pdf.set_xy(150, y_position + 18)
        pdf.cell(40, 6, arabic_text('رقم الجوال:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(10, y_position + 18)
        
        beneficiary_phone = ticket.beneficiary.phone if ticket.beneficiary and ticket.beneficiary.phone else '______________________'
        pdf.cell(140, 6, arabic_text(beneficiary_phone), 0, 1, 'R')
        
        # طريقة استلام البلاغ - بالأسلوب القديم
        pdf.set_y(pdf.get_y() + 2)
        pdf.set_fill_color(header_color[0], header_color[1], header_color[2])
        pdf.set_text_color(255, 255, 255)
        pdf.rect(10, pdf.get_y(), 190, 8, 'F')
        pdf.set_font('Arial', 'B', header_font_size)
        pdf.cell(190, 8, arabic_text('طريقة استلام البلاغ'), 0, 1, 'C')
        
        # إعادة تعيين لون النص
        pdf.set_text_color(0, 0, 0)
        
        # إطار طريقة الاستلام
        y_position = pdf.get_y()
        pdf.rect(10, y_position, 190, 12)
        
        # خيارات طريقة استلام البلاغ
        options = ['حضور شخصي', 'البريد الإلكتروني', 'واتساب', 'الاتصال']
        
        # تحديد طريقة الاستلام
        selected_method = ticket.contact_method if ticket.contact_method else None
        
        # تقسيم الخيارات
        right_options = options[:2]
        option_width = 95
        
        for i, option in enumerate(right_options):
            x_pos = 105
            text_x = x_pos + (i * option_width/2)
            
            # مربع الاختيار
            checkbox_x = text_x + 70
            pdf.set_xy(checkbox_x, y_position + 4)
            pdf.rect(checkbox_x, y_position + 4, 4, 4, 'D')
            
            # إذا كانت هذه الطريقة هي المحددة، ضع علامة X
            if selected_method == option:
                pdf.set_xy(checkbox_x, y_position + 4)
                pdf.cell(4, 4, 'X', 0, 0, 'C')
            
            # نص الخيار
            pdf.set_xy(text_x, y_position + 3)
            pdf.set_font('Arial', '', 10)
            pdf.cell(option_width/2 - 5, 6, arabic_text(option), 0, 0, 'R')
        
        # الجانب الأيسر
        left_options = options[2:]
        
        for i, option in enumerate(left_options):
            x_pos = 10
            text_x = x_pos + (i * option_width/2)
            
            # مربع الاختيار
            checkbox_x = text_x + 70
            pdf.set_xy(checkbox_x, y_position + 4)
            pdf.rect(checkbox_x, y_position + 4, 4, 4, 'D')
            
            # إذا كانت هذه الطريقة هي المحددة، ضع علامة X
            if selected_method == option:
                pdf.set_xy(checkbox_x, y_position + 4)
                pdf.cell(4, 4, 'X', 0, 0, 'C')
            
            # نص الخيار
            pdf.set_xy(text_x, y_position + 3)
            pdf.set_font('Arial', '', 10)
            pdf.cell(option_width/2 - 5, 6, arabic_text(option), 0, 0, 'R')
        
        pdf.ln(12)
        
        # تصنيف العطل
        pdf.set_y(pdf.get_y() + 2)
        pdf.set_fill_color(header_color[0], header_color[1], header_color[2])
        pdf.set_text_color(255, 255, 255)
        pdf.rect(10, pdf.get_y(), 190, 8, 'F')
        pdf.set_font('Arial', 'B', header_font_size)
        pdf.cell(190, 8, arabic_text('تصنيف العطل'), 0, 1, 'C')
        
        # إعادة تعيين لون النص
        pdf.set_text_color(0, 0, 0)
        
        # إطار تصنيفات العطل
        y_position = pdf.get_y()
        pdf.rect(10, y_position, 190, 35)
        
        # تقسيم التصنيفات
        right_categories = [
            {'name': 'أجهزة الحاسب', 'match': 'أجهزة'},
            {'name': 'البرمجيات', 'match': 'برمجيات'},
            {'name': 'الشبكات', 'match': 'شبكات'}
        ]
        
        left_categories = [
            {'name': 'الطابعات', 'match': 'طابعات'},
            {'name': 'أخرى ..............................', 'match': 'أخرى'}
        ]
        
        # رسم العمود الأيمن
        for i, category in enumerate(right_categories):
            y_offset = y_position + (i * 10) + 5
            
            # نص التصنيف
            pdf.set_xy(110, y_offset)
            pdf.set_font('Arial', '', 10)
            pdf.cell(80, 6, arabic_text(category['name']), 0, 0, 'R')
            
            # مربع الاختيار
            checkbox_x = 190
            pdf.set_xy(190, y_offset)
            pdf.rect(190, y_offset, 4, 4, 'D')
            
            # تحديد إذا كان يجب وضع علامة
            checked = False
            if ticket.category:
                category_lower = ticket.category.name.lower()
                checked = category['match'] in category_lower
            
            if checked:
                pdf.set_xy(190, y_offset)
                pdf.cell(4, 4, 'X', 0, 0, 'C')
        
        # رسم العمود الأيسر
        for i, category in enumerate(left_categories):
            y_offset = y_position + (i * 10) + 5
            
            # نص التصنيف
            pdf.set_xy(10, y_offset)
            pdf.set_font('Arial', '', 10)
            pdf.cell(80, 6, arabic_text(category['name']), 0, 0, 'R')
            
            # مربع الاختيار
            checkbox_x = 90
            pdf.set_xy(90, y_offset)
            pdf.rect(90, y_offset, 4, 4, 'D')
            
            # تحديد إذا كان يجب وضع علامة
            checked = False
            if ticket.category:
                category_lower = ticket.category.name.lower()
                checked = category['match'] in category_lower
            
            if checked:
                pdf.set_xy(90, y_offset)
                pdf.cell(4, 4, 'X', 0, 0, 'C')
        
        # وصف المشكلة
        section_height = 30
        
        pdf.set_y(y_position + 40)
        pdf.set_fill_color(header_color[0], header_color[1], header_color[2])
        pdf.set_text_color(255, 255, 255)
        pdf.rect(10, pdf.get_y(), 190, 8, 'F')
        pdf.set_font('Arial', 'B', header_font_size)
        pdf.cell(190, 8, arabic_text('وصف المشكلة'), 0, 1, 'C')
        
        # إعادة تعيين لون النص
        pdf.set_text_color(0, 0, 0)
        
        # مربع وصف المشكلة
        y_position = pdf.get_y()
        pdf.rect(10, y_position, 190, section_height, 'D')
        
        # إضافة وصف المشكلة
        pdf.set_xy(15, y_position + 3)
        pdf.set_font('Arial', '', 10)
        
        # تقسيم الوصف إلى أسطر
        description_lines = ticket.description.split('\n')
        for line in description_lines[:5]:
            pdf.multi_cell(180, 5, arabic_text(line), 0, 'R')
        
        # تقرير الفني
        pdf.set_y(y_position + section_height + 5)
        pdf.set_fill_color(subheader_color[0], subheader_color[1], subheader_color[2])
        pdf.set_text_color(255, 255, 255)
        pdf.rect(10, pdf.get_y(), 190, 8, 'F')
        pdf.set_font('Arial', 'B', header_font_size)
        pdf.cell(190, 8, arabic_text('تقرير فني الصيانة'), 0, 1, 'C')
        
        # إعادة تعيين لون النص
        pdf.set_text_color(0, 0, 0)
        
        # مربع تقرير الفني
        y_position = pdf.get_y()
        pdf.rect(10, y_position, 190, section_height, 'D')
        
        # إضافة تقرير الفني
        pdf.set_xy(15, y_position + 3)
        pdf.set_font('Arial', '', 10)
        
        # إذا لم يتم تمرير تعليق، ابحث عن أحدث تعليق من الفني
        if not technician_comment and ticket.assigned_to_id:
            latest_comment = Comment.query.filter_by(
                ticket_id=ticket.id,
                user_id=ticket.assigned_to_id
            ).order_by(Comment.created_at.desc()).first()
            
            if latest_comment:
                technician_comment = latest_comment.content
        
        if technician_comment:
            # تقسيم التعليق إلى أسطر
            comment_lines = technician_comment.split('\n')
            for line in comment_lines[:5]:
                pdf.multi_cell(180, 5, arabic_text(line), 0, 'R')
        else:
            pdf.multi_cell(180, 5, arabic_text("لا يوجد تقرير حتى الآن"), 0, 'R')
        
        # نتيجة الصيانة
        pdf.set_y(y_position + section_height + 5)
        pdf.set_fill_color(header_color[0], header_color[1], header_color[2])
        pdf.set_text_color(255, 255, 255)
        pdf.rect(10, pdf.get_y(), 190, 8, 'F')
        pdf.set_font('Arial', 'B', header_font_size)
        pdf.cell(190, 8, arabic_text('نتيجة الصيانة'), 0, 1, 'C')
        
        # إعادة تعيين لون النص
        pdf.set_text_color(0, 0, 0)
        
        # مربع نتيجة الصيانة
        y_position = pdf.get_y()
        pdf.rect(10, y_position, 190, 20, 'D')
        
        # هل تم حل المشكلة
        pdf.set_xy(150, y_position + 8)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, 6, arabic_text('هل تم حل المشكلة؟'), 0, 0, 'R')
        
        # خيار نعم
        pdf.set_xy(120, y_position + 8)
        pdf.rect(120, y_position + 8, 4, 4, 'D')
        pdf.set_xy(100, y_position + 8)
        pdf.set_font('Arial', '', 10)
        pdf.cell(20, 6, arabic_text('نعم'), 0, 0, 'R')
        
        # وضع علامة X إذا تم حل المشكلة
        if problem_solved:
            pdf.set_xy(120, y_position + 8)
            pdf.cell(4, 4, 'X', 0, 0, 'C')
        
        # خيار لا
        pdf.set_xy(80, y_position + 8)
        pdf.rect(80, y_position + 8, 4, 4, 'D')
        pdf.set_xy(60, y_position + 8)
        pdf.set_font('Arial', '', 10)
        pdf.cell(20, 6, arabic_text('لا'), 0, 0, 'R')
        
        # وضع علامة X إذا لم يتم حل المشكلة
        if not problem_solved:
            pdf.set_xy(80, y_position + 8)
            pdf.cell(4, 4, 'X', 0, 0, 'C')
        
        # إضافة الأسباب إذا لم يتم حل المشكلة
        if not problem_solved and problem_reasons:
            pdf.set_xy(30, y_position + 8)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(30, 6, arabic_text('الأسباب:'), 0, 0, 'R')
            
            pdf.set_xy(15, y_position + 14)
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(180, 5, arabic_text(problem_reasons), 0, 'R')
        
        # التوقيعات
        y_position = pdf.get_y() + 10
        
        # توقيع الفني
        pdf.set_xy(150, y_position)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, 6, arabic_text('اسم الفني:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(10, y_position)
        pdf.cell(140, 6, arabic_text(ticket.assignee.name if ticket.assignee else '_________________'), 0, 1, 'R')
        
        # توقيع مقدم الطلب
        pdf.set_xy(150, y_position + 10)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, 6, arabic_text('اسم مقدم الطلب:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(10, y_position + 10)
        pdf.cell(140, 6, arabic_text(ticket.beneficiary.name if ticket.beneficiary else '_________________'), 0, 1, 'R')
        
        # توقيع مقدم الطلب
        pdf.set_xy(150, y_position + 20)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, 6, arabic_text('توقيع مقدم الطلب:'), 0, 0, 'R')
        pdf.set_font('Arial', '', 10)
        pdf.set_xy(10, y_position + 20)
        pdf.cell(140, 6, arabic_text('_________________________'), 0, 1, 'R')
        
        # حفظ الملف
        basedir = os.path.abspath(os.path.dirname(__file__))
        pdf_folder = os.path.join(basedir, 'uploads')
        
        # التأكد من وجود المجلد
        if not os.path.exists(pdf_folder):
            os.makedirs(pdf_folder)
        
        # إنشاء اسم فريد للملف
        filename = f"maintenance_form_{ticket_id}_{uuid.uuid4().hex}.pdf"
        file_path = os.path.join(pdf_folder, filename)
        
        # حفظ الملف
        pdf.output(file_path)
        
        return file_path
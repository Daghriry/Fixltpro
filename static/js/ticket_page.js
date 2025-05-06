/**
 * ticket_page.js
 * سكربت لإدارة صفحة عرض البلاغات في نظام Fixltpro
 */

// بيانات البلاغ التي سيتم استخدامها عالميًا في الصفحة
var TICKET_DATA = {
    id: 0,
    title: "",
    category: "",
    priority: "",
    beneficiary: "",
    department: "",
    description: "",
    contact_method: ""
};

document.addEventListener('DOMContentLoaded', function() {
    // قراءة بيانات البلاغ من سمات البيانات في HTML
    var ticketContainer = document.getElementById('ticketContainer');
    if (ticketContainer) {
        TICKET_DATA = {
            id: ticketContainer.getAttribute('data-ticket-id'),
            title: ticketContainer.getAttribute('data-ticket-title'),
            category: ticketContainer.getAttribute('data-ticket-category'),
            priority: ticketContainer.getAttribute('data-ticket-priority'),
            beneficiary: ticketContainer.getAttribute('data-ticket-beneficiary'),
            department: ticketContainer.getAttribute('data-ticket-department'),
            description: ticketContainer.getAttribute('data-ticket-description'),
            contact_method: ticketContainer.getAttribute('data-ticket-contact-method')
        };
    }
    
    // وظيفة إرسال واتساب للفني
    function sendWhatsappNotification(phone, techName) {
        if (!phone) {
            alert('لا يوجد رقم هاتف مسجل لهذا الفني.');
            return;
        }
        
        // تنسيق رقم الهاتف
        var cleanPhone = phone.replace(/\D/g, '');
        if (cleanPhone.startsWith('0')) {
            cleanPhone = '966' + cleanPhone.substring(1);
        }
        if (!cleanPhone.startsWith('966')) {
            cleanPhone = '966' + cleanPhone;
        }
        
        // بناء نص الرسالة
        var message = "بلاغ رقم: " + TICKET_DATA.id + "\n";
        message += "العنوان: " + TICKET_DATA.title + "\n";
        message += "التصنيف: " + TICKET_DATA.category + "\n";
        message += "الأولوية: " + TICKET_DATA.priority + "\n";
        message += "المستفيد: " + TICKET_DATA.beneficiary + "\n";
        message += "الإدارة: " + TICKET_DATA.department + "\n";
        if (TICKET_DATA.contact_method) {
            message += "طريقة الاستلام: " + TICKET_DATA.contact_method + "\n";
        }
        message += "وصف المشكلة: ";
        
        // اختصار الوصف إذا كان طويلاً
        if (TICKET_DATA.description.length > 100) {
            message += TICKET_DATA.description.substring(0, 100) + "...";
        } else {
            message += TICKET_DATA.description;
        }
        message += "\nالرجاء مراجعة البلاغ في نظام Fixltpro في أقرب وقت.";
        
        var encodedMessage = encodeURIComponent(message);
        
        // إظهار رسالة تأكيد
        if (confirm("هل تريد إرسال تنبيه عبر واتساب للفني " + techName + "؟")) {
            window.open("https://wa.me/" + cleanPhone + "?text=" + encodedMessage, "_blank");
            
            // إرسال طلب إضافة تعليق تلقائي
            addWhatsappComment(techName);
        }
    }
    
    // إضافة تعليق تلقائي عند إرسال تنبيه واتساب
    function addWhatsappComment(techName) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/add_whatsapp_comment', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xhr.setRequestHeader('X-CSRFToken', document.querySelector('input[name="csrf_token"]').value);
        
        xhr.onload = function() {
            if (xhr.status === 200) {
                var data = JSON.parse(xhr.responseText);
                if (data.status === 'success') {
                    // إعادة تحميل الصفحة لعرض التعليق الجديد
                    location.reload();
                } else {
                    console.error('فشلت عملية إضافة تعليق واتساب:', data.message);
                }
            } else {
                console.error('حدث خطأ أثناء إرسال الطلب:', xhr.statusText);
            }
        };
        
        xhr.onerror = function() {
            console.error('حدث خطأ في الاتصال بالخادم');
        };
        
        xhr.send(JSON.stringify({
            ticket_id: TICKET_DATA.id,
            tech_name: techName
        }));
    }
    
    // زر إرسال واتساب للفني في قائمة التعيين
    var sendWhatsappToTechBtn = document.getElementById('sendWhatsappToTech');
    var maintenanceIdSelect = document.getElementById('maintenance_id');
    
    if (sendWhatsappToTechBtn && maintenanceIdSelect) {
        sendWhatsappToTechBtn.addEventListener('click', function() {
            if (maintenanceIdSelect.value) {
                var selectedOption = maintenanceIdSelect.options[maintenanceIdSelect.selectedIndex];
                var phone = selectedOption.getAttribute('data-phone');
                var techName = selectedOption.textContent;
                
                sendWhatsappNotification(phone, techName);
            } else {
                alert('يرجى اختيار فني أولاً.');
            }
        });
    }
    
    // زر إرسال واتساب مباشرة للفني المسؤول
    var sendDirectWhatsappBtn = document.getElementById('sendDirectWhatsappBtn');
    
    if (sendDirectWhatsappBtn) {
        sendDirectWhatsappBtn.addEventListener('click', function() {
            var phone = this.getAttribute('data-phone');
            var techName = this.getAttribute('data-name');
            
            sendWhatsappNotification(phone, techName);
        });
    }
    
    // التعامل مع تغيير الأولوية في نموذج التعديل
    var editPrioritySelect = document.getElementById('edit_priority_id');
    var editCustomPriorityContainer = document.getElementById('edit_custom_priority_container');
    
    if (editPrioritySelect && editCustomPriorityContainer) {
        editPrioritySelect.addEventListener('change', function() {
            if (this.value === "0") {
                editCustomPriorityContainer.classList.add('visible');
            } else {
                editCustomPriorityContainer.classList.remove('visible');
            }
        });
        
        // التحقق من الحالة الأولية
        if (editPrioritySelect.value === "0") {
            editCustomPriorityContainer.classList.add('visible');
        }
    }
    
    // تحديث نافذة حذف المرفق بمعلومات المرفق المحدد
    var deleteAttachmentModal = document.getElementById('deleteAttachmentModal');
    if (deleteAttachmentModal) {
        deleteAttachmentModal.addEventListener('show.bs.modal', function(event) {
            var button = event.relatedTarget;
            var attachmentId = button.getAttribute('data-attachment-id');
            var attachmentName = button.getAttribute('data-attachment-name');
            
            var attachmentToDeleteSpan = document.getElementById('attachmentToDelete');
            if (attachmentToDeleteSpan) {
                attachmentToDeleteSpan.textContent = attachmentName;
            }
            
            var form = document.getElementById('deleteAttachmentForm');
            if (form) {
                form.action = "/attachment/" + attachmentId + "/delete";
            }
        });
    }
    
    // تحديث الأقسام عند تغيير الإدارة في نموذج التعديل
    var editDepartmentSelect = document.getElementById('edit_department_id');
    var editSectionSelect = document.getElementById('edit_section_id');
    
    if (editDepartmentSelect && editSectionSelect) {
        editDepartmentSelect.addEventListener('change', function() {
            var departmentId = this.value;
            
            if (departmentId) {
                // تفعيل قائمة الأقسام
                editSectionSelect.disabled = false;
                
                // جلب الأقسام من الخادم
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/api/sections/' + departmentId, true);
                
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        var data = JSON.parse(xhr.responseText);
                        
                        // مسح الخيارات الحالية
                        editSectionSelect.innerHTML = '<option value="">-- اختر القسم --</option>';
                        
                        if (data.sections && data.sections.length > 0) {
                            // إضافة الأقسام إلى القائمة
                            data.sections.forEach(function(section) {
                                var option = document.createElement('option');
                                option.value = section.id;
                                option.textContent = section.name;
                                editSectionSelect.appendChild(option);
                            });
                        }
                    } else {
                        console.error('حدث خطأ أثناء جلب الأقسام:', xhr.statusText);
                    }
                };
                
                xhr.onerror = function() {
                    console.error('حدث خطأ في الاتصال بالخادم');
                };
                
                xhr.send();
            } else {
                // تعطيل قائمة الأقسام وإفراغها
                editSectionSelect.disabled = true;
                editSectionSelect.innerHTML = '<option value="">-- اختر القسم --</option>';
            }
        });
    }
    
    // تحديث التصنيفات الفرعية عند تغيير التصنيف في نموذج التعديل
    var editCategorySelect = document.getElementById('edit_category_id');
    var editSubcategorySelect = document.getElementById('edit_subcategory_id');
    
    if (editCategorySelect && editSubcategorySelect) {
        editCategorySelect.addEventListener('change', function() {
            var categoryId = this.value;
            
            if (categoryId) {
                // تفعيل قائمة التصنيفات الفرعية
                editSubcategorySelect.disabled = false;
                
                // جلب التصنيفات الفرعية من الخادم
                var xhr = new XMLHttpRequest();
                xhr.open('GET', '/api/subcategories/' + categoryId, true);
                
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        var data = JSON.parse(xhr.responseText);
                        
                        // مسح الخيارات الحالية
                        editSubcategorySelect.innerHTML = '<option value="">-- اختر التصنيف الفرعي --</option>';
                        
                        if (data.subcategories && data.subcategories.length > 0) {
                            // إضافة التصنيفات الفرعية إلى القائمة
                            data.subcategories.forEach(function(subcategory) {
                                var option = document.createElement('option');
                                option.value = subcategory.id;
                                option.textContent = subcategory.name;
                                editSubcategorySelect.appendChild(option);
                            });
                        }
                    } else {
                        console.error('حدث خطأ أثناء جلب التصنيفات الفرعية:', xhr.statusText);
                    }
                };
                
                xhr.onerror = function() {
                    console.error('حدث خطأ في الاتصال بالخادم');
                };
                
                xhr.send();
            } else {
                // تعطيل قائمة التصنيفات الفرعية وإفراغها
                editSubcategorySelect.disabled = true;
                editSubcategorySelect.innerHTML = '<option value="">-- اختر التصنيف الفرعي --</option>';
            }
        });
    }
    
    // معالجة النموذج عند التقديم
    var editTicketForm = document.getElementById('editTicketForm');
    
    if (editTicketForm) {
        editTicketForm.addEventListener('submit', function(event) {
            // التحقق من وجود تصنيف قبل التقديم
            var categorySelect = document.getElementById('edit_category_id');
            if (!categorySelect.value) {
                event.preventDefault();
                alert('يرجى اختيار التصنيف قبل حفظ التغييرات.');
                return false;
            }
            
            // إضافة سمة للنموذج لتوضيح أن التعديل مكتمل
            this.setAttribute('data-submitted', 'true');
            
            return true;
        });
    }
    
    // التعامل مع نقر روابط المرفقات
    var attachmentLinks = document.querySelectorAll('.ticket-attachments-table a[target="_blank"]');
    
    if (attachmentLinks.length > 0) {
        attachmentLinks.forEach(function(link) {
            link.addEventListener('click', function(event) {
                // سجل نقرة على المرفق في سجل الأحداث (اختياري)
                console.log('تم النقر على المرفق:', this.href);
                
                // استمر بفتح الرابط في نافذة جديدة
                return true;
            });
        });
    }
    
    // ============ وظائف مساعدة إضافية ============
    
    // مراقبة توقيت الموعد النهائي وتحديثه
    function updateDueDateStatus() {
        var dueDateElements = document.querySelectorAll('.ticket-due-date');
        
        if (dueDateElements.length > 0) {
            dueDateElements.forEach(function(element) {
                var dateText = element.textContent.trim();
                if (dateText) {
                    var dueDate = new Date(dateText);
                    var now = new Date();
                    
                    if (dueDate < now && !element.querySelector('.badge.bg-danger')) {
                        // إذا كان الموعد النهائي قد مر ولم تكن هناك علامة "متأخر" بالفعل
                        var badge = document.createElement('span');
                        badge.className = 'badge bg-danger ms-2';
                        badge.textContent = 'متأخر';
                        element.appendChild(badge);
                    }
                }
            });
        }
    }
    
    // استدعاء التحديث أول مرة
    updateDueDateStatus();
    
    // تحديث كل دقيقة للتحقق من تغير الحالة
    setInterval(updateDueDateStatus, 60000);
    
    // تعامل مع التعليقات الطويلة وطيها
    function initializeCommentCollapsing() {
        var commentContents = document.querySelectorAll('.card-ticket-comments .list-group-item div:nth-child(2)');
        
        if (commentContents.length > 0) {
            commentContents.forEach(function(content) {
                if (content.clientHeight > 200) {
                    content.style.maxHeight = '200px';
                    content.style.overflow = 'hidden';
                    content.style.position = 'relative';
                    
                    var overlay = document.createElement('div');
                    overlay.className = 'comment-overlay';
                    overlay.style.position = 'absolute';
                    overlay.style.bottom = '0';
                    overlay.style.left = '0';
                    overlay.style.right = '0';
                    overlay.style.textAlign = 'center';
                    overlay.style.padding = '20px 0 5px 0';
                    overlay.style.background = 'linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1))';
                    
                    var showMoreBtn = document.createElement('button');
                    showMoreBtn.className = 'btn btn-sm btn-link';
                    showMoreBtn.textContent = 'عرض المزيد';
                    showMoreBtn.style.textDecoration = 'none';
                    
                    overlay.appendChild(showMoreBtn);
                    content.parentNode.appendChild(overlay);
                    
                    showMoreBtn.addEventListener('click', function() {
                        if (content.style.maxHeight === '200px') {
                            content.style.maxHeight = 'none';
                            this.textContent = 'عرض أقل';
                            overlay.style.background = 'none';
                            overlay.style.position = 'static';
                        } else {
                            content.style.maxHeight = '200px';
                            this.textContent = 'عرض المزيد';
                            overlay.style.background = 'linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1))';
                            overlay.style.position = 'absolute';
                        }
                    });
                }
            });
        }
    }
    
    // تهيئة طي التعليقات (اختياري)
    // initializeCommentCollapsing();
    
    // معالجة خاصة للجوال
    function setupMobileView() {
        if (window.innerWidth < 768) {
            // تصغير حجم الخط في جداول المعلومات
            var infoTables = document.querySelectorAll('.ticket-info-table');
            if (infoTables.length > 0) {
                infoTables.forEach(function(table) {
                    table.classList.add('small');
                });
            }
            
            // تحسين عرض جدول المرفقات
            var attachmentTables = document.querySelectorAll('.ticket-attachments-table');
            if (attachmentTables.length > 0) {
                // إخفاء بعض الأعمدة للشاشات الصغيرة
                var hideColumns = [2, 3]; // أعمدة المستخدم وتاريخ الرفع
                
                attachmentTables.forEach(function(table) {
                    var headers = table.querySelectorAll('th');
                    var rows = table.querySelectorAll('tbody tr');
                    
                    hideColumns.forEach(function(colIndex) {
                        if (headers[colIndex]) {
                            headers[colIndex].style.display = 'none';
                        }
                        
                        rows.forEach(function(row) {
                            var cells = row.querySelectorAll('td');
                            if (cells[colIndex]) {
                                cells[colIndex].style.display = 'none';
                            }
                        });
                    });
                });
            }
        }
    }
    
    // تنفيذ التحسينات للجوال عند تحميل الصفحة
    // setupMobileView();
    
    // معالجة تغيير حجم النافذة
    window.addEventListener('resize', function() {
        // setupMobileView();
    });
});
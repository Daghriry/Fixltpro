/**
 * create_ticket.js
 * سكربت لإدارة صفحة إنشاء البلاغات في نظام Fixltpro
 */

document.addEventListener('DOMContentLoaded', function() {
    // تعريف المتغيرات الرئيسية
    const contactMethodRadios = document.querySelectorAll('input[name="contact_method"]');
    const contactMethodOptions = document.querySelectorAll('.contact-method-option');
    const prioritySelect = document.getElementById('priority_id');
    const customPriorityContainer = document.getElementById('custom_priority_container');
    const customPrioritySelect = document.getElementById('custom_priority');
    const maintenanceContainer = document.getElementById('maintenance_container');
    const beneficiaryNameInput = document.getElementById('beneficiary_name');
    const beneficiaryIdInput = document.getElementById('beneficiary_id');
    const departmentSelect = document.getElementById('department_id');
    const sectionSelect = document.getElementById('section_id');
    const addSectionBtn = document.getElementById('addSectionBtn');
    const categorySelect = document.getElementById('category_id');
    const subcategorySelect = document.getElementById('subcategory_id');
    const addSubcategoryBtn = document.getElementById('addSubcategoryBtn');
    const assignedToSelect = document.getElementById('assigned_to_id');
    const sendWhatsappBtn = document.getElementById('sendWhatsappBtn');
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
    const fileInput = document.getElementById('attachments');
    const previewContainer = document.querySelector('.preview-container');
    const previewDiv = document.getElementById('attachments-preview');

    // --- تهيئة طريقة استلام البلاغ ---
    if (contactMethodOptions.length > 0) {
        // تفعيل الخيار الأول افتراضيًا
        contactMethodOptions[0].classList.add('active');
        
        // إضافة استماع أحداث لكل خيار
        contactMethodOptions.forEach(option => {
            option.addEventListener('click', function() {
                // إزالة الفئة النشطة من جميع الخيارات
                contactMethodOptions.forEach(opt => opt.classList.remove('active'));
                
                // إضافة الفئة النشطة للخيار المحدد
                this.classList.add('active');
                
                // تحديد زر الراديو المقابل
                const radio = this.querySelector('input[type="radio"]');
                if (radio) {
                    radio.checked = true;
                }
            });
        });
        
        // تحديث حالة الخيارات عند تغيير أزرار الراديو
        contactMethodRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                contactMethodOptions.forEach(opt => {
                    const optionRadio = opt.querySelector('input[type="radio"]');
                    if (optionRadio === this) {
                        opt.classList.add('active');
                    } else {
                        opt.classList.remove('active');
                    }
                });
            });
        });
    }

    // --- التعامل مع الأولوية المخصصة ---
    function toggleCustomPriority() {
        if (prioritySelect && customPriorityContainer && customPrioritySelect && maintenanceContainer) {
            if (prioritySelect.value === "0") {
                customPriorityContainer.style.display = "block";
                customPrioritySelect.setAttribute('required', 'required');
                maintenanceContainer.className = "col-md-6 mt-3";
            } else {
                customPriorityContainer.style.display = "none";
                customPrioritySelect.removeAttribute('required');
                maintenanceContainer.className = "col-md-6";
            }
        }
    }
    
    // تطبيق التغييرات عند تغيير الأولوية
    if (prioritySelect) {
        prioritySelect.addEventListener('change', toggleCustomPriority);
        // التطبيق الأولي عند تحميل الصفحة
        toggleCustomPriority();
    }

    // --- تهيئة البحث التلقائي للمستفيدين ---
    if (typeof $.fn.autocomplete !== 'undefined' && beneficiaryNameInput) {
        console.log('تهيئة وظيفة البحث التلقائي للمستفيدين');
        
        $(beneficiaryNameInput).autocomplete({
            source: function(request, response) {
                // إضافة مؤشر تحميل
                $(beneficiaryNameInput).addClass("loading");
                
                $.ajax({
                    url: "/api/beneficiaries/search",
                    dataType: "json",
                    data: {
                        term: request.term
                    },
                    success: function(data) {
                        // إزالة مؤشر التحميل
                        $(beneficiaryNameInput).removeClass("loading");
                        console.log("تم استلام البيانات:", data);
                        
                        // التحقق من تنسيق البيانات
                        if (Array.isArray(data)) {
                            response(data);
                        } else {
                            console.error("تنسيق البيانات غير صحيح:", data);
                            response([]);
                        }
                    },
                    error: function(xhr, status, error) {
                        // إزالة مؤشر التحميل
                        $(beneficiaryNameInput).removeClass("loading");
                        console.error("خطأ في طلب البحث:", error);
                        response([]);
                    }
                });
            },
            minLength: 2,
            select: function(event, ui) {
                console.log("تم اختيار مستفيد:", ui.item);
                beneficiaryIdInput.value = ui.item.id;
                return true;
            }
        });
        
        // مسح معرف المستفيد عند تغيير النص
        beneficiaryNameInput.addEventListener('input', function() {
            if (this.value === '') {
                beneficiaryIdInput.value = '';
            }
        });
    } else {
        console.warn('مكتبة jQuery UI Autocomplete غير متوفرة أو حقل beneficiaryNameInput غير موجود');
    }

    // --- التعامل مع الأقسام والإدارات ---
    if (departmentSelect && sectionSelect) {
        // تحميل الأقسام عند اختيار الإدارة
        departmentSelect.addEventListener('change', function() {
            const departmentId = this.value;
            
            if (departmentId) {
                // تفعيل قائمة الأقسام وزر إضافة قسم
                sectionSelect.disabled = false;
                if (addSectionBtn) {
                    addSectionBtn.disabled = false;
                }
                
                sectionSelect.innerHTML = '<option value="" selected disabled>-- اختر القسم --</option>';
                
                // جلب الأقسام من الخادم
                fetch('/api/sections/' + departmentId)
                    .then(response => response.json())
                    .then(data => {
                        if (data.sections && data.sections.length > 0) {
                            // إضافة الأقسام إلى القائمة
                            data.sections.forEach(section => {
                                const option = document.createElement('option');
                                option.value = section.id;
                                option.textContent = section.name;
                                sectionSelect.appendChild(option);
                            });
                        } else {
                            // إضافة خيار "لا توجد أقسام"
                            const option = document.createElement('option');
                            option.value = "";
                            option.textContent = "-- لا توجد أقسام --";
                            option.disabled = true;
                            sectionSelect.appendChild(option);
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching sections:', error);
                    });
            } else {
                // تعطيل قائمة الأقسام وزر إضافة قسم
                sectionSelect.disabled = true;
                if (addSectionBtn) {
                    addSectionBtn.disabled = true;
                }
                sectionSelect.innerHTML = '<option value="" selected disabled>-- اختر القسم --</option>';
            }
        });
    }

    // --- التعامل مع التصنيفات والتصنيفات الفرعية ---
    if (categorySelect && subcategorySelect) {
        // تحميل التصنيفات الفرعية عند اختيار التصنيف
        categorySelect.addEventListener('change', function() {
            const categoryId = this.value;
            
            if (categoryId) {
                // تفعيل قائمة التصنيفات الفرعية وزر إضافة تصنيف فرعي
                subcategorySelect.disabled = false;
                if (addSubcategoryBtn) {
                    addSubcategoryBtn.disabled = false;
                }
                
                subcategorySelect.innerHTML = '<option value="" selected disabled>-- اختر التصنيف الفرعي --</option>';
                
                // جلب التصنيفات الفرعية من الخادم
                fetch('/api/subcategories/' + categoryId)
                    .then(response => response.json())
                    .then(data => {
                        if (data.subcategories && data.subcategories.length > 0) {
                            // إضافة التصنيفات الفرعية إلى القائمة
                            data.subcategories.forEach(subcategory => {
                                const option = document.createElement('option');
                                option.value = subcategory.id;
                                option.textContent = subcategory.name;
                                subcategorySelect.appendChild(option);
                            });
                        } else {
                            // إضافة خيار "لا توجد تصنيفات فرعية"
                            const option = document.createElement('option');
                            option.value = "";
                            option.textContent = "-- لا توجد تصنيفات فرعية --";
                            option.disabled = true;
                            subcategorySelect.appendChild(option);
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching subcategories:', error);
                    });
            } else {
                // تعطيل قائمة التصنيفات الفرعية وزر إضافة تصنيف فرعي
                subcategorySelect.disabled = true;
                if (addSubcategoryBtn) {
                    addSubcategoryBtn.disabled = true;
                }
                subcategorySelect.innerHTML = '<option value="" selected disabled>-- اختر التصنيف الفرعي --</option>';
            }
        });
    }

    // --- معاينة المرفقات ---
    if (fileInput && previewContainer && previewDiv) {
        fileInput.addEventListener('change', function() {
            // مسح المعاينات السابقة
            previewDiv.innerHTML = '';
            
            if (this.files.length > 0) {
                // إظهار حاوية المعاينة
                previewContainer.classList.remove('d-none');
                
                // إنشاء معاينة لكل ملف
                Array.from(this.files).forEach((file, index) => {
                    // حد أقصى 5 ملفات
                    if (index >= 5) return;
                    
                    const col = document.createElement('div');
                    col.className = 'col-md-4 mb-3';
                    
                    const card = document.createElement('div');
                    card.className = 'card h-100';
                    
                    const cardBody = document.createElement('div');
                    cardBody.className = 'card-body text-center';
                    
                    // إنشاء أيقونة بناءً على نوع الملف
                    if (file.type.startsWith('image/')) {
                        // للصور، إنشاء معاينة مصغرة
                        const img = document.createElement('img');
                        img.className = 'img-thumbnail mb-2';
                        img.style.maxHeight = '100px';
                        img.style.maxWidth = '100%';
                        
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            img.src = e.target.result;
                        };
                        reader.readAsDataURL(file);
                        
                        cardBody.appendChild(img);
                    } else {
                        // لأنواع الملفات الأخرى، إظهار أيقونة مناسبة
                        const iconElement = document.createElement('i');
                        
                        if (file.type.includes('pdf')) {
                            iconElement.className = 'fas fa-file-pdf fa-3x text-danger mb-2';
                        } else if (file.type.includes('word') || file.name.endsWith('.doc') || file.name.endsWith('.docx')) {
                            iconElement.className = 'fas fa-file-word fa-3x text-primary mb-2';
                        } else if (file.type.includes('excel') || file.name.endsWith('.xls') || file.name.endsWith('.xlsx')) {
                            iconElement.className = 'fas fa-file-excel fa-3x text-success mb-2';
                        } else if (file.type.includes('text')) {
                            iconElement.className = 'fas fa-file-alt fa-3x text-info mb-2';
                        } else {
                            iconElement.className = 'fas fa-file fa-3x text-secondary mb-2';
                        }
                        
                        cardBody.appendChild(iconElement);
                    }
                    
                    // إضافة اسم الملف
                    const fileName = document.createElement('p');
                    fileName.className = 'mb-0 text-truncate';
                    fileName.title = file.name;
                    fileName.textContent = file.name;
                    cardBody.appendChild(fileName);
                    
                    // إضافة حجم الملف
                    const fileSize = document.createElement('small');
                    fileSize.className = 'text-muted';
                    fileSize.textContent = formatFileSize(file.size);
                    cardBody.appendChild(fileSize);
                    
                    card.appendChild(cardBody);
                    col.appendChild(card);
                    previewDiv.appendChild(col);
                });
                
                // إذا كان عدد الملفات أكبر من 5، إظهار تنبيه
                if (this.files.length > 5) {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-warning mt-2';
                    alertDiv.textContent = `تم اختيار ${this.files.length} ملفات، ولكن سيتم رفع أول 5 ملفات فقط.`;
                    previewDiv.appendChild(alertDiv);
                }
            } else {
                // إخفاء حاوية المعاينة
                previewContainer.classList.add('d-none');
            }
        });
    }

    // دالة لتنسيق حجم الملف
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // --- التعامل مع زر إرسال واتساب ---
    if (sendWhatsappBtn && assignedToSelect) {
        // تفعيل/تعطيل زر إرسال واتساب بناءً على اختيار فني الصيانة
        assignedToSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (this.value && selectedOption.dataset.phone) {
                sendWhatsappBtn.disabled = false;
            } else {
                sendWhatsappBtn.disabled = true;
            }
        });
        
        // إرسال رسالة واتساب للفني
        sendWhatsappBtn.addEventListener('click', function() {
            const selectedOption = assignedToSelect.options[assignedToSelect.selectedIndex];
            if (assignedToSelect.value && selectedOption.dataset.phone) {
                // تنسيق رقم الهاتف بالصيغة الدولية
                let phone = selectedOption.dataset.phone.replace(/\D/g, ''); // إزالة الأحرف غير الرقمية
                if (phone.startsWith('0')) {
                    phone = '966' + phone.substring(1); // استبدال الصفر البادئ بـ 966
                }
                
                // إعداد معلومات البلاغ للرسالة
                const techName = selectedOption.textContent;
                const categoryName = categorySelect.options[categorySelect.selectedIndex].textContent;
                const priorityName = prioritySelect.options[prioritySelect.selectedIndex].textContent;
                const beneficiaryName = beneficiaryNameInput.value || 'غير محدد';
                const description = document.getElementById('description').value;
                
                // إنشاء نص الرسالة
                let message = "بلاغ جديد في انتظار المعالجة\n\n";
                message += "الفني المسؤول: " + techName + "\n";
                message += "التصنيف: " + categoryName + "\n";
                message += "الأولوية: " + priorityName + "\n";
                message += "المستفيد: " + beneficiaryName + "\n";
                message += "وصف المشكلة: " + description.substring(0, 100) + (description.length > 100 ? "..." : "") + "\n\n";
                message += "الرجاء مراجعة البلاغ في نظام Fixltpro بعد إنشائه.";
                
                // فتح واتساب
                window.open(`https://wa.me/${phone}?text=${encodeURIComponent(message)}`, '_blank');
            }
        });
    }

    // --- إضافة مستفيد جديد من النافذة المنبثقة ---
    const saveQuickBeneficiaryBtn = document.getElementById('save_quick_beneficiary');
    
    if (saveQuickBeneficiaryBtn && beneficiaryNameInput && beneficiaryIdInput && csrfToken) {
        saveQuickBeneficiaryBtn.addEventListener('click', function() {
            const name = document.getElementById('quick_beneficiary_name').value;
            const phone = document.getElementById('quick_beneficiary_phone').value;
            
            if (!name) {
                alert('يرجى إدخال اسم المستفيد');
                return;
            }
            
            // إرسال طلب AJAX لإضافة المستفيد
            fetch('/api/beneficiaries/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    name: name,
                    phone: phone
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('حدث خطأ أثناء إضافة المستفيد');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    // تحديث حقل المستفيد
                    beneficiaryNameInput.value = data.beneficiary.name;
                    beneficiaryIdInput.value = data.beneficiary.id;
                    
                    // إغلاق النافذة المنبثقة
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addQuickBeneficiaryModal'));
                    modal.hide();
                    
                    // مسح حقول النافذة المنبثقة
                    document.getElementById('quick_beneficiary_name').value = '';
                    document.getElementById('quick_beneficiary_phone').value = '';
                    
                    // عرض رسالة نجاح
                    alert('تم إضافة المستفيد بنجاح');
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('حدث خطأ أثناء إضافة المستفيد');
            });
        });
    }

    // --- تحديث معلومات الإدارة/التصنيف في النوافذ المنبثقة ---
    if (typeof $ !== 'undefined') {
        // تحديث معلومات الإدارة في نافذة إضافة قسم
        $('#addSectionModal').on('show.bs.modal', function () {
            if (departmentSelect) {
                const departmentId = departmentSelect.value;
                const departmentName = departmentSelect.options[departmentSelect.selectedIndex].text;
                
                const container = document.getElementById('department_for_section_container');
                if (container) {
                    container.innerHTML = `
                        <input type="hidden" id="department_id_for_section" value="${departmentId}">
                        <div class="alert alert-info">
                            <strong>الإدارة:</strong> ${departmentName}
                        </div>
                    `;
                }
            }
        });
        
        // تحديث معلومات التصنيف في نافذة إضافة تصنيف فرعي
        $('#addSubcategoryModal').on('show.bs.modal', function () {
            if (categorySelect) {
                const categoryId = categorySelect.value;
                const categoryName = categorySelect.options[categorySelect.selectedIndex].text;
                
                const container = document.getElementById('category_for_subcategory_container');
                if (container) {
                    container.innerHTML = `
                        <input type="hidden" id="category_id_for_subcategory" value="${categoryId}">
                        <div class="alert alert-info">
                            <strong>التصنيف:</strong> ${categoryName}
                        </div>
                    `;
                }
            }
        });
    }

    // --- إضافة إدارة جديدة ---
    const saveDepartmentBtn = document.getElementById('save_department');
    
    if (saveDepartmentBtn && departmentSelect && csrfToken) {
        saveDepartmentBtn.addEventListener('click', function() {
            const departmentName = document.getElementById('new_department_name').value;
            
            if (!departmentName) {
                alert('يرجى إدخال اسم الإدارة');
                return;
            }
            
            fetch('/api/departments/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    name: departmentName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // إضافة الإدارة الجديدة إلى القائمة
                    const option = document.createElement('option');
                    option.value = data.department.id;
                    option.textContent = data.department.name;
                    
                    // إضافة خيار الإدارة الجديدة وتحديده
                    departmentSelect.appendChild(option);
                    departmentSelect.value = data.department.id;
                    
                    // تفعيل قائمة الأقسام وزر إضافة القسم
                    sectionSelect.disabled = false;
                    if (addSectionBtn) {
                        addSectionBtn.disabled = false;
                    }
                    
                    // إغلاق النافذة المنبثقة
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addDepartmentModal'));
                    modal.hide();
                    
                    // مسح حقول النافذة المنبثقة
                    document.getElementById('new_department_name').value = '';
                    
                    // عرض رسالة نجاح
                    alert('تم إضافة الإدارة بنجاح');
                    
                    // تنفيذ حدث change لتحديث القسم
                    departmentSelect.dispatchEvent(new Event('change'));
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('حدث خطأ أثناء إضافة الإدارة');
            });
        });
    }

    // --- إضافة قسم جديد ---
    const saveSectionBtn = document.getElementById('save_section');
    
    if (saveSectionBtn && sectionSelect && csrfToken) {
        saveSectionBtn.addEventListener('click', function() {
            const departmentIdInput = document.getElementById('department_id_for_section');
            if (!departmentIdInput) {
                alert('خطأ: لم يتم العثور على معرف الإدارة');
                return;
            }
            
            const departmentId = departmentIdInput.value;
            const sectionName = document.getElementById('new_section_name').value;
            
            if (!sectionName) {
                alert('يرجى إدخال اسم القسم');
                return;
            }
            
            fetch('/api/sections/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    department_id: departmentId,
                    name: sectionName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // إضافة القسم الجديد إلى القائمة
                    const option = document.createElement('option');
                    option.value = data.section.id;
                    option.textContent = data.section.name;
                    
                    // إضافة خيار القسم الجديد وتحديده
                    sectionSelect.innerHTML = '<option value="" disabled>-- اختر القسم --</option>';
                    sectionSelect.appendChild(option);
                    sectionSelect.value = data.section.id;
                    
                    // إغلاق النافذة المنبثقة
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addSectionModal'));
                    modal.hide();
                    
                    // مسح حقول النافذة المنبثقة
                    document.getElementById('new_section_name').value = '';
                    
                    // عرض رسالة نجاح
                    alert('تم إضافة القسم بنجاح');
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('حدث خطأ أثناء إضافة القسم');
            });
        });
    }

    // --- إضافة تصنيف جديد ---
    const saveCategoryBtn = document.getElementById('save_category');
    
    if (saveCategoryBtn && categorySelect && csrfToken) {
        saveCategoryBtn.addEventListener('click', function() {
            const categoryName = document.getElementById('new_category_name').value;
            
            if (!categoryName) {
                alert('يرجى إدخال اسم التصنيف');
                return;
            }
            
            fetch('/api/categories/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    name: categoryName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // إضافة التصنيف الجديد إلى القائمة
                    const option = document.createElement('option');
                    option.value = data.category.id;
                    option.textContent = data.category.name;
                    
                    // إضافة خيار التصنيف الجديد وتحديده
                    categorySelect.appendChild(option);
                    categorySelect.value = data.category.id;
                    
                    // تفعيل قائمة التصنيفات الفرعية وزر إضافة التصنيف الفرعي
                    subcategorySelect.disabled = false;
                    if (addSubcategoryBtn) {
                        addSubcategoryBtn.disabled = false;
                    }
                    
                    // إغلاق النافذة المنبثقة
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addCategoryModal'));
                    modal.hide();
                    
                    // مسح حقول النافذة المنبثقة
                    document.getElementById('new_category_name').value = '';
                    
                    // عرض رسالة نجاح
                    alert('تم إضافة التصنيف بنجاح');
                    
                    // تنفيذ حدث change لتحديث التصنيفات الفرعية
                    categorySelect.dispatchEvent(new Event('change'));
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('حدث خطأ أثناء إضافة التصنيف');
            });
        });
    }

    // --- إضافة تصنيف فرعي جديد ---
    const saveSubcategoryBtn = document.getElementById('save_subcategory');
    
    if (saveSubcategoryBtn && subcategorySelect && csrfToken) {
        saveSubcategoryBtn.addEventListener('click', function() {
            const categoryIdInput = document.getElementById('category_id_for_subcategory');
            if (!categoryIdInput) {
                alert('خطأ: لم يتم العثور على معرف التصنيف');
                return;
            }
            
            const categoryId = categoryIdInput.value;
            const subcategoryName = document.getElementById('new_subcategory_name').value;
            
            if (!subcategoryName) {
                alert('يرجى إدخال اسم التصنيف الفرعي');
                return;
            }
            
            fetch('/api/subcategories/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    category_id: categoryId,
                    name: subcategoryName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // إضافة التصنيف الفرعي الجديد إلى القائمة
                    const option = document.createElement('option');
                    option.value = data.subcategory.id;
                    option.textContent = data.subcategory.name;
                    
                    // إضافة خيار التصنيف الفرعي الجديد وتحديده
                    subcategorySelect.innerHTML = '<option value="" disabled>-- اختر التصنيف الفرعي --</option>';
                    subcategorySelect.appendChild(option);
                    subcategorySelect.value = data.subcategory.id;
                    
                    // إغلاق النافذة المنبثقة
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addSubcategoryModal'));
                    modal.hide();
                    
                    // مسح حقول النافذة المنبثقة
                    document.getElementById('new_subcategory_name').value = '';
                    
                    // عرض رسالة نجاح
                    alert('تم إضافة التصنيف الفرعي بنجاح');
                } else {
                    alert(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('حدث خطأ أثناء إضافة التصنيف الفرعي');
            });
        });
    }
});
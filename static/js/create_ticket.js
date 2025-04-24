document.addEventListener('DOMContentLoaded', function() {
    // تفريغ النموذج عند تحميل الصفحة
    const form = document.getElementById('ticketForm');
    form.reset();
    
    // حذف أي بيانات مخزنة في المتصفح
    sessionStorage.removeItem('formData');
    
    // منع حفظ البيانات في المتصفح
    window.onbeforeunload = function() {
        // تفريغ النموذج قبل مغادرة الصفحة
        form.reset();
    };
    
    // استجابة للتغيير في اختيار الإدارة
    const departmentSelect = document.getElementById('department_id');
    const sectionSelect = document.getElementById('section_id');
    
    // تحميل الأقسام عند اختيار الإدارة
    departmentSelect.addEventListener('change', function() {
        // تفعيل حقل الأقسام
        sectionSelect.disabled = false;
        sectionSelect.innerHTML = '<option value="" selected disabled>-- اختر القسم --</option>';
        
        const departmentId = this.value;
        if (departmentId) {
            // استدعاء API للحصول على الأقسام المرتبطة بالإدارة
            fetch('/api/sections/' + departmentId)
                .then(response => response.json())
                .then(data => {
                    if (data.sections && data.sections.length > 0) {
                        // إضافة القيمة "بدون قسم"
                        const noneOption = document.createElement('option');
                        noneOption.value = '0';
                        noneOption.textContent = '-- بدون قسم --';
                        sectionSelect.appendChild(noneOption);
                        
                        // إضافة الأقسام
                        data.sections.forEach(section => {
                            const option = document.createElement('option');
                            option.value = section.id;
                            option.textContent = section.name;
                            sectionSelect.appendChild(option);
                        });
                    } else {
                        // إذا لم تكن هناك أقسام للإدارة المحددة
                        const noneOption = document.createElement('option');
                        noneOption.value = '0';
                        noneOption.textContent = '-- لا توجد أقسام --';
                        sectionSelect.appendChild(noneOption);
                    }
                })
                .catch(error => {
                    console.error('خطأ في تحميل الأقسام:', error);
                    sectionSelect.innerHTML = '<option value="" selected disabled>-- حدث خطأ في تحميل الأقسام --</option>';
                });
        } else {
            sectionSelect.disabled = true;
        }
    });
    
    // استجابة للتغيير في اختيار التصنيف
    const categorySelect = document.getElementById('category_id');
    const subcategorySelect = document.getElementById('subcategory_id');
    
    categorySelect.addEventListener('change', function() {
        // تفعيل حقل التصنيفات الفرعية
        subcategorySelect.disabled = false;
        subcategorySelect.innerHTML = '<option value="" selected disabled>-- اختر التصنيف الفرعي --</option>';
        
        const categoryId = this.value;
        if (categoryId) {
            // استدعاء API للحصول على التصنيفات الفرعية المرتبطة بالتصنيف
            fetch('/api/subcategories/' + categoryId)
                .then(response => response.json())
                .then(data => {
                    if (data.subcategories && data.subcategories.length > 0) {
                        // إضافة القيمة "بدون تصنيف فرعي"
                        const noneOption = document.createElement('option');
                        noneOption.value = '0';
                        noneOption.textContent = '-- بدون تصنيف فرعي --';
                        subcategorySelect.appendChild(noneOption);
                        
                        // إضافة التصنيفات الفرعية
                        data.subcategories.forEach(subcategory => {
                            const option = document.createElement('option');
                            option.value = subcategory.id;
                            option.textContent = subcategory.name;
                            subcategorySelect.appendChild(option);
                        });
                    } else {
                        // إذا لم تكن هناك تصنيفات فرعية للتصنيف المحدد
                        const noneOption = document.createElement('option');
                        noneOption.value = '0';
                        noneOption.textContent = '-- لا توجد تصنيفات فرعية --';
                        subcategorySelect.appendChild(noneOption);
                    }
                })
                .catch(error => {
                    console.error('خطأ في تحميل التصنيفات الفرعية:', error);
                    subcategorySelect.innerHTML = '<option value="" selected disabled>-- حدث خطأ في تحميل التصنيفات الفرعية --</option>';
                });
        } else {
            subcategorySelect.disabled = true;
        }
    });
    
    // معاينة المرفقات
    const attachmentsInput = document.getElementById('attachments');
    const previewContainer = document.querySelector('.preview-container');
    const previewsDiv = document.getElementById('attachments-preview');
    
    attachmentsInput.addEventListener('change', function() {
        // حذف المعاينات السابقة
        previewsDiv.innerHTML = '';
        
        // التحقق من وجود ملفات
        if (this.files.length > 0) {
            previewContainer.classList.remove('d-none');
            
            // إنشاء معاينة لكل ملف
            Array.from(this.files).forEach((file, index) => {
                if (index >= 5) return; // الحد الأقصى 5 ملفات

                const col = document.createElement('div');
                col.className = 'col-md-4 mb-2';
                
                const card = document.createElement('div');
                card.className = 'card h-100';
                
                const cardBody = document.createElement('div');
                cardBody.className = 'card-body text-center';
                
                // معالجة أنواع الملفات المختلفة
                if (file.type.startsWith('image/')) {
                    // إذا كان الملف صورة
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        img.className = 'img-fluid mb-2';
                        img.style.maxHeight = '150px';
                        cardBody.appendChild(img);
                    };
                    reader.readAsDataURL(file);
                } else {
                    // إذا كان الملف من نوع آخر
                    const icon = document.createElement('i');
                    if (file.type.includes('pdf')) {
                        icon.className = 'fas fa-file-pdf fa-4x text-danger mb-2';
                    } else if (file.type.includes('word') || file.type.includes('document')) {
                        icon.className = 'fas fa-file-word fa-4x text-primary mb-2';
                    } else if (file.type.includes('excel') || file.type.includes('spreadsheet')) {
                        icon.className = 'fas fa-file-excel fa-4x text-success mb-2';
                    } else if (file.type.includes('zip') || file.type.includes('compressed')) {
                        icon.className = 'fas fa-file-archive fa-4x text-warning mb-2';
                    } else {
                        icon.className = 'fas fa-file fa-4x text-secondary mb-2';
                    }
                    cardBody.appendChild(icon);
                }
                
                // إضافة اسم الملف
                const fileName = document.createElement('p');
                fileName.className = 'small mb-0 text-truncate';
                fileName.textContent = file.name;
                cardBody.appendChild(fileName);
                
                // إضافة حجم الملف
                const fileSize = document.createElement('small');
                fileSize.className = 'text-muted';
                fileSize.textContent = formatFileSize(file.size);
                cardBody.appendChild(fileSize);
                
                card.appendChild(cardBody);
                col.appendChild(card);
                previewsDiv.appendChild(col);
            });
        } else {
            previewContainer.classList.add('d-none');
        }
    });
    
    // تنسيق حجم الملف
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' بايت';
        else if (bytes < 1048576) return Math.round(bytes / 1024) + ' كيلوبايت';
        else return Math.round(bytes / 1048576 * 10) / 10 + ' ميجابايت';
    }
});
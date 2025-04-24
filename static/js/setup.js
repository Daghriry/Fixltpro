document.addEventListener('DOMContentLoaded', function() {
    const progressBar = document.getElementById('progressBar');
    const currentOperation = document.getElementById('currentOperation');
    const setupLog = document.getElementById('setupLog');
    const setupComplete = document.getElementById('setupComplete');
    const setupError = document.getElementById('setupError');
    const errorMessage = document.getElementById('errorMessage');
    const retryBtn = document.getElementById('retryBtn');

    // تسلسل عمليات الإعداد
    const setupOperations = [
        { name: 'إنشاء جداول قاعدة البيانات', progress: 10 },
        { name: 'إعداد جدول المستخدمين', progress: 20 },
        { name: 'إنشاء حسابات المستخدمين الافتراضية', progress: 30 },
        { name: 'إعداد جدول الأولويات', progress: 40 },
        { name: 'إعداد جدول حالات البلاغات', progress: 50 },
        { name: 'إعداد جدول التصنيفات والتصنيفات الفرعية', progress: 60 },
        { name: 'إعداد جدول الإدارات والأقسام', progress: 70 },
        { name: 'إنشاء بيانات تجريبية', progress: 80 },
        { name: 'تهيئة مجلد المرفقات', progress: 90 },
        { name: 'اكتمال الإعداد', progress: 100 }
    ];

    // إضافة سجل جديد إلى الشاشة
    function addLog(message, type = 'info') {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${type}`;
        const timestamp = new Date().toLocaleTimeString('ar-SA');
        logEntry.innerHTML = `[${timestamp}] ${message}`;
        setupLog.appendChild(logEntry);
        setupLog.scrollTop = setupLog.scrollHeight;
    }

    // تحديث شريط التقدم
    function updateProgress(percent, operationName) {
        progressBar.style.width = `${percent}%`;
        progressBar.setAttribute('aria-valuenow', percent);
        currentOperation.textContent = operationName;

        // تغيير لون شريط التقدم حسب النسبة
        if (percent < 30) {
            progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated bg-info';
        } else if (percent < 70) {
            progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated bg-primary';
        } else if (percent < 100) {
            progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated bg-warning';
        } else {
            progressBar.className = 'progress-bar progress-bar-striped bg-success';
        }
    }

    // الحصول على وقت عشوائي بين القيمتين (بالمللي ثانية)
    function getRandomTime(min, max) {
        return Math.floor(Math.random() * (max - min + 1) + min);
    }

    // التعامل مع طلب الإعداد الفعلي
    // التعامل مع طلب الإعداد الفعلي
    function performRealSetup() {
        // إضافة السجل الأولي
        addLog('بدء عملية إعداد قاعدة البيانات...', 'info');
        updateProgress(5, 'جاري الاتصال بالخادم...');
        
        // إرسال طلب إلى المسار /setup_api باستخدام fetch API
        fetch('/setup_api', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            // عدم إرسال البيانات في هذه الحالة لأننا لا نحتاجها
            body: JSON.stringify({})
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`فشل الاتصال بالخادم: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // تقدم شريط التقدم وتحديث السجل
                let currentIndex = 0;
                
                function processNextOperation() {
                    if (currentIndex >= setupOperations.length) {
                        // اكتملت جميع العمليات
                        updateProgress(100, 'اكتمل الإعداد بنجاح');
                        addLog('تم إكمال عملية الإعداد بنجاح!', 'success');
                        setTimeout(() => {
                            setupComplete.style.display = 'block';
                        }, 1000);
                        return;
                    }
                    
                    const operation = setupOperations[currentIndex];
                    updateProgress(operation.progress, operation.name);
                    addLog(`جاري ${operation.name}...`, 'info');
                    
                    // محاكاة وقت العملية
                    setTimeout(() => {
                        addLog(`تم ${operation.name} بنجاح.`, 'success');
                        currentIndex++;
                        processNextOperation();
                    }, getRandomTime(500, 1500));
                }
                
                // بدء تسلسل العمليات
                processNextOperation();
            } else if (data.status === 'info') {
                // الإعداد تم مسبقاً
                addLog(data.message, 'info');
                updateProgress(100, 'تم الإعداد مسبقاً');
                setTimeout(() => {
                    setupComplete.style.display = 'block';
                }, 1000);
            } else {
                throw new Error(data.message || 'حدث خطأ غير معروف');
            }
        })
        .catch(error => {
            addLog(`فشل الإعداد: ${error.message}`, 'error');
            errorMessage.textContent = error.message;
            setupError.style.display = 'block';
            updateProgress(100, 'فشل الإعداد');
            progressBar.className = 'progress-bar bg-danger';
        });
    }

    // إعادة المحاولة عند النقر على زر "إعادة المحاولة"
    retryBtn.addEventListener('click', function() {
        setupError.style.display = 'none';
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', 0);
        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
        currentOperation.textContent = 'جاري الإعداد...';
        performRealSetup();
    });

    // بدء عملية الإعداد تلقائيًا عند تحميل الصفحة
    performRealSetup();
});
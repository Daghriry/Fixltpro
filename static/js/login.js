// login.js
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const usernameFeedback = document.getElementById('username-feedback');
    const passwordFeedback = document.getElementById('password-feedback');
    const loginButton = document.querySelector('.login-btn');
    const spinner = document.querySelector('.spinner-border');
    const togglePasswordButton = document.querySelector('.toggle-password');
    
    // Enable password visibility toggle
    if (togglePasswordButton) {
        togglePasswordButton.addEventListener('click', function() {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            // Toggle eye icon
            const eyeIcon = this.querySelector('i');
            if (type === 'password') {
                eyeIcon.classList.remove('fa-eye-slash');
                eyeIcon.classList.add('fa-eye');
            } else {
                eyeIcon.classList.remove('fa-eye');
                eyeIcon.classList.add('fa-eye-slash');
            }
        });
    }
    
    // Form validation
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            let isValid = true;
            
            // Clear previous validation messages
            usernameInput.classList.remove('is-invalid');
            passwordInput.classList.remove('is-invalid');
            usernameFeedback.textContent = '';
            passwordFeedback.textContent = '';
            
            // Validate username
            if (!usernameInput.value.trim()) {
                usernameInput.classList.add('is-invalid');
                usernameFeedback.textContent = 'يرجى إدخال اسم المستخدم';
                isValid = false;
            }
            
            // Validate password
            if (!passwordInput.value) {
                passwordInput.classList.add('is-invalid');
                passwordFeedback.textContent = 'يرجى إدخال كلمة المرور';
                isValid = false;
            }
            
            if (!isValid) {
                event.preventDefault();
                return;
            }
            
            // Show loading spinner
            loginButton.setAttribute('disabled', 'disabled');
            spinner.classList.remove('d-none');
        });
    }
    
    // Auto-focus on username field
    if (usernameInput) {
        usernameInput.focus();
    }
    
    // Disable form submission when Enter is pressed in a field with invalid data
    document.querySelectorAll('input').forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && this.classList.contains('is-invalid')) {
                e.preventDefault();
            }
        });
    });
});
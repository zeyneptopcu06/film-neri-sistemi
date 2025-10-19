// ==========================================
// auth.js - Login & Register + Password Toggle
// ==========================================

// 👁️ Şifre göster/gizle fonksiyonu
window.togglePassword = function (inputId) {
    const input = document.getElementById(inputId);
    const btn = event.currentTarget;
    if (!input) return;

    if (input.type === "password") {
        input.type = "text";
        btn.textContent = "👁️";
    } else {
        input.type = "password";
        btn.textContent = "🙈";
    }
};

// ==========================================
// LOGIN FORM
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const email = document.getElementById('login-username').value.trim();
            const sifre = document.getElementById('login-password').value.trim();
            const loginMessage = document.getElementById('login-message');
            loginMessage.textContent = '';

            const btn = loginForm.querySelector('.auth-btn .loading-spinner');
            if (btn) btn.style.display = 'inline-block';

            try {
                const res = await fetch('/api/giris', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email, 
                        sifre,
                        remember: document.getElementById('remember').checked
                    })
                });

                const data = await res.json();

                if (!res.ok) {
    loginMessage.style.display = "block"; // görünür yap
    if (res.status === 404) {
        loginMessage.className = "message warning";
        loginMessage.textContent = data.hata || "E-posta adresi bulunamadı.";
    } else if (res.status === 401) {
        loginMessage.className = "message error";
        loginMessage.textContent = data.hata || "Şifre hatalı.";
    } else {
        loginMessage.className = "message error";
        loginMessage.textContent = data.hata || "Sunucu hatası. Tekrar deneyin.";
    }
} else {
    loginMessage.className = "message success";
    loginMessage.textContent = data.mesaj || "Giriş başarılı!";
    setTimeout(() => window.location.href = '/', 1000);

}
            
                
            } catch (err) {
                loginMessage.style.color = 'red';
                loginMessage.textContent = 'Sunucu hatası. Tekrar deneyin.';
                console.error('Login error:', err);
            } finally {
                if (btn) btn.style.display = 'none';
            }
        });
    }
});

const forgotLink = document.querySelector('.forgot-link');
if (forgotLink) {
    forgotLink.addEventListener('click', (e) => {
        e.preventDefault();
        const email = prompt("Lütfen kayıtlı e-posta adresinizi girin:");
        if (!email) return;

        fetch('/api/forgot_password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        })
        .then(res => res.json())
        .then(data => {
            alert(data.mesaj || data.hata || "İşlem tamamlandı.");
        })
        .catch(err => {
            console.error('Forgot password error:', err);
            alert('Sunucu hatası. Tekrar deneyin.');
        });
    });
}
// ==========================================
// REGISTER FORM
// ==========================================
const registerForm = document.getElementById('register-form');
if (registerForm) {
    const passwordInput = document.getElementById('register-password');
    const confirmInput = document.getElementById('register-confirm');
    const usernameInput = document.getElementById('register-username');
    const emailInput = document.getElementById('register-email');
    const termsCheckbox = document.getElementById('terms-check');

    // Şifre gücü kontrolü
    function checkPasswordStrength(password) {
        const strengthFill = document.getElementById('strength-fill');
        const strengthText = document.getElementById('strength-text');
        if (!strengthFill || !strengthText) return;

        let strength = 0;
        if (password.length >= 6) strength++;
        if (/[A-Z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[\W]/.test(password)) strength++;

        switch (strength) {
            case 0:
            case 1:
                strengthFill.style.width = "25%";
                strengthFill.style.backgroundColor = "red";
                strengthText.textContent = "Zayıf";
                break;
            case 2:
                strengthFill.style.width = "50%";
                strengthFill.style.backgroundColor = "orange";
                strengthText.textContent = "Orta";
                break;
            case 3:
                strengthFill.style.width = "75%";
                strengthFill.style.backgroundColor = "yellowgreen";
                strengthText.textContent = "İyi";
                break;
            case 4:
                strengthFill.style.width = "100%";
                strengthFill.style.backgroundColor = "green";
                strengthText.textContent = "Güçlü";
                break;
        }
    }

    passwordInput.addEventListener('input', (e) => checkPasswordStrength(e.target.value));

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = usernameInput.value.trim();
        const email = emailInput.value.trim();
        const sifre = passwordInput.value.trim();
        const confirm = confirmInput.value.trim();
        const termsAccepted = termsCheckbox.checked;

        const registerMessage = document.getElementById('register-message');
        registerMessage.textContent = '';

        if (!username) {
            registerMessage.style.color = 'red';
            registerMessage.textContent = 'Kullanıcı adı boş bırakılamaz.';
            return;
        }
        if (!termsAccepted) {
            registerMessage.style.color = 'red';
            registerMessage.textContent = 'Kullanım koşullarını kabul etmelisiniz.';
            return;
        }
        if (sifre !== confirm) {
            registerMessage.style.color = 'red';
            registerMessage.textContent = 'Şifreler eşleşmiyor.';
            return;
        }

        const btn = registerForm.querySelector('.auth-btn .loading-spinner');
        if (btn) btn.style.display = 'inline-block';

        try {
            const res = await fetch('/api/kayit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, sifre })
            });

            const data = await res.json();

            if (res.ok) {
                registerMessage.style.color = 'green';
                registerMessage.textContent = data.mesaj || 'Kayıt başarılı! Giriş sayfasına yönlendiriliyorsunuz...';
                setTimeout(() => window.location.href = '/giris', 1500);
            } else {
                registerMessage.style.color = 'red';
                registerMessage.textContent = data.hata || 'Kayıt başarısız!';
            }
        } catch (err) {
            registerMessage.style.color = 'red';
            registerMessage.textContent = 'Sunucu hatası. Tekrar deneyin.';
            console.error('Register error:', err);
        } finally {
            if (btn) btn.style.display = 'none';
        }
    });
}

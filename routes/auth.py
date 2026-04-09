import random
import smtplib
from email.mime.text import MIMEText
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from config import supabase, SENDER_EMAIL, SENDER_PASSWORD

# Bikin Blueprint untuk Auth
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nama_lengkap = request.form.get('nama_lengkap')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        cek_user = supabase.table('users').select('*').eq('username', username).execute()
        if cek_user.data:
            return render_template('register.html', error="Username sudah terdaftar!")

        hashed_password = generate_password_hash(password)

        user_baru = supabase.table('users').insert({
            "nama_lengkap": nama_lengkap, "username": username, "email": email,
            "password": hashed_password, "role": "user" 
        }).execute()

        user_id_baru = user_baru.data[0]['id']
        supabase.table('dompet').insert({
            "user_id": user_id_baru, "nama_dompet": "Dompet Utama (Cash)",
            "saldo": 0, "target_saldo": 0
        }).execute()

        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_response = supabase.table('users').select('*').eq('username', username).execute()
        
        if user_response.data:
            user = user_response.data[0]
            if check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['nama_lengkap'] = user['nama_lengkap']
                session['role'] = user['role']
                return redirect(url_for('keuangan.index'))
            else:
                return render_template('login.html', error="Password salah!")
        else:
            return render_template('login.html', error="Username tidak ditemukan!")
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/lupa_password', methods=['GET', 'POST'])
def lupa_password():
    if request.method == 'POST':
        username = request.form.get('username')
        user_response = supabase.table('users').select('*').eq('username', username).execute()

        if user_response.data:
            user = user_response.data[0]
            email_tujuan = user.get('email')

            if not email_tujuan:
                return render_template('lupa_password.html', error="Gagal: Akun tanpa email.")

            otp = str(random.randint(100000, 999999))
            session['reset_otp'] = otp
            session['reset_username'] = username

            try:
                msg = MIMEText(f"Halo {user['nama_lengkap']},\n\nKode OTP: {otp}\nJangan berikan ke siapapun.")
                msg['Subject'] = 'Kode OTP Reset Password'
                msg['From'] = SENDER_EMAIL
                msg['To'] = email_tujuan

                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(SENDER_EMAIL, SENDER_PASSWORD)
                    server.send_message(msg)

                return redirect(url_for('auth.verify_otp'))
            except Exception as e:
                return render_template('lupa_password.html', error="Gagal ngirim email.")
        else:
            return render_template('lupa_password.html', error="Username tidak ditemukan!")
    return render_template('lupa_password.html')

@auth_bp.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_username' not in session: return redirect(url_for('auth.lupa_password'))
    if request.method == 'POST':
        if request.form.get('otp') == session.get('reset_otp'):
            return redirect(url_for('auth.reset_password'))
        return render_template('verify_otp.html', error="Kode OTP Salah!")
    return render_template('verify_otp.html')

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_username' not in session: return redirect(url_for('auth.lupa_password'))
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        hashed_password = generate_password_hash(new_password)
        supabase.table('users').update({"password": hashed_password}).eq('username', session['reset_username']).execute()
        session.pop('reset_otp', None)
        session.pop('reset_username', None)
        return redirect(url_for('auth.login'))
    return render_template('reset_password.html')
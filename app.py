import os
import urllib.parse
import json
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash 
from supabase import create_client, Client
import google.generativeai as genai
from PIL import Image
import base64
import io

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")
SUPABASE_URL = os.environ.get("SUPABASE_URL") 
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ==========================================
# ROUTE REGISTER & LOGIN
# ==========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nama_lengkap = request.form.get('nama_lengkap')
        username = request.form.get('username')
        password = request.form.get('password')

        cek_user = supabase.table('users').select('*').eq('username', username).execute()
        if cek_user.data:
            return render_template('register.html', error="Username sudah terdaftar! Pilih yang lain.")

        hashed_password = generate_password_hash(password)

        user_baru = supabase.table('users').insert({
            "nama_lengkap": nama_lengkap,
            "username": username,
            "password": hashed_password,
            "role": "user" 
        }).execute()

        user_id_baru = user_baru.data[0]['id']
        supabase.table('dompet').insert({
            "user_id": user_id_baru,
            "nama_dompet": "Dompet Utama (Cash)",
            "saldo": 0
        }).execute()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
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
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Password salah!")
        else:
            return render_template('login.html', error="Username tidak ditemukan!")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ==========================================
# ROUTE UTAMA (INDEX)
# ==========================================
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']

    try:
        dompet_response = supabase.table('dompet').select('*').eq('user_id', user_id).order('id').execute()
        daftar_dompet = dompet_response.data
        total_aset = sum(d['saldo'] for d in daftar_dompet)

        transaksi_response = supabase.table('transaksi').select('*, dompet:dompet_id(nama_dompet)').eq('user_id', user_id).order('id', desc=False).execute()
        data_transaksi = transaksi_response.data

        for row in data_transaksi:
            if row['tanggal']:
                try:
                    dt = datetime.strptime(row['tanggal'], '%Y-%m-%d')
                    row['tanggal'] = dt.strftime('%d %b %Y')
                except ValueError:
                    pass
            row['nama_dompet'] = row['dompet']['nama_dompet'] if row.get('dompet') else "Dompet Dihapus"

        buka_wa = session.pop('buka_wa', None)
        error_msg = session.pop('error_msg', None)
        
        return render_template('index.html', data=data_transaksi, daftar_dompet=daftar_dompet, total_aset=total_aset, role=session['role'], nama_user=session.get('nama_lengkap'), buka_wa=buka_wa, error_msg=error_msg)
    
    except Exception as e:
        return f"Gagal narik data: {str(e)}", 500


# ==========================================
# ROUTE TAMBAH DOMPET BARU
# ==========================================
@app.route('/tambah_dompet', methods=['POST'])
def tambah_dompet():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    nama_dompet = request.form.get('nama_dompet')
    saldo_awal = int(request.form.get('saldo_awal') or 0)

    supabase.table('dompet').insert({
        "user_id": session['user_id'],
        "nama_dompet": nama_dompet,
        "saldo": saldo_awal
    }).execute()

    return redirect(url_for('index'))


# ==========================================
# ROUTE TAMBAH TRANSAKSI MANUAL
# ==========================================
@app.route('/tambah', methods=['POST'])
def tambah():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    tanggal = request.form.get('tanggal')
    jenis = request.form.get('jenis')
    keterangan = request.form.get('keterangan')
    
    uang_masuk = int(request.form.get('uang_masuk') or 0)
    uang_keluar = int(request.form.get('uang_keluar') or 0)
    
    # Variabel buat nyimpan data untuk WA
    nama_dompet_wa = ""
    nama_dompet_tujuan_wa = ""
    
    if jenis == 'Pemasukan' or jenis == 'Pengeluaran':
        dompet_id = request.form.get('dompet_id')
        dompet_data = supabase.table('dompet').select('*').eq('id', dompet_id).execute().data[0]
        saldo_sekarang = dompet_data['saldo']
        nama_dompet_wa = dompet_data['nama_dompet']

        if jenis == 'Pengeluaran' and saldo_sekarang < uang_keluar:
            session['error_msg'] = f"Gagal: Saldo {nama_dompet_wa} tidak cukup!"
            return redirect(url_for('index'))

        saldo_baru = saldo_sekarang + uang_masuk if jenis == 'Pemasukan' else saldo_sekarang - uang_keluar
        
        supabase.table('dompet').update({'saldo': saldo_baru}).eq('id', dompet_id).execute()

        keterangan_full = f"[{jenis}] {keterangan}"
        supabase.table('transaksi').insert({
            "user_id": user_id,
            "dompet_id": dompet_id,
            "tanggal": tanggal,
            "keterangan": keterangan_full,
            "uang_masuk": uang_masuk,
            "uang_keluar": uang_keluar,
            "saldo_akhir_dompet": saldo_baru
        }).execute()

    elif jenis == 'Transfer':
        dompet_asal_id = request.form.get('dompet_asal_id')
        dompet_tujuan_id = request.form.get('dompet_tujuan_id')
        nominal_transfer = uang_keluar

        if dompet_asal_id == dompet_tujuan_id:
            session['error_msg'] = "Gagal: Dompet asal dan tujuan tidak boleh sama!"
            return redirect(url_for('index'))

        dompet_asal = supabase.table('dompet').select('*').eq('id', dompet_asal_id).execute().data[0]
        dompet_tujuan = supabase.table('dompet').select('*').eq('id', dompet_tujuan_id).execute().data[0]
        nama_dompet_wa = dompet_asal['nama_dompet']
        nama_dompet_tujuan_wa = dompet_tujuan['nama_dompet']

        if dompet_asal['saldo'] < nominal_transfer:
            session['error_msg'] = f"Gagal: Saldo {nama_dompet_wa} tidak cukup untuk transfer!"
            return redirect(url_for('index'))

        saldo_baru_asal = dompet_asal['saldo'] - nominal_transfer
        saldo_baru_tujuan = dompet_tujuan['saldo'] + nominal_transfer

        supabase.table('dompet').update({'saldo': saldo_baru_asal}).eq('id', dompet_asal_id).execute()
        supabase.table('dompet').update({'saldo': saldo_baru_tujuan}).eq('id', dompet_tujuan_id).execute()

        ket_keluar = f"[Transfer Keluar] Ke {nama_dompet_tujuan_wa} - {keterangan}"
        ket_masuk = f"[Transfer Masuk] Dari {nama_dompet_wa} - {keterangan}"

        supabase.table('transaksi').insert([
            {"user_id": user_id, "dompet_id": dompet_asal_id, "tanggal": tanggal, "keterangan": ket_keluar, "uang_masuk": 0, "uang_keluar": nominal_transfer, "saldo_akhir_dompet": saldo_baru_asal},
            {"user_id": user_id, "dompet_id": dompet_tujuan_id, "tanggal": tanggal, "keterangan": ket_masuk, "uang_masuk": nominal_transfer, "uang_keluar": 0, "saldo_akhir_dompet": saldo_baru_tujuan}
        ]).execute()

    # --- LOGIKA WHATSAPP V2 ---
    semua_dompet = supabase.table('dompet').select('*').eq('user_id', user_id).execute().data
    total_aset = sum(d['saldo'] for d in semua_dompet)
    
    aset_str = "{:,.0f}".format(total_aset).replace(',', '.')
    nom_str = "{:,.0f}".format(uang_masuk if jenis == 'Pemasukan' else uang_keluar).replace(',', '.')
    
    pesan = f"Halo {session.get('nama_lengkap', 'User')}!\n"
    if jenis == 'Transfer':
        pesan += f"Ada 🔄 *TRANSFER Rp {nom_str}*\n"
        pesan += f"Dari *{nama_dompet_wa}* ke *{nama_dompet_tujuan_wa}*\n"
    else:
        jenis_tx = "MASUK" if jenis == 'Pemasukan' else "KELUAR"
        pesan += f"Ada uang {jenis_tx} *Rp {nom_str}* di dompet *{nama_dompet_wa}*\n"
    
    pesan += f"Tanggal : {tanggal}\n"
    pesan += f"Catatan : {keterangan}\n\n"
    pesan += f"Total Aset Keseluruhan : *Rp {aset_str}*\n"
    
    for d in semua_dompet:
        saldo_str = "{:,.0f}".format(d['saldo']).replace(',', '.')
        pesan += f"- {d['nama_dompet']} : Rp {saldo_str}\n"

    pesan_url = urllib.parse.quote(pesan)
    session['buka_wa'] = f"https://wa.me/?text={pesan_url}"

    return redirect(url_for('index'))


# ==========================================
# ROUTE SCAN STRUK (UPLOAD & PROSES AI)
# ==========================================
@app.route('/scan', methods=['GET', 'POST'])
def scan():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        foto_b64 = request.form.get('foto_base64')
        if not foto_b64:
            return "Tidak ada file foto", 400

        try:
            header, encoded = foto_b64.split(",", 1)
            img_data = base64.b64decode(encoded)
            img = Image.open(io.BytesIO(img_data))
            
            prompt = """
            Kamu adalah asisten keuangan pintar. Baca struk belanja di foto ini.
            Ekstrak daftar barang dan harganya. 
            Jika ada Pajak (PPN/Tax), Biaya Layanan (Service/PB1), atau Diskon, MASUKKAN juga ke dalam daftar sebagai item tersendiri (jadikan harga diskon bernilai minus/negatif).
            Abaikan nominal Uang Tunai yang dibayarkan atau Kembalian. FOKUS HANYA PADA BARANG/BIAYA YANG MEMPENGARUHI TOTAL AKHIR.
            Output HARUS murni dalam format JSON array of objects tanpa teks pengantar atau markdown, contoh:
            [{"nama": "Minyak Goreng", "harga": 35000}, {"nama": "Beras 5kg", "harga": 70000}]
            """
            
            prioritas_model = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-2.0-flash']
            model_tersedia = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            response = None
            model_pilihan = "Tidak ada"

            for model_id in prioritas_model:
                if model_id in model_tersedia:
                    try:
                        model = genai.GenerativeModel(model_id)
                        response = model.generate_content([prompt, img], request_options={"retry": None})
                        model_pilihan = model_id
                        break 
                    except Exception:
                        continue 
            
            if not response:
                raise Exception("Semua model kena limit atau menolak permintaan. Coba lagi 1 menit kemudian.")

            ai_text = response.text.strip()
            start_idx = ai_text.find('[')
            end_idx = ai_text.rfind(']') + 1
            
            bersih = ai_text[start_idx:end_idx] if (start_idx != -1 and end_idx != 0) else ai_text
            items = json.loads(bersih)
            total_belanja = sum(item['harga'] for item in items)
            
            tanggal_hari_ini = datetime.now().strftime('%Y-%m-%d')
            rincian_wa = "\n".join([f"- {item['nama']}: Rp {'{:,}'.format(item['harga']).replace(',', '.')}" for item in items])
            
            daftar_dompet = supabase.table('dompet').select('*').eq('user_id', session['user_id']).execute().data
            
            return render_template('preview.html', items=items, total=total_belanja, tanggal=tanggal_hari_ini, rincian_wa=rincian_wa, model_terpakai=model_pilihan, daftar_dompet=daftar_dompet)
            
        except Exception as e:
            return f"Waduh, AI-nya gagal baca struk. Detail error: {str(e)}"

    return render_template('scan.html')


# ==========================================
# ROUTE SIMPAN HASIL SCAN
# ==========================================
@app.route('/simpan_scan', methods=['POST'])
def simpan_scan():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    tanggal = request.form.get('tanggal')
    total_belanja = int(request.form.get('total'))
    rincian_wa = request.form.get('rincian_wa')
    dompet_id = request.form.get('dompet_id') 

    dompet_data = supabase.table('dompet').select('*').eq('id', dompet_id).execute().data[0]
    saldo_sekarang = dompet_data['saldo']
    nama_dompet = dompet_data['nama_dompet']

    if saldo_sekarang < total_belanja:
        session['error_msg'] = f"Scan Dibatalkan: Saldo {nama_dompet} tidak cukup!"
        return redirect(url_for('index'))

    saldo_baru = saldo_sekarang - total_belanja
    supabase.table('dompet').update({'saldo': saldo_baru}).eq('id', dompet_id).execute()

    keterangan_db = f"[Scan AI] Belanja pakai {nama_dompet}\n{rincian_wa}"

    supabase.table('transaksi').insert({
        "user_id": user_id,
        "dompet_id": dompet_id,
        "tanggal": tanggal,
        "keterangan": keterangan_db,
        "uang_masuk": 0,
        "uang_keluar": total_belanja,
        "saldo_akhir_dompet": saldo_baru
    }).execute()

    # --- LOGIKA WHATSAPP SCAN ---
    semua_dompet = supabase.table('dompet').select('*').eq('user_id', user_id).execute().data
    total_aset = sum(d['saldo'] for d in semua_dompet)
    
    aset_str = "{:,.0f}".format(total_aset).replace(',', '.')
    nom_str = "{:,.0f}".format(total_belanja).replace(',', '.')
    
    pesan = f"Halo {session.get('nama_lengkap', 'User')}!\n"
    pesan += f"Ada uang KELUAR *Rp {nom_str}* dari dompet *{nama_dompet}*\n\n"
    pesan += f"Tanggal : {tanggal}\n"
    pesan += f"Catatan : {keterangan_db}\n\n"
    pesan += f"Total Aset Keseluruhan : *Rp {aset_str}*\n"
    
    for d in semua_dompet:
        saldo_str = "{:,.0f}".format(d['saldo']).replace(',', '.')
        pesan += f"- {d['nama_dompet']} : Rp {saldo_str}\n"

    pesan_url = urllib.parse.quote(pesan)
    session['buka_wa'] = f"https://wa.me/?text={pesan_url}"

    return redirect(url_for('index'))


# ==========================================
# ROUTE API LIVE CHAT AI
# ==========================================
@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user_id' not in session:
        return jsonify({"error": "Silakan login dulu"}), 401

    user_id = session['user_id']
    data = request.json
    user_message = data.get('message')

    daftar_dompet = supabase.table('dompet').select('*').eq('user_id', user_id).execute().data
    
    rincian_dompet_str = ""
    total_aset = 0
    for d in daftar_dompet:
        rincian_dompet_str += f"- {d['nama_dompet']}: Rp {d['saldo']}\n"
        total_aset += d['saldo']

    system_prompt = f"""
    Kamu adalah asisten keuangan pribadi yang cerdas. 
    
    INFORMASI DOMPET & KEUANGAN USER SAAT INI:
    {rincian_dompet_str}
    Total Kekayaan Keseluruhan: Rp {total_aset}
    
    ATURAN MENJAWAB:
    1. Jawab santai (bro/sis/aku/kamu).
    2. Berikan saran logis sesuai dompet yang dia miliki. Jika dia nanya mau beli sesuatu, cek dulu apakah total uangnya cukup.
    3. Ringkas dan pakai bullet points.

    Pertanyaan User: "{user_message}"
    """
    
    try:
        prioritas_model = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-2.0-flash']
        model_tersedia = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        model_pilihan = 'gemini-2.5-flash' 
        for model_id in prioritas_model:
            if model_id in model_tersedia:
                model_pilihan = model_id
                break 
                
        model = genai.GenerativeModel(model_pilihan)
        response = model.generate_content(system_prompt)
        return jsonify({"reply": response.text.strip()})
        
    except Exception as e:
        return jsonify({"reply": "Waduh, otak AI-ku lagi nge-blank nih. Error: " + str(e)})


# ==========================================
# ROUTE HAPUS TRANSAKSI
# ==========================================
@app.route('/hapus/<int:id>', methods=['POST'])
def hapus(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    transaksi = supabase.table('transaksi').select('*').eq('id', id).eq('user_id', session['user_id']).execute().data
    
    if transaksi:
        t = transaksi[0]
        dompet_id = t['dompet_id']
        dompet = supabase.table('dompet').select('*').eq('id', dompet_id).execute().data[0]
        saldo_sekarang = dompet['saldo']
        
        saldo_baru = saldo_sekarang - t['uang_masuk'] + t['uang_keluar']
        supabase.table('dompet').update({'saldo': saldo_baru}).eq('id', dompet_id).execute()
        supabase.table('transaksi').delete().eq('id', id).execute()
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
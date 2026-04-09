from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import urllib.parse
import json
import base64
import io
from PIL import Image
import google.generativeai as genai
from config import supabase

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/scan', methods=['GET', 'POST'])
def scan():
    if 'user_id' not in session: return redirect(url_for('auth.login'))

    if request.method == 'POST':
        foto_b64 = request.form.get('foto_base64')
        if not foto_b64: return "Tidak ada file foto", 400

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
            
            if not response: raise Exception("Semua model kena limit. Coba lagi 1 menit kemudian.")

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


@ai_bp.route('/simpan_scan', methods=['POST'])
def simpan_scan():
    if 'user_id' not in session: return redirect(url_for('auth.login'))

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
        return redirect(url_for('keuangan.index'))

    saldo_baru = saldo_sekarang - total_belanja
    supabase.table('dompet').update({'saldo': saldo_baru}).eq('id', dompet_id).execute()

    keterangan_db = f"[Scan AI] Belanja pakai {nama_dompet}\n{rincian_wa}"
    supabase.table('transaksi').insert({
        "user_id": user_id, "dompet_id": dompet_id, "tanggal": tanggal,
        "keterangan": keterangan_db, "uang_masuk": 0, "uang_keluar": total_belanja,
        "saldo_akhir_dompet": saldo_baru
    }).execute()

    semua_dompet = supabase.table('dompet').select('*').eq('user_id', user_id).execute().data
    total_aset = sum(d['saldo'] for d in semua_dompet)
    
    pesan = f"Halo {session.get('nama_lengkap', 'User')}!\nAda uang KELUAR *Rp {'{:,.0f}'.format(total_belanja).replace(',', '.')}* dari dompet *{nama_dompet}*\n\nTanggal : {tanggal}\nCatatan : {keterangan_db}\n\nTotal Aset Keseluruhan : *Rp {'{:,.0f}'.format(total_aset).replace(',', '.')}*\n"
    for d in semua_dompet:
        pesan += f"- {d['nama_dompet']} : Rp {'{:,.0f}'.format(d['saldo']).replace(',', '.')}\n"

    session['buka_wa'] = f"https://wa.me/?text={urllib.parse.quote(pesan)}"
    return redirect(url_for('keuangan.index'))


@ai_bp.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user_id' not in session: return jsonify({"error": "Silakan login dulu"}), 401

    user_id = session['user_id']
    data = request.json
    user_message = data.get('message')

    daftar_dompet = supabase.table('dompet').select('*').eq('user_id', user_id).execute().data
    rincian_dompet_str = "".join([f"- {d['nama_dompet']}: Rp {d['saldo']}\n" for d in daftar_dompet])
    total_aset = sum(d['saldo'] for d in daftar_dompet)

    system_prompt = f"""
    Kamu adalah asisten keuangan pribadi yang cerdas. 
    INFORMASI DOMPET & KEUANGAN USER SAAT INI:
    {rincian_dompet_str}
    Total Kekayaan Keseluruhan: Rp {total_aset}
    ATURAN MENJAWAB:
    1. Jawab santai (bro/sis/aku/kamu).
    2. Berikan saran logis sesuai dompet yang dia miliki.
    3. Ringkas dan pakai bullet points.

    Pertanyaan User: "{user_message}"
    """
    
    try:
        prioritas_model = ['gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-2.0-flash']
        model_tersedia = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_pilihan = next((m for m in prioritas_model if m in model_tersedia), 'gemini-2.5-flash')
                
        model = genai.GenerativeModel(model_pilihan)
        response = model.generate_content(system_prompt)
        return jsonify({"reply": response.text.strip()})
    except Exception as e:
        return jsonify({"reply": f"Waduh, otak AI-ku lagi nge-blank nih. Error: {str(e)}"})
from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import datetime
import urllib.parse
from config import supabase

keuangan_bp = Blueprint('keuangan', __name__)

@keuangan_bp.route('/')
def splash():
    
    return render_template('splash.html')

@keuangan_bp.route('/dashboard')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']

    try:
        dompet_response = supabase.table('dompet').select('*').eq('user_id', user_id).order('id').execute()
        daftar_dompet = dompet_response.data
        total_aset = sum(d['saldo'] for d in daftar_dompet)

        transaksi_response = supabase.table('transaksi').select('*, dompet:dompet_id(nama_dompet)').eq('user_id', user_id).order('id', desc=False).limit(50).execute()
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


@keuangan_bp.route('/tambah_dompet', methods=['POST'])
def tambah_dompet():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    
    nama_dompet = request.form.get('nama_dompet')
    saldo_awal = int(str(request.form.get('saldo_awal') or '0').replace('.', ''))
    target_saldo = int(str(request.form.get('target_saldo') or '0').replace('.', ''))

    supabase.table('dompet').insert({
        "user_id": session['user_id'], "nama_dompet": nama_dompet,
        "saldo": saldo_awal, "target_saldo": target_saldo
    }).execute()
    return redirect(url_for('keuangan.index'))


@keuangan_bp.route('/edit_dompet/<int:id>', methods=['POST'])
def edit_dompet(id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    
    nama_dompet_baru = request.form.get('nama_dompet')
    target_baru = int(str(request.form.get('target_saldo') or '0').replace('.', ''))

    try:
        supabase.table('dompet').update({
            "nama_dompet": nama_dompet_baru,
            "target_saldo": target_baru
        }).eq('id', id).eq('user_id', session['user_id']).execute()
    except Exception as e:
        session['error_msg'] = "Gagal mengedit dompet. Pastikan format isian benar."

    return redirect(url_for('keuangan.index'))


@keuangan_bp.route('/hapus_dompet/<int:id>', methods=['POST'])
def hapus_dompet(id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    
    force_delete = request.form.get('force_delete') == '1'

    try:
        dompet_target = supabase.table('dompet').select('saldo').eq('id', id).eq('user_id', session['user_id']).execute().data
        
        if not dompet_target:
            session['error_msg'] = "Dompet tidak ditemukan."
            return redirect(url_for('keuangan.index'))

        saldo = dompet_target[0]['saldo']

        # Kalau saldo lebih dari 0 dan TIDAK maksa hapus, batalkan dan kasih error
        if saldo > 0 and not force_delete:
            session['error_msg'] = f"Gagal! Dompet ini masih punya saldo Rp {'{:,.0f}'.format(saldo).replace(',', '.')}. Kosongkan dulu atau pilih 'Hapus Bersama Saldo'."
            return redirect(url_for('keuangan.index'))

        # Jika saldo 0 atau force_delete = True, hajar hapus!
        # (Pastikan relasi di Supabase sudah CASCADE)
        supabase.table('dompet').delete().eq('id', id).eq('user_id', session['user_id']).execute()

    except Exception as e:
        session['error_msg'] = f"Terjadi kesalahan saat menghapus dompet: {str(e)}"

    return redirect(url_for('keuangan.index'))


@keuangan_bp.route('/tambah', methods=['POST'])
def tambah():
    if 'user_id' not in session: return redirect(url_for('auth.login'))

    user_id = session['user_id']
    tanggal = request.form.get('tanggal')
    jenis = request.form.get('jenis')
    keterangan = request.form.get('keterangan')
    uang_masuk = int(str(request.form.get('uang_masuk') or '0').replace('.', ''))
    uang_keluar = int(str(request.form.get('uang_keluar') or '0').replace('.', ''))
    
    nama_dompet_wa = ""
    nama_dompet_tujuan_wa = ""
    
    if jenis in ['Pemasukan', 'Pengeluaran']:
        dompet_id = request.form.get('dompet_id')
        dompet_data = supabase.table('dompet').select('*').eq('id', dompet_id).execute().data[0]
        saldo_sekarang = dompet_data['saldo']
        nama_dompet_wa = dompet_data['nama_dompet']

        if jenis == 'Pengeluaran' and saldo_sekarang < uang_keluar:
            session['error_msg'] = f"Gagal: Saldo {nama_dompet_wa} tidak cukup!"
            return redirect(url_for('keuangan.index'))

        saldo_baru = saldo_sekarang + uang_masuk if jenis == 'Pemasukan' else saldo_sekarang - uang_keluar
        supabase.table('dompet').update({'saldo': saldo_baru}).eq('id', dompet_id).execute()

        keterangan_full = f"[{jenis}] {keterangan}"
        supabase.table('transaksi').insert({
            "user_id": user_id, "dompet_id": dompet_id, "tanggal": tanggal,
            "keterangan": keterangan_full, "uang_masuk": uang_masuk,
            "uang_keluar": uang_keluar, "saldo_akhir_dompet": saldo_baru
        }).execute()

    elif jenis == 'Transfer':
        dompet_asal_id = request.form.get('dompet_asal_id')
        dompet_tujuan_id = request.form.get('dompet_tujuan_id')
        nominal_transfer = uang_keluar

        if dompet_asal_id == dompet_tujuan_id:
            session['error_msg'] = "Gagal: Dompet asal dan tujuan tidak boleh sama!"
            return redirect(url_for('keuangan.index'))

        dompet_asal = supabase.table('dompet').select('*').eq('id', dompet_asal_id).execute().data[0]
        dompet_tujuan = supabase.table('dompet').select('*').eq('id', dompet_tujuan_id).execute().data[0]
        nama_dompet_wa = dompet_asal['nama_dompet']
        nama_dompet_tujuan_wa = dompet_tujuan['nama_dompet']

        if dompet_asal['saldo'] < nominal_transfer:
            session['error_msg'] = f"Gagal: Saldo {nama_dompet_wa} tidak cukup untuk transfer!"
            return redirect(url_for('keuangan.index'))

        saldo_baru_asal = dompet_asal['saldo'] - nominal_transfer
        saldo_baru_tujuan = dompet_tujuan['saldo'] + nominal_transfer

        supabase.table('dompet').update({'saldo': saldo_baru_asal}).eq('id', dompet_asal_id).execute()
        supabase.table('dompet').update({'saldo': saldo_baru_tujuan}).eq('id', dompet_tujuan_id).execute()

        supabase.table('transaksi').insert([
            {"user_id": user_id, "dompet_id": dompet_asal_id, "tanggal": tanggal, "keterangan": f"[Transfer Keluar] Ke {nama_dompet_tujuan_wa} - {keterangan}", "uang_masuk": 0, "uang_keluar": nominal_transfer, "saldo_akhir_dompet": saldo_baru_asal},
            {"user_id": user_id, "dompet_id": dompet_tujuan_id, "tanggal": tanggal, "keterangan": f"[Transfer Masuk] Dari {nama_dompet_wa} - {keterangan}", "uang_masuk": nominal_transfer, "uang_keluar": 0, "saldo_akhir_dompet": saldo_baru_tujuan}
        ]).execute()

    # --- LOGIKA WHATSAPP V2 ---
    semua_dompet = supabase.table('dompet').select('*').eq('user_id', user_id).execute().data
    total_aset = sum(d['saldo'] for d in semua_dompet)
    
    pesan = f"Halo {session.get('nama_lengkap', 'User')}!\n"
    if jenis == 'Transfer':
        pesan += f"Ada 🔄 *TRANSFER Rp {'{:,.0f}'.format(uang_keluar).replace(',', '.')}*\nDari *{nama_dompet_wa}* ke *{nama_dompet_tujuan_wa}*\n"
    else:
        pesan += f"Ada uang {'MASUK' if jenis == 'Pemasukan' else 'KELUAR'} *Rp {'{:,.0f}'.format(uang_masuk if jenis == 'Pemasukan' else uang_keluar).replace(',', '.')}* di dompet *{nama_dompet_wa}*\n"
    
    pesan += f"Tanggal : {tanggal}\nCatatan : {keterangan}\n\nTotal Aset Keseluruhan : *Rp {'{:,.0f}'.format(total_aset).replace(',', '.')}*\n"
    for d in semua_dompet:
        pesan += f"- {d['nama_dompet']} : Rp {'{:,.0f}'.format(d['saldo']).replace(',', '.')}\n"

    session['buka_wa'] = f"https://wa.me/?text={urllib.parse.quote(pesan)}"
    return redirect(url_for('keuangan.index'))


@keuangan_bp.route('/hapus/<int:id>', methods=['POST'])
def hapus(id):
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    
    transaksi = supabase.table('transaksi').select('*').eq('id', id).eq('user_id', session['user_id']).execute().data
    if transaksi:
        t = transaksi[0]
        dompet_id = t['dompet_id']
        dompet = supabase.table('dompet').select('*').eq('id', dompet_id).execute().data[0]
        
        saldo_baru = dompet['saldo'] - t['uang_masuk'] + t['uang_keluar']
        supabase.table('dompet').update({'saldo': saldo_baru}).eq('id', dompet_id).execute()
        supabase.table('transaksi').delete().eq('id', id).execute()
        
    return redirect(url_for('keuangan.index'))
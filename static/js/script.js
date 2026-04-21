// --- FORMAT RUPIAH TITIK ---
function formatUang(input) {
    let value = input.value.replace(/[^0-9]/g, '');
    input.value = value.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// Bersihkan titik sebelum submit
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function() {
        const inputs = form.querySelectorAll('input[inputmode="numeric"]');
        inputs.forEach(inp => {
            if (inp.value) inp.value = inp.value.replace(/\./g, '');
        });
    });
});

// --- MENU TITIK TIGA ---
function toggleMenu(id, event) {
    event.stopPropagation();
    const menus = document.querySelectorAll('.menu-dropdown');
    menus.forEach(m => { if (m.id !== 'menu-' + id) m.classList.remove('show'); });
    document.getElementById('menu-' + id).classList.toggle('show');
}

document.addEventListener('click', function(e) {
    document.querySelectorAll('.menu-dropdown').forEach(m => m.classList.remove('show'));
});

// --- MODAL ANIMASI ---
function bukaEditModal(id, nama, target, event) {
    event.preventDefault();
    const targetFormat = target > 0 ? target.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".") : "";
    document.getElementById('editNama').value = nama;
    document.getElementById('editTarget').value = targetFormat;
    document.getElementById('formEditDompet').action = '/edit_dompet/' + id;
    document.getElementById('modalEdit').classList.add('active');
}

function bukaHapusModal(id, nama, saldo, event) {
    event.preventDefault();
    document.getElementById('hapusNama').innerText = nama;
    document.getElementById('formHapusDompet').action = '/hapus_dompet/' + id;
    
    const warningText = document.getElementById('hapusWarningText');
    const forceInput = document.getElementById('forceDeleteInput');
    
    if (saldo > 0) {
        warningText.innerHTML = `⚠️ <br>Dompet ini masih berisi saldo <b>Rp ${saldo.toLocaleString('id-ID')}</b>!<br><br><span style="color: #ff6b6b; font-size: 0.8rem;">Apakah kamu yakin ingin menghapus dompet beserta seluruh saldo dan riwayat transaksinya? Uang ini akan dianggap hangus.</span>`;
        forceInput.value = "1"; // Kirim flag force delete
    } else {
        warningText.innerHTML = `<span style="color: #ff6b6b; font-size: 0.8rem;">Semua riwayat transaksi yang pakai dompet ini akan ikut terhapus permanen!</span>`;
        forceInput.value = "0";
    }

    document.getElementById('modalHapus').classList.add('active');
}

function tutupModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// --- FORM TRANSAKSI DINAMIS ---
document.addEventListener('DOMContentLoaded', function () {
    const jenisSelect = document.getElementById('jenisSelect');
    const dompetSelect = document.getElementById('dompetSelect');
    const dompetAsalSelect = document.getElementById('dompetAsalSelect');
    const dompetTujuanSelect = document.getElementById('dompetTujuanSelect');
    const inputMasuk = document.getElementById('inputMasuk');
    const inputKeluar = document.getElementById('inputKeluar');

    if (jenisSelect) {
        jenisSelect.addEventListener('change', function () {
            const jenis = this.value;
            dompetSelect.style.display = 'none'; dompetSelect.required = false;
            dompetAsalSelect.style.display = 'none'; dompetAsalSelect.required = false;
            dompetTujuanSelect.style.display = 'none'; dompetTujuanSelect.required = false;
            inputMasuk.style.display = 'none'; inputMasuk.disabled = true; inputMasuk.required = false; inputMasuk.value = '';
            inputKeluar.style.display = 'none'; inputKeluar.disabled = true; inputKeluar.required = false; inputKeluar.value = '';

            if (jenis === 'Pemasukan') {
                dompetSelect.style.display = 'block'; dompetSelect.required = true;
                inputMasuk.style.display = 'block'; inputMasuk.disabled = false; inputMasuk.required = true;
            } else if (jenis === 'Pengeluaran') {
                dompetSelect.style.display = 'block'; dompetSelect.required = true;
                inputKeluar.style.display = 'block'; inputKeluar.disabled = false; inputKeluar.required = true;
                inputKeluar.placeholder = "Nominal Keluar (Rp)";
            } else if (jenis === 'Transfer') {
                dompetAsalSelect.style.display = 'block'; dompetAsalSelect.required = true;
                dompetTujuanSelect.style.display = 'block'; dompetTujuanSelect.required = true;
                inputKeluar.style.display = 'block'; inputKeluar.disabled = false; inputKeluar.required = true;
                inputKeluar.placeholder = "Nominal Transfer (Rp)";
            }
        });
    }
});

// --- LIVE CHAT AI ---
// --- LIVE CHAT AI ---
function toggleChat() { document.getElementById('chatPanel').classList.toggle('active'); }

// Fungsi auto-resize untuk Textarea
const chatInput = document.getElementById('chatInput');
if(chatInput) {
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto'; // KUNCI: Reset ke auto dulu
        this.style.height = (this.scrollHeight) + 'px'; // Baru ukur tinggi aslinya
    });
}

function handleEnter(e) { 
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault(); 
        kirimPesan(); 
    }
}

async function kirimPesan() {
    const inputField = document.getElementById('chatInput');
    const chatBody = document.getElementById('chatBody');
    const pesanUser = inputField.value.trim();
    if (!pesanUser) return;

    chatBody.innerHTML += `<div class="msg user">${pesanUser.replace(/\n/g, '<br>')}</div>`; 
    
    // Reset isi dan tinggi textarea kembali ke ukuran awal setelah kirim
    inputField.value = '';
    inputField.style.height = 'auto'; // Reset form
    chatBody.scrollTop = chatBody.scrollHeight;

    const typingId = "typing-" + Date.now();
    chatBody.innerHTML += `<div class="msg bot" id="${typingId}">Sedang mikir... 🤔</div>`;
    chatBody.scrollTop = chatBody.scrollHeight;

    try {
        const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: pesanUser }) });
        const data = await response.json();
        document.getElementById(typingId).remove();
        
        let reply = data.reply.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
        chatBody.innerHTML += `<div class="msg bot">${reply}</div>`;
        chatBody.scrollTop = chatBody.scrollHeight;
    } catch (error) {
        document.getElementById(typingId).remove();
        chatBody.innerHTML += `<div class="msg bot" style="color:#ff6b6b;">Koneksi error nih, coba lagi ya.</div>`;
    }
}

// --- FUNGSI EXPORT KE EXCEL ---
function prosesExport(jenis) {
    // Gunakan window.rawDompet yang sudah dilempar dari HTML
    const dataDompet = window.rawDompet.map(d => ({
        "ID Dompet": d.id,
        "Nama Dompet/Kategori": d.nama_dompet,
        "Saldo Saat Ini (Rp)": d.saldo,
        "Target Saldo (Rp)": d.target_saldo || 0
    }));

    // Gunakan window.rawTransaksi
    const dataTransaksi = window.rawTransaksi.map(t => ({
        "Tanggal": t.tanggal,
        "Dompet Terpakai": t.nama_dompet,
        "Keterangan": t.keterangan.replace(/\n/g, ' | '), 
        "Uang Masuk (Rp)": t.uang_masuk,
        "Uang Keluar (Rp)": t.uang_keluar,
        "Sisa Saldo di Dompet (Rp)": t.saldo_akhir_dompet
    }));

    const wb = XLSX.utils.book_new();

    if (jenis === 'all' || jenis === 'wallet') {
        const wsDompet = XLSX.utils.json_to_sheet(dataDompet);
        XLSX.utils.book_append_sheet(wb, wsDompet, "Ringkasan Dompet");
    }
    if (jenis === 'all' || jenis === 'history') {
        const wsTransaksi = XLSX.utils.json_to_sheet(dataTransaksi);
        XLSX.utils.book_append_sheet(wb, wsTransaksi, "Riwayat Transaksi");
    }

    const tanggalSekarang = new Date().toISOString().split('T')[0];
    XLSX.writeFile(wb, `Laporan_Keuangan_${jenis}_${tanggalSekarang}.xlsx`);
    
    tutupModal('modalExport');
}

// --- FUNGSI SHARE SALDO KE WHATSAPP ---
function shareWA() {
    let totalAset = 0;
    let teksWA = `*Laporan Saldo Terkini*\nTanggal: ${new Date().toLocaleDateString('id-ID')}\n\n`;
    
    window.rawDompet.forEach(d => {
        teksWA += `👛 *${d.nama_dompet}*: Rp ${d.saldo.toLocaleString('id-ID')}\n`;
        totalAset += d.saldo;
    });
    
    teksWA += `\n💰 *Total Aset: Rp ${totalAset.toLocaleString('id-ID')}*`;
    
    window.open(`https://wa.me/?text=${encodeURIComponent(teksWA)}`, '_blank');
    tutupModal('modalExport');
}
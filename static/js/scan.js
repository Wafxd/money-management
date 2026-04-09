// static/js/scan.js
document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const previewImg = document.getElementById('previewImg');
    const startBtn = document.getElementById('startBtn');
    const snapBtn = document.getElementById('snapBtn');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileInput');
    const scanForm = document.getElementById('scanForm');
    const fotoBase64 = document.getElementById('fotoBase64');
    const controls = document.getElementById('controls');
    const submitBtn = document.getElementById('submitBtn');
    const loading = document.getElementById('loading');

    // Nyalakan Kamera
    if(startBtn) {
        startBtn.addEventListener('click', async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
                video.srcObject = stream;
                video.style.display = 'block';
                startBtn.style.display = 'none';
                uploadBtn.style.display = 'none';
                snapBtn.style.display = 'block';
                document.querySelector('.container p').style.display = 'none';
                document.querySelector('.container div[style*="margin: 20px"]').style.display = 'none';
            } catch (err) {
                alert("Kamera tidak bisa diakses! Pastikan kamu memberi izin browser.");
            }
        });
    }

    // Ambil Foto dari Kamera
    if(snapBtn) {
        snapBtn.addEventListener('click', () => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
            
            video.srcObject.getTracks().forEach(track => track.stop());
            video.style.display = 'none';
            showPreview(dataUrl);
        });
    }

    // Pilih Foto dari Galeri
    if(fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    showPreview(event.target.result);
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Tampilkan Preview sebelum kirim
    function showPreview(dataUrl) {
        previewImg.src = dataUrl;
        previewImg.style.display = 'block';
        controls.style.display = 'none';
        scanForm.style.display = 'block';
        fotoBase64.value = dataUrl;
        
        const pTag = document.querySelector('.container p');
        if(pTag) pTag.style.display = 'none';
    }

    // Tampilkan Loading saat klik kirim
    if(scanForm) {
        scanForm.addEventListener('submit', () => {
            submitBtn.style.display = 'none';
            const btnBatal = document.querySelector('button[onclick="location.reload()"]');
            if(btnBatal) btnBatal.style.display = 'none';
            loading.style.display = 'block';
        });
    }
});
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
                // Minta resolusi yang nggak terlalu raksasa dari kamera HP
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } } 
                });
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

    // Ambil Foto dari Kamera & KOMPRES
    if(snapBtn) {
        snapBtn.addEventListener('click', () => {
            const MAX_WIDTH = 1200; // Batasi lebar maksimal
            let width = video.videoWidth;
            let height = video.videoHeight;

            // Hitung rasio biar foto ga gepeng
            if (width > MAX_WIDTH) {
                height *= MAX_WIDTH / width;
                width = MAX_WIDTH;
            }

            canvas.width = width;
            canvas.height = height;
            canvas.getContext('2d').drawImage(video, 0, 0, width, height);
            
            // Kompres jadi JPEG dengan kualitas 70% (Biar ukuran file turun drastis)
            const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
            
            video.srcObject.getTracks().forEach(track => track.stop());
            video.style.display = 'none';
            showPreview(dataUrl);
        });
    }

    // Pilih Foto dari Galeri & KOMPRES
    if(fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    const img = new Image();
                    img.onload = () => {
                        const MAX_WIDTH = 1200; // Batasi ukuran foto galeri HP
                        const MAX_HEIGHT = 1200;
                        let width = img.width;
                        let height = img.height;

                        if (width > height) {
                            if (width > MAX_WIDTH) {
                                height *= MAX_WIDTH / width;
                                width = MAX_WIDTH;
                            }
                        } else {
                            if (height > MAX_HEIGHT) {
                                width *= MAX_HEIGHT / height;
                                height = MAX_HEIGHT;
                            }
                        }

                        canvas.width = width;
                        canvas.height = height;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0, width, height);
                        
                        // Kompres jadi JPEG dengan kualitas 70%
                        const dataUrl = canvas.toDataURL('image/jpeg', 0.7);
                        showPreview(dataUrl);
                    };
                    img.src = event.target.result;
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
// Fungsi untuk memunculkan layar loading animasi saat tombol diklik
function tampilkanLoader(pesan) {
    const loaderText = document.getElementById('loaderText');
    const loaderOverlay = document.getElementById('loaderOverlay');
    
    // Pastikan elemennya ada di HTML sebelum diubah
    if(loaderText && loaderOverlay) {
        loaderText.innerText = pesan;
        loaderOverlay.classList.add('active');
    }
}
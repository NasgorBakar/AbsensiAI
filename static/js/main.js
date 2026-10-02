// Main helper JS for AbsensiAI
console.log("AbsensiAI System Loaded");

// Helper untuk format tanggal dan waktu Indonesia
function formatWaktuIndo(dateObj) {
    if (!dateObj) dateObj = new Date();
    return dateObj.toLocaleTimeString('id-ID', { hour12: false });
}

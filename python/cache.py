# cache.py - Modul terpisah untuk semua manajemen caching aplikasi

import utils 

def clear_all_caches():
    """
    Membersihkan semua cache aplikasi yang terdaftar,
    termasuk cache dari fungsi I/O berat seperti utils.list_dir.
    """
    print("\n--- 🧹 Membersihkan Cache Aplikasi ---")
    
    # 1. Membersihkan cache I/O File dari utils.list_dir
    try:
        # Panggil method cache_clear() pada fungsi list_dir yang sudah didekorasi
        utils.list_dir.cache_clear()
        print("✅ CACHE CLEARED: list_dir cache berhasil dibersihkan.")
    except AttributeError:
        # Jika utils.list_dir belum didekorasi dengan @lru_cache, 
        # atau modul utils belum selesai diimpor/disuntikkan.
        print("⚠️ Gagal membersihkan list_dir cache. Fungsi belum didekorasi atau diinisialisasi.")
    
    # Tambahkan pembersihan cache dari modul lain di masa depan di sini
    # Contoh: lazy.clear_lazy_results_cache() 
    
    print("--- ✅ Pembersihan Cache Selesai ---")

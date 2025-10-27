document.addEventListener('DOMContentLoaded', function() {
    const fileList = document.getElementById('file-list');
    const gridToggle = document.getElementById('grid-toggle');
    const backButton = document.getElementById('back-button');
    const menuToggle = document.getElementById('menu-toggle'); 
    const menuOverlay = document.getElementById('menu-overlay');
    const closeMenuButton = document.getElementById('close-menu');
    const browserLink = document.getElementById('browser-link'); 
    const menuModal = document.querySelector('.menu-modal');

    let pressTimer;
    const LONG_PRESS_THRESHOLD = 500; 
    let isSelecting = false;
    let isClipboardPopulated = false; // State untuk mengaktifkan Paste
    let selectionMode = 0; // 0: Normal, 1: Seleksi Tunggal, 2: Seleksi Penuh
    
    // --- FUNGSI UTILITY ---
    function getAllItems() {
        return document.querySelectorAll('.file-item');
    }

    function getSelectedItems() {
        return document.querySelectorAll('.file-item.selected');
    }
    
    // FUNGSI BARU: Mengubah ikon MenuToggle
    function setMenuToggleIcon(iconClass, enabled = true) {
        menuToggle.querySelector('i').className = iconClass;
        menuToggle.style.pointerEvents = enabled ? 'auto' : 'none'; 
        menuToggle.style.opacity = enabled ? '1' : '0.5'; 
    }

    function updateSelectionCount() {
        const selectedCount = getSelectedItems().length;
        const totalCount = getAllItems().length;
        const selectionBar = document.getElementById('browser-link').querySelector('i');
        
        if (selectedCount > 0) {
            selectionBar.className = 'fas fa-bars'; // Hamburger
            // Jika Anda ingin menampilkan jumlah di footer:
            // document.getElementById('browser-link').querySelector('span').textContent = `${selectedCount}`;
        } else if (isClipboardPopulated) {
             selectionBar.className = 'fas fa-paste'; // Paste
        } else {
            selectionBar.className = 'fas fa-globe'; // Default Browser
        }

        // Kontrol Menu Toggle (fas fa-plus vs fas fa-check)
        if (isSelecting) {
            if (selectedCount === totalCount && totalCount > 0) {
                 setMenuToggleIcon('fas fa-check-double');
                 selectionMode = 2;
            } else if (selectedCount > 0) {
                 setMenuToggleIcon('fas fa-check');
                 selectionMode = 1;
            } else {
                 setMenuToggleIcon('fas fa-check'); // Tetap di check, tapi tidak terseleksi
                 selectionMode = 1;
            }
        }
    }

    function toggleSelectionMode(activate) {
        isSelecting = activate;
        fileList.classList.toggle('selecting', activate);
        
        // Atur ulang ikon dan mode jika nonaktif
        if (!activate) {
            getSelectedItems().forEach(item => item.classList.remove('selected'));
            selectionMode = 0;
            setMenuToggleIcon('fas fa-plus', true);
            updateSelectionCount();
        }
    }

    function toggleMenu(show) {
        menuOverlay.style.display = show ? 'flex' : 'none';
        setTimeout(() => {
            menuOverlay.classList.toggle('active', show);
        }, 10);
    }

    // --- 1. NONAKTIFKAN CONTEXT MENU MOBILE (TEKAN LAMA) ---
    document.addEventListener('contextmenu', function(e) {
        if ('ontouchstart' in window) { 
             e.preventDefault();
        }
    });

    // --- 2. GRID/LIST VIEW TOGGLE (LOGIC UTAMA) ---
    function loadViewPreference() {
        const view = localStorage.getItem('viewMode') || 'list-view';
        if (view === 'grid-view') {
            fileList.classList.remove('list-view');
            fileList.classList.add('grid-view');
            gridToggle.querySelector('i').className = 'fas fa-list';
            document.getElementById('view-label').textContent = 'List';
        } else {
            fileList.classList.remove('grid-view');
            fileList.classList.add('list-view');
            gridToggle.querySelector('i').className = 'fas fa-th-large';
            document.getElementById('view-label').textContent = 'Grid';
        }
    }
    
    // Inisialisasi tampilan
    loadViewPreference();

    gridToggle.addEventListener('click', function(e) {
        e.preventDefault();
        const isGridView = fileList.classList.contains('grid-view');
        
        if (isGridView) {
            fileList.classList.remove('grid-view');
            fileList.classList.add('list-view');
            gridToggle.querySelector('i').className = 'fas fa-th-large';
            document.getElementById('view-label').textContent = 'Grid';
            localStorage.setItem('viewMode', 'list-view');
        } else {
            fileList.classList.remove('list-view');
            fileList.classList.add('grid-view');
            gridToggle.querySelector('i').className = 'fas fa-list';
            document.getElementById('view-label').textContent = 'List';
            localStorage.setItem('viewMode', 'grid-view');
        }
    });

    // --- 3. SELEKSI (TEKAN LAMA & KLIK) ---
    fileList.addEventListener('mousedown', startPress);
    fileList.addEventListener('mouseup', endPress);
    fileList.addEventListener('touchstart', startPress);
    fileList.addEventListener('touchend', endPress);
    fileList.addEventListener('click', handleItemClick, true); // Tangkap klik di fase capture

    function startPress(e) {
        if (e.target.closest('.file-item')) {
            const item = e.target.closest('.file-item');
            clearTimeout(pressTimer);
            
            // Hanya mulai timer jika tidak sedang menyeleksi atau di mode normal
            if (!isSelecting) {
                pressTimer = setTimeout(function() {
                    handleLongPress(item, e);
                }, LONG_PRESS_THRESHOLD);
            }
        }
    }

    function endPress() {
        clearTimeout(pressTimer);
    }

    function handleLongPress(item, event) {
        event.preventDefault(); // Mencegah tindakan default browser (seperti membuka link)
        if (!isSelecting) {
            toggleSelectionMode(true);
            item.classList.add('selected');
            updateSelectionCount();
        }
    }

    function handleItemClick(e) {
        const item = e.target.closest('.file-item');
        if (!item) return;

        // Jika sedang dalam mode seleksi
        if (isSelecting) {
            e.preventDefault(); // Blok navigasi
            e.stopPropagation(); // Hentikan event agar tidak memicu link
            
            item.classList.toggle('selected');
            
            // Jika semua item dibatalkan seleksi, keluar dari mode seleksi
            if (getSelectedItems().length === 0) {
                 // Tidak langsung keluar, biarkan user tetap di mode seleksi
            }
            updateSelectionCount();
        } 
        // Jika tidak dalam mode seleksi, biarkan event berlanjut (membuka link)
    }

    // --- 4. NAVIGASI LAIN ---
    // Tombol Kembali
    if (backButton) {
        backButton.addEventListener('click', function(e) {
            e.preventDefault();
            const currentPath = document.getElementById('current-path-display').textContent;
            const parentPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/';
            // Hindari navigasi ke path yang sama jika sudah di root
            if (parentPath !== currentPath) {
                window.location.href = `/?path=${parentPath}`;
            }
        });
    }

    // --- 5. LOGIKA MENU TOGGLE (BARU) ---
    menuToggle.addEventListener('click', function(e) {
        e.preventDefault();
        
        if (!isSelecting) {
             // Jika tidak menyeleksi, buka menu utama (Menu Aksi Normal)
             toggleMenu(true);
             return;
        }

        // --- Logika Seleksi Massal saat MenuToggle di mode ceklis ---
        const allItems = getAllItems(); // Ambil semua item untuk diseleksi

        if (selectionMode === 1) { // Status Ceklis Tunggal (fas fa-check): Seleksi Penuh
            // Pilih semua item
            allItems.forEach(item => item.classList.add('selected'));
            selectionMode = 2;
            setMenuToggleIcon('fas fa-check-double');
        } else if (selectionMode === 2) { // Status Ceklis Ganda (fas fa-check-double): Batalkan Seleksi Penuh
            // Batalkan semua seleksi dan keluar mode seleksi
            allItems.forEach(item => item.classList.remove('selected'));
            selectionMode = 0; 
            toggleSelectionMode(false); // Keluar dari mode seleksi sepenuhnya
        }
        
        // Setelah aksi seleksi, update Menu Hamburger
        updateSelectionCount(); 
    });
    
    // Tombol BROWSER/HAMBURGER (Menu Aksi Seleksi/Paste)
    browserLink.addEventListener('click', function(e) {
        e.preventDefault();
        if (!isSelecting && !isClipboardPopulated) {
            alert('Membuka link Browser/Dunia!');
            // window.location.href = 'URL_BROWSER_DEFAULT'; 
        } else {
            // Jika ada yang terseleksi atau clipboard terisi, buka Menu Aksi
            toggleMenu(true);
        } 
    });

    // Menutup Menu
    closeMenuButton.addEventListener('click', function() {
        toggleMenu(false);
    });

    menuOverlay.addEventListener('click', function(e) {
        if (e.target.id === 'menu-overlay') {
            toggleMenu(false);
        }
    });

    // --- 6. MENU OVERLAY ACTIONS (Perlu diisi dengan aksi nyata nanti) ---
    // Di sini Anda akan menambahkan event listeners untuk tombol-tombol di dalam menu-list.
    // Contoh: document.getElementById('delete-selected').addEventListener('click', handleDelete);
});

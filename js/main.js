document.addEventListener('DOMContentLoaded', function() {
    const fileList = document.getElementById('file-list');
    const currentPathCode = document.getElementById('current-path-code'); // ID Baru untuk Path
    const gridToggle = document.getElementById('grid-toggle');
    const backButton = document.getElementById('back-button');
    const homeButton = document.getElementById('home-button'); // ID Baru untuk Tombol Home
    const menuToggle = document.getElementById('menu-toggle'); 
    const menuOverlay = document.getElementById('menu-overlay');
    const closeMenuButton = document.getElementById('close-menu');
    const browserLink = document.getElementById('browser-link'); 
    const menuModal = document.querySelector('.menu-modal');

    let pressTimer;
    const LONG_PRESS_THRESHOLD = 500; 
    let isSelecting = false;
    let isClipboardPopulated = false; // State untuk mengaktifkan Paste
    
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

    // FUNGSI BARU: Membuat elemen item file dari data JSON
    function createItemElement(file) {
        // Logika MyDrive pintasan tidak perlu diulang di JS, biarkan server yang menanganinya
        const path = file.full_path;
        const iconClass = file.icon_class;
        const isDir = file.is_dir;
        
        const wrapper = document.createElement(isDir ? 'a' : 'div');
        wrapper.className = `file-item ${isDir ? 'file-folder js-folder-link' : 'file-file js-file-item'}`;
        
        // HANYA folder yang mendapatkan href="#" untuk mencegah navigasi default
        if (isDir) { wrapper.href = '#'; }

        wrapper.setAttribute('data-path', path);

        wrapper.innerHTML = `
            <span class="file-name-absolute" title="${file.name}">${file.name}</span>
            <i class="fas ${iconClass} fa-fw"></i>
            <span class="file-size-absolute">${file.size}</span>
            <div class="file-text-container">
                <span class="file-name">${file.name}</span>
                <span class="file-size">${file.size}</span>
            </div>
        `;
        return wrapper;
    }

    // FUNGSI BARU: Merender ulang daftar file setelah fetch data
    function renderFileList(data) {
        fileList.innerHTML = ''; // Kosongkan daftar yang lama
        
        // 1. Update Path di Header
        currentPathCode.textContent = data.current_path;
        
        // 2. Render item baru
        data.files.forEach(file => {
            const item = createItemElement(file);
            fileList.appendChild(item);
        });
        
        // 3. Terapkan View Mode yang tersimpan
        setView(isGridView); 
        
        // 4. Reset mode seleksi
        toggleSelectionMode(false);
        
        // 5. Update URL di browser history
        const url = `/?path=${encodeURIComponent(data.current_path)}`;
        window.history.pushState({path: data.current_path}, '', url);
    }
    
    // FUNGSI INTI AJAX: Mengambil data folder dari server
    async function fetchDirData(path) {
        // Sembunyikan daftar file lama saat memuat
        fileList.style.opacity = 0.5;
        
        try {
            const encodedPath = encodeURIComponent(path);
            const response = await fetch(`/api/data?path=${encodedPath}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                renderFileList(data);
            } else {
                alert(`Gagal memuat folder: ${data.message || 'Error tidak diketahui'}`);
            }
        } catch (error) {
            console.error('Error fetching directory data:', error);
            alert(`Terjadi kesalahan jaringan atau server: ${error.message}`);
        } finally {
            fileList.style.opacity = 1; // Tampilkan kembali
        }
    }


    // --- 1. NONAKTIFKAN CONTEXT MENU MOBILE (TEKAN LAMA) ---
    document.addEventListener('contextmenu', function(e) {
        if ('ontouchstart' in window) { 
             e.preventDefault();
        }
    });

    // --- 2. LOGIKA SELEKSI & MENU DINAMIS (TIDAK BERUBAH) ---
    // ... (Fungsi handleSelectionAction, updateSelectionMenu, updateSelectionCount, toggleSelectionMode, toggleItemSelection tetap sama) ...
    function handleSelectionAction(actionId, count) {
        // ... (Logika yang sama) ...
        let message = '';
        let shouldCloseModal = true; 
        
        const selectedItems = getSelectedItems();
        const selectedPaths = Array.from(selectedItems).map(item => 
            item.getAttribute('data-path') || item.getAttribute('href')
        ).filter(path => path);

        switch(actionId) {
            case 'selection-copy':
                message = `Menyalin ${count} item! (Siap untuk Tempel)`;
                isClipboardPopulated = true; 
                break;
            case 'selection-move':
                message = `Memotong ${count} item! (Siap untuk Tempel)`;
                isClipboardPopulated = true; 
                break;
            case 'selection-paste':
                message = `Tempel item dari clipboard ke ${document.getElementById('current-path-code').textContent.trim()}!`;
                isClipboardPopulated = false; 
                
                // PENTING: Panggil pembatalan cache setelah operasi penulisan
                fetch('/api/clear-cache', { method: 'POST' }); 
                
                break;
            case 'selection-slideshow':
                message = `Memulai Slideshow untuk ${count} gambar!`;
                break;
            case 'selection-delete':
                if (confirm(`Yakin ingin menghapus ${count} item yang terpilih?\nPaths:\n${selectedPaths.join('\n')}`)) {
                    message = `Menghapus ${count} item!`;
                    // fetch('/api/delete', { method: 'POST', body: JSON.stringify({ paths: selectedPaths }) })
                    
                    // PENTING: Panggil pembatalan cache setelah operasi penulisan
                    fetch('/api/clear-cache', { method: 'POST' }); 

                } else {
                    return;
                }
                break;
            case 'selection-compress':
                message = `Compress ${count} item!`;
                break;
            case 'selection-extract':
                message = `Extract file kompresi!`;
                break;
            default:
                message = `Aksi ${actionId} dipanggil.`;
        }
        
        alert(message);
        
        if (shouldCloseModal) {
            document.querySelectorAll('.file-item.selected').forEach(sel => sel.classList.remove('selected'));
            toggleSelectionMode(false); 
        }
    }

    // ... (Semua fungsi menu dan seleksi lainnya tetap sama) ...
    function updateSelectionMenu() {
        // ... (Logika yang sama) ...
    }
    
    let selectionMode = 0; 

    function updateSelectionCount(shouldUpdateMenu = true) {
        // ... (Logika yang sama) ...
    }

    function toggleSelectionMode(enable) {
        // ... (Logika yang sama) ...
    }
    
    function toggleItemSelection(item) {
        // ... (Logika yang sama) ...
    }
    
    // ... (Logika Touch dan Mouse Events tetap sama) ...
    fileList.addEventListener('touchstart', function(e) {
        const item = e.target.closest('.file-item');
        if (!item) return;
        
        clearTimeout(pressTimer);
        pressTimer = setTimeout(() => {
            if (!isSelecting) {
                e.preventDefault(); 
                toggleSelectionMode(true);
                toggleItemSelection(item); 
            }
        }, LONG_PRESS_THRESHOLD);
    });

    fileList.addEventListener('touchend', function(e) {
        clearTimeout(pressTimer);
    });
    
    fileList.addEventListener('touchcancel', function(e) {
        clearTimeout(pressTimer);
    });
    
    // --- PERUBAHAN UTAMA: KLIK ITEM (Folder Link) ---
    fileList.addEventListener('click', function(e) {
         const item = e.target.closest('.file-item');
         if (!item) return;
         
         if (isSelecting) {
             e.preventDefault(); 
             toggleItemSelection(item);
         } else if (pressTimer) {
             clearTimeout(pressTimer);
         }
         
         // Logika AJAX untuk link folder
         if (item.classList.contains('js-folder-link')) {
             e.preventDefault(); // Cegah navigasi browser
             const path = item.getAttribute('data-path');
             if (path) {
                 fetchDirData(path);
             }
         }
    });
    // ... (Mouse Events lainnya tetap sama) ...


    // --- 3. KLIK DI LUAR ITEM (KELUAR MODE SELEKSI) ---
    document.addEventListener('click', function(e) {
        const isOutsideSelectionArea = !e.target.closest('.file-item') && !e.target.closest('#menu-overlay') && !e.target.closest('.fixed-footer');

        if (isSelecting && isOutsideSelectionArea) {
            if (!isClipboardPopulated) {
                toggleSelectionMode(false);
            }
        }
    });


    // --- 4. FUNGSI FOOTER NAVIGASI & MENU (AJAX NAVIGATION) ---

    // Toggle Grid/List
    let isGridView = sessionStorage.getItem('viewMode') === 'grid';
    
    const setView = (isGrid) => {
        if (isGrid) {
            fileList.classList.add('grid-view');
            gridToggle.querySelector('i').className = 'fas fa-list fa-fw';
            sessionStorage.setItem('viewMode', 'grid');
        } else {
            fileList.classList.remove('grid-view');
            gridToggle.querySelector('i').className = 'fas fa-th-large fa-fw';
            sessionStorage.setItem('viewMode', 'list');
        }
    };
    setView(isGridView);

    gridToggle.addEventListener('click', function(e) {
        e.preventDefault();
        isGridView = !isGridView;
        setView(isGridView);
    });

    // Tombol Kembali
    if (backButton) {
        backButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            const currentPath = currentPathCode.textContent.trim();
            const rootPath = homeButton.getAttribute('data-path').trim();
            
            if (currentPath === rootPath) return; 

            // Cari path induk
            const parentPath = currentPath.substring(0, currentPath.lastIndexOf('/'));
            const finalPath = parentPath === '' ? rootPath : parentPath;
            
            if (finalPath) {
                fetchDirData(finalPath);
            }
        });
    }

    // Tombol Home (Sekarang ditangani oleh js-folder-link, tapi kita tambahkan listener eksplisit untuk jaga-jaga)
    if (homeButton) {
        homeButton.addEventListener('click', function(e) {
            if (e.target.closest('.js-folder-link')) return; // Ditangani oleh listener fileList
            e.preventDefault();
            fetchDirData(homeButton.getAttribute('data-path'));
        });
    }

    // Handle History PopState (Jika user menggunakan tombol back/forward browser)
    window.addEventListener('popstate', function(e) {
        const path = e.state ? e.state.path : currentPathCode.textContent.trim();
        if (path) {
            fetchDirData(path);
        }
    });

    // Menu Overlay Logic
    // ... (Logika Toggle Menu dan Menu Toggle Click tetap sama) ...

    // Inisialisasi
    updateSelectionCount(); 
});

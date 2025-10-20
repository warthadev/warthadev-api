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
    
    // --- FUNGSI UTILITY ---
    function getSelectedItems() {
        return document.querySelectorAll('.file-item.selected');
    }

    // --- 1. NONAKTIFKAN CONTEXT MENU MOBILE (TEKAN LAMA) ---
    document.addEventListener('contextmenu', function(e) {
        if ('ontouchstart' in window) { 
             e.preventDefault();
        }
    });

    // --- 2. LOGIKA SELEKSI & MENU DINAMIS ---
    
    function handleSelectionAction(actionId, count) {
        let message = '';
        let shouldCloseModal = true; 
        
        const selectedItems = getSelectedItems();
        const selectedPaths = Array.from(selectedItems).map(item => 
            item.getAttribute('data-path') || item.getAttribute('href')
        ).filter(path => path);

        switch(actionId) {
            case 'selection-all':
                fileList.querySelectorAll('.file-item').forEach(item => item.classList.add('selected'));
                updateSelectionCount();
                shouldCloseModal = false;
                return;
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
                break;
            case 'selection-slideshow':
                message = `Memulai Slideshow untuk ${count} gambar!`;
                break;
            case 'selection-delete':
                if (confirm(`Yakin ingin menghapus ${count} item yang terpilih?\nPaths:\n${selectedPaths.join('\n')}`)) {
                    message = `Menghapus ${count} item!`;
                    // fetch('/api/delete', { method: 'POST', body: JSON.stringify({ paths: selectedPaths }) })
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
            toggleSelectionMode(false); 
        }
    }

    function updateSelectionMenu() {
        const selectedItems = getSelectedItems();
        const count = selectedItems.length;
        const menuList = menuModal.querySelector('.menu-list');
        
        let allImages = count > 0;
        let isSingleCompress = count === 1;
        
        selectedItems.forEach(item => {
            const isFile = item.classList.contains('file-file');
            const path = item.getAttribute('data-path') || '';
            if (isFile && !/\.(jpe?g|png|gif|webp)$/i.test(path)) { allImages = false; }
            if (isFile && !/\.(zip|rar|7z|tar\.gz)$/i.test(path)) { isSingleCompress = false; }
            if (!isFile || count > 1) { isSingleCompress = false; }
            if (!isFile) { allImages = false; }
        });

        // --- REGENERASI ISI MENU HAMBURGER ---
        menuList.innerHTML = '';
        const selectionActions = [];
        
        selectionActions.push({ id: 'selection-all', icon: 'fas fa-check-double', label: `Pilih Semua` });
        
        if (isClipboardPopulated && count === 0) { 
             selectionActions.push({ id: 'selection-paste', icon: 'fas fa-paste', label: `Tempel dari Clipboard` });
        }
        
        if (count > 0) {
            if (allImages) { selectionActions.push({ id: 'selection-slideshow', icon: 'fas fa-images', label: `Slideshow (${count})` }); }
            
            selectionActions.push(
                { id: 'selection-copy', icon: 'fas fa-copy', label: `Salin (${count})` },
                { id: 'selection-move', icon: 'fas fa-external-link-alt', label: `Pindahkan (${count})` }
            );
            
            if (count > 0) {
                 selectionActions.push({ id: 'selection-compress', icon: 'fas fa-file-archive', label: `Compress (${count})` });
            }
            
            if (isSingleCompress) {
                 selectionActions.push({ id: 'selection-extract', icon: 'fas fa-file-export', label: `Extract` });
            }
            
            selectionActions.push({ id: 'selection-delete', icon: 'fas fa-trash', label: `Hapus (${count})` });
        }

        // Render Menu Items
        selectionActions.forEach(action => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'menu-item selection-action';
            itemDiv.id = action.id;
            itemDiv.innerHTML = `<i class="${action.icon}"></i> ${action.label}`;
            menuList.appendChild(itemDiv);
            
            itemDiv.addEventListener('click', (e) => {
                e.preventDefault();
                handleSelectionAction(action.id, count);
                if(action.id !== 'selection-all') {
                   toggleMenu(false);
                }
            });
        });
    }

    function updateSelectionCount() {
        const count = getSelectedItems().length;
        
        if (count > 0) {
            if (!isSelecting) {
                toggleSelectionMode(true);
            }
            updateSelectionMenu(); 
        } else {
            if (isClipboardPopulated) {
                updateSelectionMenu();
            } else if (isSelecting) {
                toggleSelectionMode(false);
            }
        }
    }

    // FUNGSI INTI PERBAIKAN: Mengontrol Tombol + dan Globe
    function toggleSelectionMode(enable) {
        isSelecting = enable;
        
        if (enable) {
            // 1. NONAKTIFKAN TOMBOL PLUS saat seleksi aktif
            menuToggle.style.pointerEvents = 'none'; 
            menuToggle.style.opacity = '0.5'; 
            menuToggle.querySelector('i').className = 'fas fa-check'; 

            // 2. AKTIFKAN TOMBOL BROWSER sebagai Menu Hamburger
            browserLink.querySelector('i').className = 'fas fa-bars'; 
            
        } else {
            // 1. AKTIFKAN KEMBALI TOMBOL PLUS (jika clipboard kosong)
            if (!isClipboardPopulated) {
                 menuToggle.style.pointerEvents = 'auto'; 
                 menuToggle.style.opacity = '1'; 
                 menuToggle.querySelector('i').className = 'fas fa-plus'; 
            } else {
                // Jika clipboard terisi, biarkan tombol + nonaktif dan ikon check/done
                menuToggle.style.pointerEvents = 'none'; 
                menuToggle.style.opacity = '0.5'; 
                menuToggle.querySelector('i').className = 'fas fa-check';
            }
            
            // 2. KEMBALI ke ikon Globe
            browserLink.querySelector('i').className = 'fas fa-globe';
            
            document.querySelectorAll('.file-item.selected').forEach(sel => sel.classList.remove('selected'));
        }
    }
    
    function toggleItemSelection(item) {
        item.classList.toggle('selected');
        updateSelectionCount();
    }

    // --- 3. EVENT LONG PRESS/KLIK (DELEGATION) ---
    
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
    
    fileList.addEventListener('click', function(e) {
         const item = e.target.closest('.file-item');
         if (!item) return;
         
         if (isSelecting) {
             e.preventDefault(); 
             toggleItemSelection(item);
         } else if (pressTimer) {
             clearTimeout(pressTimer);
         }
    });

    // DESKTOP/Mouse Events
    fileList.addEventListener('mousedown', function(e) {
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

    fileList.addEventListener('mouseup', function(e) {
        clearTimeout(pressTimer);
    });
    
    fileList.addEventListener('mouseleave', function(e) {
        const item = e.target.closest('.file-item');
        if (item) clearTimeout(pressTimer);
    });
    
    fileList.addEventListener('contextmenu', (e) => {
        const item = e.target.closest('.file-item');
        if (!item) return;
        
        if (isSelecting) {
             e.preventDefault(); 
        }
    });


    // --- 4. KLIK DI LUAR ITEM (KELUAR MODE SELEKSI) ---
    document.addEventListener('click', function(e) {
        if (isSelecting && !e.target.closest('.file-item') && !e.target.closest('#menu-overlay') && !e.target.closest('#menu-toggle') && !e.target.closest('#browser-link')) {
            if (!isClipboardPopulated) {
                toggleSelectionMode(false);
            }
        }
    });


    // --- 5. FUNGSI FOOTER NAVIGASI & MENU ---

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
            window.history.back();
        });
    }

    // Menu Overlay Logic
    const toggleMenu = (show) => {
        if (show) {
            menuOverlay.style.display = 'flex';
            if (isSelecting || isClipboardPopulated) { 
                menuModal.querySelector('h3').textContent = 'Menu Aksi Seleksi';
                updateSelectionMenu(); 
            } else {
                menuModal.querySelector('h3').textContent = 'Menu Aksi Cepat';
                menuModal.querySelector('.menu-list').innerHTML = `
                     <div class="menu-item" id="alternatif-cloud"><i class="fas fa-cloud-upload-alt"></i> Alternatif Cloud</div>
                     <div class="menu-item" id="add-folder"><i class="fas fa-folder-plus"></i> Tambah Folder Baru</div>
                `;
                menuModal.querySelectorAll('.menu-item').forEach(item => {
                    item.addEventListener('click', function(e) {
                        e.preventDefault(); 
                        alert(`Aksi Cepat: ${item.textContent.trim()} dipanggil!`);
                        toggleMenu(false);
                    });
                });
            }
            setTimeout(() => menuOverlay.classList.add('active'), 10); 
        } else {
            menuOverlay.classList.remove('active');
            setTimeout(() => menuOverlay.style.display = 'none', 300);
        }
    };

    // Tombol PLUS (Menu Cepat)
    menuToggle.addEventListener('click', function(e) {
        e.preventDefault();
        if (!isSelecting && !isClipboardPopulated) { 
            toggleMenu(true);
        }
    });
    
    // Tombol BROWSER/HAMBURGER (Menu Aksi Seleksi/Paste)
    browserLink.addEventListener('click', function(e) {
        e.preventDefault();
        if (isSelecting || isClipboardPopulated) {
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

    toggleSelectionMode(isSelecting); 
});
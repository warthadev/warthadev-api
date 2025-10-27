document.addEventListener('DOMContentLoaded', function() {
    const fileList = document.getElementById('file-list');
    const currentPathCode = document.getElementById('current-path-code'); 
    const gridToggle = document.getElementById('grid-toggle');
    const backButton = document.getElementById('back-button');
    const homeButton = document.getElementById('home-button'); 
    const menuToggle = document.getElementById('menu-toggle'); 
    const menuOverlay = document.getElementById('menu-overlay');
    const closeMenuButton = document.getElementById('close-menu');
    const browserLink = document.getElementById('browser-link'); 
    const menuModal = document.querySelector('.menu-modal');

    let pressTimer;
    const LONG_PRESS_THRESHOLD = 500; 
    let isSelecting = false;
    let isClipboardPopulated = false; // State untuk mengaktifkan Paste
    
    // Mode Ceklis: 0=Tidak Terseleksi, 1=Terseleksi Sebagian, 2=Terseleksi Penuh
    let selectionMode = 0; 
    
    // Ambil rootPath Colab dari data-path tombol Home
    const rootPath = homeButton ? homeButton.getAttribute('data-path').trim() : '/'; 

    // --- FUNGSI UTILITY ---
    function getAllItems() {
        return document.querySelectorAll('.file-item');
    }

    function getSelectedItems() {
        return document.querySelectorAll('.file-item.selected');
    }
    
    function setMenuToggleIcon(iconClass, enabled = true) {
        menuToggle.querySelector('i').className = iconClass;
        menuToggle.style.pointerEvents = enabled ? 'auto' : 'none'; 
        menuToggle.style.opacity = enabled ? '1' : '0.5'; 
    }

    // FUNGSI AJAX: Membuat elemen item file dari data JSON
    function createItemElement(file) {
        const path = file.full_path;
        const iconClass = file.icon_class;
        const isDir = file.is_dir;
        
        const wrapper = document.createElement(isDir ? 'a' : 'div');
        wrapper.className = `file-item ${isDir ? 'file-folder js-folder-link' : 'file-file js-file-item'}`;
        
        if (isDir) { wrapper.href = '#'; } // Cegah navigasi browser default

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

    // FUNGSI AJAX: Merender ulang daftar file setelah fetch data
    function renderFileList(data) {
        fileList.innerHTML = ''; 
        
        currentPathCode.textContent = data.current_path;
        
        data.files.forEach(file => {
            const item = createItemElement(file);
            fileList.appendChild(item);
        });
        
        setView(isGridView); 
        toggleSelectionMode(false);
        
        const url = `/?path=${encodeURIComponent(data.current_path)}`;
        window.history.pushState({path: data.current_path}, '', url);
    }
    
    // FUNGSI INTI AJAX: Mengambil data folder dari server
    async function fetchDirData(path, pushHistory = true) { // Tambahkan flag pushHistory
        if (path === undefined || path === null) return;
        
        // Cek Pintasan MyDrive: Jika mencoba kembali ke '/content/driver' (path root Colab)
        // dan path saat ini adalah '/content/driver/MyDrive', ganti path ke '/content/driver'
        // agar tidak terjadi loop navigasi di Colab.
        const currentPath = currentPathCode.textContent.trim();

        if (path.endsWith("/MyDrive") && currentPath.endsWith("/MyDrive") && path.length > currentPath.length) {
            // Jika user mencoba klik folder MyDrive, padahal sudah di dalamnya (jaga-jaga)
        } else if (path === "/content/driver/MyDrive" && currentPath === rootPath) {
            // Navigasi awal dari root ke MyDrive
        } else if (currentPath === "/content/driver/MyDrive" && path === "/content/driver") {
            // Ketika tombol Back dari MyDrive. Pastikan path yang diminta adalah rootPath.
            path = rootPath; 
        }

        // Jika path yang diminta sama dengan path saat ini (dan bukan refresh), abaikan
        if (path === currentPath && pushHistory) return;

        fileList.style.opacity = 0.5;
        
        try {
            const encodedPath = encodeURIComponent(path);
            const response = await fetch(`/api/data?path=${encodedPath}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                fileList.innerHTML = ''; // Kosongkan saat rendering
                currentPathCode.textContent = data.current_path;
                
                // Cek Pintasan MyDrive untuk tombol Kembali/Home
                const finalPathForRendering = data.current_path;

                data.files.forEach(file => {
                    const item = createItemElement(file);
                    fileList.appendChild(item);
                });
                
                setView(isGridView); 
                toggleSelectionMode(false);

                if (pushHistory) {
                    const url = `/?path=${encodeURIComponent(finalPathForRendering)}`;
                    window.history.pushState({path: finalPathForRendering}, '', url);
                }
            } else {
                alert(`Gagal memuat folder: ${data.message || 'Error tidak diketahui'}`);
            }
        } catch (error) {
            console.error('Error fetching directory data:', error);
            alert(`Terjadi kesalahan jaringan atau server: ${error.message}`);
        } finally {
            fileList.style.opacity = 1; 
        }
    }


    // --- LOGIKA SELEKSI & MENU DINAMIS ---
    
    function handleSelectionAction(actionId, count) {
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
                fetch('/api/clear-cache', { method: 'POST' }); 
                break;
            case 'selection-delete':
                if (confirm(`Yakin ingin menghapus ${count} item yang terpilih?\nPaths:\n${selectedPaths.join('\n')}`)) {
                    message = `Menghapus ${count} item!`;
                    fetch('/api/clear-cache', { method: 'POST' }); 
                } else {
                    return;
                }
                break;
            default:
                message = `Aksi ${actionId} dipanggil.`;
        }
        
        alert(message);
        
        if (shouldCloseModal) {
            document.querySelectorAll('.file-item.selected').forEach(sel => sel.classList.remove('selected'));
            toggleSelectionMode(false); 
            fetchDirData(currentPathCode.textContent.trim(), false); // Refresh folder setelah aksi
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
            if (!isFile) { allImages = false; }
            if (isFile && !/\.(zip|rar|7z|tar\.gz)$/i.test(path)) { isSingleCompress = false; }
            if (!isFile || count > 1) { isSingleCompress = false; }
        });

        menuList.innerHTML = '';
        const selectionActions = [];
        
        if (isClipboardPopulated && count === 0) { 
             selectionActions.push({ id: 'selection-paste', icon: 'fas fa-paste', label: `Tempel dari Clipboard` });
        }
        
        if (count > 0) {
            selectionActions.push(
                { id: 'selection-copy', icon: 'fas fa-copy', label: `Salin (${count})` },
                { id: 'selection-move', icon: 'fas fa-external-link-alt', label: `Pindahkan (${count})` }
            );
            if (allImages) { selectionActions.push({ id: 'selection-slideshow', icon: 'fas fa-images', label: `Slideshow (${count})` }); }
            selectionActions.push({ id: 'selection-compress', icon: 'fas fa-file-archive', label: `Compress (${count})` });
            if (isSingleCompress) { selectionActions.push({ id: 'selection-extract', icon: 'fas fa-file-export', label: `Extract` }); }
            selectionActions.push({ id: 'selection-delete', icon: 'fas fa-trash', label: `Hapus (${count})` });
        }

        selectionActions.forEach(action => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'menu-item selection-action';
            itemDiv.id = action.id;
            itemDiv.innerHTML = `<i class="${action.icon}"></i> ${action.label}`;
            menuList.appendChild(itemDiv);
            
            itemDiv.addEventListener('click', (e) => {
                e.preventDefault();
                handleSelectionAction(action.id, count);
                toggleMenu(false); 
            });
        });
        
        updateSelectionCount(false);
    }
    
    function updateSelectionCount(shouldUpdateMenu = true) {
        const count = getSelectedItems().length;
        const allItems = getAllItems();
        const totalCount = allItems.length;
        
        const wasSelecting = isSelecting;

        if (count > 0 || isClipboardPopulated) {
            isSelecting = true;
            if (!wasSelecting) {
                toggleSelectionMode(true);
            }
            
            if (count > 0 && count < totalCount) {
                selectionMode = 1; 
                setMenuToggleIcon('fas fa-check'); 
            } else if (count === totalCount && totalCount > 0) {
                selectionMode = 2; 
                setMenuToggleIcon('fas fa-check-double');
            } else if (isClipboardPopulated && count === 0) {
                 selectionMode = 0; 
                 setMenuToggleIcon('fas fa-paste');
            } else {
                 selectionMode = 1; 
                 setMenuToggleIcon('fas fa-check'); 
            }

            if (shouldUpdateMenu) { updateSelectionMenu(); }
        } else if (isSelecting) {
            toggleSelectionMode(false);
        }
    }

    function toggleSelectionMode(enable) {
        isSelecting = enable;
        
        if (enable) {
            const count = getSelectedItems().length;
            const total = getAllItems().length;
            
            if (count === total && total > 0) {
                 setMenuToggleIcon('fas fa-check-double');
                 selectionMode = 2;
            } else if (isClipboardPopulated && count === 0) {
                 setMenuToggleIcon('fas fa-paste');
                 selectionMode = 0;
            } else {
                 setMenuToggleIcon('fas fa-check');
                 selectionMode = 1;
            }

            browserLink.style.pointerEvents = 'auto';
            browserLink.style.opacity = '1'; 
            browserLink.querySelector('i').className = 'fas fa-bars'; 
            
        } else {
            selectionMode = 0;
            
            setMenuToggleIcon('fas fa-plus');
            
            browserLink.style.pointerEvents = 'auto';
            browserLink.style.opacity = '1'; 
            browserLink.querySelector('i').className = 'fas fa-globe';
            
            document.querySelectorAll('.file-item.selected').forEach(sel => sel.classList.remove('selected'));
        }
    }
    
    function toggleItemSelection(item) {
        item.classList.toggle('selected');
        updateSelectionCount();
    }

    // --- LOGIKA TOUCH/MOUSE & KLIK ITEM ---
    
    document.addEventListener('contextmenu', function(e) {
        if ('ontouchstart' in window) { e.preventDefault(); }
    });
    
    // Delegasi Event Click (Folder Link dan Seleksi)
    fileList.addEventListener('click', function(e) {
         const item = e.target.closest('.file-item');
         if (!item) return;
         
         if (isSelecting) {
             e.preventDefault(); 
             toggleItemSelection(item);
         } else if (item.classList.contains('js-folder-link')) {
             e.preventDefault(); 
             const path = item.getAttribute('data-path');
             if (path) { fetchDirData(path); }
         }
    });

    // ... (Logika touchstart, touchend, mousedown, mouseup tetap sama) ...

    // --- KLIK DI LUAR ITEM (KELUAR MODE SELEKSI) ---
    document.addEventListener('click', function(e) {
        const isOutsideSelectionArea = !e.target.closest('.file-item') && !e.target.closest('#menu-overlay') && !e.target.closest('.fixed-footer');

        if (isSelecting && isOutsideSelectionArea) {
            if (!isClipboardPopulated) {
                toggleSelectionMode(false);
            }
        }
    });


    // --- FUNGSI FOOTER NAVIGASI & MENU ---

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

    // Tombol Kembali (AJAX)
    if (backButton) {
        backButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            const currentPath = currentPathCode.textContent.trim();
            
            if (currentPath === rootPath) return; 

            let targetPath;
            
            // Logika pintasan: Jika di MyDrive, kembali ke root Colab
            if (currentPath.endsWith("/MyDrive")) {
                targetPath = rootPath; 
            } else {
                // Logika kembali normal: potong path terakhir
                const parentPath = currentPath.substring(0, currentPath.lastIndexOf('/'));
                targetPath = parentPath === '' ? rootPath : parentPath;
            }
            
            if (targetPath) { fetchDirData(targetPath); }
        });
    }

    // Tombol Home (AJAX) - Menggunakan data-path rootPath
    if (homeButton) {
        homeButton.addEventListener('click', function(e) {
            e.preventDefault();
            fetchDirData(rootPath);
        });
    }


    // Handle History PopState (Jika user menggunakan tombol back/forward browser)
    window.addEventListener('popstate', function(e) {
        // Ambil path dari state history, jika tidak ada, gunakan path saat ini.
        const path = e.state ? e.state.path : currentPathCode.textContent.trim();
        if (path) { fetchDirData(path, false); } // Jangan push history lagi
    });

    // Menu Overlay Logic
    const toggleMenu = (show) => {
        // ... (Logika toggleMenu tetap sama) ...
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
    
    // --- Logika Klik Tombol MenuToggle (+) ---
    menuToggle.addEventListener('click', function(e) {
        e.preventDefault();
        
        const allItems = getAllItems();
        const totalCount = allItems.length;

        // A. Mode NORMAL/PASTE: Buka Menu
        if (selectionMode === 0) { 
            toggleMenu(true);
            return;
        }

        // B. Mode SELEKSI AKTIF
        if (totalCount === 0) return; 

        if (selectionMode === 1) { // Seleksi Sebagian -> Seleksi Penuh
            allItems.forEach(item => item.classList.add('selected'));
            setMenuToggleIcon('fas fa-check-double');
            selectionMode = 2;
        } else if (selectionMode === 2) { // Seleksi Penuh -> Batalkan Seleksi
            allItems.forEach(item => item.classList.remove('selected'));
            selectionMode = 0; 
            toggleSelectionMode(false); 
        }
        
        updateSelectionCount(); 
    });
    
    // Tombol BROWSER/HAMBURGER
    browserLink.addEventListener('click', function(e) {
        e.preventDefault();
        if (!isSelecting && !isClipboardPopulated) {
            alert('Membuka link Browser/Dunia!');
        } else {
            toggleMenu(true);
        } 
    });

    // Menutup Menu
    closeMenuButton.addEventListener('click', function() { toggleMenu(false); });
    menuOverlay.addEventListener('click', function(e) {
        if (e.target.id === 'menu-overlay') { toggleMenu(false); }
    });

    // Inisialisasi
    updateSelectionCount(); 
});

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
    let isClipboardPopulated = false;

    function getSelectedItems() {
        return document.querySelectorAll('.file-item.selected');
    }

    document.addEventListener('contextmenu', function(e) {
        if ('ontouchstart' in window) e.preventDefault();
    });

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
                message = `Menyalin ${count} item!`;
                isClipboardPopulated = true; 
                break;
            case 'selection-move':
                message = `Memotong ${count} item!`;
                isClipboardPopulated = true; 
                break;
            case 'selection-paste':
                message = `Tempel item dari clipboard ke ${document.getElementById('current-path-code').textContent.trim()}!`;
                isClipboardPopulated = false; 
                break;
            case 'selection-delete':
                if (confirm(`Yakin ingin menghapus ${count} item?`)) message = `Menghapus ${count} item!`;
                else return;
                break;
            default:
                message = `Aksi ${actionId} dipanggil.`;
        }
        alert(message);
        if (shouldCloseModal) toggleSelectionMode(false);
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
            if (isFile && !/\.(jpe?g|png|gif|webp)$/i.test(path)) allImages = false;
            if (isFile && !/\.(zip|rar|7z|tar\.gz)$/i.test(path)) isSingleCompress = false;
            if (!isFile || count > 1) isSingleCompress = false;
            if (!isFile) allImages = false;
        });

        menuList.innerHTML = '';
        const actions = [];
        actions.push({ id: 'selection-all', icon: 'fas fa-check-double', label: 'Pilih Semua' });
        if (isClipboardPopulated && count === 0) actions.push({ id: 'selection-paste', icon: 'fas fa-paste', label: 'Tempel' });
        if (count > 0) {
            if (allImages) actions.push({ id: 'selection-slideshow', icon: 'fas fa-images', label: `Slideshow (${count})` });
            actions.push({ id: 'selection-copy', icon: 'fas fa-copy', label: `Salin (${count})` });
            actions.push({ id: 'selection-move', icon: 'fas fa-external-link-alt', label: `Pindahkan (${count})` });
            actions.push({ id: 'selection-delete', icon: 'fas fa-trash', label: `Hapus (${count})` });
        }

        actions.forEach(action => {
            const itemDiv = document.createElement('div');
            itemDiv.className = 'menu-item selection-action';
            itemDiv.id = action.id;
            itemDiv.innerHTML = `<i class="${action.icon}"></i> ${action.label}`;
            menuList.appendChild(itemDiv);
            itemDiv.addEventListener('click', (e) => {
                e.preventDefault();
                handleSelectionAction(action.id, count);
                if (action.id !== 'selection-all') toggleMenu(false);
            });
        });
    }

    function updateSelectionCount() {
        const count = getSelectedItems().length;
        if (count > 0) {
            if (!isSelecting) toggleSelectionMode(true);
            updateSelectionMenu(); 
        } else if (isSelecting && !isClipboardPopulated) {
            toggleSelectionMode(false);
        }
    }

    function toggleSelectionMode(enable) {
        isSelecting = enable;
        if (enable) {
            menuToggle.style.pointerEvents = 'none';
            menuToggle.style.opacity = '0.5';
            menuToggle.querySelector('i').className = 'fas fa-check';
            browserLink.querySelector('i').className = 'fas fa-bars';
        } else {
            if (!isClipboardPopulated) {
                menuToggle.style.pointerEvents = 'auto';
                menuToggle.style.opacity = '1';
                menuToggle.querySelector('i').className = 'fas fa-plus';
            } else {
                menuToggle.style.pointerEvents = 'none';
                menuToggle.style.opacity = '0.5';
                menuToggle.querySelector('i').className = 'fas fa-check';
            }
            browserLink.querySelector('i').className = 'fas fa-globe';
            document.querySelectorAll('.file-item.selected').forEach(sel => sel.classList.remove('selected'));
        }
    }

    function toggleItemSelection(item) {
        item.classList.toggle('selected');
        updateSelectionCount();
    }

    fileList.addEventListener('click', function(e) {
        const item = e.target.closest('.file-item');
        if (!item) return;
        if (isSelecting) e.preventDefault(), toggleItemSelection(item);
    });

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
            }
            setTimeout(() => menuOverlay.classList.add('active'), 10);
        } else {
            menuOverlay.classList.remove('active');
            setTimeout(() => menuOverlay.style.display = 'none', 300);
        }
    };

    gridToggle.addEventListener('click', function(e) {
        e.preventDefault();
        const grid = fileList.classList.toggle('grid-view');
        gridToggle.querySelector('i').className = grid ? 'fas fa-list' : 'fas fa-th-large';
    });

    if (backButton) backButton.addEventListener('click', e => { e.preventDefault(); window.history.back(); });
    menuToggle.addEventListener('click', e => { e.preventDefault(); if (!isSelecting && !isClipboardPopulated) toggleMenu(true); });
    browserLink.addEventListener('click', e => { e.preventDefault(); if (isSelecting || isClipboardPopulated) toggleMenu(true); });
    closeMenuButton.addEventListener('click', () => toggleMenu(false));
    menuOverlay.addEventListener('click', e => { if (e.target.id === 'menu-overlay') toggleMenu(false); });
});
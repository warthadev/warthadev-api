document.addEventListener("DOMContentLoaded", () => {
    const fileItems = document.querySelectorAll(".file-item");
    const menuOverlay = document.getElementById("menu-overlay");
    const closeMenu = document.getElementById("close-menu");
    const menuList = document.getElementById("menu-list");

    // --- NAVBAR EVENTS ---
    document.getElementById("menu-toggle")?.addEventListener("click", e => {
        e.preventDefault();
        alert("Menu utama diklik (belum ada aksi)");
    });
    document.getElementById("grid-toggle")?.addEventListener("click", e => {
        e.preventDefault();
        document.body.classList.toggle("grid-view");
    });
    document.getElementById("browser-link")?.addEventListener("click", e => {
        e.preventDefault();
        alert("Browser-link diklik (placeholder)");
    });
    document.getElementById("back-button")?.addEventListener("click", e => {
        e.preventDefault();
        window.history.back();
    });

    // --- SELECTION HANDLER ---
    fileItems.forEach(item => {
        item.addEventListener("click", e => {
            const isSelected = item.classList.toggle("selected");
            if (isSelected) {
                showMenu(item.dataset.path);
            } else {
                hideMenu();
            }
        });
    });

    function showMenu(path) {
        menuList.innerHTML = `
            <button class="menu-btn" onclick="alert('Buka: ${path}')"><i class="fas fa-folder-open"></i> Buka</button>
            <button class="menu-btn" onclick="alert('Download: ${path}')"><i class="fas fa-download"></i> Download</button>
            <button class="menu-btn" onclick="alert('Hapus: ${path}')"><i class="fas fa-trash"></i> Hapus</button>
        `;
        menuOverlay.classList.remove("hidden");
    }

    function hideMenu() {
        menuOverlay.classList.add("hidden");
        document.querySelectorAll(".file-item.selected").forEach(el => el.classList.remove("selected"));
    }

    closeMenu?.addEventListener("click", hideMenu);
    menuOverlay?.addEventListener("click", e => {
        if (e.target === menuOverlay) hideMenu();
    });
});
// Dynamische Sidebar-Navigation und Auto-Hide
(function() {
    const sidebar = document.getElementById('sidebar');
    const anchorsList = document.getElementById('sidebar-dynamic-anchors');
    let hideTimeout;

    // Dynamische Navigation aus <section id=...>
    function populateSidebarAnchors() {
        if (!anchorsList) return;
        anchorsList.innerHTML = '';
        const sections = document.querySelectorAll('section[id]');
        sections.forEach(section => {
            const id = section.id;
            // Überschrift suchen
            let label = section.querySelector('h1, h2, h3, h4, h5, h6');
            label = label ? label.textContent.trim() : id;
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = `#${id}`;
            a.className = 'sidebar-link text-gray-300 hover:text-white';
            a.dataset.section = id;
            a.textContent = label;
            li.appendChild(a);
            anchorsList.appendChild(li);
        });
    }
    populateSidebarAnchors();

    // Sidebar Auto-Hide/Show
    function showSidebar() {
        if (sidebar) sidebar.classList.remove('sidebar-hidden');
    }
    function hideSidebar() {
        if (sidebar) sidebar.classList.add('sidebar-hidden');
    }
    function resetSidebarTimer() {
        showSidebar();
        clearTimeout(hideTimeout);
        hideTimeout = setTimeout(hideSidebar, 3000);
    }
    document.addEventListener('mousemove', (e) => {
        if (e.clientX < 60) {
            showSidebar();
            clearTimeout(hideTimeout);
        } else {
            resetSidebarTimer();
        }
    });
    document.addEventListener('scroll', resetSidebarTimer, true);
    // Initial hide after 3s
    hideTimeout = setTimeout(hideSidebar, 3000);
})();

// Dynamic sidebar navigation and active indicator (with debug logging for .snap-container)
(function() {
    const sidebar = document.getElementById('sidebar');
    const anchorsList = document.getElementById('sidebar-dynamic-anchors');
    const mainContent = document.querySelector('.snap-container') || document.getElementById('main-content');

    // Dynamically populate sidebar navigation from <section id=...>
    function populateSidebarAnchors() {
        if (!anchorsList) return;
        anchorsList.innerHTML = '';
        const sections = document.querySelectorAll('section[id]');
        sections.forEach(section => {
            const id = section.id;
            let label = section.querySelector('h1, h2, h3, h4, h5, h6');
            label = label ? label.textContent.trim() : id;
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = `#${id}`;
            a.className = 'sidebar-link text-gray-300 hover:text-white';
            a.dataset.section = id;
            a.textContent = label;
            li.appendChild(a);
            anchorsList.appendChild(li);
        });
    }
    populateSidebarAnchors();

    // Highlight the active sidebar link based on scroll position in the main content
    function highlightActiveSidebarLink() {
        const sections = document.querySelectorAll('section[id]');
        const sidebarLinks = document.querySelectorAll('.sidebar-link');
        let currentSectionId = null;
        let scrollTop = 0;
        let viewHeight = 0;
        if (mainContent) {
            scrollTop = mainContent.scrollTop;
            viewHeight = mainContent.clientHeight;
        } else {
            scrollTop = window.scrollY || window.pageYOffset;
            viewHeight = window.innerHeight;
        }
        const offset = viewHeight * 0.3;
        sections.forEach(section => {
            // Calculate section position relative to the scroll container
            let sectionTop = section.offsetTop;
            let sectionBottom = sectionTop + section.offsetHeight;
            if (mainContent) {
                // Adjust for the scroll container's offset
                const relativeTop = sectionTop - mainContent.offsetTop;
                const relativeBottom = sectionBottom - mainContent.offsetTop;
                if (scrollTop + offset >= relativeTop && scrollTop + offset < relativeBottom) {
                    currentSectionId = section.id;
                }
            } else {
                // Fallback for window scrolling
                const rect = section.getBoundingClientRect();
                if (rect.top <= offset && rect.bottom > offset) {
                    currentSectionId = section.id;
                }
            }
        });
        sidebarLinks.forEach(link => {
            link.classList.toggle('active', link.getAttribute('href') === `#${currentSectionId}`);
        });
        // Debug output
        console.log('Active section:', currentSectionId);
    }
    if (mainContent) {
        mainContent.addEventListener('scroll', highlightActiveSidebarLink);
        mainContent.addEventListener('resize', highlightActiveSidebarLink);
    } else {
        window.addEventListener('scroll', highlightActiveSidebarLink);
        window.addEventListener('resize', highlightActiveSidebarLink);
    }
    document.addEventListener('DOMContentLoaded', highlightActiveSidebarLink);
    highlightActiveSidebarLink();
})(); 
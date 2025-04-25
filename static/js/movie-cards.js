// Movie Card Functionality
class MovieCardManager {
    constructor() {
        this.initializeSidebar();
        this.initializeHeroScroll();
        this.initializeCategoryHighlight();
        this.initializeGridNavigation();
        this.initializeCardTilt();
    }

    initializeSidebar() {
        let mouseMoveTimeout;
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.getElementById('main-content');
        
        if (!sidebar || !mainContent) return;
        
        function hideSidebar() {
            sidebar.classList.add('hidden');
            mainContent.classList.add('full-width');
        }
        
        function showSidebar() {
            sidebar.classList.remove('hidden');
            mainContent.classList.remove('full-width');
        }
        
        document.addEventListener('mousemove', (e) => {
            if (e.clientX < 60) {
                showSidebar();
                clearTimeout(mouseMoveTimeout);
            } else {
                clearTimeout(mouseMoveTimeout);
                mouseMoveTimeout = setTimeout(hideSidebar, 3000);
            }
        });

        document.addEventListener('scroll', () => {
            showSidebar();
            clearTimeout(mouseMoveTimeout);
            mouseMoveTimeout = setTimeout(hideSidebar, 3000);
        }, true);

        // Initial state
        setTimeout(hideSidebar, 3000);
    }

    initializeHeroScroll() {
        const mainContent = document.getElementById('main-content');
        const heroes = document.querySelectorAll('.hero-image');
        
        if (!mainContent || heroes.length === 0) return;
        
        mainContent.addEventListener('scroll', () => {
            heroes.forEach(hero => {
                const section = hero.closest('section');
                const rect = section.getBoundingClientRect();
                const scrollProgress = rect.top / window.innerHeight;
                const translateY = Math.min(100, Math.max(-100, scrollProgress * 50));
                hero.style.transform = `translateY(${translateY}px)`;
            });
        });
    }

    initializeCategoryHighlight() {
        const mainContent = document.getElementById('main-content');
        if (!mainContent) return;

        function updateActiveCategory() {
            const sections = document.querySelectorAll('section');
            const navItems = document.querySelectorAll('#category-nav a');
            
            sections.forEach((section, index) => {
                const rect = section.getBoundingClientRect();
                if (rect.top <= 100 && rect.bottom >= 100) {
                    navItems.forEach(item => item.classList.remove('text-accent'));
                    navItems[index].classList.add('text-accent');
                }
            });
        }

        mainContent.addEventListener('scroll', updateActiveCategory);
        updateActiveCategory();
    }

    initializeGridNavigation() {
        document.querySelectorAll('.movie-grid-container').forEach(container => {
            const wrapper = container.querySelector('.movie-grid-wrapper');
            const prevBtn = container.querySelector('button:first-of-type');
            const nextBtn = container.querySelector('button:last-of-type');
            let currentPage = 0;
            
            if (!wrapper || !prevBtn || !nextBtn) return;
            
            function updateNavigation() {
                const gridWidth = wrapper.scrollWidth;
                const containerWidth = container.clientWidth;
                const maxPages = Math.ceil(gridWidth / containerWidth) - 1;
                
                prevBtn.style.display = currentPage === 0 ? 'none' : 'block';
                nextBtn.style.display = currentPage >= maxPages ? 'none' : 'block';
            }
            
            prevBtn.addEventListener('click', () => {
                if (currentPage > 0) {
                    currentPage--;
                    wrapper.style.transform = `translateX(-${currentPage * 100}%)`;
                    updateNavigation();
                }
            });
            
            nextBtn.addEventListener('click', () => {
                const gridWidth = wrapper.scrollWidth;
                const containerWidth = container.clientWidth;
                const maxPages = Math.ceil(gridWidth / containerWidth) - 1;
                
                if (currentPage < maxPages) {
                    currentPage++;
                    wrapper.style.transform = `translateX(-${currentPage * 100}%)`;
                    updateNavigation();
                }
            });
            
            updateNavigation();
            window.addEventListener('resize', updateNavigation);
        });
    }

    initializeCardTilt() {
        document.querySelectorAll('.movie-card').forEach(card => {
            let bounds;
            let glareAngle = 125;

            function rotateToMouse(e) {
                const mouseX = e.clientX;
                const mouseY = e.clientY;
                const leftX = mouseX - bounds.x;
                const topY = mouseY - bounds.y;
                const center = {
                    x: leftX - bounds.width / 2,
                    y: topY - bounds.height / 2
                }
                const distance = Math.sqrt(center.x**2 + center.y**2);
                
                const rotateX = -center.y / 20;
                const rotateY = center.x / 20;
                
                glareAngle = 125 + (rotateY * 2);
                
                card.style.transform = `
                    perspective(1000px)
                    rotateX(${rotateX}deg)
                    rotateY(${rotateY}deg)
                    translateY(-4px)
                    scale(1.02)
                `;
                
                const glareOpacity = Math.min(distance / bounds.width, 0.5);
                card.style.setProperty('--glare-opacity', glareOpacity);
                card.querySelector('.movie-info').style.transform = `translateZ(20px)`;
                card.style.setProperty('--glare-angle', `${glareAngle}deg`);
                
                card.style.background = `
                    linear-gradient(
                        ${glareAngle}deg,
                        rgba(255,255,255,${glareOpacity * 0.4}) 0%,
                        rgba(255,255,255,0) 65%
                    ),
                    rgba(255,255,255,0.15)
                `;
            }

            function resetStyles() {
                card.style.transform = '';
                card.style.background = '';
                card.querySelector('.movie-info').style.transform = '';
            }

            card.addEventListener('mouseenter', () => {
                bounds = card.getBoundingClientRect();
                document.addEventListener('mousemove', rotateToMouse);
                card.style.transition = 'transform 0.2s ease-out, box-shadow 0.2s ease-out, background 0.2s ease-out';
            });

            card.addEventListener('mouseleave', () => {
                document.removeEventListener('mousemove', rotateToMouse);
                card.style.transition = 'transform 0.2s ease-out, box-shadow 0.2s ease-out, background 3s ease-out';
                resetStyles();
            });
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new MovieCardManager();
}); 
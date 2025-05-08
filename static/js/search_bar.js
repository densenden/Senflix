// search_bar.js - Handle search in top navigation bar

(function() {
    // Initialize search functionality when the page loads
    document.addEventListener('DOMContentLoaded', function() {
        initializeSearch();
    });
    
    // Initialize search bar and functionality
    function initializeSearch() {
        const searchContainer = document.getElementById('search-container');
        if (!searchContainer) return;
        
        const searchInput = document.getElementById('search-input');
        const resultsContainer = document.getElementById('search-results-container');
        let searchTimeout = null;
        
        // Toggle search results on input focus/blur
        searchInput.addEventListener('focus', function() {
            resultsContainer.classList.remove('hidden');
        });
        
        // Close search results when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchContainer.contains(e.target)) {
                resultsContainer.classList.add('hidden');
            }
        });
        
        // Handle search input
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            
            // Clear previous timeout
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            
            // Clear results if query is too short
            if (query.length < 2) {
                resultsContainer.innerHTML = '<div class="px-4 py-2 text-sm text-gray-400">Enter at least 2 characters</div>';
                return;
            }
            
            // Loading indicator
            resultsContainer.innerHTML = '<div class="px-4 py-2 text-sm text-gray-400">Searching...</div>';
            
            // Set a timeout to avoid too many requests
            searchTimeout = setTimeout(() => {
                performSearch(query, resultsContainer);
            }, 500);
        });
        
        // Handle keyboard navigation and enter key
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                resultsContainer.classList.add('hidden');
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                navigateResults('down');
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                navigateResults('up');
            } else if (e.key === 'Enter') {
                const selected = resultsContainer.querySelector('.search-result.selected');
                if (selected) {
                    selected.click();
                }
            }
        });
    }
    
    // Navigate through search results with keyboard
    function navigateResults(direction) {
        const results = document.querySelectorAll('.search-result');
        if (results.length === 0) return;
        
        const selected = document.querySelector('.search-result.selected');
        let nextIndex = 0;
        
        if (selected) {
            const currentIndex = Array.from(results).indexOf(selected);
            selected.classList.remove('selected');
            
            if (direction === 'down') {
                nextIndex = (currentIndex + 1) % results.length;
            } else {
                nextIndex = (currentIndex - 1 + results.length) % results.length;
            }
        }
        
        results[nextIndex].classList.add('selected');
        results[nextIndex].scrollIntoView({ block: 'nearest' });
    }
    
    // Perform the search and display results
    function performSearch(query, resultsContainer) {
        fetch(`/search_omdb?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (!data.results || data.results.length === 0) {
                    resultsContainer.innerHTML = '<div class="px-4 py-2 text-sm text-gray-400">No results found</div>';
                    return;
                }
                
                // Group results by source
                const senflixResults = data.results.filter(movie => movie.source === 'senflix');
                const omdbResults = data.results.filter(movie => movie.source === 'omdb');
                
                // Build HTML for results
                let html = '';
                
                // SenFlix results section
                if (senflixResults.length > 0) {
                    html += '<div class="px-4 py-1 bg-gray-800 text-xs font-semibold text-gray-300">SenFlix Movies</div>';
                    html += senflixResults.map(movie => createResultItem(movie, true)).join('');
                }
                
                // OMDB results section
                if (omdbResults.length > 0) {
                    html += '<div class="px-4 py-1 bg-gray-800 text-xs font-semibold text-gray-300">Add from OMDB</div>';
                    html += omdbResults.map(movie => createResultItem(movie, false)).join('');
                }
                
                resultsContainer.innerHTML = html;
                
                // Add click handlers
                document.querySelectorAll('.search-result').forEach(result => {
                    result.addEventListener('click', handleResultClick);
                });
            })
            .catch(error => {
                console.error('Error searching:', error);
                resultsContainer.innerHTML = '<div class="px-4 py-2 text-sm text-red-400">Error searching</div>';
            });
    }
    
    // Create HTML for a search result item
    function createResultItem(movie, isSenflix) {
        const posterUrl = movie.poster && movie.poster !== 'N/A' 
            ? movie.poster 
            : '/static/placeholders/poster_missing.png';
            
        return `
        <div class="search-result flex items-center px-3 py-2 hover:bg-gray-700 cursor-pointer" 
             data-movie='${JSON.stringify(movie).replace(/'/g, "&#39;")}'>
            <div class="w-10 h-14 flex-shrink-0 mr-3">
                <img src="${posterUrl}" alt="${movie.title}" class="w-full h-full object-cover rounded">
            </div>
            <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-white truncate">${movie.title}</div>
                <div class="text-xs text-gray-400">${movie.year || ''}</div>
            </div>
            <div class="ml-2">
                <span class="px-2 py-1 text-xs rounded ${isSenflix ? 'bg-blue-900 text-blue-300' : 'bg-amber-900 text-amber-300'}">
                    ${isSenflix ? 'View' : 'Add'}
                </span>
            </div>
        </div>`;
    }
    
    // Handle click on a search result
    function handleResultClick() {
        const movieData = JSON.parse(this.dataset.movie);
        
        if (movieData.source === 'senflix') {
            // For SenFlix movies, navigate to the movie detail page
            window.location.href = `/movie/${movieData.id}`;
        } else {
            // For OMDB movies, open the add movie modal at step 2
            if (window.showAddMovieModal) {
                window.showAddMovieModal(movieData, 2);
            } else {
                console.error('showAddMovieModal function not available');
                alert('Cannot add movie: feature not available');
            }
        }
    }
})(); 
// add_movie_modal.js - Add Movie modal with multi-step process

(function() {
    // Track the current step in the modal
    let currentStep = 1;
    let totalSteps = 4;
    let selectedMovie = null;
    let selectedCategories = [];
    let searchTimeout = null;
    
    // Movie preferences
    let moviePreferences = {
        watched: false,
        watchlist: false,
        favorite: false,
        rating: 0
    };
    
    // Initialize the modal when the page loads
    document.addEventListener('DOMContentLoaded', function() {
        // Attach click handler to add movie button
        const addMovieBtn = document.getElementById('addMovieBtn');
        if (addMovieBtn) {
            addMovieBtn.addEventListener('click', showAddMovieModal);
        }
    });
    
    // Show the add movie modal
    function showAddMovieModal(movieDataParam, startStep) {
        // Reset state
        currentStep = startStep || 1;
        selectedMovie = movieDataParam || null;
        selectedCategories = [];
        moviePreferences = {
            watched: false,
            watchlist: false,
            favorite: false,
            rating: 0
        };
        
        // Create modal HTML
        const modalHtml = `
        <div id="add-movie-modal" class="fixed inset-0 z-50 flex items-center justify-center">
            <!-- Backdrop with blur effect -->
            <div class="absolute inset-0 bg-black/80 backdrop-blur-sm z-0"></div>
            
            <!-- Modal content with glass effect -->
            <div class="relative z-10 w-full max-w-3xl mx-auto bg-white/10 backdrop-blur-md rounded-xl overflow-hidden shadow-2xl">
                <!-- Modal header -->
                <div class="p-6 border-b border-white/20">
                    <div class="flex justify-between items-center">
                        <h2 class="text-2xl font-bold text-white">Add New Movie</h2>
                        <button id="closeModalBtn" class="text-white hover:text-gray-300 focus:outline-none">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                        </button>
                    </div>
                    <!-- Step indicator -->
                    <div class="flex justify-between mt-4">
                        ${Array.from({length: totalSteps}, (_, i) => 
                            `<div class="flex flex-col items-center">
                                <div class="w-8 h-8 rounded-full flex items-center justify-center ${i+1 === currentStep ? 'bg-[#e50914] text-white' : i+1 < currentStep ? 'bg-green-500 text-white' : 'bg-white/20 text-white/70'} text-sm font-bold">${i+1}</div>
                                <span class="text-xs mt-1 text-white/70">Step ${i+1}</span>
                            </div>`
                        ).join('<div class="flex-1 h-px bg-white/20 self-center mx-2"></div>')}
                    </div>
                </div>
                
                <!-- Modal content area -->
                <div id="modal-content" class="p-6">
                    <!-- Step 1: Search for a movie -->
                    <div id="step-1" class="step-content ${currentStep === 1 ? '' : 'hidden'}">
                        <h3 class="text-xl font-semibold text-white mb-4">Search for a movie</h3>
                        <div class="mb-4">
                            <input type="text" id="movie-search" placeholder="Enter movie title..." 
                                   class="w-full px-4 py-2 bg-white/30 backdrop-blur-sm rounded-lg border border-white/20 focus:ring-2 focus:ring-white/50 focus:border-transparent text-white">
                        </div>
                        <div id="search-results" class="max-h-96 overflow-y-auto space-y-2">
                            <!-- Search results will appear here -->
                            <div class="text-center text-white/70 py-8">
                                Search for a movie to see results
                            </div>
                        </div>
                    </div>
                    
                    <!-- Step 2: Movie Info -->
                    <div id="step-2" class="step-content ${currentStep === 2 ? '' : 'hidden'}">
                        <h3 class="text-xl font-semibold text-white mb-4">Movie Information</h3>
                        <div id="movie-info" class="space-y-4">
                            <!-- Movie info will appear here -->
                        </div>
                    </div>
                    
                    <!-- Step 3: User Experience -->
                    <div id="step-3" class="step-content ${currentStep === 3 ? '' : 'hidden'}">
                        <h3 class="text-xl font-semibold text-white mb-4">Your Experience</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <h4 class="text-white font-medium mb-2">Movie Status</h4>
                                <div class="space-y-3">
                                    <label class="flex items-center space-x-2 text-white cursor-pointer">
                                        <input type="checkbox" id="watched-checkbox" class="h-5 w-5 rounded border-white/30 bg-white/10 text-[#e50914] focus:ring-[#e50914]">
                                        <span>Watched</span>
                                    </label>
                                    <label class="flex items-center space-x-2 text-white cursor-pointer">
                                        <input type="checkbox" id="watchlist-checkbox" class="h-5 w-5 rounded border-white/30 bg-white/10 text-[#e50914] focus:ring-[#e50914]">
                                        <span>Add to Watchlist</span>
                                    </label>
                                    <label class="flex items-center space-x-2 text-white cursor-pointer">
                                        <input type="checkbox" id="favorite-checkbox" class="h-5 w-5 rounded border-white/30 bg-white/10 text-[#e50914] focus:ring-[#e50914]">
                                        <span>Add to Favorites</span>
                                    </label>
                                </div>
                            </div>
                            
                            <div>
                                <h4 class="text-white font-medium mb-2">Your Rating</h4>
                                <div class="flex justify-center space-x-2 mb-4">
                                    ${Array.from({length: 10}, (_, i) => 
                                        `<button type="button" class="rating-star text-3xl focus:outline-none transition-all duration-200 hover:scale-110" data-value="${i+1}">
                                            <svg class="w-8 h-8 text-gray-300" fill="currentColor" viewBox="0 0 24 24">
                                                <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"></path>
                                            </svg>
                                        </button>`
                                    ).join('')}
                                </div>
                                <input type="hidden" id="rating-value" value="0">
                            </div>
                        </div>
                        
                        <div class="mt-6">
                            <h4 class="text-white font-medium mb-2">Your Comment</h4>
                            <textarea id="comment-text" rows="3" 
                                   class="w-full px-4 py-2 bg-white/30 backdrop-blur-sm rounded-lg border border-white/20 focus:ring-2 focus:ring-white/50 focus:border-transparent text-white resize-none"></textarea>
                        </div>
                    </div>
                    
                    <!-- Step 4: Categories -->
                    <div id="step-4" class="step-content ${currentStep === 4 ? '' : 'hidden'}">
                        <h3 class="text-xl font-semibold text-white mb-4">Select Categories (1-5)</h3>
                        <div id="categories-container" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                            <!-- Categories will be loaded here -->
                            <div class="text-center text-white/70 py-8 col-span-full">
                                Loading categories...
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Modal footer with buttons -->
                <div class="p-6 border-t border-white/20 flex justify-between">
                    <button id="prev-step-btn" class="px-5 py-2 bg-white/20 backdrop-blur-sm text-white rounded-lg hover:bg-white/30 transition-colors ${currentStep === 1 ? 'invisible' : ''}">
                        Back
                    </button>
                    <button id="next-step-btn" class="px-5 py-2 bg-amber-500/80 backdrop-blur-sm text-white rounded-lg hover:bg-amber-500 transition-colors">
                        ${currentStep === totalSteps ? 'Save Movie' : 'Next'}
                    </button>
                </div>
            </div>
        </div>`;
        
        // Add modal to the document
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Set up event listeners
        document.getElementById('closeModalBtn').addEventListener('click', hideAddMovieModal);
        document.getElementById('prev-step-btn').addEventListener('click', goToPreviousStep);
        document.getElementById('next-step-btn').addEventListener('click', goToNextStep);
        
        // Only set up search if we're on step 1
        if (currentStep === 1) {
            document.getElementById('movie-search').addEventListener('input', handleMovieSearch);
        }
        
        // Star rating in Step 3
        document.querySelectorAll('.rating-star').forEach(star => {
            star.addEventListener('click', handleRatingClick);
        });
        
        // If we're starting with a movie already selected, display it
        if (selectedMovie && currentStep === 2) {
            displayMovieInfo(selectedMovie);
        }
        
        // If we're on step 4, load categories
        if (currentStep === 4) {
            loadCategories();
        }
        
        // Modal click outside to close
        document.getElementById('add-movie-modal').addEventListener('click', function(e) {
            if (e.target === this) {
                hideAddMovieModal();
            }
        });
    }
    
    // Hide the add movie modal
    function hideAddMovieModal() {
        const modal = document.getElementById('add-movie-modal');
        if (modal) {
            modal.remove();
        }
    }
    
    // Go to the next step in the modal
    function goToNextStep() {
        // Validate current step
        if (!validateCurrentStep()) {
            return;
        }
        
        if (currentStep < totalSteps) {
            currentStep++;
            updateModalStep();
        } else {
            // On final step, submit the form
            saveMovie();
        }
    }
    
    // Go to the previous step in the modal
    function goToPreviousStep() {
        if (currentStep > 1) {
            currentStep--;
            updateModalStep();
        }
    }
    
    // Update the modal to show the current step
    function updateModalStep() {
        // Hide all step content
        document.querySelectorAll('.step-content').forEach(step => {
            step.classList.add('hidden');
        });
        
        // Show current step
        const currentStepElement = document.getElementById(`step-${currentStep}`);
        if (currentStepElement) {
            currentStepElement.classList.remove('hidden');
        }
        
        // Update step indicators
        const stepIndicators = document.querySelectorAll('.rounded-full');
        stepIndicators.forEach((indicator, index) => {
            if (index + 1 === currentStep) {
                indicator.classList.remove('bg-white/20', 'text-white/70');
                indicator.classList.add('bg-[#e50914]', 'text-white');
            } else if (index + 1 < currentStep) {
                indicator.classList.remove('bg-white/20', 'text-white/70');
                indicator.classList.add('bg-green-500', 'text-white');
            } else {
                indicator.classList.remove('bg-[#e50914]', 'bg-green-500', 'text-white');
                indicator.classList.add('bg-white/20', 'text-white/70');
            }
        });
        
        // Update button text
        const nextButton = document.getElementById('next-step-btn');
        if (nextButton) {
            nextButton.textContent = currentStep === totalSteps ? 'Save Movie' : 'Next';
        }
        
        // Special handling for specific steps
        if (currentStep === 2 && selectedMovie) {
            displayMovieInfo(selectedMovie);
        } else if (currentStep === 4) {
            loadCategories();
        }
        
        updateNavigationButtons();
    }
    
    // Update navigation buttons based on current step
    function updateNavigationButtons() {
        const prevButton = document.getElementById('prev-step-btn');
        if (prevButton) {
            prevButton.style.visibility = currentStep === 1 ? 'hidden' : 'visible';
        }
    }
    
    // Handle movie search input
    function handleMovieSearch(e) {
        const query = e.target.value.trim();
        const resultsContainer = document.getElementById('search-results');
        
        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        if (query.length < 2) {
            resultsContainer.innerHTML = '<div class="text-center text-white/70 py-8">Enter at least 2 characters</div>';
            return;
        }
        
        resultsContainer.innerHTML = '<div class="text-center text-white/70 py-8">Searching...</div>';
        
        // Set a timeout to avoid too many requests
        searchTimeout = setTimeout(() => {
            searchMovies(query);
        }, 500);
    }
    
    // Search for movies
    function searchMovies(query) {
        fetch(`/search_omdb?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                displaySearchResults(data.results || []);
            })
            .catch(error => {
                console.error('Error searching for movies:', error);
                const resultsContainer = document.getElementById('search-results');
                resultsContainer.innerHTML = '<div class="text-center text-red-400 py-8">Error searching for movies</div>';
            });
    }
    
    // Display search results
    function displaySearchResults(results) {
        const resultsContainer = document.getElementById('search-results');
        
        if (!results.length) {
            resultsContainer.innerHTML = '<div class="text-center text-white/70 py-8">No results found</div>';
            return;
        }
        
        const resultsHtml = results.map(movie => {
            const posterUrl = movie.poster && movie.poster !== 'N/A' 
                ? movie.poster 
                : '/static/placeholders/poster_missing.png';
            
            return `
            <div class="movie-result flex space-x-4 p-3 rounded-lg hover:bg-white/10 cursor-pointer transition-colors"
                 data-movie='${JSON.stringify(movie).replace(/'/g, "&#39;")}'>
                <div class="w-16 h-24 flex-shrink-0">
                    <img src="${posterUrl}" alt="${movie.title}" 
                         class="w-full h-full object-cover rounded-md">
                </div>
                <div class="flex flex-col justify-center">
                    <h4 class="text-white font-semibold">${movie.title}</h4>
                    <p class="text-white/70 text-sm">${movie.year || ''}</p>
                    <p class="text-white/50 text-xs">${movie.source === 'senflix' ? 'Already in Senflix' : 'From OMDB'}</p>
                </div>
            </div>`;
        }).join('');
        
        resultsContainer.innerHTML = resultsHtml;
        
        // Add click handlers
        document.querySelectorAll('.movie-result').forEach(result => {
            result.addEventListener('click', () => {
                const movieData = JSON.parse(result.dataset.movie);
                selectMovie(movieData);
            });
        });
    }
    
    // Select a movie from search results
    function selectMovie(movie) {
        selectedMovie = movie;
        currentStep++;
        updateModalStep();
    }
    
    // Display movie info in step 2
    function displayMovieInfo(movie) {
        const infoContainer = document.getElementById('movie-info');
        
        const posterUrl = movie.poster && movie.poster !== 'N/A' 
            ? movie.poster 
            : '/static/placeholders/poster_missing.png';
            
        const movieInfoHtml = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="flex justify-center">
                <img src="${posterUrl}" alt="${movie.title}" 
                     class="h-64 object-cover rounded-lg shadow-lg">
            </div>
            <div class="md:col-span-2">
                <h3 class="text-2xl font-bold text-white mb-1">${movie.title}</h3>
                <p class="text-white/70 mb-4">${movie.year || ''}</p>
                
                <h4 class="text-lg font-semibold text-white mt-4 mb-2">Plot</h4>
                <div class="max-h-36 overflow-y-auto pr-2 mb-4 custom-scrollbar">
                    <p class="text-white/80">${movie.plot || 'No plot available'}</p>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2 text-sm">
                    ${movie.director ? `<div><span class="text-white/60">Director:</span> <span class="text-white">${movie.director}</span></div>` : ''}
                    ${movie.actors ? `<div><span class="text-white/60">Actors:</span> <span class="text-white">${movie.actors}</span></div>` : ''}
                    ${movie.imdbID ? `<div><span class="text-white/60">IMDb ID:</span> <span class="text-white">${movie.imdbID}</span></div>` : ''}
                </div>
            </div>
        </div>`;
        
        infoContainer.innerHTML = movieInfoHtml;
        
        // Add custom scrollbar styling
        const style = document.createElement('style');
        style.textContent = `
            .custom-scrollbar::-webkit-scrollbar {
                width: 8px;
            }
            .custom-scrollbar::-webkit-scrollbar-track {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            .custom-scrollbar::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
            }
            .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                background: rgba(255, 255, 255, 0.5);
            }
        `;
        document.head.appendChild(style);
    }
    
    // Handle rating star click
    function handleRatingClick(e) {
        const star = e.currentTarget;
        const rating = parseInt(star.dataset.value);
        
        // Update hidden input
        document.getElementById('rating-value').value = rating;
        moviePreferences.rating = rating;
        
        // Update star colors
        document.querySelectorAll('.rating-star svg').forEach((starSvg, index) => {
            if (index < rating) {
                starSvg.classList.remove('text-gray-300');
                starSvg.classList.add('text-yellow-400');
            } else {
                starSvg.classList.remove('text-yellow-400');
                starSvg.classList.add('text-gray-300');
            }
        });
    }
    
    // Load categories for step 4
    function loadCategories() {
        const categoriesContainer = document.getElementById('categories-container');
        
        fetch('/api/categories')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Categories response:', data);
                
                if (!data.success) {
                    throw new Error(data.error || 'Failed to load categories');
                }
                
                const categories = data.categories || [];
                
                if (!categories.length) {
                    categoriesContainer.innerHTML = '<div class="text-center text-white/70 py-8 col-span-full">No categories available</div>';
                    return;
                }
                
                const categoriesHtml = categories.map(category => `
                <div class="category-option group relative cursor-pointer" data-category-id="${category.id}">
                    <div class="relative block h-24 rounded-xl overflow-hidden shadow-lg bg-gray-900 transition-all duration-300">
                        <div class="absolute inset-0 bg-no-repeat bg-cover bg-center opacity-60 transition-opacity duration-300"
                            style="background-image: url('/static/categories/${category.img || 'default-category.jpg'}');">
                        </div>
                        <div class="absolute inset-0 bg-gradient-to-r from-gray-900/95 via-gray-900/85 to-gray-900/30"></div>
                        <div class="relative flex flex-col justify-center h-full p-4 text-gray-100">
                            <span class="text-md font-bold drop-shadow-lg">${category.name}</span>
                        </div>
                        
                        <!-- Selection indicator -->
                        <div class="absolute top-2 right-2 w-5 h-5 rounded-full bg-[#e50914] opacity-0 transition-opacity duration-300 flex items-center justify-center">
                            <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                            </svg>
                        </div>
                    </div>
                </div>`).join('');
                
                categoriesContainer.innerHTML = categoriesHtml;
                
                // Add click handlers for categories
                document.querySelectorAll('.category-option').forEach(option => {
                    option.addEventListener('click', toggleCategorySelection);
                });
            })
            .catch(error => {
                console.error('Error loading categories:', error);
                categoriesContainer.innerHTML = `<div class="text-center text-red-400 py-8 col-span-full">Error loading categories: ${error.message}</div>`;
            });
    }
    
    // Toggle category selection
    function toggleCategorySelection(e) {
        const option = e.currentTarget;
        const categoryId = option.dataset.categoryId;
        const indicator = option.querySelector('.absolute.top-2.right-2');
        const backdrop = option.querySelector('.absolute.inset-0.bg-no-repeat');
        
        const isSelected = selectedCategories.includes(categoryId);
        
        if (isSelected) {
            // Remove category
            selectedCategories = selectedCategories.filter(id => id !== categoryId);
            indicator.style.opacity = '0';
            backdrop.style.opacity = '0.6';
        } else {
            // Add category if limit not reached
            if (selectedCategories.length < 5) {
                selectedCategories.push(categoryId);
                indicator.style.opacity = '1';
                backdrop.style.opacity = '0.9';
            } else {
                // Show error toast
                showToast('You can select a maximum of 5 categories', 'error');
                return;
            }
        }
    }
    
    // Validate the current step
    function validateCurrentStep() {
        switch (currentStep) {
            case 1:
                return true; // Move to Step 2 happens on movie selection
            case 2:
                return selectedMovie !== null;
            case 3:
                // Update preferences from checkboxes
                moviePreferences.watched = document.getElementById('watched-checkbox').checked;
                moviePreferences.watchlist = document.getElementById('watchlist-checkbox').checked;
                moviePreferences.favorite = document.getElementById('favorite-checkbox').checked;
                return true;
            case 4:
                return true; // Categories are optional
            default:
                return true;
        }
    }
    
    // Save the movie
    function saveMovie() {
        const loadingBtn = document.getElementById('next-step-btn');
        loadingBtn.textContent = 'Saving...';
        loadingBtn.disabled = true;
        
        // Get comment
        const comment = document.getElementById('comment-text').value.trim();
        
        // Prepare data
        const movieData = {
            title: selectedMovie.title,
            year: selectedMovie.year ? parseInt(selectedMovie.year) : null,
            imdbID: selectedMovie.imdbID,
            plot: selectedMovie.plot,
            poster: selectedMovie.poster,
            director: selectedMovie.director,
            actors: selectedMovie.actors,
            source: selectedMovie.source || 'manual',
            watched: moviePreferences.watched,
            watchlist: moviePreferences.watchlist,
            favorite: moviePreferences.favorite,
            rating: moviePreferences.rating || 0,
            comment: comment,
            categories: selectedCategories
        };
        
        console.log('Sending movie data:', movieData);
        
        // Show saving indicator
        showToast('Saving movie...', 'info');
        
        // Send data to server
        fetch('/add_new_movie', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(movieData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Server response:', data);
            if (data.success) {
                // Force modal removal immediately
                const modal = document.getElementById('add-movie-modal');
                if (modal) {
                    modal.remove();
                }
                
                // Show more detailed success message
                let successMessage = 'Movie added successfully!';
                if (data.poster_filename) {
                    successMessage += ' Poster saved.';
                }
                
                // Show success toast after modal is closed
                showToast(successMessage, 'success');
                
                // Refresh the page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                throw new Error(data.error || 'Failed to add movie');
            }
        })
        .catch(error => {
            console.error('Error saving movie:', error);
            showToast(error.message || 'Error saving movie', 'error');
            
            // Re-enable button
            loadingBtn.textContent = 'Save Movie';
            loadingBtn.disabled = false;
        });
    }
    
    // Show a toast message
    function showToast(message, type = 'success') {
        // Remove any existing toasts
        document.querySelectorAll('.toast-message').forEach(toast => toast.remove());
        
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 z-50 px-4 py-2 rounded-lg shadow-lg toast-message 
            ${type === 'success' ? 'bg-green-600' : 
              type === 'error' ? 'bg-red-600' : 
              'bg-blue-600'} text-white`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        // Remove after 3 seconds
        setTimeout(() => {
            toast.classList.add('opacity-0');
            toast.style.transition = 'opacity 300ms ease-out';
            
            // Remove from DOM after fade out
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 300);
        }, 3000);
    }
    
    // Make functions available globally
    window.showAddMovieModal = showAddMovieModal;
    window.hideAddMovieModal = hideAddMovieModal;
})(); 
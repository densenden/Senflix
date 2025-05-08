// movie_modal.js - Modern glass design rating modal
window.showRatingModal = function(movieId) {
    // Get movie card info to populate modal
    const card = document.querySelector(`.movie-card-wrapper[data-movie-id="${movieId}"]`);
    if (!card) {
        return;
    }
    
    // Extract movie details from the card
    const posterBackground = card.querySelector('.poster-bg')?.style.backgroundImage;
    const posterUrl = posterBackground ? posterBackground.replace('url("','').replace('")','') : '';
    const title = card.querySelector('h3')?.textContent || '';
    const year = card.querySelector('.text-xs span')?.textContent || '';
    
    // Create modal HTML structure with glass design
    const modalHtml = `
    <div id="rating-modal" class="fixed inset-0 z-50 flex items-center justify-center">
        <!-- Full screen backdrop with blur effect -->
        <div class="absolute inset-0 bg-black/80 backdrop-blur-sm z-0"></div>
        
        <!-- Modal content with glass effect -->
        <div class="relative z-10 w-full max-w-2xl mx-auto bg-white/10 backdrop-blur-md rounded-xl overflow-hidden shadow-2xl">
            <!-- Modal header with movie details and background -->
            <div class="relative h-72 overflow-hidden">
                <!-- Movie poster background with stronger gradient overlay -->
                <div class="absolute inset-0">
                    <div class="absolute inset-0 bg-gradient-to-b from-black/30 via-black/70 to-black/95 z-0"></div>
                    <div class="absolute inset-0 bg-cover bg-center z-0" style="background-image: url('${posterUrl}')"></div>
                </div>
                
                <div class="absolute bottom-0 left-0 w-full p-6 z-10">
                    <h2 id="modalTitle" class="text-4xl font-bold text-white mb-1">${title}</h2>
                    <p id="modalYear" class="text-xl text-white/80">${year}</p>
                </div>
            </div>
            
            <!-- Rating form -->
            <div class="p-6 pt-3 bg-white/20 backdrop-blur-md">
                <form id="ratingForm" class="space-y-6">
                    <input type="hidden" id="modalMovieId" name="movie_id" value="${movieId}">
                    <input type="hidden" id="ratingValue" name="rating" value="0">
                    
                    <!-- Star rating -->
                    <div>
                        <p class="text-white text-lg mb-3">Your Rating</p>
                        <div class="flex justify-center space-x-3">
                            ${Array.from({length: 10}, (_, i) => 
                                `<button type="button" class="rating-star text-4xl focus:outline-none transition-all duration-200 hover:scale-110" data-value="${i+1}">
                                    <svg class="w-10 h-10 text-gray-300" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"></path>
                                    </svg>
                                </button>`
                            ).join('')}
                        </div>
                    </div>
                    
                    <!-- Comment section -->
                    <div>
                        <label for="comment" class="block text-white text-lg mb-2">Your Comment</label>
                        <textarea id="comment" name="comment" rows="3" 
                                  class="w-full px-4 py-2 bg-white/30 backdrop-blur-sm rounded-lg border border-white/20 focus:ring-2 focus:ring-white/50 focus:border-transparent resize-none text-white"></textarea>
                    </div>
                    
                    <!-- Error message -->
                    <div id="ratingErrorMessage" class="hidden text-red-500 bg-white/30 backdrop-blur-sm p-3 rounded-lg"></div>
                    
                    <!-- Buttons -->
                    <div class="flex justify-end space-x-3">
                        <button type="button" id="cancelBtn" class="px-5 py-2 bg-white/20 backdrop-blur-sm text-white rounded-lg hover:bg-white/30 transition-colors">
                            Cancel
                        </button>
                        <button type="submit" class="px-5 py-2 bg-amber-500/80 backdrop-blur-sm text-white rounded-lg hover:bg-amber-500 transition-colors">
                            Submit
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>`;
    
    // Remove any existing modals
    const existingModals = document.querySelectorAll('[id$="Modal"], [id$="modal"]');
    existingModals.forEach(modal => modal.remove());
    
    // Add modal to the document
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Get references to new elements
    const modal = document.getElementById('rating-modal');
    const form = document.getElementById('ratingForm');
    const ratingInput = document.getElementById('ratingValue');
    const commentInput = document.getElementById('comment');
    const stars = document.querySelectorAll('.rating-star');
    const errorMessage = document.getElementById('ratingErrorMessage');
    const cancelBtn = document.getElementById('cancelBtn');
    
    // Set up star rating functionality
    stars.forEach(star => {
        star.addEventListener('click', () => {
            const rating = parseInt(star.dataset.value);
            
            // Set the hidden input value
            if (ratingInput) {
                ratingInput.value = rating;
            }
            
            // Update the star colors
            stars.forEach(s => {
                const starValue = parseInt(s.dataset.value);
                const starSvg = s.querySelector('svg');
                
                if (starValue <= rating) {
                    starSvg.classList.remove('text-gray-300');
                    starSvg.classList.add('text-yellow-400');
                } else {
                    starSvg.classList.remove('text-yellow-400');
                    starSvg.classList.add('text-gray-300');
                }
            });
        });
    });
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            window.hideRatingModal();
        }
    });
    
    // Cancel button handler
    cancelBtn.addEventListener('click', () => {
        window.hideRatingModal();
    });
    
    // Form submission handler
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Get form data
        const formData = new FormData(form);
        const movieId = formData.get('movie_id');
        const rating = formData.get('rating');
        const comment = formData.get('comment');
        
        // Validate rating
        if (!rating || parseInt(rating) <= 0) {
            if (errorMessage) {
                errorMessage.textContent = 'Please select a rating (1-10 stars)';
                errorMessage.classList.remove('hidden');
                setTimeout(() => {
                    errorMessage.classList.add('hidden');
                }, 3000);
            }
            return;
        }
        
        try {
            // Submit the rating
            const response = await fetch('/rate_movie', {
                method: 'POST',
                body: new URLSearchParams(formData),
                headers: {
                    'Cache-Control': 'no-cache'
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Hide the modal
                window.hideRatingModal();
                
                // Show success message
                const toast = document.createElement('div');
                toast.className = 'fixed bottom-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg z-50';
                toast.textContent = 'Rating saved successfully!';
                document.body.appendChild(toast);
                
                // Remove toast after 3 seconds
                setTimeout(() => {
                    toast.remove();
                }, 3000);
                
                // Update UI to reflect the new rating status
                updateMovieCardStatus(movieId, { rated: true, rating: rating });
            } else {
                // Show error message
                if (errorMessage) {
                    errorMessage.textContent = 'Error saving rating: ' + (result.error || 'Unknown error');
                    errorMessage.classList.remove('hidden');
                }
            }
        } catch (error) {
            if (errorMessage) {
                errorMessage.textContent = 'Error saving rating: ' + error.message;
                errorMessage.classList.remove('hidden');
            }
        }
    });
    
    // Immediately fetch existing rating with delay to ensure DOM is ready
    setTimeout(() => {
        fetchExistingRating(movieId);
    }, 100);
};

// Function to update movie card status icons
function updateMovieCardStatus(movieId, status) {
    const card = document.querySelector(`.movie-card-wrapper[data-movie-id="${movieId}"]`);
    if (!card) return;
    
    // Update rate button/icon status
    if (status.rated) {
        // Find all rate buttons for this movie
        const rateButtons = card.querySelectorAll('.rate-btn, .star-btn, .star-rating');
        rateButtons.forEach(btn => {
            btn.classList.add('active', 'text-yellow-400');
            btn.classList.remove('text-gray-400', 'text-gray-500');
            
            // If it has an SVG, update its color too
            const svg = btn.querySelector('svg');
            if (svg) {
                svg.classList.add('text-yellow-400');
                svg.classList.remove('text-gray-400', 'text-gray-500');
            }
        });
    }
    
    // Update watched button/icon status if needed
    if (status.watched !== undefined) {
        const watchButtons = card.querySelectorAll('.watch-btn, .eye-btn');
        watchButtons.forEach(btn => {
            if (status.watched) {
                btn.classList.add('active', 'text-blue-400');
                btn.classList.remove('text-gray-400', 'text-gray-500');
            } else {
                btn.classList.remove('active', 'text-blue-400');
                btn.classList.add('text-gray-500');
            }
            
            // If it has an SVG, update its color too
            const svg = btn.querySelector('svg');
            if (svg) {
                if (status.watched) {
                    svg.classList.add('text-blue-400');
                    svg.classList.remove('text-gray-400', 'text-gray-500');
                } else {
                    svg.classList.remove('text-blue-400');
                    svg.classList.add('text-gray-500');
                }
            }
        });
    }
}

// Function to fetch and apply existing rating
function fetchExistingRating(movieId) {
    // Make sure the modal elements exist
    const ratingInput = document.getElementById('ratingValue');
    const commentInput = document.getElementById('comment');
    const stars = document.querySelectorAll('.rating-star');
    const errorMessage = document.getElementById('ratingErrorMessage');
    
    if (!ratingInput || !stars.length) return;
    
    const cacheBuster = new Date().getTime();
    const fetchUrl = `/get_movie_rating/${movieId}?t=${cacheBuster}`;
    
    fetch(fetchUrl, {
        method: 'GET',
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server returned status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Log what we received to help debug
        console.log(`Rating data for movie ${movieId}:`, data);
        
        // Skip updating form if we don't have valid data
        if (!data || (data.success === false && !data.rating && !data.comment)) {
            return;
        }
        
        // Set rating value and update stars
        if (data.rating !== null && data.rating !== undefined) {
            const rating = parseFloat(data.rating);
            
            if (!isNaN(rating)) {
                console.log(`Setting rating to ${rating} stars`);
                
                // Set hidden input value
                ratingInput.value = rating;
                
                // Update stars visually
                let starsUpdated = 0;
                stars.forEach(star => {
                    const starValue = parseInt(star.dataset.value);
                    const starSvg = star.querySelector('svg');
                    
                    if (starValue <= rating) {
                        starSvg.classList.remove('text-gray-300');
                        starSvg.classList.add('text-yellow-400');
                        starsUpdated++;
                    }
                });
                
                console.log(`Updated ${starsUpdated} stars out of ${stars.length}`);
                
                // Also update card status
                updateMovieCardStatus(movieId, { rated: true, rating: rating });
            }
        }
        
        // Set comment value
        if (data.comment !== undefined && commentInput) {
            commentInput.value = data.comment;
            console.log(`Set comment to: ${data.comment}`);
        }
    })
    .catch(error => {
        console.error(`Error fetching rating for movie ${movieId}:`, error);
        if (errorMessage) {
            errorMessage.textContent = `Error loading rating data: ${error.message}`;
            errorMessage.classList.remove('hidden');
        }
    });
}

// Function to hide and remove the rating modal
window.hideRatingModal = function() {
    const modal = document.getElementById('rating-modal');
    if (modal) {
        // Add fade-out animation
        modal.classList.add('opacity-0');
        modal.style.transition = 'opacity 300ms ease-out';
        
        // Remove modal after animation completes
        setTimeout(() => {
            modal.remove();
        }, 300);
    }
};

// Initialize event listeners when the DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Attach click handlers to rate buttons
    document.querySelectorAll('.rate-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const movieId = this.closest('.movie-card-wrapper').dataset.movieId;
            window.showRatingModal(movieId);
        });
    });
    
    // Attach click handlers to star buttons on movie cards
    document.querySelectorAll('.movie-card-wrapper .star-btn, .movie-card-wrapper .star-rating').forEach(starElement => {
        starElement.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const movieId = this.closest('.movie-card-wrapper').dataset.movieId;
            window.showRatingModal(movieId);
        });
    });
});


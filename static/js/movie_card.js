// movie_card.js
console.log('movie_card.js loaded - Adding event listeners for rating buttons');

(function() {
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    function bindActionButtons() {
        document.querySelectorAll('.action-btn').forEach(button => {
            if (button.dataset.listenerAttached === 'true') return;
            button.dataset.listenerAttached = 'true';
            button.addEventListener('click', async function(e) {
                e.preventDefault();
                e.stopPropagation();
                await handleButtonClick(button);
            });
        });
    }
    function updateButtonState(movieId, action, isActive) {
        document.querySelectorAll(`.action-btn[data-movie-id="${movieId}"][data-action="${action}"]`).forEach(btn => {
            btn.classList.toggle('active', isActive);
            
            const tooltipSpan = btn.querySelector('.tooltip');
            let tooltipText = '';

            if (action === 'watchlist') {
                tooltipText = isActive ? 'Remove from Watchlist' : 'Add to Watchlist';
            } else if (action === 'watched') {
                tooltipText = isActive ? 'Mark as Unwatched' : 'Mark as Watched'; 
            } else if (action === 'favorite') {
                tooltipText = isActive ? 'Remove from Favorites' : 'Add to Favorites';
            } else if (action === 'rate') {
                tooltipText = isActive ? 'Update Rating' : 'Rate Movie';
            }

            btn.title = tooltipText; 
            if (tooltipSpan) {
                tooltipSpan.textContent = tooltipText;
            }
        });
    }
    async function handleButtonClick(button) {
        const movieId = button.dataset.movieId;
        const action = button.dataset.action;
        if (!movieId || !action) return;
        if (button.classList.contains('processing')) return;
        
        button.classList.add('processing');
        const wasActive = button.classList.contains('active'); 

        try {
            let endpoint = '';
            let method = 'POST';
            let toastMessage = '';

            if (action === 'watchlist') {
                endpoint = `/toggle_watchlist/${movieId}`;
                toastMessage = 'Watchlist updated successfully!';
            } else if (action === 'watched') {
                endpoint = `/toggle_watched/${movieId}`;
                toastMessage = 'Watched status updated successfully!';
            } else if (action === 'favorite') {
                endpoint = `/toggle_favorite/${movieId}`;
                toastMessage = 'Favorites updated successfully!';
            } else if (action === 'rate') {
                if (typeof window.showRatingModal === 'function') {
                    console.log(`Opening rating modal for movie ID: ${movieId}`);
                    window.showRatingModal(movieId);
                } else {
                    console.error('showRatingModal function is not defined globally.');
                    alert('Rating feature is currently unavailable.');
                }
                button.classList.remove('processing'); 
                return; 
            } else throw new Error('Invalid action');

            const response = await fetch(endpoint, { method });
            if (!response.ok) {
                let errorMsg = `Request failed with status ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.error || errorMsg;
                } catch (jsonError) {
                    errorMsg += await response.text(); 
                }
                throw new Error(errorMsg);
            }
            
            // Parse the response for user status information
            const responseData = await response.json();
            
            // Update button states based on server response
            if (responseData.success) {
                // Update state for the clicked button
                updateButtonState(movieId, action, responseData.new_state);
                
                // Update other buttons if needed
                if (responseData.user_watched !== undefined) {
                    updateButtonState(movieId, 'watched', responseData.user_watched);
                }
                if (responseData.user_watchlist !== undefined) {
                    updateButtonState(movieId, 'watchlist', responseData.user_watchlist);
                }
                if (responseData.user_rated !== undefined) {
                    updateButtonState(movieId, 'rate', responseData.user_rated);
                }
            }
            
            // Show success message
            showToast(toastMessage);
            
        } catch (error) {
            console.error('Error handling button click:', error);
            showToast(`Error: ${error.message}`, 'error');
            // Revert the button to original state on error
            button.classList.toggle('active', wasActive);
        } finally {
            button.classList.remove('processing');
        }
    }

    // Initial button bindings
    document.addEventListener('DOMContentLoaded', bindActionButtons);
    bindActionButtons(); // Bind immediately in case DOM is already loaded

    // Expose for potential external use
    window.bindMovieCardActions = bindActionButtons;

    if (typeof window.showRatingModal !== 'function') {
        window.showRatingModal = function(movieId) { 
            console.warn('showRatingModal stub called for movie:', movieId);
            alert('Rating modal functionality is not loaded correctly.'); 
        };
    }
    if (typeof window.hideRatingModal !== 'function') {
        window.hideRatingModal = function() { 
            console.warn('hideRatingModal stub called.'); 
            const modal = document.getElementById('ratingModal');
            if(modal) modal.classList.add('hidden');
        };
    }

    // Enhanced debugging for rate button clicks
    document.addEventListener('click', function(event) {
        // Check for rate buttons with various selectors to ensure we catch all
        let rateBtn = null;
        if (event.target.classList.contains('rate-btn') || event.target.closest('.rate-btn')) {
            rateBtn = event.target.classList.contains('rate-btn') ? event.target : event.target.closest('.rate-btn');
        } else if (event.target.classList.contains('star-btn') || event.target.closest('.star-btn')) {
            rateBtn = event.target.classList.contains('star-btn') ? event.target : event.target.closest('.star-btn');
        } else if (event.target.classList.contains('star-rating') || event.target.closest('.star-rating')) {
            rateBtn = event.target.classList.contains('star-rating') ? event.target : event.target.closest('.star-rating');
        } else if (event.target.classList.contains('action-btn') && event.target.dataset.action === 'rate') {
            rateBtn = event.target;
        }
        
        if (rateBtn) {
            const movieCard = rateBtn.closest('.movie-card-wrapper');
            
            if (movieCard) {
                const movieId = movieCard.dataset.movieId;
                console.log(`Rate button clicked for movie ID: ${movieId}`);
                
                // Prevent default to avoid any navigation
                event.preventDefault();
                event.stopPropagation();
                
                // Call rating modal directly
                if (typeof window.showRatingModal === 'function') {
                    console.log(`Opening rating modal for movie ID: ${movieId}`);
                    window.showRatingModal(movieId);
                }
            }
        }
    });
})(); 
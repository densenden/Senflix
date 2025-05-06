// movie_modal.js - Completely rewritten for simplicity
window.showRatingModal = function(movieId) {
    console.clear(); // Clear previous console logs
    console.log('%c===== RATING MODAL DEBUG =====', 'background:#222; color:#bada55; font-size:16px');
    console.log('Opening rating modal for movie ID:', movieId);
    
    // Get DOM elements
    const modal = document.getElementById('ratingModal');
    const form = document.getElementById('ratingForm');
    const movieIdInput = document.getElementById('modalMovieId');
    const ratingInput = document.getElementById('ratingValue');
    const commentInput = document.getElementById('comment');
    const stars = document.querySelectorAll('.rating-star');
    
    console.log('DOM elements found:', {
        modal: !!modal,
        form: !!form,
        movieIdInput: !!movieIdInput,
        ratingInput: !!ratingInput, 
        commentInput: !!commentInput,
        stars: stars.length
    });
    
    // Set movie ID in the form
    if (movieIdInput) {
        movieIdInput.value = movieId;
        console.log('Set movie ID in form:', movieId);
    }
    
    // Show the modal immediately for better UX
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        console.log('Modal displayed');
    }
    
    // Get movie card info to populate modal header
    const card = document.querySelector(`.movie-card-wrapper[data-movie-id="${movieId}"]`);
    console.log('Found movie card:', !!card);
    
    if (card) {
        const poster = card.querySelector('.poster-bg')?.style.backgroundImage;
        const title = card.querySelector('h3')?.textContent || '';
        const year = card.querySelector('.text-xs span')?.textContent || '';
        
        console.log('Movie info from card:', { title, year, hasPoster: !!poster });
        
        if (document.getElementById('modalPoster')) {
            document.getElementById('modalPoster').src = poster ? poster.replace('url("','').replace('")','') : '';
        }
        
        if (document.getElementById('modalTitle')) {
            document.getElementById('modalTitle').textContent = title;
        }
        
        if (document.getElementById('modalYear')) {
            document.getElementById('modalYear').textContent = year;
        }
    }
    
    // Initialize with default state but DON'T RESET THE FORM YET
    // We'll wait until we know if there's existing data
    
    // Fetch existing rating data with cache busting timestamp
    const cacheBuster = new Date().getTime();
    const fetchUrl = `/get_movie_rating/${movieId}?t=${cacheBuster}`;
    console.log('Fetching data from URL:', fetchUrl);
    
    fetch(fetchUrl, {
        method: 'GET',
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
        .then(response => {
            console.log('Response status:', response.status);
            console.log('Response OK:', response.ok);
            
            if (!response.ok) {
                throw new Error(`Server returned status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('%c Rating data received from server:', 'color:#4CAF50; font-weight:bold');
            console.log(data);
            
            // Debug all properties for troubleshooting
            console.log('Data properties:', Object.keys(data));
            console.log('Success:', data.success);
            console.log('Rating:', data.rating, '(type:', typeof data.rating, ')');
            console.log('Comment:', data.comment, '(type:', typeof data.comment, ')');
            
            // Reset the form ONLY if we don't have valid data
            if (!data || !data.success) {
                console.log('No valid data or success=false, resetting form');
                if (form) {
                    form.reset();
                }
                
                // Reset all stars to gray
                stars.forEach(star => {
                    star.classList.remove('text-yellow-400', 'selected');
                    star.classList.add('text-gray-500');
                });
                
                // Set rating value to 0
                if (ratingInput) {
                    ratingInput.value = 0;
                }
                return;
            }
            
            // If we have valid data, we DON'T reset the form
            console.log('Valid data received, updating form...');
            
            // Reset stars first (we'll update them if we have a rating)
            stars.forEach(star => {
                star.classList.remove('text-yellow-400', 'selected');
                star.classList.add('text-gray-500');
            });
            
            // Set comment if available
            if (commentInput && data.comment) {
                commentInput.value = data.comment;
                console.log('Comment set to:', data.comment);
            } else {
                // Clear comment if none provided
                if (commentInput) {
                    commentInput.value = '';
                }
                console.log('No comment data, cleared comment field');
            }
            
            // Set rating if available
            if (ratingInput && data.rating !== null && data.rating !== undefined) {
                // Parse the rating as a number and round it
                const rating = Math.round(parseFloat(data.rating));
                ratingInput.value = rating;
                console.log('Rating set to:', rating);
                
                // Highlight the appropriate stars
                let starsUpdated = 0;
                stars.forEach(star => {
                    const starValue = parseInt(star.dataset.value);
                    if (starValue <= rating) {
                        star.classList.add('text-yellow-400', 'selected');
                        star.classList.remove('text-gray-500');
                        starsUpdated++;
                    }
                });
                console.log(`Updated ${starsUpdated} stars to yellow`);
            } else {
                // Reset rating if none provided
                if (ratingInput) {
                    ratingInput.value = 0;
                }
                console.log('No rating data, reset to 0');
            }
            
            // Log final form state
            console.log('Final form state:', {
                rating: ratingInput ? ratingInput.value : 'N/A',
                comment: commentInput ? commentInput.value : 'N/A'
            });
        })
        .catch(error => {
            console.error('Error fetching rating data:', error);
            console.error('Error details:', {
                message: error.message,
                stack: error.stack
            });
            
            // On error, reset the form
            if (form) {
                form.reset();
            }
            
            // Reset all stars to gray
            stars.forEach(star => {
                star.classList.remove('text-yellow-400', 'selected');
                star.classList.add('text-gray-500');
            });
            
            // Set rating value to 0
            if (ratingInput) {
                ratingInput.value = 0;
            }
        })
        .finally(() => {
            console.log('%c===== RATING MODAL SETUP COMPLETE =====', 'background:#222; color:#bada55; font-size:16px');
        });
        
    // Add additional verification with a small delay to ensure data is displayed
    setTimeout(() => {
        console.log('%c Verification check after timeout:', 'color:orange; font-weight:bold');
        console.log('Current rating value:', ratingInput ? ratingInput.value : 'N/A');
        console.log('Current comment value:', commentInput ? commentInput.value : 'N/A');
        console.log('Yellow stars count:', document.querySelectorAll('.rating-star.text-yellow-400').length);
    }, 1000);
};

window.hideRatingModal = function() {
    const modal = document.getElementById('ratingModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        console.log('Rating modal hidden');
    }
};

// Initialize event listeners when the DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing rating modal functionality');
    
    // Set up star rating click handlers
    const stars = document.querySelectorAll('.rating-star');
    const ratingInput = document.getElementById('ratingValue');
    
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
                if (starValue <= rating) {
                    s.classList.add('text-yellow-400', 'selected');
                    s.classList.remove('text-gray-500');
                } else {
                    s.classList.remove('text-yellow-400', 'selected');
                    s.classList.add('text-gray-500');
                }
            });
        });
    });
    
    // Set up form submission
    const ratingForm = document.getElementById('ratingForm');
    if (ratingForm) {
        ratingForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Get form data
            const formData = new FormData(ratingForm);
            const movieId = formData.get('movie_id');
            const rating = formData.get('rating');
            const comment = formData.get('comment');
            
            console.log('Submitting rating:', {
                movieId,
                rating,
                comment
            });
            
            // Validate rating
            if (!rating || parseInt(rating) <= 0) {
                alert('Please select a rating (1-10 stars)');
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
                console.log('Rating saved, response:', result);
                
                if (result.success) {
                    // Hide the modal
                    window.hideRatingModal();
                    
                    // Show success message
                    const toast = document.createElement('div');
                    toast.className = 'fixed bottom-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg';
                    toast.textContent = 'Rating saved successfully!';
                    document.body.appendChild(toast);
                    
                    // Remove toast after 3 seconds
                    setTimeout(() => {
                        toast.remove();
                    }, 3000);
                    
                    // Update UI - mark the rate button as active
                    const rateButtons = document.querySelectorAll(`.movie-card-wrapper[data-movie-id="${movieId}"] .rate-btn`);
                    rateButtons.forEach(btn => btn.classList.add('active'));
                } else {
                    // Show error message
                    alert('Error saving rating: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error saving rating:', error);
                alert('Error saving rating: ' + error.message);
            }
        });
    }
});

// movie_modal.js
window.showRatingModal = function(movieId) {
    console.log('Opening rating modal for movie ID:', movieId);
    
    // Fetch movie info from card
    const card = document.querySelector(`.movie-card-wrapper[data-movie-id="${movieId}"]`);
    if (card) {
        const poster = card.querySelector('.poster-bg').style.backgroundImage;
        const title = card.querySelector('h3')?.textContent || '';
        const year = card.querySelector('.text-xs span')?.textContent || '';
        document.getElementById('modalPoster').src = poster ? poster.replace('url("','').replace('")','') : '';
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalYear').textContent = year;
    } else {
        console.log('Movie card not found in DOM');
    }
    document.getElementById('modalMovieId').value = movieId;
    
    // Reset form before fetching data
    console.log('Resetting form');
    document.getElementById('ratingForm').reset();
    document.getElementById('ratingValue').value = 0;
    document.querySelectorAll('.rating-star').forEach(star => {
        star.classList.remove('text-yellow-400', 'selected');
        star.classList.add('text-gray-500');
    });
    
    // Always fetch the existing rating data, whether the button is active or not
    console.log('Fetching rating data from server');
    fetch(`/get_movie_rating/${movieId}`)
        .then(response => {
            console.log('Server response status:', response.status);
            if (!response.ok) {
                throw new Error('Network response was not ok: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            console.log('Rating data received:', JSON.stringify(data));
            
            // Update stars to reflect existing rating even if it's 0
            if (data.success) {
                console.log('Rating value from server:', data.rating, 'Type:', typeof data.rating);
                
                if (data.rating !== null && data.rating !== undefined) {
                    // Convert to 1-10 scale if needed
                    const serverRating = parseFloat(data.rating);
                    console.log('Parsed rating:', serverRating);
                    
                    // Calculate rating for UI
                    // If it's already on a 1-10 scale (rating ≥ 5), use as is
                    // If it's on a 0-5 scale (rating < 5), multiply by 2
                    let rating;
                    if (serverRating <= 5) {
                        rating = Math.round(serverRating * 2);
                        console.log('Converting from 0-5 scale to 1-10:', rating);
                    } else {
                        rating = Math.round(serverRating);
                        console.log('Rating already on 1-10 scale:', rating);
                    }
                    
                    console.log('Final rating for UI (1-10 scale):', rating);
                    
                    document.getElementById('ratingValue').value = rating;
                    console.log('Set hidden rating field value to:', rating);
                    
                    // Update star visuals
                    document.querySelectorAll('.rating-star').forEach(star => {
                        const starValue = parseInt(star.dataset.value);
                        const shouldBeSelected = starValue <= rating;
                        console.log(`Star ${starValue} should be ${shouldBeSelected ? 'selected' : 'unselected'}`);
                        
                        if (shouldBeSelected) {
                            star.classList.add('text-yellow-400', 'selected');
                            star.classList.remove('text-gray-500');
                        } else {
                            star.classList.remove('text-yellow-400', 'selected');
                            star.classList.add('text-gray-500');
                        }
                    });
                } else {
                    console.log('No rating value found in data');
                }
                
                // Set comment if exists
                if (data.comment) {
                    console.log('Comment found:', data.comment);
                    document.getElementById('comment').value = data.comment;
                } else {
                    console.log('No comment found in data');
                }
            } else {
                console.log('Server response indicates failure or no data');
            }
        })
        .catch(error => {
            console.error('Error fetching rating data:', error);
        });
    
    document.getElementById('ratingModal').classList.remove('hidden');
    document.getElementById('ratingModal').classList.add('flex');
}
window.hideRatingModal = function() {
    document.getElementById('ratingModal').classList.add('hidden');
    document.getElementById('ratingModal').classList.remove('flex');
}

// Helper function to show toast messages
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 ${type === 'success' ? 'bg-green-600' : 'bg-red-600'} text-white px-4 py-2 rounded-lg shadow-lg z-50`;
    toast.style.opacity = '1';
    toast.style.transition = 'opacity 0.5s ease-in-out';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Ensure the toast is visible for at least 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Movie modal JS initialized');
    let selectedRating = 0;
    const ratingContainer = document.getElementById('starRatingContainer');
    if (!ratingContainer) {
        console.warn('Rating container not found in DOM');
        return;
    }
    const ratingInput = document.getElementById('ratingValue');
    const stars = ratingContainer.querySelectorAll('.rating-star');
    const errorMsgElement = document.getElementById('ratingErrorMessage');
    
    // Function to display error messages in the modal
    function showModalError(message) {
        if (errorMsgElement) {
            errorMsgElement.textContent = message;
            errorMsgElement.classList.remove('hidden');
            // Automatically hide after 5 seconds
            setTimeout(() => {
                errorMsgElement.classList.add('hidden');
            }, 5000);
        }
    }
    
    // Function to hide the error message
    function hideModalError() {
        if (errorMsgElement) {
            errorMsgElement.classList.add('hidden');
        }
    }
    
    function updateStarsVisual(rating) {
        console.log('Updating stars visual for rating:', rating);
        stars.forEach(star => {
            const starValue = parseInt(star.dataset.value);
            const shouldBeSelected = starValue <= rating;
            console.log(`Star ${starValue} should be ${shouldBeSelected ? 'selected' : 'unselected'}`);
            
            star.classList.toggle('text-yellow-400', shouldBeSelected);
            star.classList.toggle('selected', shouldBeSelected);
            star.classList.toggle('text-gray-500', !shouldBeSelected);
        });
    }
    
    stars.forEach(star => {
        star.addEventListener('click', () => {
            selectedRating = parseInt(star.dataset.value);
            console.log('Star clicked, new rating:', selectedRating);
            ratingInput.value = selectedRating;
            updateStarsVisual(selectedRating);
            // Hide error message when a rating is selected
            hideModalError();
        });
    });
    
    document.getElementById('ratingForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        hideModalError(); // Reset error at the beginning
        
        const submitButton = e.target.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.textContent = 'Saving...';
        const formData = new FormData(e.target);
        const movieId = formData.get('movie_id');
        const ratingValue = parseInt(formData.get('rating'));
        
        console.log('Submitting rating form:', {
            movieId: movieId,
            rating: ratingValue,
            comment: formData.get('comment')
        });
        
        if (ratingValue <= 0) {
            showModalError('Please select a rating (1-10 stars).');
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Rating';
            return;
        }
        
        // Convert from 1-10 scale to 0-5 scale if needed
        // This is a temporary conversion that should be handled by backend standardization
        // If the rating system is 0-5, we need to divide by 2 to get the correct value
        const convertedRating = ratingValue / 2; // Convert 1-10 to 0-5 scale
        
        // Create a new FormData object with the converted rating
        const adjustedFormData = new FormData();
        adjustedFormData.append('movie_id', movieId);
        adjustedFormData.append('rating', convertedRating);
        adjustedFormData.append('comment', formData.get('comment'));
        
        try {
            const response = await fetch('/rate_movie', {
                method: 'POST',
                body: new URLSearchParams(adjustedFormData)
            });
            
            console.log('Server response status:', response.status);
            const result = await response.json();
            console.log('Server response data:', result);
            
            if (response.ok && result.success) {
                window.hideRatingModal();
                
                // Update all rate buttons for this movie to show as active
                document.querySelectorAll(`.movie-card-wrapper[data-movie-id="${movieId}"] .rate-btn`).forEach(btn => {
                    console.log('Updating rate button to active state');
                    btn.classList.add('active');
                    
                    // Update icon display
                    const outlineIcon = btn.querySelector('.icon-star-outline');
                    const filledIcon = btn.querySelector('.icon-star-filled');
                    
                    if (outlineIcon) outlineIcon.style.display = 'none';
                    if (filledIcon) filledIcon.style.display = 'block';
                });
                
                // Show success message
                showToast('Rating saved successfully!', 'success');
            } else {
                // Display error message in the modal if available
                const errorMsg = result.error || 'Error saving rating';
                showModalError(errorMsg);
                console.error('Rating error:', errorMsg);
            }
        } catch (error) {
            console.error('Rating error:', error);
            // Display error message in the modal
            showModalError(`Error saving: ${error.message || 'Unknown error'}`);
            
            // Additionally show toast message
            showToast(`Error saving: ${error.message || 'Unknown error'}`, 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Rating';
        }
    });
}); 
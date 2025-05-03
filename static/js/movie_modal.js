// movie_modal.js
window.showRatingModal = function(movieId) {
    // Fetch movie info from card
    const card = document.querySelector(`.movie-card-wrapper[data-movie-id="${movieId}"]`);
    if (card) {
        const poster = card.querySelector('.poster-bg').style.backgroundImage;
        const title = card.querySelector('h3')?.textContent || '';
        const year = card.querySelector('.text-xs span')?.textContent || '';
        document.getElementById('modalPoster').src = poster ? poster.replace('url("','').replace('")','') : '';
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalYear').textContent = year;
    }
    document.getElementById('modalMovieId').value = movieId;
    document.getElementById('ratingModal').classList.remove('hidden');
    document.getElementById('ratingModal').classList.add('flex');
}
window.hideRatingModal = function() {
    document.getElementById('ratingModal').classList.add('hidden');
    document.getElementById('ratingModal').classList.remove('flex');
}

document.addEventListener('DOMContentLoaded', function() {
    let selectedRating = 0;
    const ratingContainer = document.getElementById('starRatingContainer');
    if (!ratingContainer) return;
    const ratingInput = document.getElementById('ratingValue');
    const stars = ratingContainer.querySelectorAll('.rating-star');
    function updateStarsVisual(rating) {
        stars.forEach(star => {
            star.classList.toggle('text-yellow-400', parseInt(star.dataset.value) <= rating);
            star.classList.toggle('selected', parseInt(star.dataset.value) <= rating);
            star.classList.toggle('text-gray-500', parseInt(star.dataset.value) > rating);
        });
    }
    stars.forEach(star => {
        star.addEventListener('click', () => {
            selectedRating = parseInt(star.dataset.value);
            ratingInput.value = selectedRating;
            updateStarsVisual(selectedRating);
        });
    });
    document.getElementById('ratingForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitButton = e.target.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.textContent = 'Saving...';
        const formData = new FormData(e.target);
        if (parseInt(formData.get('rating')) <= 0) {
            alert('Please select a rating.');
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Rating';
            return;
        }
        try {
            const response = await fetch('/rate_movie', {
                method: 'POST',
                body: new URLSearchParams(formData)
            });
            const result = await response.json();
            if (response.ok && result.success) {
                window.hideRatingModal();
                document.querySelectorAll(`.movie-card-wrapper[data-movie-id="${formData.get('movie_id')}"] .rate-btn`).forEach(btn => btn.classList.add('active'));
                const successMessage = document.createElement('div');
                successMessage.className = 'fixed bottom-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg transition-opacity duration-500';
                successMessage.textContent = 'Rating saved successfully!';
                document.body.appendChild(successMessage);
                setTimeout(() => {
                    successMessage.style.opacity = '0';
                    setTimeout(() => successMessage.remove(), 500);
                }, 3000);
            } else {
                throw new Error(result.error || 'Error saving rating');
            }
        } catch (error) {
            alert('Error saving rating: ' + error.message);
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = 'Submit Rating';
        }
    });
}); 
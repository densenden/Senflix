// movie_card.js
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
        document.querySelectorAll(`.${action}-btn[data-movie-id="${movieId}"]`).forEach(btn => {
            btn.classList.toggle('active', isActive);
            if (action === 'watchlist') {
                btn.title = isActive ? 'Remove from Watchlist' : 'Add to Watchlist';
                btn.querySelector('.tooltip').textContent = isActive ? 'Remove from Watchlist' : 'Add to Watchlist';
            } else if (action === 'watched') {
                btn.title = isActive ? 'Mark as Unwatched' : 'Mark as Watched';
                btn.querySelector('.tooltip').textContent = isActive ? 'Mark as Unwatched' : 'Mark as Watched';
            } else if (action === 'rate') {
                btn.title = isActive ? 'Update Rating' : 'Rate Movie';
                btn.querySelector('.tooltip').textContent = isActive ? 'Update Rating' : 'Rate Movie';
            }
        });
    }
    async function handleButtonClick(button) {
        const movieId = button.dataset.movieId;
        const action = button.dataset.action;
        if (!movieId || !action) return;
        if (button.classList.contains('processing')) return;
        button.classList.add('processing');
        try {
            let endpoint, method = 'POST';
            if (action === 'watchlist') endpoint = `/toggle_watchlist/${movieId}`;
            else if (action === 'watched') endpoint = `/toggle_watched/${movieId}`;
            else if (action === 'rate') {
                window.showRatingModal && window.showRatingModal(movieId);
                button.classList.remove('processing');
                return;
            } else throw new Error('Invalid action');
            const response = await fetch(endpoint, { method });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to update movie status');
            const isActive = !button.classList.contains('active');
            updateButtonState(movieId, action, isActive);
            showToast((action === 'watchlist' ? 'Watchlist' : action === 'watched' ? 'Watched status' : 'Status') + ' updated successfully!');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            button.classList.remove('processing');
        }
    }
    document.addEventListener('DOMContentLoaded', bindActionButtons);
    if (!window.showRatingModal) {
        window.showRatingModal = function() { alert('Rating modal is not available.'); };
    }
    if (!window.hideRatingModal) {
        window.hideRatingModal = function() { /* no-op */ };
    }
})(); 
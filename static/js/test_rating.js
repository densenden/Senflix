// Simple test script to verify the rating modal functionality

// Add to DOMContentLoaded to ensure it runs after the page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('TEST SCRIPT: Initializing rating modal test');
    
    // Function to create a test button
    function createTestButton() {
        const testButton = document.createElement('button');
        testButton.textContent = '🛠️ Test Rating Modal';
        testButton.style.position = 'fixed';
        testButton.style.bottom = '20px';
        testButton.style.left = '20px';
        testButton.style.zIndex = '9999';
        testButton.style.padding = '8px 16px';
        testButton.style.backgroundColor = '#4CAF50';
        testButton.style.color = 'white';
        testButton.style.border = 'none';
        testButton.style.borderRadius = '4px';
        testButton.style.cursor = 'pointer';
        
        testButton.addEventListener('click', runTest);
        
        document.body.appendChild(testButton);
        console.log('TEST SCRIPT: Test button created');
    }
    
    // Test function
    function runTest() {
        console.log('TEST SCRIPT: Running rating modal test');
        
        // Test data
        const testRating = 8;
        const testComment = "This is a test comment from direct JS injection";
        
        // First, clear any existing data
        document.getElementById('ratingForm').reset();
        
        // Set the test data directly
        document.getElementById('ratingValue').value = testRating;
        document.getElementById('comment').value = testComment;
        
        // Update the star visuals
        const stars = document.querySelectorAll('.rating-star');
        stars.forEach(star => {
            const starValue = parseInt(star.dataset.value);
            if (starValue <= testRating) {
                star.classList.add('text-yellow-400', 'selected');
                star.classList.remove('text-gray-500');
            } else {
                star.classList.remove('text-yellow-400', 'selected');
                star.classList.add('text-gray-500');
            }
        });
        
        // Show the modal
        document.getElementById('ratingModal').classList.remove('hidden');
        document.getElementById('ratingModal').classList.add('flex');
        
        console.log('TEST SCRIPT: Test completed - modal should be visible with test data');
        console.log('TEST SCRIPT: Rating value:', document.getElementById('ratingValue').value);
        console.log('TEST SCRIPT: Comment value:', document.getElementById('comment').value);
    }
    
    // Create the test button
    createTestButton();
}); 
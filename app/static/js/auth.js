document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const errorMsg = document.getElementById('errorMessage');
    
    // Show loading state
    submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Signing in...';
    submitBtn.disabled = true;
    errorMsg.classList.add('hidden');
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: document.getElementById('username').value,
                password: document.getElementById('password').value
            })
        });
        
        const data = await response.json();
        if (response.ok) {
            // Show success briefly before redirect
            submitBtn.innerHTML = '<i class="fas fa-check"></i> Success!';
            submitBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
            submitBtn.classList.add('bg-green-600', 'hover:bg-green-700');
            
            // Redirect after small delay
            setTimeout(() => {
                window.location.href = '/';
            }, 500);
        } else {
            // Show error
            errorMsg.textContent = data.error || 'Login failed. Please try again.';
            errorMsg.classList.remove('hidden');
            
            // Reset button
            submitBtn.innerHTML = 'Sign in';
            submitBtn.disabled = false;
        }
    } catch (error) {
        // Show network error
        errorMsg.textContent = 'Network error. Please check your connection.';
        errorMsg.classList.remove('hidden');
        
        // Reset button
        submitBtn.innerHTML = 'Sign in';
        submitBtn.disabled = false;
    }
});
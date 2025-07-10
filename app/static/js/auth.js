document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
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
        window.location.href = '/';
    } else {
        document.getElementById('errorMessage').textContent = data.error;
    }
});
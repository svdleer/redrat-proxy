document.addEventListener('DOMContentLoaded', () => {
    const userForm = document.getElementById('userForm');
    
    userForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = {
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            is_admin: document.getElementById('is_admin').checked
        };
        
        try {
            const response = await fetch('/api/users', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                window.location.reload();
            }
        } catch (error) {
            console.error('Error creating user:', error);
        }
    });
});

async function deleteUser(userId) {
    if (confirm('Are you sure you want to delete this user?')) {
        try {
            const response = await fetch(`/api/users/${userId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (response.ok) {
                window.location.reload();
            }
        } catch (error) {
            console.error('Error deleting user:', error);
        }
    }
}
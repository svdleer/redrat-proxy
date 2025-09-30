// Common function to handle API calls with authentication
async function apiCall(url, options = {}) {
    try {
        // Ensure we have the right headers and credentials
        const defaultOptions = {
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                ...options.headers
            }
        };
        
        const response = await fetch(url, {...defaultOptions, ...options});
        
        if (response.status === 401) {
            // User is not authenticated, redirect to login
            window.location.href = '/login';
            return null;
        }
        
        // Return response for all status codes so caller can handle errors
        return response;
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Global variables
let users = [];
let filteredUsers = [];

// Global function definitions
async function loadUsers() {
    console.log('loadUsers() called');
    try {
        const response = await apiCall('/api/users');
        console.log('API response:', response);
        if (!response) return; // User was redirected to login
        
        if (response.ok) {
            const data = await response.json();
            console.log('Users data:', data);
            if (data.success) {
                users = data.users;
                filteredUsers = [...users];
                console.log('Calling renderUsers with', users.length, 'users');
                renderUsers();
            } else {
                console.error('API error:', data.error);
                showError('Failed to load users: ' + data.error);
            }
        } else {
            const data = await response.json();
            console.error('HTTP error:', response.status, data);
            showError('Failed to load users: ' + (data.error || response.statusText));
        }
    } catch (error) {
        console.error('Exception in loadUsers:', error);
        showError('Failed to load users: ' + error.message);
    }
}

function renderUsers() {
    console.log('renderUsers() called with', filteredUsers.length, 'users');
    const tbody = document.getElementById('users-table-body');
    console.log('tbody element:', tbody);
    if (!tbody) {
        console.error('users-table-body element not found!');
        return;
    }

    if (filteredUsers.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-4 text-center text-gray-500">No users found</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filteredUsers.map(user => `
        <tr class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${user.username}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${user.is_admin ? 'bg-purple-100 text-purple-800' : 'bg-green-100 text-green-800'}">
                    ${user.is_admin ? 'Admin' : 'User'}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${user.last_login || 'Never'}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                    Active
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button onclick="editUser(${user.id})" class="text-indigo-600 hover:text-indigo-900 mr-3">
                    <i class="fas fa-edit"></i>
                </button>
                <button onclick="resetPassword(${user.id})" class="text-yellow-600 hover:text-yellow-900 mr-3">
                    <i class="fas fa-key"></i>
                </button>
                ${user.username !== 'admin' ? `<button onclick="deleteUser(${user.id})" class="text-red-600 hover:text-red-900">
                    <i class="fas fa-trash"></i>
                </button>` : ''}
            </td>
        </tr>
    `).join('');
}

function filterUsers() {
    const searchInput = document.getElementById('search-users');
    const filterRole = document.getElementById('filter-role');
    
    const searchTerm = searchInput.value.toLowerCase();
    const roleFilter = filterRole.value;

    filteredUsers = users.filter(user => {
        const matchesSearch = user.username.toLowerCase().includes(searchTerm);
        const matchesRole = !roleFilter || 
            (roleFilter === 'admin' && user.is_admin) || 
            (roleFilter === 'user' && !user.is_admin);
        
        return matchesSearch && matchesRole;
    });

    renderUsers();
}

function showNewUserModal() {
    document.getElementById('modal-title').textContent = 'Add New User';
    document.getElementById('user-id').value = '';
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
    document.getElementById('is_admin').checked = false;
    document.getElementById('password').required = true;
    showModal();
}

function showModal() {
    const userModal = document.getElementById('user-modal');
    userModal.classList.remove('hidden');
}

function hideModal() {
    const userModal = document.getElementById('user-modal');
    userModal.classList.add('hidden');
}

async function handleSubmit(e) {
    e.preventDefault();
    
    const userId = document.getElementById('user-id').value;
    const isEdit = !!userId;
    
    const formData = {
        username: document.getElementById('username').value,
        is_admin: document.getElementById('is_admin').checked
    };

    if (!isEdit || document.getElementById('password').value) {
        formData.password = document.getElementById('password').value;
    }
    
    try {
        const url = isEdit ? `/api/users/${userId}` : '/api/users';
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await apiCall(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!response) return; // User was redirected to login
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                showSuccess(isEdit ? 'User updated successfully' : 'User created successfully');
                hideModal();
                loadUsers();
            } else {
                showError('Failed to save user: ' + data.error);
            }
        } else {
            // Handle error responses (like 409, 400, etc.)
            const data = await response.json();
            if (data.error) {
                showError('Failed to save user: ' + data.error);
            } else {
                showError(`Failed to save user: HTTP ${response.status}: ${response.statusText}`);
            }
        }
    } catch (error) {
        showError('Failed to save user: ' + error.message);
    }
}

async function editUser(userId) {
    const user = users.find(u => u.id === userId);
    if (!user) return;

    document.getElementById('modal-title').textContent = 'Edit User';
    document.getElementById('user-id').value = user.id;
    document.getElementById('username').value = user.username;
    document.getElementById('password').value = '';
    document.getElementById('is_admin').checked = user.is_admin;
    document.getElementById('password').required = false;
    
    showModal();
}

async function deleteUser(userId) {
    const user = users.find(u => u.id === userId);
    if (!user) return;

    if (confirm(`Are you sure you want to delete user "${user.username}"?`)) {
        try {
            const response = await apiCall(`/api/users/${userId}`, {
                method: 'DELETE'
            });
            
            if (!response) return; // User was redirected to login
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    showSuccess('User deleted successfully');
                    users = users.filter(u => u.id !== userId);
                    filteredUsers = filteredUsers.filter(u => u.id !== userId);
                    renderUsers();
                } else {
                    showError('Failed to delete user: ' + data.error);
                }
            } else {
                const data = await response.json();
                showError('Failed to delete user: ' + (data.error || response.statusText));
            }
        } catch (error) {
            showError('Failed to delete user: ' + error.message);
        }
    }
}

async function resetPassword(userId) {
    const user = users.find(u => u.id === userId);
    if (!user) return;

    if (confirm(`Reset password for user "${user.username}"?`)) {
        try {
            const response = await apiCall(`/api/users/${userId}/reset-password`, {
                method: 'POST'
            });
            
            if (!response) return; // User was redirected to login
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    showSuccess('Password reset successfully. New password: ' + data.new_password);
                } else {
                    showError('Failed to reset password: ' + data.error);
                }
            } else {
                const data = await response.json();
                showError('Failed to reset password: ' + (data.error || response.statusText));
            }
        } catch (error) {
            showError('Failed to reset password: ' + error.message);
        }
    }
}

function showError(message) {
    // Simple error display - you might want to use a more sophisticated notification system
    alert('Error: ' + message);
}

function showSuccess(message) {
    // Simple success display - you might want to use a more sophisticated notification system
    alert('Success: ' + message);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const userModal = document.getElementById('user-modal');
    const userForm = document.getElementById('user-form');
    const btnNewUser = document.getElementById('btn-new-user');
    const btnCancel = document.getElementById('btn-cancel');
    const searchInput = document.getElementById('search-users');
    const filterRole = document.getElementById('filter-role');

    // Event listeners
    if (btnNewUser) {
        btnNewUser.addEventListener('click', showNewUserModal);
    }
    if (btnCancel) {
        btnCancel.addEventListener('click', hideModal);
    }
    if (userForm) {
        userForm.addEventListener('submit', handleSubmit);
    }
    if (searchInput) {
        searchInput.addEventListener('input', filterUsers);
    }
    if (filterRole) {
        filterRole.addEventListener('change', filterUsers);
    }

    // Load initial data
    loadUsers();
});
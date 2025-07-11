document.addEventListener('DOMContentLoaded', () => {
    // Remote form handling
    const remoteForm = document.getElementById('remoteForm');
    const xmlForm = document.getElementById('xmlUploadForm');
    
    if (remoteForm) {
        remoteForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = {
                name: document.getElementById('remoteName').value,
                description: document.getElementById('remoteDesc').value,
                manufacturer: document.getElementById('remoteManufacturer')?.value || '',
                device_type: document.getElementById('remoteType')?.value || ''
            };
            
            try {
                const response = await fetch('/api/remotes', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify(formData)
                });
                
                if (response.ok) {
                    window.location.reload();
                } else {
                    alert('Error saving remote');
                }
            } catch (error) {
                console.error('Error saving remote:', error);
                alert('Error saving remote');
            }
        });
    }
    
    if (xmlForm) {
        xmlForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(xmlForm);
            
            try {
                // Show loading indicator
                const submitBtn = xmlForm.querySelector('button[type="submit"]');
                const originalContent = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Uploading...';
                submitBtn.disabled = true;
                
                const response = await fetch('/api/remotes/import-xml', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: formData
                });
                
                // Restore button
                submitBtn.innerHTML = originalContent;
                submitBtn.disabled = false;
                
                if (response.ok) {
                    const result = await response.json();
                    alert(`Import successful: ${result.imported} remotes imported.`);
                    window.location.reload();
                } else {
                    const error = await response.json();
                    alert(`Error uploading XML: ${error.message || 'Unknown error'}`);
                }
            } catch (error) {
                console.error('Error uploading XML:', error);
                alert('Error uploading XML file');
            }
        });
    }
});

// Function to open the remote modal for editing
function openRemoteModal(remote = null) {
    const modal = document.getElementById('remoteModal');
    const form = document.getElementById('remoteForm');
    const title = document.getElementById('modalTitle');
    
    // Reset form
    form.reset();
    
    if (remote) {
        // Edit mode
        title.textContent = 'Edit Remote';
        document.getElementById('remoteId').value = remote.id;
        document.getElementById('remoteName').value = remote.name;
        document.getElementById('remoteDesc').value = remote.description || '';
        
        if (document.getElementById('remoteManufacturer')) {
            document.getElementById('remoteManufacturer').value = remote.manufacturer || '';
        }
        
        if (document.getElementById('remoteType')) {
            document.getElementById('remoteType').value = remote.device_type || '';
        }
        
        if (document.getElementById('remoteModelNumber')) {
            document.getElementById('remoteModelNumber').value = remote.device_model_number || '';
        }
    } else {
        // Create mode
        title.textContent = 'Add New Remote';
        document.getElementById('remoteId').value = '';
    }
    
    // Show modal
    modal.classList.remove('hidden');
}

// Function to close the modal
function closeModal() {
    const modal = document.getElementById('remoteModal');
    modal.classList.add('hidden');
}

// Function to edit a remote
async function editRemote(id) {
    try {
        const response = await fetch(`/api/remotes/${id}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (response.ok) {
            const remote = await response.json();
            openRemoteModal(remote);
        } else {
            alert('Error loading remote data');
        }
    } catch (error) {
        console.error('Error loading remote:', error);
        alert('Error loading remote data');
    }
}

// Function to delete a remote
async function deleteRemote(id) {
    if (!confirm('Are you sure you want to delete this remote?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/remotes/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });
        
        if (response.ok) {
            window.location.reload();
        } else {
            alert('Error deleting remote');
        }
    } catch (error) {
        console.error('Error deleting remote:', error);
        alert('Error deleting remote');
    }
}

function openRemoteModal(remote = null) {
    const modal = document.getElementById('remoteModal');
    const title = document.getElementById('modalTitle');
    const form = document.getElementById('remoteForm');
    
    if (remote) {
        title.textContent = 'Edit Remote';
        document.getElementById('remoteId').value = remote.id;
        document.getElementById('remoteName').value = remote.name;
        document.getElementById('remoteDesc').value = remote.description || '';
    } else {
        title.textContent = 'Add New Remote';
        form.reset();
    }
    
    modal.classList.remove('hidden');
}

function closeModal() {
    document.getElementById('remoteModal').classList.add('hidden');
}
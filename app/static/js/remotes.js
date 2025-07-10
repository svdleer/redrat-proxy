document.addEventListener('DOMContentLoaded', () => {
    // Remote form handling
    const remoteForm = document.getElementById('remoteForm');
    const irdbForm = document.getElementById('irdbUploadForm');
    
    remoteForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = {
            name: document.getElementById('remoteName').value,
            description: document.getElementById('remoteDesc').value
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
            }
        } catch (error) {
            console.error('Error saving remote:', error);
        }
    });
    
    irdbForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(irdbForm);
        
        try {
            const response = await fetch('/api/irdb', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: formData
            });
            
            if (response.ok) {
                window.location.reload();
            }
        } catch (error) {
            console.error('Error uploading IRDB:', error);
        }
    });
});

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
document.addEventListener('DOMContentLoaded', () => {
    // Initialize real-time updates
    const eventSource = new EventSource('/api/events');
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'command_update') {
            updateCommandStatus(data.command);
        }
    };
    
    // Command form handling
    document.getElementById('commandForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = {
            remote_id: document.getElementById('remoteSelect').value,
            command: document.getElementById('commandSelect').value,
            device: document.getElementById('deviceInput').value
        };
        
        try {
            const response = await fetch('/api/commands', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(formData)
            });
            
            if (response.ok) {
                document.getElementById('commandForm').reset();
            }
        } catch (error) {
            console.error('Error sending command:', error);
        }
    });
});

function updateCommandStatus(command) {
    const row = document.getElementById(`command-${command.id}`);
    if (row) {
        row.querySelector('.status').textContent = command.status;
        row.querySelector('.status').className = `status px-2 py-1 rounded-full text-xs ${
            command.status === 'executed' ? 'bg-green-100 text-green-800' :
            command.status === 'failed' ? 'bg-red-100 text-red-800' :
            'bg-yellow-100 text-yellow-800'
        }`;
    }
}
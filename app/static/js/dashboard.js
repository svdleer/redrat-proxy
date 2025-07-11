document.addEventListener('DOMContentLoaded', () => {
    // Load remotes for the dropdown
    loadRemotes();
    
    // Load recent commands
    loadRecentCommands();
    
    // Command form handling
    document.getElementById('commandForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const remoteId = document.getElementById('remoteSelect').value;
        const command = document.getElementById('commandSelect').value;
        const device = document.getElementById('deviceInput').value;
        
        // Basic validation
        if (!remoteId || !command) {
            alert('Please select a remote and command');
            return;
        }
        
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        
        // Show loading state
        submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Sending...';
        submitBtn.disabled = true;
        
        try {
            const response = await fetch('/api/commands', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    remote_id: remoteId,
                    command: command,
                    device: device || 'Unknown Device'
                })
            });
            
            if (response.ok) {
                // Show success briefly
                submitBtn.innerHTML = '<i class="fas fa-check"></i> Sent!';
                submitBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                submitBtn.classList.add('bg-green-600', 'hover:bg-green-700');
                
                // Reset form and reload commands after a delay
                setTimeout(() => {
                    document.getElementById('commandForm').reset();
                    submitBtn.innerHTML = originalBtnText;
                    submitBtn.classList.remove('bg-green-600', 'hover:bg-green-700');
                    submitBtn.classList.add('bg-blue-600', 'hover:bg-blue-700');
                    submitBtn.disabled = false;
                    
                    // Reload the command list
                    loadRecentCommands();
                }, 1000);
            } else {
                const error = await response.json();
                alert(error.error || 'Failed to send command. Please try again.');
                
                // Reset button
                submitBtn.innerHTML = originalBtnText;
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error sending command:', error);
            alert('Network error. Please check your connection.');
            
            // Reset button
            submitBtn.innerHTML = originalBtnText;
            submitBtn.disabled = false;
        }
    });
    
    // Handle remote change to load commands
    document.getElementById('remoteSelect').addEventListener('change', (e) => {
        const remoteId = e.target.value;
        if (remoteId) {
            loadCommands(remoteId);
        } else {
            // Clear commands dropdown if no remote selected
            const commandSelect = document.getElementById('commandSelect');
            commandSelect.innerHTML = '<option value="">Select a command...</option>';
        }
    });
});

async function loadRemotes() {
    try {
        const response = await fetch('/api/remotes');
        if (response.ok) {
            const remotes = await response.json();
            const remoteSelect = document.getElementById('remoteSelect');
            
            remoteSelect.innerHTML = '<option value="">Select a remote...</option>';
            
            if (remotes.length === 0) {
                remoteSelect.innerHTML += '<option disabled>No remotes available</option>';
            } else {
                remotes.forEach(remote => {
                    remoteSelect.innerHTML += `<option value="${remote.id}">${remote.name}</option>`;
                });
            }
        }
    } catch (error) {
        console.error('Error loading remotes:', error);
    }
}

async function loadCommands(remoteId) {
    // In a real implementation, this would fetch commands for the selected remote
    // For now, we'll use some placeholder commands
    const commandSelect = document.getElementById('commandSelect');
    commandSelect.innerHTML = '<option value="">Loading commands...</option>';
    
    const placeholderCommands = [
        'Power', 'Volume Up', 'Volume Down', 'Mute', 
        'Channel Up', 'Channel Down', 'Menu', 'Exit',
        'Up', 'Down', 'Left', 'Right', 'OK',
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
    ];
    
    // Simulate network delay
    setTimeout(() => {
        commandSelect.innerHTML = '<option value="">Select a command...</option>';
        placeholderCommands.forEach(cmd => {
            commandSelect.innerHTML += `<option value="${cmd}">${cmd}</option>`;
        });
    }, 500);
}

async function loadRecentCommands() {
    try {
        const response = await fetch('/api/commands');
        if (response.ok) {
            const commands = await response.json();
            const recentCommandsTable = document.getElementById('recent-commands');
            
            if (recentCommandsTable) {
                recentCommandsTable.innerHTML = '';
                
                if (commands.length === 0) {
                    recentCommandsTable.innerHTML = `
                        <tr class="text-center py-4 text-gray-500">
                            <td colspan="4" class="px-4 py-3">No commands yet</td>
                        </tr>
                    `;
                } else {
                    commands.forEach(cmd => {
                        // Format timestamp
                        const timestamp = new Date(cmd.created_at);
                        const formattedTime = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                        
                        // Determine status class
                        let statusClass = 'bg-yellow-100 text-yellow-800';
                        if (cmd.status === 'executed') {
                            statusClass = 'bg-green-100 text-green-800';
                        } else if (cmd.status === 'failed') {
                            statusClass = 'bg-red-100 text-red-800';
                        }
                        
                        recentCommandsTable.innerHTML += `
                            <tr id="command-${cmd.id}">
                                <td class="px-4 py-2">
                                    <div class="flex items-center">
                                        <div class="ml-2">
                                            <div class="font-medium text-gray-900">${cmd.command}</div>
                                            <div class="text-xs text-gray-500">${cmd.device || 'Unknown Device'}</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-4 py-2 text-sm text-gray-900">${cmd.remote_name}</td>
                                <td class="px-4 py-2">
                                    <span class="status px-2 py-1 rounded-full text-xs ${statusClass}">${cmd.status}</span>
                                </td>
                                <td class="px-4 py-2 text-sm text-gray-500">${formattedTime}</td>
                            </tr>
                        `;
                    });
                }
            }
        }
    } catch (error) {
        console.error('Error loading recent commands:', error);
    }
}
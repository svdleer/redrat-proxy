// Common function to handle API calls with authentication
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, options);
        
        if (response.status === 401) {
            // User is not authenticated, redirect to login
            window.location.href = '/login';
            return null;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return response;
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard DOMContentLoaded event fired');
    
    // Initialize dashboard tiles with click handlers
    initializeDashboardTiles();
    
    // Load RedRat devices for the dropdown
    loadRedRatDevices();
    
    // Load remotes for the dropdown
    loadRemotes();
    
    // Load recent commands
    loadRecentCommands();
    
    // Setup event source for real-time updates
    setupEventSource();
    
    // Power level slider update
    const powerRange = document.getElementById('powerRange');
    const powerValue = document.getElementById('powerValue');
    if (powerRange && powerValue) {
        powerRange.addEventListener('input', (e) => {
            powerValue.textContent = `${e.target.value}%`;
        });
    }
    
    // Command form handling
    document.getElementById('commandForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const redratDeviceId = document.getElementById('redratSelect').value;
        const remoteId = document.getElementById('remoteSelect').value;
        const command = document.getElementById('commandSelect').value;
        const irPort = document.getElementById('irPortSelect').value;
        const power = document.getElementById('powerRange').value;
        
        // Basic validation
        if (!redratDeviceId || !remoteId || !command) {
            alert('Please select a RedRat device, remote, and command');
            return;
        }
        
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        
        // Show loading state
        submitBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Sending...';
        submitBtn.disabled = true;
        
        try {
            const response = await apiCall('/api/commands', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    remote_id: remoteId,
                    command: command,
                    redrat_device_id: redratDeviceId,
                    ir_port: parseInt(irPort),
                    power: parseInt(power)
                })
            });
            
            if (response && response.ok) {
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
            } else if (response) {
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
    
    // Handle RedRat device change to update IR port options
    document.getElementById('redratSelect').addEventListener('change', (e) => {
        const selectedOption = e.target.selectedOptions[0];
        const ports = selectedOption ? parseInt(selectedOption.getAttribute('data-ports')) || 1 : 1;
        const portDescriptions = selectedOption ? selectedOption.getAttribute('data-port-descriptions') : '';
        let descriptions = {};
        try {
            descriptions = portDescriptions ? JSON.parse(portDescriptions) : {};
        } catch (e) {
            descriptions = {};
        }
        updateIrPortOptions(ports, descriptions);
    });
});

function updateIrPortOptions(maxPorts, portDescriptions = {}) {
    const irPortSelect = document.getElementById('irPortSelect');
    irPortSelect.innerHTML = '';
    
    for (let i = 1; i <= maxPorts; i++) {
        const selected = i === 1 ? 'selected' : '';
        const description = portDescriptions[i.toString()] || '';
        const label = description ? `Port ${i} (${description})` : `Port ${i}`;
        irPortSelect.innerHTML += `<option value="${i}" ${selected}>${label}</option>`;
    }
}

async function loadRemotes() {
    try {
        const response = await apiCall('/api/remotes');
        if (response && response.ok) {
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
    const commandSelect = document.getElementById('commandSelect');
    commandSelect.innerHTML = '<option value="">Loading commands...</option>';
    
    try {
        const response = await apiCall(`/api/remotes/${remoteId}/commands`);
        if (response && response.ok) {
            const commands = await response.json();
            
            commandSelect.innerHTML = '<option value="">Select a command...</option>';
            
            if (commands.length === 0) {
                commandSelect.innerHTML += '<option disabled>No commands available</option>';
            } else {
                commands.forEach(cmd => {
                    commandSelect.innerHTML += `<option value="${cmd.name}">${cmd.name}</option>`;
                });
            }
        } else {
            console.error('Failed to load commands');
            commandSelect.innerHTML = '<option disabled>Failed to load commands</option>';
        }
    } catch (error) {
        console.error('Error loading commands:', error);
        commandSelect.innerHTML = '<option disabled>Error loading commands</option>';
    }
}

async function loadRecentCommands() {
    try {
        const response = await apiCall('/api/commands');
        if (response && response.ok) {
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

function setupEventSource() {
    try {
        const eventSource = new EventSource('/api/events');
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'command_update') {
                // Update the command in the UI
                updateCommandStatus(data.command);
                // Reload recent commands
                loadRecentCommands();
            } else if (data.type === 'heartbeat') {
                // Just a keep-alive, no action needed
                console.log('Heartbeat received');
            }
        };
        
        eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            // Try to reconnect after 5 seconds
            setTimeout(() => {
                setupEventSource();
            }, 5000);
        };
    } catch (error) {
        console.error('Error setting up EventSource:', error);
    }
}

function updateCommandStatus(command) {
    const commandRow = document.getElementById(`command-${command.id}`);
    if (!commandRow) return;
    
    const statusCell = commandRow.querySelector('.status');
    if (!statusCell) return;
    
    // Determine status class
    let statusClass = 'bg-yellow-100 text-yellow-800';
    if (command.status === 'executed') {
        statusClass = 'bg-green-100 text-green-800';
    } else if (command.status === 'failed') {
        statusClass = 'bg-red-100 text-red-800';
    }
    
    // Update the status text and class
    statusCell.textContent = command.status;
    statusCell.className = `status px-2 py-1 rounded-full text-xs ${statusClass}`;
}

// Navigation function for dashboard tiles
function navigateTo(url) {
    console.log(`Navigating to: ${url}`);
    window.location.href = url;
}

// Initialize dashboard tiles with click handlers
function initializeDashboardTiles() {
    console.log('Initializing dashboard tiles...');
    const tiles = document.querySelectorAll('[data-navigate]');
    console.log(`Found ${tiles.length} tiles with data-navigate attributes`);
    
    tiles.forEach((tile, index) => {
        const url = tile.getAttribute('data-navigate');
        console.log(`Setting up tile ${index + 1}: ${url}`);
        
        tile.addEventListener('click', function() {
            console.log(`Tile clicked: ${url}`);
            if (url) {
                navigateTo(url);
            }
        });
        
        // Add keyboard accessibility
        tile.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                console.log(`Tile activated via keyboard: ${url}`);
                if (url) {
                    navigateTo(url);
                }
            }
        });
        
        // Make tiles focusable for keyboard navigation
        tile.setAttribute('tabindex', '0');
    });
    
    console.log('Dashboard tiles initialization complete');
}

async function loadRedRatDevices() {
    const redratSelect = document.getElementById('redratSelect');
    redratSelect.innerHTML = '<option value="">Loading RedRat devices...</option>';
    
    try {
        const response = await apiCall('/api/redrat/devices');
        
        if (response) {
            const data = await response.json();
            console.log('RedRat devices API response:', data);
            const devices = data.devices || [];
            
            redratSelect.innerHTML = '<option value="">Select a RedRat device...</option>';
            
            if (devices.length === 0) {
                redratSelect.innerHTML += '<option disabled>No RedRat devices available</option>';
            } else {
                devices.forEach(device => {
                    console.log('Device status:', device.last_status, 'for device:', device.name || device.ip_address);
                    
                    // Determine status icon with fallback logic
                    let status = '🔴'; // Default to offline
                    if (device.last_status === 'online') {
                        status = '🟢';
                    } else if (device.last_status === 'error') {
                        status = '❌';
                    } else if (device.last_status === 'offline' || !device.last_status) {
                        status = '🔴';
                    }
                    
                    const ports = device.device_ports || 1;
                    const portDescriptions = device.port_descriptions ? JSON.stringify(device.port_descriptions) : '';
                    const deviceLabel = `${status} ${device.name || device.ip_address} (${device.ip_address}:${device.port}) - ${ports} ports`;
                    console.log('Creating option with label:', deviceLabel);
                    
                    redratSelect.innerHTML += `<option value="${device.id}" data-ports="${ports}" data-port-descriptions='${portDescriptions}'>${deviceLabel}</option>`;
                });
            }
        }
    } catch (error) {
        console.error('Error loading RedRat devices:', error);
        redratSelect.innerHTML = '<option disabled>Error loading devices</option>';
    }
}

// Clear activity log function
async function clearActivityLog() {
    if (!confirm('Are you sure you want to clear the activity log? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await apiCall('/api/activity', { method: 'DELETE' });
        if (response) {
            // Clear the activity feed display
            const activityFeed = document.getElementById('activity-feed');
            if (activityFeed) {
                activityFeed.innerHTML = '<div class="text-center py-4 text-gray-500"><p>Activity cleared</p></div>';
            }
            
            // Show success message
            showNotification('Activity log cleared successfully', 'success');
        }
    } catch (error) {
        console.error('Error clearing activity log:', error);
        showNotification('Failed to clear activity log', 'error');
    }
}

// Clear recent commands function
async function clearRecentCommands() {
    if (!confirm('Are you sure you want to clear recent commands? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await apiCall('/api/history', { method: 'DELETE' });
        if (response) {
            // Clear the recent commands display
            const recentCommands = document.getElementById('recent-commands');
            if (recentCommands) {
                recentCommands.innerHTML = '<tr class="text-center py-4 text-gray-500"><td colspan="4" class="px-4 py-3">No commands yet</td></tr>';
            }
            
            // Show success message
            showNotification('Recent commands cleared successfully', 'success');
        }
    } catch (error) {
        console.error('Error clearing recent commands:', error);
        showNotification('Failed to clear recent commands', 'error');
    }
}

// Simple notification function
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        'bg-blue-500 text-white'
    }`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove notification after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}
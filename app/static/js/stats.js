document.addEventListener('DOMContentLoaded', () => {
    // Load initial stats
    loadDashboardStats();
    
    // Load activity feed
    loadActivityFeed();
    
    // Setup real-time updates via SSE
    setupEventSource();
    
    // Refresh stats every 30 seconds
    setInterval(loadDashboardStats, 30000);
});

async function loadDashboardStats() {
    try {
        const response = await apiCall('/api/stats');
        if (response) {
            const stats = await response.json();
            
            // Update stat counters with animation
            updateStatWithAnimation('total-remotes', stats.remotes);
            updateStatWithAnimation('total-commands', stats.commands);
            updateStatWithAnimation('total-sequences', stats.sequences);
            updateStatWithAnimation('total-schedules', stats.schedules);
            
            // Update RedRat devices count if element exists (admin only)
            if (stats.redrat_devices !== undefined) {
                updateStatWithAnimation('total-redrat-devices', stats.redrat_devices);
            }
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
    
    // Load RedRat devices stats separately (admin only)
    await loadRedRatDeviceStatus();
}

async function loadRedRatDeviceStatus() {
    try {
        const response = await apiCall('/api/redrat/devices');
        if (response) {
            const data = await response.json();
            if (data.success && data.devices) {
                updateStatWithAnimation('total-redrat-devices', data.devices.length);
                
                // Update RedRat status icon based on device status
                updateRedRatStatusIcon(data.devices);
            }
        }
    } catch (error) {
        console.error('Error loading RedRat devices stats:', error);
        // This might fail for non-admin users, so we don't show an error
    }
}

async function loadActivityFeed() {
    try {
        const response = await apiCall('/api/activity');
        if (response) {
            const activities = await response.json();
            const activityFeed = document.getElementById('activity-feed');
            
            if (activityFeed) {
                activityFeed.innerHTML = '';
                
                if (activities.length === 0) {
                    activityFeed.innerHTML = `
                        <div class="text-center py-4 text-gray-500">
                            <p>No recent activity</p>
                        </div>
                    `;
                } else {
                    activities.forEach(activity => {
                        // Format timestamp
                        const timestamp = new Date(activity.created_at);
                        const formattedTime = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                        const formattedDate = timestamp.toLocaleDateString();
                        
                        // Determine status class
                        let statusClass = 'bg-yellow-100 text-yellow-800';
                        if (activity.status === 'executed') {
                            statusClass = 'bg-green-100 text-green-800';
                        } else if (activity.status === 'failed') {
                            statusClass = 'bg-red-100 text-red-800';
                        }
                        
                        activityFeed.innerHTML += `
                            <div class="flex items-start space-x-4 mb-4 pb-4 border-b border-gray-100">
                                <div class="flex-shrink-0 mt-1">
                                    <div class="bg-blue-100 p-2 rounded-full">
                                        <i class="fas fa-satellite-dish text-blue-600 text-sm"></i>
                                    </div>
                                </div>
                                <div class="flex-grow min-w-0">
                                    <div class="flex justify-between">
                                        <p class="text-sm font-medium text-gray-900 truncate">${activity.user_name}</p>
                                        <span class="text-xs text-gray-500">${formattedTime} · ${formattedDate}</span>
                                    </div>
                                    <p class="text-sm text-gray-600 mt-1">
                                        Sent <span class="font-semibold">${activity.command}</span> to
                                        <span class="font-semibold">${activity.device}</span> via
                                        <span class="font-semibold">${activity.remote_name}</span>
                                    </p>
                                    <div class="mt-2">
                                        <span class="px-2 py-1 rounded-full text-xs ${statusClass}">
                                            ${activity.status}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                }
            }
        }
    } catch (error) {
        console.error('Error loading activity feed:', error);
    }
}

function setupEventSource() {
    const eventSource = new EventSource('/api/events');
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'command_update') {
            // Update command status in the activity feed
            updateCommandInActivityFeed(data.command);
            
            // Refresh stats since something changed
            loadDashboardStats();
            
            // Also refresh RedRat device status icon (admin only)
            loadRedRatDeviceStatus();
        }
    };
    
    eventSource.onerror = (error) => {
        console.error('EventSource error:', error);
        // Try to reconnect after 5 seconds
        setTimeout(() => {
            setupEventSource();
        }, 5000);
    };
}

function updateCommandInActivityFeed(command) {
    loadActivityFeed(); // For simplicity, just reload the entire feed
}

function updateStatWithAnimation(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const oldValue = parseInt(element.textContent) || 0;
    if (oldValue === newValue) return;
    
    // Animate the counter
    let currentValue = oldValue;
    const step = newValue > oldValue ? 1 : -1;
    const duration = 1000; // 1 second
    const steps = Math.min(50, Math.abs(newValue - oldValue));
    const increment = Math.max(1, Math.abs(Math.floor((newValue - oldValue) / steps)));
    const interval = duration / steps;
    
    const counter = setInterval(() => {
        currentValue += (step * increment);
        
        // Make sure we don't overshoot
        if ((step > 0 && currentValue >= newValue) || 
            (step < 0 && currentValue <= newValue)) {
            currentValue = newValue;
            clearInterval(counter);
        }
        
        element.textContent = currentValue;
    }, interval);
}

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

function updateRedRatStatusIcon(devices) {
    const statusIcon = document.getElementById('redrat-status-icon');
    const statusIconI = statusIcon?.querySelector('i');
    
    if (!statusIcon || !statusIconI) {
        return; // Icon not found, user might not be admin
    }
    
    if (devices.length === 0) {
        // No devices - gray
        statusIcon.className = 'bg-gray-100 p-3 rounded-full';
        statusIconI.className = 'fas fa-microchip text-gray-600 text-xl';
        return;
    }
    
    // Count device statuses
    const statusCounts = {
        online: 0,
        offline: 0,
        error: 0
    };
    
    devices.forEach(device => {
        const status = device.last_status || 'offline';
        if (status in statusCounts) {
            statusCounts[status]++;
        } else {
            statusCounts.offline++;
        }
    });
    
    // Determine overall status and color
    let bgClass, textClass;
    
    if (statusCounts.online > 0 && statusCounts.offline === 0 && statusCounts.error === 0) {
        // All online - green
        bgClass = 'bg-green-100 p-3 rounded-full';
        textClass = 'fas fa-microchip text-green-600 text-xl';
    } else if (statusCounts.error > 0) {
        // Any errors - red
        bgClass = 'bg-red-100 p-3 rounded-full';
        textClass = 'fas fa-microchip text-red-600 text-xl';
    } else if (statusCounts.online > 0) {
        // Some online, some offline - yellow
        bgClass = 'bg-yellow-100 p-3 rounded-full';
        textClass = 'fas fa-microchip text-yellow-600 text-xl';
    } else {
        // All offline - red
        bgClass = 'bg-red-100 p-3 rounded-full';
        textClass = 'fas fa-microchip text-red-600 text-xl';
    }
    
    // Update the icon with smooth transition
    statusIcon.className = bgClass;
    statusIconI.className = textClass;
}

// Dashboard statistics and activity functions

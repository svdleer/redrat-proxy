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
        const response = await fetch('/api/stats');
        if (response.ok) {
            const stats = await response.json();
            
            // Update stat counters with animation
            updateStatWithAnimation('total-remotes', stats.remotes);
            updateStatWithAnimation('total-commands', stats.commands);
            updateStatWithAnimation('total-sequences', stats.sequences);
            updateStatWithAnimation('total-schedules', stats.schedules);
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

async function loadActivityFeed() {
    try {
        const response = await fetch('/api/activity');
        if (response.ok) {
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

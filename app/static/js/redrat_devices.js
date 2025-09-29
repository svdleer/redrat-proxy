// RedRat Devices Management JavaScript

let devices = [];
let currentDeviceId = null;

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    loadDevices();
    loadDeviceStatus();
    loadNetBoxTypes();
});

// Modal functions
function openAddDeviceModal() {
    console.log('External JS: openAddDeviceModal called');
    const modal = document.getElementById('addDeviceModal');
    if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex'; // Force display as flex for centering
        console.log('External JS: Modal opened successfully');
    } else {
        console.error('External JS: Modal element not found!');
    }
}

function closeAddDeviceModal() {
    console.log('External JS: closeAddDeviceModal called');
    const modal = document.getElementById('addDeviceModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none'; // Force hide
        document.getElementById('addDeviceForm').reset();
        // Clear port descriptions
        document.getElementById('portDescriptionsContainer').innerHTML = '';
        console.log('External JS: Modal closed successfully');
    }
}

function openEditDeviceModal() {
    console.log('openEditDeviceModal called');
    const modal = document.getElementById('editDeviceModal');
    if (modal) {
        console.log('Edit modal found, showing...');
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
    } else {
        console.error('Edit modal not found!');
    }
}

function closeEditDeviceModal() {
    const modal = document.getElementById('editDeviceModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
    // Clear port descriptions
    const container = document.getElementById('editPortDescriptionsContainer');
    if (container) {
        container.innerHTML = '';
    }
}

function openDeviceControlModal() {
    console.log('openDeviceControlModal called');
    const modal = document.getElementById('deviceControlModal');
    if (modal) {
        console.log('Control modal found, showing...');
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
    } else {
        console.error('Control modal not found!');
    }
}

function closeDeviceControlModal() {
    const modal = document.getElementById('deviceControlModal');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
    const controlResult = document.getElementById('controlResult');
    if (controlResult) {
        controlResult.innerHTML = '';
    }
}

function loadDevices() {
    fetch('/api/redrat/devices', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            devices = data.devices || [];
            console.log('Devices loaded:', devices);
            // Debug: Log first device to see what fields are available
            if (devices.length > 0) {
                console.log('First device:', devices[0]);
                console.log('netbox_type_name:', devices[0].netbox_type_name);
                console.log('netbox_type:', devices[0].netbox_type);
            }
            renderDevicesTable();
        } else {
            showAlert(`Error loading devices: ${data.error || 'Unknown error'}`, 'error');
        }
    })
    .catch(error => {
        console.error('Error loading devices:', error);
        showAlert(`Error loading devices: ${error.message}`, 'error');
    });
}

function loadDeviceStatus() {
    fetch('/api/redrat/devices/status', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            updateStatusCards(data.summary);
        }
    })
    .catch(error => {
        console.error('Error loading device status:', error);
        // Don't show alert for status loading failures to avoid spam
    });
}

// Load available NetBox types
function loadNetBoxTypes() {
    fetch('/api/netbox-types', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success && data.netbox_types) {
            window.netboxTypes = data.netbox_types;
            console.log('NetBox types loaded:', data.netbox_types);
        }
    })
    .catch(error => {
        console.error('Error loading NetBox types:', error);
        // Don't show alert for this as it's not critical
    });
}

// Utility function to get NetBox type name by value
function getNetBoxTypeName(value) {
    if (window.netboxTypes) {
        const type = window.netboxTypes.find(t => t.value === value);
        return type ? type.name : `Unknown Type (${value})`;
    }
    return 'Unknown Type';
}

function updateStatusCards(summary) {
    const totalDevices = document.getElementById('total-devices');
    const onlineDevices = document.getElementById('online-devices');
    const offlineDevices = document.getElementById('offline-devices');
    const errorDevices = document.getElementById('error-devices');
    
    if (totalDevices) totalDevices.textContent = summary.total_devices;
    if (onlineDevices) onlineDevices.textContent = summary.online;
    if (offlineDevices) offlineDevices.textContent = summary.offline;
    if (errorDevices) errorDevices.textContent = summary.error;
}

function renderDevicesTable() {
    const tbody = document.getElementById('devices-tbody');
    if (!tbody) {
        console.error('devices-tbody element not found');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (devices.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-12 text-center">
                    <div class="flex flex-col items-center">
                        <i class="fas fa-microchip text-gray-400 text-6xl mb-4"></i>
                        <h3 class="text-lg font-medium text-gray-900 mb-2">No devices found</h3>
                        <p class="text-gray-500">Click "Add New Device" to get started.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    devices.forEach(device => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 transition-colors duration-200';
        
        const statusIndicator = getStatusIndicator(device.last_status);
        // Use translated NetBox type name if available, otherwise fall back to device_model
        const modelInfo = device.netbox_type_name || device.device_model || 'Unknown Model';
        const portInfo = device.device_ports ? `${device.device_ports} ports` : 'Unknown ports';
        
        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <div class="flex-shrink-0 h-10 w-10">
                        <div class="h-10 w-10 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600 flex items-center justify-center">
                            <i class="fas fa-microchip text-white text-sm"></i>
                        </div>
                    </div>
                    <div class="ml-4">
                        <div class="text-sm font-medium text-gray-900">${escapeHtml(device.name)}</div>
                        <div class="text-sm text-gray-500">${escapeHtml(device.description || 'No description')}</div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <i class="fas fa-network-wired text-gray-400 mr-2"></i>
                    <div>
                        <div class="text-sm font-medium text-gray-900">${escapeHtml(device.ip_address)}</div>
                        <div class="text-sm text-gray-500">Port ${device.port}</div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    ${statusIndicator}
                    <span class="text-sm font-medium capitalize">${device.last_status}</span>
                </div>
                ${device.is_active ? '' : '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 mt-1">Inactive</span>'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <i class="fas fa-info-circle text-gray-400 mr-2"></i>
                    <div>
                        <div class="text-sm font-medium text-gray-900">${modelInfo}</div>
                        <div class="text-sm text-gray-500">${portInfo}</div>
                        ${device.port_descriptions && Object.keys(device.port_descriptions).length > 0 ? 
                            `<div class="text-xs text-indigo-600 mt-1 cursor-help" title="${formatPortDescriptions(device.port_descriptions)}">
                                <i class="fas fa-info-circle mr-1"></i>Port descriptions available
                            </div>` : ''}
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <div class="flex items-center">
                    <i class="fas fa-clock text-gray-400 mr-2"></i>
                    ${formatTimestamp(device.last_status_check)}
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <div class="flex space-x-2">
                    <button onclick="controlDevice('test', ${device.id})" class="action-button test" title="Test Connection">
                        <i class="fas fa-plug"></i>
                    </button>
                    <button onclick="showDeviceControl(${device.id})" class="action-button control" title="Control Device">
                        <i class="fas fa-cog"></i>
                    </button>
                    <button onclick="editDevice(${device.id})" class="action-button edit" title="Edit Device">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button onclick="deleteDevice(${device.id})" class="action-button delete" title="Delete Device">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function getStatusIndicator(status) {
    return `<span class="status-indicator ${status}"></span>`;
}

function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';
    return new Date(timestamp).toLocaleString();
}

function formatPortDescriptions(portDescriptions) {
    if (!portDescriptions || Object.keys(portDescriptions).length === 0) {
        return 'No port descriptions';
    }
    
    const descriptions = Object.entries(portDescriptions)
        .map(([port, desc]) => `Port ${port}: ${desc}`)
        .join('\n');
    
    return descriptions;
}

// Port descriptions management
function addPortDescription() {
    const container = document.getElementById('portDescriptionsContainer');
    const index = container.children.length;
    
    const portDescDiv = document.createElement('div');
    portDescDiv.className = 'flex items-center space-x-2 port-description-item';
    portDescDiv.innerHTML = `
        <div class="flex-shrink-0 w-20">
            <label class="text-sm font-medium text-gray-700">Port</label>
            <select class="form-input text-sm h-8 port-number-select" onchange="updatePortNumber(this)">
                ${generatePortOptions()}
            </select>
        </div>
        <div class="flex-grow">
            <label class="text-sm font-medium text-gray-700">Description</label>
            <input type="text" placeholder="e.g., Living Room TV" class="form-input text-sm h-8 port-description-input" maxlength="100">
        </div>
        <button type="button" onclick="removePortDescription(this)" class="btn-secondary text-sm px-2 py-1 h-8 mt-5">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(portDescDiv);
    updatePortSelectOptions();
}

function addEditPortDescription() {
    const container = document.getElementById('editPortDescriptionsContainer');
    const index = container.children.length;
    
    const portDescDiv = document.createElement('div');
    portDescDiv.className = 'flex items-center space-x-2 port-description-item';
    portDescDiv.innerHTML = `
        <div class="flex-shrink-0 w-20">
            <label class="text-sm font-medium text-gray-700">Port</label>
            <select class="form-input text-sm h-8 port-number-select" onchange="updatePortNumber(this)">
                ${generatePortOptions()}
            </select>
        </div>
        <div class="flex-grow">
            <label class="text-sm font-medium text-gray-700">Description</label>
            <input type="text" placeholder="e.g., Living Room TV" class="form-input text-sm h-8 port-description-input" maxlength="100">
        </div>
        <button type="button" onclick="removePortDescription(this)" class="btn-secondary text-sm px-2 py-1 h-8 mt-5">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(portDescDiv);
    updatePortSelectOptions();
}

function removePortDescription(button) {
    const portDescDiv = button.closest('.port-description-item');
    portDescDiv.remove();
    updatePortSelectOptions();
}

function generatePortOptions() {
    let options = '<option value="">Select Port</option>';
    for (let i = 1; i <= 16; i++) {
        options += `<option value="${i}">Port ${i}</option>`;
    }
    return options;
}

function updatePortNumber(select) {
    updatePortSelectOptions();
}

function updatePortSelectOptions() {
    // Get all port select elements in both add and edit forms
    const allSelects = document.querySelectorAll('.port-number-select');
    const usedPorts = new Set();
    
    // Collect all selected port numbers
    allSelects.forEach(select => {
        if (select.value) {
            usedPorts.add(parseInt(select.value));
        }
    });
    
    // Update each select to disable already used ports
    allSelects.forEach(select => {
        const currentValue = select.value;
        const options = select.querySelectorAll('option');
        
        options.forEach(option => {
            const portNum = parseInt(option.value);
            if (portNum && usedPorts.has(portNum) && option.value !== currentValue) {
                option.disabled = true;
                option.textContent = `Port ${portNum} (used)`;
            } else if (portNum) {
                option.disabled = false;
                option.textContent = `Port ${portNum}`;
            }
        });
    });
}

function getPortDescriptions(containerId) {
    const container = document.getElementById(containerId);
    const portDescriptions = {};
    
    container.querySelectorAll('.port-description-item').forEach(item => {
        const portSelect = item.querySelector('.port-number-select');
        const descInput = item.querySelector('.port-description-input');
        
        if (portSelect.value && descInput.value.trim()) {
            portDescriptions[portSelect.value] = descInput.value.trim();
        }
    });
    
    return portDescriptions;
}

function setPortDescriptions(containerId, portDescriptions) {
    const container = document.getElementById(containerId);
    container.innerHTML = ''; // Clear existing
    
    if (portDescriptions && Object.keys(portDescriptions).length > 0) {
        Object.entries(portDescriptions).forEach(([port, description]) => {
            // Add the port description UI
            if (containerId === 'portDescriptionsContainer') {
                addPortDescription();
            } else {
                addEditPortDescription();
            }
            
            // Set the values
            const lastItem = container.lastElementChild;
            const portSelect = lastItem.querySelector('.port-number-select');
            const descInput = lastItem.querySelector('.port-description-input');
            
            portSelect.value = port;
            descInput.value = description;
        });
    }
    
    updatePortSelectOptions();
}

function saveDevice() {
    console.log('saveDevice() called'); // Debug log
    
    const formData = {
        name: document.getElementById('deviceName').value.trim(),
        ip_address: document.getElementById('deviceIP').value.trim(),
        port: parseInt(document.getElementById('devicePort').value) || 10001,
        description: document.getElementById('deviceDescription').value.trim(),
        port_descriptions: getPortDescriptions('portDescriptionsContainer')
    };
    
    console.log('Form data:', formData); // Debug log
    
    // Validate input
    if (!formData.name || !formData.ip_address) {
        console.log('Validation failed: missing name or IP'); // Debug log
        showAlert('Name and IP address are required', 'error');
        return;
    }
    
    // Validate IP address format
    const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
    if (!ipRegex.test(formData.ip_address)) {
        console.log('Validation failed: invalid IP format'); // Debug log
        showAlert('Please enter a valid IP address', 'error');
        return;
    }
    
    console.log('Validation passed, sending request'); // Debug log
    
    // Disable button during request
    const saveButton = document.querySelector('button[onclick="saveDevice()"]');
    const originalText = saveButton.innerHTML;
    saveButton.innerHTML = '<div class="loading-spinner inline-block mr-2"></div>Saving...';
    saveButton.disabled = true;
    
    fetch('/api/redrat/devices', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(formData),
        credentials: 'same-origin'
    })
    .then(response => {
        console.log('Response received:', response.status, response.statusText); // Debug log
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Response data:', data); // Debug log
        if (data.success) {
            showAlert('Device added successfully!', 'success');
            closeAddDeviceModal();
            loadDevices();
            loadDeviceStatus();
        } else {
            showAlert(`Error: ${data.message || 'Failed to add device'}`, 'error');
        }
    })
    .catch(error => {
        console.error('Error adding device:', error);
        showAlert(`Error adding device: ${error.message}`, 'error');
    })
    .finally(() => {
        // Re-enable button
        saveButton.innerHTML = originalText;
        saveButton.disabled = false;
    });
}

function editDevice(deviceId) {
    console.log('editDevice called with deviceId:', deviceId);
    const device = devices.find(d => d.id === deviceId);
    if (!device) {
        console.error('Device not found:', deviceId);
        return;
    }
    console.log('Device found:', device);
    
    document.getElementById('editDeviceId').value = device.id;
    document.getElementById('editDeviceName').value = device.name;
    document.getElementById('editDeviceIP').value = device.ip_address;
    document.getElementById('editDevicePort').value = device.port;
    document.getElementById('editDeviceDescription').value = device.description || '';
    document.getElementById('editDeviceActive').checked = device.is_active;
    
    // Set port descriptions
    setPortDescriptions('editPortDescriptionsContainer', device.port_descriptions || {});
    
    openEditDeviceModal();
}

function updateDevice() {
    const deviceId = document.getElementById('editDeviceId').value;
    const formData = {
        name: document.getElementById('editDeviceName').value,
        ip_address: document.getElementById('editDeviceIP').value,
        port: parseInt(document.getElementById('editDevicePort').value),
        description: document.getElementById('editDeviceDescription').value,
        is_active: document.getElementById('editDeviceActive').checked,
        port_descriptions: getPortDescriptions('editPortDescriptionsContainer')
    };
    
    if (!formData.name || !formData.ip_address) {
        showAlert('Name and IP address are required', 'error');
        return;
    }
    
    fetch(`/api/redrat/devices/${deviceId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin',
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Device updated successfully', 'success');
            closeEditDeviceModal();
            loadDevices();
            loadDeviceStatus();
        } else {
            showAlert('Error updating device: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error updating device:', error);
        showAlert('Error updating device: ' + error.message, 'error');
    });
}

function deleteDevice(deviceId) {
    const device = devices.find(d => d.id === deviceId);
    if (!device) return;
    
    if (!confirm(`Are you sure you want to delete device "${device.name}"?`)) {
        return;
    }
    
    fetch(`/api/redrat/devices/${deviceId}`, {
        method: 'DELETE',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Device deleted successfully', 'success');
            loadDevices();
            loadDeviceStatus();
        } else {
            showAlert('Error deleting device: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting device:', error);
        showAlert('Error deleting device: ' + error.message, 'error');
    });
}

function showDeviceControl(deviceId) {
    console.log('showDeviceControl called with deviceId:', deviceId);
    const device = devices.find(d => d.id === deviceId);
    if (!device) {
        console.error('Device not found:', deviceId);
        return;
    }
    console.log('Device found:', device);
    
    currentDeviceId = deviceId;
    const netboxType = device.netbox_type_name || getNetBoxTypeName(device.netbox_type) || 'Unknown Type';
    
    const deviceControlInfo = document.getElementById('deviceControlInfo');
    const controlResult = document.getElementById('controlResult');
    
    if (deviceControlInfo) {
        deviceControlInfo.innerHTML = 
            `<div class="flex items-center">
                <i class="fas fa-microchip text-indigo-600 mr-2"></i>
                <div>
                    <div class="font-medium">${escapeHtml(device.name)} (${netboxType})</div>
                    <div class="text-sm text-gray-500">${escapeHtml(device.ip_address)}:${device.port}</div>
                </div>
            </div>`;
    }
    
    if (controlResult) {
        controlResult.innerHTML = '';
    }
    
    openDeviceControlModal();
}

function controlDevice(action, deviceId = null) {
    console.log('controlDevice called with action:', action, 'deviceId:', deviceId);
    const targetDeviceId = deviceId || currentDeviceId;
    if (!targetDeviceId) {
        console.error('No target device ID');
        return;
    }
    console.log('Target device ID:', targetDeviceId);
    
    const device = devices.find(d => d.id === targetDeviceId);
    if (!device) return;
    
    let url;
    let method = 'POST';
    
    switch(action) {
        case 'power-on':
            url = `/api/redrat/devices/${targetDeviceId}/power-on`;
            break;
        case 'power-off':
            url = `/api/redrat/devices/${targetDeviceId}/power-off`;
            break;
        case 'reset':
            url = `/api/redrat/devices/${targetDeviceId}/reset`;
            break;
        case 'test':
            url = `/api/redrat/devices/${targetDeviceId}/test`;
            break;
        default:
            return;
    }
    
    // Show loading state
    const resultDiv = document.getElementById('controlResult');
    if (resultDiv) {
        resultDiv.innerHTML = `
            <div class="flex items-center justify-center p-6 bg-gray-50 rounded-lg">
                <div class="loading-spinner mr-3"></div>
                <span class="text-gray-600">Processing ${action.replace('-', ' ')}...</span>
            </div>
        `;
    }
    
    fetch(url, { 
        method,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
        .then(response => response.json())
        .then(data => {
            const alertClass = data.success ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800';
            const iconClass = data.success ? 'fas fa-check-circle text-green-500' : 'fas fa-exclamation-circle text-red-500';
            
            let resultHtml = `
                <div class="p-4 rounded-lg border-2 ${alertClass}">
                    <div class="flex items-center">
                        <i class="${iconClass} mr-3 text-lg"></i>
                        <div class="flex-1">
                            <h4 class="font-semibold">${data.success ? 'Success' : 'Error'}</h4>
                            <p class="text-sm mt-1">${data.message}</p>
                        </div>
                    </div>
                </div>
            `;
            
            // If test was successful, show device info
            if (data.success && action === 'test' && data.device_info) {
                const info = data.device_info;
                resultHtml += `
                    <div class="mt-4 p-4 bg-blue-50 border-2 border-blue-200 rounded-lg">
                        <h4 class="font-semibold text-blue-800 mb-2">Device Information</h4>
                        <div class="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <span class="font-medium text-blue-700">Model:</span>
                                <span class="text-blue-600">${info.model || 'Unknown'}</span>
                            </div>
                            <div>
                                <span class="font-medium text-blue-700">Ports:</span>
                                <span class="text-blue-600">${info.ports || 'Unknown'}</span>
                            </div>
                            <div>
                                <span class="font-medium text-blue-700">Response Time:</span>
                                <span class="text-blue-600">${(info.response_time || 0).toFixed(2)}s</span>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            if (resultDiv) {
                resultDiv.innerHTML = resultHtml;
            } else {
                showAlert(data.message, data.success ? 'success' : 'error');
            }
            
            // Refresh device list and status
            loadDevices();
            loadDeviceStatus();
        })
        .catch(error => {
            console.error('Error controlling device:', error);
            const errorHtml = `
                <div class="p-4 rounded-lg border-2 bg-red-50 border-red-200">
                    <div class="flex items-center">
                        <i class="fas fa-exclamation-circle text-red-500 mr-3 text-lg"></i>
                        <div class="flex-1">
                            <h4 class="font-semibold text-red-800">Error</h4>
                            <p class="text-sm mt-1 text-red-700">${error.message}</p>
                        </div>
                    </div>
                </div>
            `;
            
            if (resultDiv) {
                resultDiv.innerHTML = errorHtml;
            } else {
                showAlert('Error: ' + error.message, 'error');
            }
        });
}

function showAlert(message, type = 'info') {
    const alertColors = {
        'success': 'bg-green-50 border-green-200 text-green-800',
        'error': 'bg-red-50 border-red-200 text-red-800',
        'info': 'bg-blue-50 border-blue-200 text-blue-800'
    };
    
    const alertIcons = {
        'success': 'fas fa-check-circle text-green-500',
        'error': 'fas fa-exclamation-circle text-red-500',
        'info': 'fas fa-info-circle text-blue-500'
    };
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert border-2 ${alertColors[type] || alertColors['info']} relative`;
    alertDiv.innerHTML = `
        <div class="flex items-center">
            <i class="${alertIcons[type] || alertIcons['info']} mr-3 text-lg"></i>
            <div class="flex-1">
                <p class="font-medium">${message}</p>
            </div>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-gray-400 hover:text-gray-600 transition-colors">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    const container = document.querySelector('.container');
    const firstChild = container.firstChild;
    container.insertBefore(alertDiv, firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.style.opacity = '0';
            alertDiv.style.transform = 'translateX(-100%)';
            setTimeout(() => alertDiv.remove(), 300);
        }
    }, 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-refresh status every 30 seconds
setInterval(loadDeviceStatus, 30000);

// Close modals when clicking outside
document.addEventListener('click', function(event) {
    const modals = ['addDeviceModal', 'editDeviceModal', 'deviceControlModal'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (event.target === modal || event.target.classList.contains('modal-backdrop')) {
            modal.classList.add('hidden');
        }
    });
});

// Handle escape key to close modals
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modals = ['addDeviceModal', 'editDeviceModal', 'deviceControlModal'];
        modals.forEach(modalId => {
            const modal = document.getElementById(modalId);
            if (!modal.classList.contains('hidden')) {
                modal.classList.add('hidden');
            }
        });
    }
});

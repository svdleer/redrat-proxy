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

// Sequences management script
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const sequenceList = document.getElementById('sequence-list');
    const sequenceEditor = document.getElementById('sequence-editor');
    const sequencePlaceholder = document.getElementById('sequence-placeholder');
    const formSequence = document.getElementById('form-sequence');
    const btnNewSequence = document.getElementById('btn-new-sequence');
    const selectCommand = document.getElementById('select-command');
    const btnAddCommand = document.getElementById('btn-add-command');
    const sequenceCommands = document.getElementById('sequence-commands');
    const btnExecuteSequence = document.getElementById('btn-execute-sequence');
    const btnScheduleSequence = document.getElementById('btn-schedule-sequence');
    
    // Schedule modal
    const scheduleModal = document.getElementById('schedule-modal');
    const formSchedule = document.getElementById('form-schedule');
    const scheduleType = document.getElementById('schedule-type');
    const onceOptions = document.getElementById('once-options');
    const dailyOptions = document.getElementById('daily-options');
    const weeklyOptions = document.getElementById('weekly-options');
    const monthlyOptions = document.getElementById('monthly-options');
    const btnCancelSchedule = document.getElementById('btn-cancel-schedule');
    
    // State
    let sequences = [];
    let commands = [];
    let currentSequence = null;
    
    // Initialize
    loadSequences();
    loadCommands();
    
    // Event listeners
    btnNewSequence.addEventListener('click', newSequence);
    formSequence.addEventListener('submit', saveSequence);
    btnAddCommand.addEventListener('click', addCommandToSequence);
    btnExecuteSequence.addEventListener('click', executeSequence);
    btnScheduleSequence.addEventListener('click', showScheduleModal);
    btnCancelSchedule.addEventListener('click', hideScheduleModal);
    formSchedule.addEventListener('submit', scheduleSequence);
    scheduleType.addEventListener('change', updateScheduleForm);
    
    // Sequence power level slider update
    const seqPowerRange = document.getElementById('seq-power');
    const seqPowerValue = document.getElementById('seq-power-value');
    if (seqPowerRange && seqPowerValue) {
        seqPowerRange.addEventListener('input', (e) => {
            seqPowerValue.textContent = `${e.target.value}%`;
        });
    }
    
    // Functions
    async function loadSequences() {
        try {
            const response = await apiCall('/api/sequences');
            
            if (!response) return; // User was redirected to login
            
            const data = await response.json();
            
            if (data.success) {
                sequences = data.sequences;
                renderSequences();
            } else {
                showError('Failed to load sequences: ' + data.message);
            }
        } catch (error) {
            showError('Failed to load sequences: ' + error.message);
        }
    }
    
    function renderSequences() {
        sequenceList.innerHTML = '';
        
        if (sequences.length === 0) {
            sequenceList.innerHTML = '<div class="text-gray-500 italic">No sequences found</div>';
            return;
        }
        
        sequences.forEach(sequence => {
            const item = document.createElement('div');
            item.classList.add('bg-gray-100', 'p-3', 'rounded', 'hover:bg-gray-200', 'cursor-pointer', 'flex', 'justify-between', 'items-center');
            
            const info = document.createElement('div');
            info.innerHTML = `<div class="font-medium">${sequence.name}</div>
                <div class="text-sm text-gray-600">${sequence.command_count || 0} command(s)</div>`;
            
            const actions = document.createElement('div');
            const editBtn = document.createElement('button');
            editBtn.classList.add('text-blue-500', 'hover:text-blue-700', 'mr-2');
            editBtn.innerHTML = '<i class="fas fa-edit"></i>';
            editBtn.addEventListener('click', () => editSequence(sequence.id));
            
            const deleteBtn = document.createElement('button');
            deleteBtn.classList.add('text-red-500', 'hover:text-red-700');
            deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (confirm('Are you sure you want to delete this sequence?')) {
                    deleteSequence(sequence.id);
                }
            });
            
            actions.appendChild(editBtn);
            actions.appendChild(deleteBtn);
            
            item.appendChild(info);
            item.appendChild(actions);
            
            item.addEventListener('click', () => editSequence(sequence.id));
            
            sequenceList.appendChild(item);
        });
    }
    
    async function loadCommands() {
        try {
            const response = await apiCall('/api/command-templates');
            
            if (!response) return; // User was redirected to login
            
            const commands_data = await response.json();
            
            if (Array.isArray(commands_data)) {
                commands = commands_data;
                renderCommandSelect();
            } else {
                showError('Failed to load commands: Invalid response format');
            }
        } catch (error) {
            showError('Failed to load commands: ' + error.message);
        }
    }
    
    function renderCommandSelect() {
        selectCommand.innerHTML = '<option value="">Select a command</option>';
        
        commands.forEach(command => {
            const option = document.createElement('option');
            option.value = command.id;
            option.textContent = `${command.command_name} (${command.remote_name})`;
            selectCommand.appendChild(option);
        });
    }
    
    function newSequence() {
        currentSequence = null;
        formSequence.reset();
        sequenceCommands.innerHTML = '<div class="text-gray-500 italic">No commands in this sequence</div>';
        showEditor();
    }
    
    async function editSequence(id) {
        try {
            const response = await apiCall(`/api/sequences/${id}`);
            
            if (!response) return; // User was redirected to login
            
            const data = await response.json();
            
            if (data.success) {
                currentSequence = data.sequence;
                formSequence.name.value = currentSequence.name;
                formSequence.description.value = currentSequence.description || '';
                
                renderSequenceCommands();
                showEditor();
            } else {
                showError('Failed to load sequence: ' + data.message);
            }
        } catch (error) {
            showError('Failed to load sequence: ' + error.message);
        }
    }
    
    function renderSequenceCommands() {
        sequenceCommands.innerHTML = '';
        
        if (!currentSequence || currentSequence.commands.length === 0) {
            sequenceCommands.innerHTML = '<div class="text-gray-500 italic">No commands in this sequence</div>';
            return;
        }
        
        currentSequence.commands.forEach(cmd => {
            const cmdElement = document.createElement('div');
            cmdElement.classList.add('bg-gray-100', 'p-3', 'rounded', 'flex', 'justify-between', 'items-center');
            
            const cmdInfo = document.createElement('div');
            const commandName = cmd.command || 'Unknown';
            const remoteName = cmd.remote_name || 'Unknown Remote';
            cmdInfo.innerHTML = `
                <div class="font-medium">${commandName} (${remoteName})</div>
                <div class="text-sm text-gray-600">Delay: ${cmd.delay_ms}ms</div>
            `;
            
            const cmdActions = document.createElement('div');
            const upBtn = document.createElement('button');
            upBtn.classList.add('text-gray-700', 'hover:text-black', 'mr-2');
            upBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
            upBtn.addEventListener('click', () => moveCommandUp(cmd.id));
            
            const downBtn = document.createElement('button');
            downBtn.classList.add('text-gray-700', 'hover:text-black', 'mr-2');
            downBtn.innerHTML = '<i class="fas fa-arrow-down"></i>';
            downBtn.addEventListener('click', () => moveCommandDown(cmd.id));
            
            const removeBtn = document.createElement('button');
            removeBtn.classList.add('text-red-500', 'hover:text-red-700');
            removeBtn.innerHTML = '<i class="fas fa-times"></i>';
            removeBtn.addEventListener('click', () => removeCommandFromSequence(cmd.id));
            
            if (cmd.position === 1) {
                upBtn.disabled = true;
                upBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
            
            if (cmd.position === currentSequence.commands.length) {
                downBtn.disabled = true;
                downBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
            
            cmdActions.appendChild(upBtn);
            cmdActions.appendChild(downBtn);
            cmdActions.appendChild(removeBtn);
            
            cmdElement.appendChild(cmdInfo);
            cmdElement.appendChild(cmdActions);
            
            sequenceCommands.appendChild(cmdElement);
        });
    }
    
    async function saveSequence(e) {
        e.preventDefault();
        
        const name = formSequence.name.value.trim();
        const description = formSequence.description.value.trim();
        
        if (!name) {
            showError('Sequence name is required');
            return;
        }
        
        try {
            let response;
            let method = 'POST';
            let url = '/api/sequences';
            
            const data = {
                name,
                description
            };
            
            if (currentSequence) {
                url += `/${currentSequence.id}`;
                method = 'PUT';
            }
            
            response = await apiCall(url, {
                method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (!response) return; // User was redirected to login
            
            const result = await response.json();
            
            if (result.success) {
                showSuccess('Sequence saved successfully');
                if (!currentSequence) {
                    currentSequence = result.sequence;
                }
                await loadSequences();
            } else {
                showError('Failed to save sequence: ' + result.message);
            }
        } catch (error) {
            showError('Failed to save sequence: ' + error.message);
        }
    }
    
    async function addCommandToSequence() {
        if (!currentSequence) {
            showError('Please save the sequence first');
            return;
        }
        
        const commandId = selectCommand.value;
        if (!commandId) {
            showError('Please select a command');
            return;
        }
        
        const irPort = document.getElementById('seq-ir-port').value;
        const power = document.getElementById('seq-power').value;
        const delayMs = document.getElementById('delay-ms').value || 0;
        
        try {
            const response = await apiCall(`/api/sequences/${currentSequence.id}/commands`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    command_id: commandId,
                    delay_ms: parseInt(delayMs),
                    ir_port: parseInt(irPort),
                    power: parseInt(power)
                })
            });
            
            if (!response) return; // User was redirected to login
            
            const data = await response.json();
            
            if (data.success) {
                showSuccess('Command added to sequence');
                // Reset the form
                selectCommand.value = '';
                document.getElementById('seq-ir-port').value = '1';
                document.getElementById('seq-power').value = '100';
                document.getElementById('seq-power-value').textContent = '100%';
                document.getElementById('delay-ms').value = '0';
                await editSequence(currentSequence.id);
            } else {
                showError('Failed to add command: ' + data.message);
            }
        } catch (error) {
            showError('Failed to add command: ' + error.message);
        }
    }
    
    async function removeCommandFromSequence(cmdId) {
        try {
            const response = await apiCall(`/api/sequences/${currentSequence.id}/commands/${cmdId}`, {
                method: 'DELETE'
            });
            
            if (!response) return; // User was redirected to login
            
            const data = await response.json();
            
            if (data.success) {
                showSuccess('Command removed from sequence');
                await editSequence(currentSequence.id);
            } else {
                showError('Failed to remove command: ' + data.message);
            }
        } catch (error) {
            showError('Failed to remove command: ' + error.message);
        }
    }
    
    async function moveCommandUp(cmdId) {
        // This would require a backend API for reordering
        console.log('Move command up:', cmdId);
    }
    
    async function moveCommandDown(cmdId) {
        // This would require a backend API for reordering
        console.log('Move command down:', cmdId);
    }
    
    async function executeSequence() {
        if (!currentSequence) {
            showError('No sequence selected');
            return;
        }
        
        try {
            const response = await apiCall(`/api/sequences/${currentSequence.id}/execute`, {
                method: 'POST'
            });
            
            if (!response) return; // User was redirected to login
            
            const data = await response.json();
            
            if (data.success) {
                showSuccess('Sequence execution started');
            } else {
                showError('Failed to execute sequence: ' + data.message);
            }
        } catch (error) {
            showError('Failed to execute sequence: ' + error.message);
        }
    }
    
    function showScheduleModal() {
        if (!currentSequence) {
            showError('No sequence selected');
            return;
        }
        
        scheduleModal.classList.remove('hidden');
        updateScheduleForm();
    }
    
    function hideScheduleModal() {
        scheduleModal.classList.add('hidden');
        formSchedule.reset();
    }
    
    function updateScheduleForm() {
        const type = scheduleType.value;
        
        // Hide all options
        onceOptions.classList.add('hidden');
        dailyOptions.classList.add('hidden');
        weeklyOptions.classList.add('hidden');
        monthlyOptions.classList.add('hidden');
        
        // Show relevant options
        if (type === 'once') {
            onceOptions.classList.remove('hidden');
        } else if (type === 'daily') {
            dailyOptions.classList.remove('hidden');
        } else if (type === 'weekly') {
            weeklyOptions.classList.remove('hidden');
        } else if (type === 'monthly') {
            monthlyOptions.classList.remove('hidden');
        }
    }
    
    async function scheduleSequence(e) {
        e.preventDefault();
        
        if (!currentSequence) {
            showError('No sequence selected');
            return;
        }
        
        const type = scheduleType.value;
        const scheduleData = {};
        
        if (type === 'once') {
            scheduleData.datetime = document.getElementById('schedule-datetime').value;
        } else if (type === 'daily') {
            scheduleData.time = document.getElementById('schedule-time-daily').value;
        } else if (type === 'weekly') {
            scheduleData.day = parseInt(document.getElementById('schedule-day').value);
            scheduleData.time = document.getElementById('schedule-time-weekly').value;
        } else if (type === 'monthly') {
            scheduleData.day = parseInt(document.getElementById('schedule-day-month').value);
            scheduleData.time = document.getElementById('schedule-time-monthly').value;
        }
        
        try {
            const response = await apiCall('/api/schedules', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: 'sequence',
                    target_id: currentSequence.id,
                    schedule_type: type,
                    schedule_data: scheduleData
                })
            });
            
            if (!response) return; // User was redirected to login
            
            const data = await response.json();
            
            if (data.success) {
                showSuccess('Sequence scheduled successfully');
                hideScheduleModal();
            } else {
                showError('Failed to schedule sequence: ' + data.message);
            }
        } catch (error) {
            showError('Failed to schedule sequence: ' + error.message);
        }
    }
    
    async function deleteSequence(id) {
        try {
            const response = await apiCall(`/api/sequences/${id}`, {
                method: 'DELETE'
            });
            
            if (!response) return; // User was redirected to login
            
            const data = await response.json();
            
            if (data.success) {
                showSuccess('Sequence deleted successfully');
                loadSequences(); // Reload the sequences list
                
                // If we're currently editing this sequence, clear the editor
                if (currentSequence && currentSequence.id === id) {
                    currentSequence = null;
                    sequenceEditor.classList.add('hidden');
                    sequencePlaceholder.classList.remove('hidden');
                }
            } else {
                showError('Failed to delete sequence: ' + data.message);
            }
        } catch (error) {
            showError('Failed to delete sequence: ' + error.message);
        }
    }

    function showEditor() {
        sequenceEditor.classList.remove('hidden');
        sequencePlaceholder.classList.add('hidden');
    }
    
    function showSuccess(message) {
        alert(message);
    }
    
    function showError(message) {
        alert('Error: ' + message);
    }
});

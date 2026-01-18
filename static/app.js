/**
 * EditFlow - Video Processing Workflow
 * A professional tool for processing videos with branding overlays
 */

// ============== State ==============
const state = {
    files: [],
    profiles: [],
    outputs: [],
    currentJob: null,
    editingProfile: null,
    renderPresets: [],
    selectedPresetId: null
};

// ============== API ==============
const API = {
    async get(endpoint) {
        const res = await fetch(`/api${endpoint}`);
        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.error || 'Request failed');
        }
        return res.json();
    },
    
    async post(endpoint, data) {
        const res = await fetch(`/api${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const respData = await res.json();
            throw new Error(respData.error || 'Request failed');
        }
        return res.json();
    },
    
    async put(endpoint, data) {
        const res = await fetch(`/api${endpoint}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const respData = await res.json();
            throw new Error(respData.error || 'Request failed');
        }
        return res.json();
    },
    
    async delete(endpoint) {
        const res = await fetch(`/api${endpoint}`, { method: 'DELETE' });
        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.error || 'Request failed');
        }
        return res.json();
    },
    
    async upload(endpoint, formData) {
        const res = await fetch(`/api${endpoint}`, {
            method: 'POST',
            body: formData
        });
        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.error || 'Upload failed');
        }
        return res.json();
    }
};

// ============== Toast ==============
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>',
        error: '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>',
        warning: '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>',
        info: '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>'
    };
    
    toast.innerHTML = `
        <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${icons[type] || icons.info}</svg>
        <span class="toast-message">${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 200);
    }, 4000);
}

// ============== Navigation ==============
function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const viewName = item.dataset.view;
            
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById(`view-${viewName}`).classList.add('active');
            
            if (viewName === 'branding') loadBranding();
            if (viewName === 'outputs') loadOutputs();
        });
    });
}

// ============== File Handling ==============
function initFileHandling() {
    const dropZone = document.getElementById('file-drop-zone');
    
    // Click on drop zone to open native file browser
    dropZone.addEventListener('click', openFileBrowser);
    
    // Drag & drop handling
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    
    dropZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        // Try to get file paths from drag data
        const paths = [];
        
        // Check for file:// URLs in text data
        const textData = e.dataTransfer.getData('text/plain');
        if (textData) {
            const lines = textData.split(/[\r\n]+/).filter(l => l.trim());
            for (const line of lines) {
                let path = line.trim();
                if (path.startsWith('file:///')) {
                    path = decodeURIComponent(path.replace('file:///', ''));
                    if (path.match(/^[a-zA-Z]:/)) {
                        path = path.replace(/\//g, '\\');
                    }
                }
                if (path.match(/\.(mp4|mkv|avi|mov|webm|wmv|flv|m4v|ts|mts)$/i)) {
                    paths.push(path);
                }
            }
        }
        
        if (paths.length > 0) {
            await addPaths(paths);
        } else {
            // If drag didn't work, just open the file browser
            showToast('Drag not detected - opening file browser...', 'info');
            openFileBrowser();
        }
    });
}

async function openFileBrowser() {
    const dropZone = document.getElementById('file-drop-zone');
    const dropText = dropZone.querySelector('.drop-text');
    const originalText = dropText.textContent;
    
    dropZone.style.pointerEvents = 'none';
    dropText.textContent = 'Opening file browser...';
    
    try {
        const result = await API.post('/browse/videos', {});
        
        if (result.cancelled) {
            // User cancelled - no toast needed
            return;
        }
        
        if (result.paths && result.paths.length > 0) {
            await addPaths(result.paths);
        }
    } catch (err) {
        showToast(`Error opening file browser: ${err.message}`, 'error');
    } finally {
        dropZone.style.pointerEvents = 'auto';
        dropText.textContent = originalText;
    }
}

async function addPaths(paths) {
    const fileList = document.getElementById('file-list');
    
    for (const path of paths) {
        // Check for duplicates
        if (state.files.some(f => f.path.toLowerCase() === path.toLowerCase())) {
            showToast(`Already added: ${path.split(/[\\/]/).pop()}`, 'warning');
            continue;
        }
        
        // Add skeleton while loading
        const skeleton = document.createElement('div');
        skeleton.className = 'file-item skeleton-item';
        skeleton.innerHTML = `
            <div class="skeleton-bar" style="width: 60%"></div>
            <div class="skeleton-bar" style="width: 40%"></div>
        `;
        fileList.appendChild(skeleton);
        
        try {
            const info = await API.post('/video/info', { path: path });
            const name = path.split(/[\\/]/).pop();
            state.files.push({ 
                path: path, 
                name: name, 
                trim_start: 0, 
                trim_end: 0,
                ...info 
            });
            skeleton.remove();
        } catch (err) {
            skeleton.remove();
            showToast(`Failed to load: ${path.split(/[\\/]/).pop()} - ${err.message}`, 'error');
        }
    }
    
    renderFileList();
    updateTrimSettings();
    updateProcessButton();
}

function renderFileList() {
    const fileList = document.getElementById('file-list');
    const fileSummary = document.getElementById('file-summary');
    
    fileList.innerHTML = state.files.map((file, index) => {
        const ext = file.path.split('.').pop().toUpperCase();
        return `
            <div class="file-item" draggable="true" data-index="${index}">
                <div class="file-drag-handle">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <circle cx="9" cy="6" r="1.5"></circle>
                        <circle cx="15" cy="6" r="1.5"></circle>
                        <circle cx="9" cy="12" r="1.5"></circle>
                        <circle cx="15" cy="12" r="1.5"></circle>
                        <circle cx="9" cy="18" r="1.5"></circle>
                        <circle cx="15" cy="18" r="1.5"></circle>
                    </svg>
                </div>
                <div class="file-info">
                    <div class="file-name" title="${file.path}">${file.name || file.path.split(/[\\/]/).pop()}</div>
                    <div class="file-meta">
                        <span>${file.duration_formatted || formatDuration(file.duration)}</span>
                        <span>${file.width}×${file.height}</span>
                        <span>${file.fps}fps</span>
                        <span class="auto-badge">${ext}</span>
                    </div>
                </div>
                <button class="file-remove" onclick="removeFile(${index})" title="Remove">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;
    }).join('');
    
    if (state.files.length > 0) {
        const totalDuration = state.files.reduce((sum, f) => sum + (f.duration || 0), 0);
        fileSummary.innerHTML = `<strong>${state.files.length}</strong> file${state.files.length > 1 ? 's' : ''} • Total: <strong>${formatDuration(totalDuration)}</strong>`;
        fileSummary.classList.add('visible');
    } else {
        fileSummary.classList.remove('visible');
    }
    
    initFileDragSort();
}

function removeFile(index) {
    state.files.splice(index, 1);
    renderFileList();
    updateTrimSettings();
    updateProcessButton();
}

function initFileDragSort() {
    document.querySelectorAll('.file-item').forEach(item => {
        item.addEventListener('dragstart', (e) => {
            item.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });
        
        item.addEventListener('dragend', () => item.classList.remove('dragging'));
        
        item.addEventListener('dragover', (e) => {
            e.preventDefault();
            const dragging = document.querySelector('.file-item.dragging');
            if (dragging && dragging !== item) {
                const rect = item.getBoundingClientRect();
                const midY = rect.top + rect.height / 2;
                if (e.clientY < midY) {
                    item.parentNode.insertBefore(dragging, item);
                } else {
                    item.parentNode.insertBefore(dragging, item.nextSibling);
                }
            }
        });
        
        item.addEventListener('drop', (e) => {
            e.preventDefault();
            const newOrder = [];
            document.querySelectorAll('.file-item').forEach(el => {
                const idx = parseInt(el.dataset.index);
                newOrder.push(state.files[idx]);
            });
            state.files = newOrder;
            renderFileList();
            updateTrimSettings();
        });
    });
}

// ============== Trim Settings ==============
function updateTrimSettings() {
    const trimCard = document.getElementById('trim-settings-card');
    const trimList = document.getElementById('trim-list');
    
    if (state.files.length === 0) {
        trimCard.style.display = 'none';
        return;
    }
    
    trimCard.style.display = 'block';
    
    const applyAll = document.getElementById('trim-apply-all').checked;
    trimList.style.display = applyAll ? 'none' : 'block';
    
    // Render per-video trim inputs
    trimList.innerHTML = state.files.map((file, index) => `
        <div class="trim-item">
            <span class="trim-item-name" title="${file.path}">${file.name}</span>
            <div class="trim-item-input">
                <label>Start:</label>
                <input type="number" class="form-input trim-input" data-index="${index}" data-type="start" 
                       value="${file.trim_start || 0}" min="0" max="${Math.floor(file.duration / 2)}" step="0.5">
                <span class="input-unit">s</span>
            </div>
            <div class="trim-item-input">
                <label>End:</label>
                <input type="number" class="form-input trim-input" data-index="${index}" data-type="end" 
                       value="${file.trim_end || 0}" min="0" max="${Math.floor(file.duration / 2)}" step="0.5">
                <span class="input-unit">s</span>
            </div>
        </div>
    `).join('');
    
    // Add event listeners to trim inputs
    trimList.querySelectorAll('.trim-input').forEach(input => {
        input.addEventListener('change', (e) => {
            const index = parseInt(e.target.dataset.index);
            const type = e.target.dataset.type;
            const value = parseFloat(e.target.value) || 0;
            
            if (type === 'start') {
                state.files[index].trim_start = value;
            } else {
                state.files[index].trim_end = value;
            }
        });
    });
}

function applyGlobalTrim() {
    const trimStart = parseFloat(document.getElementById('trim-global-start').value) || 0;
    const trimEnd = parseFloat(document.getElementById('trim-global-end').value) || 0;
    
    state.files.forEach(file => {
        file.trim_start = trimStart;
        file.trim_end = trimEnd;
    });
    
    // Update the per-video inputs if visible
    updateTrimSettings();
}

// ============== Settings ==============
function initSettings() {
    document.querySelectorAll('input[name="mode"]').forEach(input => {
        input.addEventListener('change', () => {
            document.getElementById('episodic-settings').style.display = input.value === 'episodic' ? 'block' : 'none';
        });
    });
    
    document.getElementById('transition-select').addEventListener('change', (e) => {
        document.getElementById('transition-duration-group').style.display = e.target.value === 'cut' ? 'none' : 'block';
    });
    
    // Subscribe interval visibility toggle
    document.getElementById('apply-subscribe').addEventListener('change', (e) => {
        document.getElementById('subscribe-interval-group').style.display = e.target.checked ? 'block' : 'none';
    });
    
    // Trim apply-all toggle
    document.getElementById('trim-apply-all').addEventListener('change', (e) => {
        const trimList = document.getElementById('trim-list');
        trimList.style.display = e.target.checked ? 'none' : 'block';
    });
    
    // Global trim inputs - apply to all when changed
    document.getElementById('trim-global-start').addEventListener('change', applyGlobalTrim);
    document.getElementById('trim-global-end').addEventListener('change', applyGlobalTrim);
    
    // Render preset actions
    document.getElementById('render-preset-select').addEventListener('change', loadRenderPreset);
    document.getElementById('save-preset-btn').addEventListener('click', saveRenderPreset);
    document.getElementById('update-preset-btn').addEventListener('click', updateRenderPreset);
    document.getElementById('delete-preset-btn').addEventListener('click', deleteRenderPreset);

    const outputDirBrowse = document.getElementById('output-dir-browse');
    const outputDirInput = document.getElementById('output-dir');
    if (outputDirBrowse && outputDirInput) {
        outputDirBrowse.addEventListener('click', async () => {
            const initialDir = outputDirInput.value || undefined;
            try {
                const result = await API.post('/browse/folder', { initial_dir: initialDir });
                if (result.cancelled) return;
                if (result.path) {
                    outputDirInput.value = result.path;
                    showToast('Output folder selected', 'success');
                }
            } catch (err) {
                showToast(`Failed to select folder: ${err.message}`, 'error');
            }
        });
    }
    
    loadProfileSelect();
    loadEncoderSelect();
    loadRenderPresets();
    loadLastUsedSettings();
}

async function loadProfileSelect() {
    try {
        const profiles = await API.get('/profiles');
        const select = document.getElementById('profile-select');
        select.innerHTML = '<option value="">No branding (skip intro/outro)</option>';
        profiles.forEach(p => {
            select.innerHTML += `<option value="${p.id}">${p.name}</option>`;
        });
    } catch (err) {
        console.error('Failed to load profiles:', err);
    }
}

async function loadEncoderSelect() {
    try {
        const encoders = await API.get('/encoders');
        const select = document.getElementById('encoder-select');
        select.innerHTML = '';
        
        encoders.forEach(enc => {
            const option = document.createElement('option');
            option.value = enc.id;
            option.textContent = enc.name;
            // Auto-select NVENC if available, otherwise software
            if (enc.id === 'nvenc') {
                option.selected = true;
            }
            select.appendChild(option);
        });
        
        // If NVENC wasn't found, select software
        if (!select.value) {
            select.value = 'software';
        }
    } catch (err) {
        console.error('Failed to load encoders:', err);
    }
}

// ============== Render Presets ==============
async function loadRenderPresets() {
    try {
        const presets = await API.get('/render-presets');
        const select = document.getElementById('render-preset-select');
        state.renderPresets = presets || [];
        const currentSelection = state.selectedPresetId;
        select.innerHTML = '<option value="">Load Preset...</option>';
        presets.forEach(p => {
            select.innerHTML += `<option value="${p.id}">${p.name}</option>`;
        });
        if (currentSelection && presets.some(p => p.id === currentSelection)) {
            select.value = currentSelection;
        } else {
            state.selectedPresetId = null;
            select.value = '';
        }
        updatePresetActionState();
    } catch (err) {
        console.error('Failed to load render presets:', err);
    }
}

async function loadLastUsedSettings() {
    try {
        const settings = await API.get('/render-presets/last-used');
        if (settings && Object.keys(settings).length > 0) {
            applyRenderSettings(settings);
        }
    } catch (err) {
        console.error('Failed to load last used settings:', err);
    }
}

async function loadRenderPreset(e) {
    const presetId = e.target.value;
    if (!presetId) {
        state.selectedPresetId = null;
        updatePresetActionState();
        return;
    }
    
    try {
        const preset = await API.get(`/render-presets/${presetId}`);
        if (preset && preset.settings) {
            applyRenderSettings(preset.settings);
            showToast(`Loaded preset: ${preset.name}`, 'success');
        }
        state.selectedPresetId = presetId;
        updatePresetActionState();
    } catch (err) {
        showToast('Failed to load preset', 'error');
    }
}

function applyRenderSettings(settings) {
    if (settings.profile_id) document.getElementById('profile-select').value = settings.profile_id;
    if (settings.transition) document.getElementById('transition-select').value = settings.transition;
    if (settings.transition_duration) document.getElementById('transition-duration').value = settings.transition_duration;
    if (settings.preset) document.getElementById('preset-select').value = settings.preset;
    if (settings.encoder) document.getElementById('encoder-select').value = settings.encoder;
    if (settings.output_name) document.getElementById('output-name').value = settings.output_name;
    if (Object.prototype.hasOwnProperty.call(settings, 'output_dir')) {
        document.getElementById('output-dir').value = settings.output_dir || '';
    }
    if (settings.apply_subscribe !== undefined) {
        document.getElementById('apply-subscribe').checked = settings.apply_subscribe;
        document.getElementById('subscribe-interval-group').style.display = settings.apply_subscribe ? 'block' : 'none';
    }
    if (settings.subscribe_interval) document.getElementById('subscribe-interval').value = settings.subscribe_interval;
    
    // Handle transition duration visibility
    document.getElementById('transition-duration-group').style.display = 
        settings.transition && settings.transition !== 'cut' ? 'block' : 'none';
}

function getCurrentRenderSettings() {
    return {
        profile_id: document.getElementById('profile-select').value,
        transition: document.getElementById('transition-select').value,
        transition_duration: parseFloat(document.getElementById('transition-duration').value),
        preset: document.getElementById('preset-select').value,
        encoder: document.getElementById('encoder-select').value,
        output_name: document.getElementById('output-name').value,
        output_dir: document.getElementById('output-dir').value.trim(),
        apply_subscribe: document.getElementById('apply-subscribe').checked,
        subscribe_interval: parseFloat(document.getElementById('subscribe-interval').value)
    };
}

async function saveRenderPreset() {
    const name = prompt('Enter preset name:');
    if (!name || !name.trim()) return;
    
    try {
        const settings = getCurrentRenderSettings();
        const preset = await API.post('/render-presets', { name: name.trim(), settings });
        showToast(`Preset "${preset.name}" saved!`, 'success');
        state.selectedPresetId = preset.id;
        await loadRenderPresets();
    } catch (err) {
        showToast('Failed to save preset', 'error');
    }
}

function getSelectedPreset() {
    if (!state.selectedPresetId) return null;
    return state.renderPresets.find(p => p.id === state.selectedPresetId) || null;
}

function updatePresetActionState() {
    const hasSelection = !!getSelectedPreset();
    const updateBtn = document.getElementById('update-preset-btn');
    const deleteBtn = document.getElementById('delete-preset-btn');
    if (updateBtn) updateBtn.disabled = !hasSelection;
    if (deleteBtn) deleteBtn.disabled = !hasSelection;
}

async function updateRenderPreset() {
    const preset = getSelectedPreset();
    if (!preset) {
        showToast('Select a preset to update', 'warning');
        return;
    }

    const name = prompt('Update preset name:', preset.name);
    if (name === null) return;

    const payload = { settings: getCurrentRenderSettings() };
    if (name.trim()) {
        payload.name = name.trim();
    }

    try {
        const updated = await API.put(`/render-presets/${preset.id}`, payload);
        showToast(`Preset "${updated.name}" updated`, 'success');
        state.selectedPresetId = updated.id;
        await loadRenderPresets();
    } catch (err) {
        showToast(`Failed to update preset: ${err.message}`, 'error');
    }
}

async function deleteRenderPreset() {
    const preset = getSelectedPreset();
    if (!preset) {
        showToast('Select a preset to delete', 'warning');
        return;
    }

    if (!confirm(`Delete preset "${preset.name}"?`)) return;

    try {
        await API.delete(`/render-presets/${preset.id}`);
        showToast('Preset deleted', 'success');
        state.selectedPresetId = null;
        await loadRenderPresets();
    } catch (err) {
        showToast(`Failed to delete preset: ${err.message}`, 'error');
    }
}

function updateProcessButton() {
    document.getElementById('process-btn').disabled = state.files.length === 0;
}

// ============== Processing ==============
function initProcessing() {
    document.getElementById('process-btn').addEventListener('click', startProcessing);
    document.getElementById('cancel-btn').addEventListener('click', cancelProcessing);
}

async function startProcessing() {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const profileId = document.getElementById('profile-select').value;
    const transition = document.getElementById('transition-select').value;
    const transitionDuration = parseFloat(document.getElementById('transition-duration').value);
    const preset = document.getElementById('preset-select').value;
    const encoder = document.getElementById('encoder-select').value;
    const outputName = document.getElementById('output-name').value || 'output';
    const outputDir = document.getElementById('output-dir').value.trim();
    const applySubscribe = document.getElementById('apply-subscribe').checked;
    const subscribeInterval = parseFloat(document.getElementById('subscribe-interval').value) * 60; // Convert to seconds
    
    // Apply global trim if enabled
    const applyGlobalTrim = document.getElementById('trim-apply-all').checked;
    if (applyGlobalTrim) {
        const trimStart = parseFloat(document.getElementById('trim-global-start').value) || 0;
        const trimEnd = parseFloat(document.getElementById('trim-global-end').value) || 0;
        state.files.forEach(f => {
            f.trim_start = trimStart;
            f.trim_end = trimEnd;
        });
    }
    
    const data = {
        video_paths: state.files.map(f => f.path),
        trim_settings: state.files.map(f => ({
            path: f.path,
            trim_start: f.trim_start || 0,
            trim_end: f.trim_end || 0
        })),
        profile_id: profileId || null,
        transition,
        transition_duration: transitionDuration,
        preset,
        encoder,
        output_name: outputName,
        output_dir: outputDir || null,
        apply_subscribe: applySubscribe,
        subscribe_interval: subscribeInterval
    };
    
    if (mode === 'episodic') {
        data.episode_duration = parseFloat(document.getElementById('episode-duration').value) * 60;
        data.episode_overlap = parseFloat(document.getElementById('episode-overlap').value);
        data.output_prefix = outputName;
    }
    
    try {
        // Save last used settings
        API.post('/render-presets/last-used', getCurrentRenderSettings()).catch(() => {});
        
        const endpoint = mode === 'single' ? '/process/single' : '/process/episodic';
        const result = await API.post(endpoint, data);
        
        state.currentJob = result.job_id;
        showProgressOverlay(true);
        pollJobStatus();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function pollJobStatus() {
    if (!state.currentJob) return;
    
    try {
        const status = await API.get(`/process/${state.currentJob}/status`);
        updateProgress(status);
        
        if (status.status === 'processing') {
            setTimeout(pollJobStatus, 500);
        } else if (status.status === 'completed') {
            showProgressOverlay(false);
            showToast('Processing completed!', 'success');
            state.currentJob = null;
            state.files = [];
            renderFileList();
            updateProcessButton();
        } else if (status.status === 'failed') {
            showProgressOverlay(false);
            showToast(`Failed: ${status.error}`, 'error');
            state.currentJob = null;
        } else if (status.status === 'cancelled') {
            showProgressOverlay(false);
            showToast('Processing cancelled', 'warning');
            state.currentJob = null;
        }
    } catch (err) {
        setTimeout(pollJobStatus, 1000);
    }
}

function updateProgress(status) {
    document.getElementById('progress-step').textContent = 
        status.total_steps > 0 
            ? `Step ${status.current_step_num}/${status.total_steps}: ${status.current_step}`
            : status.current_step;
    
    document.getElementById('progress-bar').style.width = `${status.progress}%`;
    document.getElementById('progress-percent').textContent = `${Math.round(status.progress)}%`;
}

function showProgressOverlay(show) {
    document.getElementById('progress-overlay').style.display = show ? 'flex' : 'none';
    if (show) {
        document.getElementById('progress-bar').style.width = '0%';
        document.getElementById('progress-percent').textContent = '0%';
        document.getElementById('progress-step').textContent = 'Initializing...';
    }
}

async function cancelProcessing() {
    if (state.currentJob) {
        try { await API.post(`/process/${state.currentJob}/cancel`); } catch (err) {}
    }
}

// ============== Branding ==============
async function loadBranding() {
    const list = document.getElementById('branding-list');
    list.innerHTML = Array(3).fill('<div class="branding-card skeleton skeleton-card"></div>').join('');
    
    try {
        state.profiles = await API.get('/profiles');
        renderBranding();
    } catch (err) {
        showToast('Failed to load branding', 'error');
        list.innerHTML = '<div class="branding-empty">Failed to load branding</div>';
    }
}

function renderBranding() {
    const list = document.getElementById('branding-list');
    
    if (state.profiles.length === 0) {
        list.innerHTML = `
            <div class="branding-empty">
                <svg class="branding-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                </svg>
                <p>No branding presets yet</p>
                <p class="hint">Create branding to add intro, outro, and subscribe graphics</p>
            </div>
        `;
        return;
    }
    
    list.innerHTML = state.profiles.map(profile => `
        <div class="branding-card" onclick="editBranding('${profile.id}')">
            <div class="branding-header-row">
                <div class="branding-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <circle cx="8.5" cy="8.5" r="1.5"></circle>
                        <polyline points="21 15 16 10 5 21"></polyline>
                    </svg>
                </div>
                <div class="branding-name">${profile.name}</div>
            </div>
            <div class="branding-assets">
                <div class="branding-asset ${profile.intro ? 'has-asset' : ''}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        ${profile.intro 
                            ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>'
                            : '<circle cx="12" cy="12" r="10"></circle>'}
                    </svg>
                    <span>Intro ${profile.intro ? `(${profile.intro.overlap_seconds}s overlap)` : '• Not set'}</span>
                </div>
                <div class="branding-asset ${profile.outro ? 'has-asset' : ''}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        ${profile.outro 
                            ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>'
                            : '<circle cx="12" cy="12" r="10"></circle>'}
                    </svg>
                    <span>Outro ${profile.outro ? `(${profile.outro.overlap_seconds}s overlap)` : '• Not set'}</span>
                </div>
                <div class="branding-asset ${profile.subscribe_graphics ? 'has-asset' : ''}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        ${profile.subscribe_graphics 
                            ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>'
                            : '<circle cx="12" cy="12" r="10"></circle>'}
                    </svg>
                    <span>Subscribe ${profile.subscribe_graphics ? `(every ${profile.subscribe_graphics.interval_seconds / 60}min)` : '• Not set'}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function initBrandingModal() {
    const modal = document.getElementById('branding-modal');
    
    document.getElementById('add-branding-btn').addEventListener('click', () => openBrandingModal());
    document.getElementById('modal-close').addEventListener('click', closeBrandingModal);
    document.getElementById('modal-cancel').addEventListener('click', closeBrandingModal);
    document.querySelector('.modal-backdrop').addEventListener('click', closeBrandingModal);
    document.getElementById('modal-delete').addEventListener('click', deleteBranding);
    
    document.getElementById('branding-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveBranding();
    });
    
    // Toggle listeners for conditional visibility
    document.getElementById('intro-full-overlap').addEventListener('change', () => toggleOverlapGroup('intro'));
    document.getElementById('outro-full-overlap').addEventListener('change', () => toggleOverlapGroup('outro'));
    document.getElementById('subscribe-full-duration').addEventListener('change', toggleDurationGroup);
    
    // Use event delegation for browse asset buttons
    document.getElementById('branding-modal').addEventListener('click', (e) => {
        const browseBtn = e.target.closest('.browse-asset-btn');
        if (browseBtn) {
            const type = browseBtn.dataset.type;
            if (type) {
                browseAsset(type);
            }
        }
    });
}
function openBrandingModal(profile = null) {
    state.editingProfile = profile;
    
    const modal = document.getElementById('branding-modal');
    document.getElementById('modal-title').textContent = profile ? 'Edit Branding' : 'New Branding';
    document.getElementById('modal-delete').style.display = profile ? 'block' : 'none';
    document.getElementById('branding-name').value = profile?.name || '';
    
    resetAssetSection('intro', profile?.intro);
    resetAssetSection('outro', profile?.outro);
    resetAssetSection('subscribe', profile?.subscribe_graphics);
    
    modal.classList.add('open');
}

function closeBrandingModal() {
    document.getElementById('branding-modal').classList.remove('open');
    state.editingProfile = null;
}

function resetAssetSection(type, data) {
    const content = document.getElementById(`${type}-asset`);
    const settings = document.getElementById(`${type}-settings`);
    
    // Clear any previous file reference
    delete content._filePath;
    delete content.dataset.remove;
    
    if (data) {
        content.innerHTML = `
            <div class="asset-uploaded">
                <span class="asset-filename" title="${data.file_path || ''}">${data.original_name || 'Selected'}</span>
                <button type="button" class="asset-remove" onclick="removeAsset('${type}')">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;
        settings.style.display = 'flex';
        
        if (type === 'intro') {
            document.getElementById('intro-full-overlap').checked = data.full_overlap === true;
            document.getElementById('intro-overlap').value = data.overlap_seconds || 0;
            document.getElementById('intro-audio').checked = data.has_audio !== false;
            toggleOverlapGroup('intro');
        } else if (type === 'outro') {
            document.getElementById('outro-full-overlap').checked = data.full_overlap === true;
            document.getElementById('outro-overlap').value = data.overlap_seconds || 0;
            document.getElementById('outro-audio').checked = data.has_audio !== false;
            toggleOverlapGroup('outro');
        } else if (type === 'subscribe') {
            document.getElementById('subscribe-full-duration').checked = data.use_full_duration !== false;
            document.getElementById('subscribe-duration').value = data.duration_seconds || 8;
            document.getElementById('subscribe-audio').checked = data.has_audio !== false;
            toggleDurationGroup();
        }
    } else {
        const typeLabel = type === 'subscribe' ? 'Subscribe Graphic' : type.charAt(0).toUpperCase() + type.slice(1);
        content.innerHTML = `
            <div class="asset-empty">
                <button type="button" class="btn btn-outline btn-sm browse-asset-btn" data-type="${type}">
                    <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                    </svg>
                    Browse ${typeLabel}
                </button>
            </div>
        `;
        settings.style.display = 'none';
    }
}

// Toggle functions for conditional visibility
function toggleOverlapGroup(type) {
    const fullOverlap = document.getElementById(`${type}-full-overlap`).checked;
    const group = document.getElementById(`${type}-overlap-group`);
    group.style.display = fullOverlap ? 'none' : 'block';
}

function toggleDurationGroup() {
    const fullDuration = document.getElementById('subscribe-full-duration').checked;
    const group = document.getElementById('subscribe-duration-group');
    group.style.display = fullDuration ? 'none' : 'block';
}

async function handleAssetUpload(e, type) {
    // This is no longer used - we use browseAsset instead
    e.target.value = '';
}

// Browse for asset file using native file dialog
async function browseAsset(type) {
    try {
        const result = await API.post('/browse-files', { 
            title: `Select ${type.charAt(0).toUpperCase() + type.slice(1)} File`,
            filetypes: [
                ['Video Files', '*.mp4 *.mov *.webm *.mkv *.avi'],
                ['All Files', '*.*']
            ]
        });
        
        if (result.paths && result.paths.length > 0) {
            const filePath = result.paths[0];
            const fileName = filePath.split(/[/\\]/).pop();
            
            const content = document.getElementById(`${type}-asset`);
            const settings = document.getElementById(`${type}-settings`);
            
            content.innerHTML = `
                <div class="asset-uploaded">
                    <span class="asset-filename" title="${filePath}">${fileName}</span>
                    <button type="button" class="asset-remove" onclick="removeAsset('${type}')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            `;
            settings.style.display = 'flex';
            content._filePath = filePath;  // Store file path, not file object
            delete content.dataset.remove;
        }
    } catch (err) {
        showToast('Failed to browse files: ' + err.message, 'error');
    }
}

function removeAsset(type) {
    const content = document.getElementById(`${type}-asset`);
    const settings = document.getElementById(`${type}-settings`);
    
    const typeLabel = type === 'subscribe' ? 'Subscribe Graphic' : type.charAt(0).toUpperCase() + type.slice(1);
    content.innerHTML = `
        <div class="asset-empty">
            <button type="button" class="btn btn-outline btn-sm browse-asset-btn" data-type="${type}">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                Browse ${typeLabel}
            </button>
        </div>
    `;
    settings.style.display = 'none';
    delete content._filePath;
    content.dataset.remove = 'true';
}

async function saveBranding() {
    const name = document.getElementById('branding-name').value.trim();
    if (!name) {
        showToast('Please enter a branding name', 'error');
        return;
    }
    
    try {
        let profile = state.editingProfile;
        
        if (profile) {
            profile = await API.put(`/profiles/${profile.id}`, { name });
        } else {
            profile = await API.post('/profiles', { name });
        }
        
        const profileId = profile.id;
        
        // Handle intro
        const introContent = document.getElementById('intro-asset');
        if (introContent.dataset.remove === 'true') {
            await API.delete(`/profiles/${profileId}/intro`);
        } else if (introContent._filePath) {
            await API.post(`/profiles/${profileId}/intro`, {
                file_path: introContent._filePath,
                full_overlap: document.getElementById('intro-full-overlap').checked,
                overlap: parseFloat(document.getElementById('intro-overlap').value),
                has_audio: document.getElementById('intro-audio').checked
            });
        } else if (state.editingProfile?.intro) {
            // Update settings even if file not changed
            await API.put(`/profiles/${profileId}/intro/settings`, {
                full_overlap: document.getElementById('intro-full-overlap').checked,
                overlap_seconds: parseFloat(document.getElementById('intro-overlap').value),
                has_audio: document.getElementById('intro-audio').checked
            });
        }
        
        // Handle outro
        const outroContent = document.getElementById('outro-asset');
        if (outroContent.dataset.remove === 'true') {
            await API.delete(`/profiles/${profileId}/outro`);
        } else if (outroContent._filePath) {
            await API.post(`/profiles/${profileId}/outro`, {
                file_path: outroContent._filePath,
                full_overlap: document.getElementById('outro-full-overlap').checked,
                overlap: parseFloat(document.getElementById('outro-overlap').value),
                has_audio: document.getElementById('outro-audio').checked
            });
        } else if (state.editingProfile?.outro) {
            // Update settings even if file not changed
            await API.put(`/profiles/${profileId}/outro/settings`, {
                full_overlap: document.getElementById('outro-full-overlap').checked,
                overlap_seconds: parseFloat(document.getElementById('outro-overlap').value),
                has_audio: document.getElementById('outro-audio').checked
            });
        }
        
        // Handle subscribe
        const subscribeContent = document.getElementById('subscribe-asset');
        if (subscribeContent.dataset.remove === 'true') {
            await API.delete(`/profiles/${profileId}/subscribe`);
        } else if (subscribeContent._filePath) {
            await API.post(`/profiles/${profileId}/subscribe`, {
                file_path: subscribeContent._filePath,
                use_full_duration: document.getElementById('subscribe-full-duration').checked,
                duration: parseFloat(document.getElementById('subscribe-duration').value),
                has_audio: document.getElementById('subscribe-audio').checked
            });
        } else if (state.editingProfile?.subscribe_graphics) {
            // Update settings even if file not changed
            await API.put(`/profiles/${profileId}/subscribe/settings`, {
                use_full_duration: document.getElementById('subscribe-full-duration').checked,
                duration_seconds: parseFloat(document.getElementById('subscribe-duration').value),
                has_audio: document.getElementById('subscribe-audio').checked
            });
        }
        
        closeBrandingModal();
        loadBranding();
        loadProfileSelect();
        showToast('Branding saved!', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function editBranding(profileId) {
    try {
        const profile = await API.get(`/profiles/${profileId}`);
        openBrandingModal(profile);
    } catch (err) {
        showToast('Failed to load branding', 'error');
    }
}

async function deleteBranding() {
    if (!state.editingProfile) return;
    if (!confirm('Delete this branding preset?')) return;
    
    try {
        await API.delete(`/profiles/${state.editingProfile.id}`);
        closeBrandingModal();
        loadBranding();
        loadProfileSelect();
        showToast('Branding deleted', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ============== Outputs ==============
async function loadOutputs() {
    const list = document.getElementById('outputs-list');
    list.innerHTML = Array(3).fill('<div class="output-item skeleton skeleton-item"></div>').join('');
    
    try {
        const outputDir = document.getElementById('output-dir')?.value.trim();
        const endpoint = outputDir ? `/output?dir=${encodeURIComponent(outputDir)}` : '/output';
        state.outputs = await API.get(endpoint);
        renderOutputs();
    } catch (err) {
        showToast('Failed to load outputs', 'error');
        list.innerHTML = '<div class="outputs-empty">Failed to load outputs</div>';
    }
}

function renderOutputs() {
    const list = document.getElementById('outputs-list');
    
    if (state.outputs.length === 0) {
        list.innerHTML = `
            <div class="outputs-empty">
                <svg class="branding-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                <p>No output files yet</p>
                <p class="hint">Process some videos to see them here</p>
            </div>
        `;
        return;
    }
    
    list.innerHTML = state.outputs.map(file => `
        <div class="output-item">
            <div class="output-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="23 7 16 12 23 17 23 7"></polygon>
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
                </svg>
            </div>
            <div class="output-info">
                <div class="output-name" title="${file.path}">${file.name}</div>
                <div class="output-meta">${file.size_formatted}</div>
            </div>
            <div class="output-actions">
                <button class="btn btn-ghost btn-sm" onclick="deleteOutput('${file.name}')" title="Delete">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        </div>
    `).join('');
}

async function deleteOutput(filename) {
    if (!confirm(`Delete ${filename}?`)) return;
    
    try {
        const outputDir = document.getElementById('output-dir')?.value.trim();
        const endpoint = outputDir
            ? `/output/${filename}?dir=${encodeURIComponent(outputDir)}`
            : `/output/${filename}`;
        await API.delete(endpoint);
        loadOutputs();
        showToast('File deleted', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function initOutputs() {
    document.getElementById('open-folder-btn').addEventListener('click', async () => {
        try {
            const outputDir = document.getElementById('output-dir')?.value.trim();
            const endpoint = outputDir ? `/output/folder?dir=${encodeURIComponent(outputDir)}` : '/output/folder';
            const data = await API.get(endpoint);
            showToast(`Output folder: ${data.path}`, 'info');
        } catch (err) {
            showToast('Failed to get folder path', 'error');
        }
    });
    
    document.getElementById('refresh-outputs-btn').addEventListener('click', loadOutputs);
}

// ============== Utilities ==============
function formatDuration(seconds) {
    if (!seconds) return '00:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return h > 0 
        ? `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
        : `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// ============== Onboarding ==============
function initOnboarding() {
    // Check if user has completed onboarding
    if (localStorage.getItem('editflow_onboarding_complete')) {
        return; // Skip onboarding
    }
    
    const modal = document.getElementById('onboarding-modal');
    const nextBtn = document.getElementById('onboarding-next');
    const skipBtn = document.getElementById('onboarding-skip');
    let currentStep = 1;
    const totalSteps = 5;
    
    // Show onboarding
    modal.classList.add('active');
    
    function showStep(step) {
        document.querySelectorAll('.onboarding-step').forEach(el => {
            el.style.display = 'none';
        });
        document.querySelectorAll('.onboarding-dot').forEach(el => {
            el.classList.remove('active');
        });
        
        const stepEl = document.querySelector(`.onboarding-step[data-step="${step}"]`);
        const dotEl = document.querySelector(`.onboarding-dot[data-step="${step}"]`);
        
        if (stepEl) stepEl.style.display = 'flex';
        if (dotEl) dotEl.classList.add('active');
        
        // Update button text
        nextBtn.textContent = step === totalSteps ? 'Get Started' : 'Next';
    }
    
    nextBtn.addEventListener('click', () => {
        if (currentStep < totalSteps) {
            currentStep++;
            showStep(currentStep);
        } else {
            completeOnboarding();
        }
    });
    
    skipBtn.addEventListener('click', completeOnboarding);
    
    // Allow clicking dots to navigate
    document.querySelectorAll('.onboarding-dot').forEach(dot => {
        dot.addEventListener('click', () => {
            currentStep = parseInt(dot.dataset.step);
            showStep(currentStep);
        });
    });
    
    function completeOnboarding() {
        localStorage.setItem('editflow_onboarding_complete', 'true');
        modal.classList.remove('active');
        showToast('Welcome to EditFlow! Let\'s create something awesome.', 'success');
    }
}

// ============== Init ==============
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initFileHandling();
    initSettings();
    initProcessing();
    initBrandingModal();
    initOutputs();
    loadProfileSelect();
    
    // Show onboarding for first-time users
    setTimeout(initOnboarding, 500);
});

// Global functions for onclick handlers
window.removeFile = removeFile;
window.editBranding = editBranding;
window.removeAsset = removeAsset;
window.deleteOutput = deleteOutput;

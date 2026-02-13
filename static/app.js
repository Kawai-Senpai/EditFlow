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
    selectedPresetId: null,
    // Audio mixer state
    audioMixer: {
        globalSettings: {}, // Track name -> {volume, mute, solo, trackType}
        applyToAll: true,   // Apply global settings to all videos
        normalizeFirst: true, // Normalize tracks before volume (disabled when LUFS auto-level is applied)
        previewAudio: null, // Currently playing audio element
        presets: [],        // Available audio mix presets
        selectedPresetId: null,
        voiceEffects: {
            enabled: false,
            presetId: null,
            presets: []     // Available voice effects presets
        },
        trackTypes: {}      // Available track types from API
    },
    thumbnail: {
        images: [],
        videos: [],
        framesByVideo: {},
        backgrounds: [],
        presets: [],
        selectedPresetId: null,
        overlayMode: 'none',
        overlayImage: { path: null, mode: 'scale_to_canvas', opacity: 1 },
        studio: {
            canvasWidth: 1280,
            canvasHeight: 720,
            elements: [],
            selectedId: null,
            editingId: null,
            transformMode: 'resize'
        },
        fonts: [],
        jobId: null
    }
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
            if (viewName === 'thumbnails') loadThumbnailView();
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
    
    // Apply global audio mix to any new files
    if (state.audioMixer.applyToAll) {
        applyGlobalAudioMix();
    }
}

function renderFileList() {
    const fileList = document.getElementById('file-list');
    const fileSummary = document.getElementById('file-summary');
    
    fileList.innerHTML = state.files.map((file, index) => {
        const ext = file.path.split('.').pop().toUpperCase();
        const audioTrackCount = file.audio_tracks?.length || (file.has_audio ? 1 : 0);
        const hasMultiTrack = audioTrackCount > 1;
        
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
                        ${hasMultiTrack ? `<span class="auto-badge audio-badge" title="${audioTrackCount} audio tracks">🎵 ${audioTrackCount}</span>` : ''}
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
    updateAudioMixerCard(); // Update audio mixer visibility
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

// ============== Audio Mixer ==============

/**
 * Get unique track signature for a file to detect common track layouts
 */
function getTrackSignature(file) {
    if (!file.audio_tracks || file.audio_tracks.length === 0) return '';
    return file.audio_tracks.map(t => `${t.title || 'Track'}:${t.channels}`).join('|');
}

/**
 * Get a friendly name for an audio track
 */
function getTrackDisplayName(track, index) {
    if (track.title) return track.title;
    return `Track ${index + 1}`;
}

/**
 * Check if all files have the same audio track layout
 */
function hasCommonTrackLayout() {
    const multiTrackFiles = state.files.filter(f => f.audio_tracks?.length > 1);
    if (multiTrackFiles.length < 2) return false;
    
    const firstSignature = getTrackSignature(multiTrackFiles[0]);
    return multiTrackFiles.every(f => getTrackSignature(f) === firstSignature);
}

/**
 * Update audio mixer card visibility and content
 */
function updateAudioMixerCard() {
    const card = document.getElementById('audio-mixer-card');
    if (!card) return;
    
    // Check if any file has multiple audio tracks
    const hasMultiTrack = state.files.some(f => f.audio_tracks?.length > 1);
    
    card.style.display = hasMultiTrack ? 'block' : 'none';
    
    if (hasMultiTrack) {
        renderAudioMixerContent();
    }
}

/**
 * Render the audio mixer content
 */
function renderAudioMixerContent() {
    const globalInputs = document.getElementById('audio-global-inputs');
    const perVideoList = document.getElementById('audio-per-video-list');
    const applyAllCheckbox = document.getElementById('audio-apply-all');
    
    if (!globalInputs || !perVideoList) return;
    
    // Get files with multiple audio tracks
    const multiTrackFiles = state.files.filter(f => f.audio_tracks?.length > 1);
    if (multiTrackFiles.length === 0) return;
    
    // Check for common track layout
    const hasCommon = hasCommonTrackLayout();
    
    // Build common track list (use first multi-track file as reference)
    const refFile = multiTrackFiles[0];
    const tracks = refFile.audio_tracks;
    
    // Initialize global settings if needed
    tracks.forEach((track, i) => {
        const trackName = getTrackDisplayName(track, i);
        if (!state.audioMixer.globalSettings[trackName]) {
            state.audioMixer.globalSettings[trackName] = {
                volume: 1.0,
                mute: false,
                solo: false,
                trackType: 'other'
            };
        }
    });
    
    // Build track type options
    const trackTypeOptions = Object.entries(state.audioMixer.trackTypes || {})
        .map(([key, val]) => `<option value="${key}">${val.name}</option>`)
        .join('');
    
    // Build audio preset options
    const presetOptions = (state.audioMixer.presets || [])
        .map(p => `<option value="${p.id}" ${state.audioMixer.selectedPresetId === p.id ? 'selected' : ''}>${p.name}</option>`)
        .join('');
    
    // Render preset and auto-level controls
    // Check if we can modify the currently selected preset
    const selectedPreset = state.audioMixer.presets.find(p => p.id === state.audioMixer.selectedPresetId);
    const canModifyPreset = state.audioMixer.selectedPresetId && selectedPreset && !selectedPreset.is_default;
    
    globalInputs.innerHTML = `
        <div class="audio-presets-bar">
            <div class="audio-preset-select-group">
                <label>Preset</label>
                <select id="audio-preset-select" class="form-select form-select-sm">
                    <option value="">Custom...</option>
                    ${presetOptions}
                </select>
                <button class="btn btn-ghost btn-xs" id="audio-preset-save" title="Save current settings as new preset">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                        <polyline points="17 21 17 13 7 13 7 21"></polyline>
                        <polyline points="7 3 7 8 15 8"></polyline>
                    </svg>
                </button>
                <button class="btn btn-ghost btn-xs ${canModifyPreset ? '' : 'hidden'}" id="audio-preset-update" title="Update current preset">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                        <path d="M12 20h9"></path>
                        <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                    </svg>
                </button>
                <button class="btn btn-ghost btn-xs ${canModifyPreset ? '' : 'hidden'}" id="audio-preset-delete" title="Delete current preset">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
            <button class="btn btn-outline btn-xs" id="audio-auto-level" title="Auto-level based on track types">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                    <path d="M12 20v-6M6 20V10M18 20V4"></path>
                </svg>
                Auto-Level
            </button>
        </div>
    `;
    
    // Render global controls with track type selector
    globalInputs.innerHTML += tracks.map((track, i) => {
        const trackName = getTrackDisplayName(track, i);
        const settings = state.audioMixer.globalSettings[trackName] || { volume: 1.0, mute: false, solo: false, trackType: 'other' };
        const volumePercent = Math.round(settings.volume * 100);
        const currentType = settings.trackType || 'other';
        
        return `
            <div class="audio-track-control" data-track="${trackName}">
                <div class="audio-track-header">
                    <span class="audio-track-name">${trackName}</span>
                    <select class="audio-track-type-select" data-track="${trackName}" title="Track type for auto-leveling">
                        ${Object.entries(state.audioMixer.trackTypes || {}).map(([key, val]) => 
                            `<option value="${key}" ${currentType === key ? 'selected' : ''}>${val.name}</option>`
                        ).join('')}
                    </select>
                    <span class="audio-track-info">${track.channels}ch • ${track.codec}</span>
                </div>
                <div class="audio-track-controls">
                    <div class="audio-volume-slider">
                        <input type="range" class="audio-volume-input" 
                               data-track="${trackName}" 
                               min="0" max="1000" value="${volumePercent}"
                               title="Volume: ${volumePercent}%">
                        <span class="audio-volume-value">${volumePercent}%</span>
                    </div>
                    <button class="audio-btn ${settings.mute ? 'active' : ''}" 
                            data-track="${trackName}" data-action="mute" 
                            title="Mute">M</button>
                    <button class="audio-btn ${settings.solo ? 'active' : ''}" 
                            data-track="${trackName}" data-action="solo" 
                            title="Solo">S</button>
                </div>
            </div>
        `;
    }).join('');
    
    // Get reference file for duration
    const refFileDuration = refFile.duration || 0;
    const defaultPreviewStart = Math.min(30, refFileDuration * 0.1); // Start at 10% or 30s
    const previewStart = state.audioMixer.previewStart ?? defaultPreviewStart;
    const previewDuration = state.audioMixer.previewDuration ?? 15;
    
    // Add preview section with time controls
    globalInputs.innerHTML += `
        <div class="audio-preview-section">
            <div class="audio-preview-header" id="audio-preview-toggle">
                <span class="audio-preview-label">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                        <polygon points="5 3 19 12 5 21 5 3"></polygon>
                    </svg>
                    Preview Settings
                </span>
                <span class="audio-preview-chevron">▼</span>
            </div>
            <div class="audio-preview-settings" id="audio-preview-settings">
                <div class="audio-preview-time-controls">
                    <div class="audio-time-input">
                        <label>Start at</label>
                        <input type="number" id="audio-preview-start" class="form-input" 
                               value="${previewStart.toFixed(1)}" min="0" max="${refFileDuration}" step="1">
                        <span class="input-unit">sec</span>
                    </div>
                    <div class="audio-time-input">
                        <label>Duration</label>
                        <input type="number" id="audio-preview-duration" class="form-input" 
                               value="${previewDuration}" min="5" max="60" step="5">
                        <span class="input-unit">sec</span>
                    </div>
                    <div class="audio-time-input">
                        <span class="audio-time-hint">of ${formatDuration(refFileDuration)}</span>
                    </div>
                </div>
                <div class="audio-preview-controls">
                    <button class="btn btn-outline btn-sm" id="audio-preview-btn" title="Preview audio mix">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                            <polygon points="5 3 19 12 5 21 5 3"></polygon>
                        </svg>
                        Play Preview
                    </button>
                    <button class="btn btn-ghost btn-sm" id="audio-preview-stop" title="Stop preview" style="display: none;">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                            <rect x="6" y="4" width="4" height="16"></rect>
                            <rect x="14" y="4" width="4" height="16"></rect>
                        </svg>
                        Stop
                    </button>
                    <span class="audio-preview-status"></span>
                </div>
            </div>
        </div>
    `;
    
    // Voice effects section (for voice-tagged tracks) - inline collapsible
    const hasVoiceTracks = Object.values(state.audioMixer.globalSettings).some(s => s.trackType === 'voice');
    const voicePresets = state.audioMixer.voiceEffects.presets || [];
    const voiceEnabled = state.audioMixer.voiceEffects.enabled;
    const selectedVoicePresetId = state.audioMixer.voiceEffects.presetId;
    const currentPreset = voicePresets.find(p => p.id === selectedVoicePresetId) || voicePresets[0] || {};
    
    // Initialize custom settings from preset if not already set
    if (!state.audioMixer.voiceEffects.customSettings) {
        state.audioMixer.voiceEffects.customSettings = JSON.parse(JSON.stringify(currentPreset));
    }
    const settings = state.audioMixer.voiceEffects.customSettings;
    const showSettings = state.audioMixer.voiceEffects.showSettings || false;
    
    globalInputs.innerHTML += `
        <div class="voice-effects-section ${hasVoiceTracks ? '' : 'disabled'}">
            <div class="voice-effects-header">
                <label class="toggle voice-effects-toggle">
                    <input type="checkbox" id="voice-effects-enabled" ${voiceEnabled ? 'checked' : ''} ${!hasVoiceTracks ? 'disabled' : ''}>
                    <span class="toggle-slider"></span>
                </label>
                <span class="voice-effects-title">Voice Effects</span>
                <span class="voice-effects-hint">${hasVoiceTracks ? 'Applied to ALL voice-tagged tracks in ALL videos' : 'Tag a track as "Voice" to enable'}</span>
            </div>
            <div class="voice-effects-content ${voiceEnabled && hasVoiceTracks ? '' : 'collapsed'}">
                <div class="voice-preset-bar">
                    <select id="voice-effects-preset-select" class="form-select form-select-sm" ${!hasVoiceTracks ? 'disabled' : ''}>
                        ${voicePresets.map(p => 
                            `<option value="${p.id}" ${selectedVoicePresetId === p.id ? 'selected' : ''}>${p.name}${p.is_default ? '' : ' ★'}</option>`
                        ).join('')}
                    </select>
                    <button class="btn btn-ghost btn-xs" id="voice-effects-preview" title="Preview voice effects" ${!hasVoiceTracks ? 'disabled' : ''}>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                            <polygon points="5 3 19 12 5 21 5 3"></polygon>
                        </svg>
                    </button>
                    <button class="btn btn-ghost btn-xs ${showSettings ? 'active' : ''}" id="voice-effects-toggle-settings" title="Toggle settings">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                            <polyline points="6 9 12 15 18 9"></polyline>
                        </svg>
                    </button>
                </div>
                <div class="voice-effects-inline-settings ${showSettings ? '' : 'collapsed'}" id="voice-effects-inline-settings">
                    ${renderVoiceEffectsInlineSettings(settings)}
                </div>
            </div>
        </div>
    `;
    
    // Per-video controls (shown when apply-all is unchecked)
    perVideoList.innerHTML = multiTrackFiles.map((file, fileIndex) => {
        const realIndex = state.files.indexOf(file);
        
        return `
            <div class="audio-per-video-item">
                <div class="audio-per-video-header" title="${file.path}">${file.name}</div>
                <div class="audio-per-video-tracks">
                    ${file.audio_tracks.map((track, i) => {
                        const trackName = getTrackDisplayName(track, i);
                        const fileSettings = file.audio_mix?.[i] || { volume: 1.0, mute: false, solo: false };
                        const volumePercent = Math.round(fileSettings.volume * 100);
                        
                        return `
                            <div class="audio-track-control compact" data-file="${realIndex}" data-track-index="${i}">
                                <span class="audio-track-name">${trackName}</span>
                                <div class="audio-track-controls">
                                    <input type="range" class="audio-volume-input-file" 
                                           data-file="${realIndex}" data-track-index="${i}"
                                           min="0" max="1000" value="${volumePercent}">
                                    <span class="audio-volume-value">${volumePercent}%</span>
                                    <button class="audio-btn-sm ${fileSettings.mute ? 'active' : ''}" 
                                            data-file="${realIndex}" data-track-index="${i}" data-action="mute">M</button>
                                    <button class="audio-btn-sm ${fileSettings.solo ? 'active' : ''}" 
                                            data-file="${realIndex}" data-track-index="${i}" data-action="solo">S</button>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }).join('');
    
    // Attach event listeners
    initAudioMixerEvents();
}

/**
 * Initialize audio mixer event listeners
 */
function initAudioMixerEvents() {
    // Global volume sliders
    document.querySelectorAll('.audio-volume-input').forEach(slider => {
        slider.addEventListener('input', (e) => {
            const trackName = e.target.dataset.track;
            const volume = parseInt(e.target.value) / 100;
            state.audioMixer.globalSettings[trackName].volume = volume;
            e.target.nextElementSibling.textContent = `${e.target.value}%`;
            
            // Apply to all files if apply-all is checked
            if (state.audioMixer.applyToAll) {
                applyGlobalAudioMix();
            }
        });
    });
    
    // Global mute/solo buttons
    document.querySelectorAll('.audio-btn[data-action]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const trackName = e.target.dataset.track;
            const action = e.target.dataset.action;
            
            if (action === 'mute') {
                state.audioMixer.globalSettings[trackName].mute = !state.audioMixer.globalSettings[trackName].mute;
            } else if (action === 'solo') {
                state.audioMixer.globalSettings[trackName].solo = !state.audioMixer.globalSettings[trackName].solo;
            }
            
            e.target.classList.toggle('active');
            
            if (state.audioMixer.applyToAll) {
                applyGlobalAudioMix();
            }
        });
    });
    
    // Track type selectors
    document.querySelectorAll('.audio-track-type-select').forEach(select => {
        select.addEventListener('change', (e) => {
            const trackName = e.target.dataset.track;
            state.audioMixer.globalSettings[trackName].trackType = e.target.value;
            state.audioMixer.selectedPresetId = null; // Custom settings now
            updateAudioPresetSelect();
            updateVoiceEffectsVisibility();
        });
    });
    
    // Audio preset select
    const presetSelect = document.getElementById('audio-preset-select');
    if (presetSelect) {
        presetSelect.addEventListener('change', (e) => {
            const presetId = e.target.value;
            if (presetId) {
                applyAudioPreset(presetId);
            }
            state.audioMixer.selectedPresetId = presetId || null;
        });
    }
    
    // Save preset button
    const savePresetBtn = document.getElementById('audio-preset-save');
    if (savePresetBtn) {
        savePresetBtn.addEventListener('click', saveCurrentAudioPreset);
    }
    
    // Update preset button
    const updatePresetBtn = document.getElementById('audio-preset-update');
    if (updatePresetBtn) {
        updatePresetBtn.addEventListener('click', updateCurrentAudioPreset);
    }
    
    // Delete preset button
    const deletePresetBtn = document.getElementById('audio-preset-delete');
    if (deletePresetBtn) {
        deletePresetBtn.addEventListener('click', deleteCurrentAudioPreset);
    }
    
    // Auto-level button
    const autoLevelBtn = document.getElementById('audio-auto-level');
    if (autoLevelBtn) {
        autoLevelBtn.addEventListener('click', applyAutoLevel);
    }
    
    // Voice effects toggle
    const voiceEffectsToggle = document.getElementById('voice-effects-enabled');
    if (voiceEffectsToggle) {
        voiceEffectsToggle.addEventListener('change', (e) => {
            state.audioMixer.voiceEffects.enabled = e.target.checked;
            const content = document.querySelector('.voice-effects-content');
            if (content) {
                content.classList.toggle('collapsed', !e.target.checked);
            }
        });
    }
    
    // Voice effects preset select
    const voicePresetSelect = document.getElementById('voice-effects-preset-select');
    if (voicePresetSelect) {
        voicePresetSelect.addEventListener('change', (e) => {
            state.audioMixer.voiceEffects.presetId = e.target.value;
            // Reset custom settings to new preset
            const preset = state.audioMixer.voiceEffects.presets.find(p => p.id === e.target.value);
            if (preset) {
                state.audioMixer.voiceEffects.customSettings = JSON.parse(JSON.stringify(preset));
                const settingsContainer = document.getElementById('voice-effects-inline-settings');
                if (settingsContainer && state.audioMixer.voiceEffects.showSettings) {
                    settingsContainer.innerHTML = renderVoiceEffectsInlineSettings(state.audioMixer.voiceEffects.customSettings);
                    initVoiceEffectsInlineEvents();
                }
            }
            updateVoicePresetDescription();
        });
    }
    
    // Voice effects preview button
    const voicePreviewBtn = document.getElementById('voice-effects-preview');
    if (voicePreviewBtn) {
        voicePreviewBtn.addEventListener('click', previewVoiceEffects);
    }
    
    // Voice effects toggle settings (expand/collapse inline settings)
    const voiceToggleSettingsBtn = document.getElementById('voice-effects-toggle-settings');
    if (voiceToggleSettingsBtn) {
        voiceToggleSettingsBtn.addEventListener('click', () => {
            state.audioMixer.voiceEffects.showSettings = !state.audioMixer.voiceEffects.showSettings;
            const inlineSettings = document.getElementById('voice-effects-inline-settings');
            if (inlineSettings) {
                inlineSettings.classList.toggle('collapsed', !state.audioMixer.voiceEffects.showSettings);
                if (state.audioMixer.voiceEffects.showSettings) {
                    // Re-render the settings HTML to reflect current customSettings
                    inlineSettings.innerHTML = renderVoiceEffectsInlineSettings(state.audioMixer.voiceEffects.customSettings);
                    initVoiceEffectsInlineEvents();
                }
            }
            voiceToggleSettingsBtn.classList.toggle('active', state.audioMixer.voiceEffects.showSettings);
        });
    }
    
    // Initialize inline voice effects events if settings are visible
    if (state.audioMixer.voiceEffects.showSettings) {
        initVoiceEffectsInlineEvents();
    }
    
    // Per-file volume sliders
    document.querySelectorAll('.audio-volume-input-file').forEach(slider => {
        slider.addEventListener('input', (e) => {
            const fileIndex = parseInt(e.target.dataset.file);
            const trackIndex = parseInt(e.target.dataset.trackIndex);
            const volume = parseInt(e.target.value) / 100;
            
            ensureFileAudioMix(fileIndex);
            state.files[fileIndex].audio_mix[trackIndex].volume = volume;
            e.target.nextElementSibling.textContent = `${e.target.value}%`;
        });
    });
    
    // Per-file mute/solo buttons
    document.querySelectorAll('.audio-btn-sm[data-action]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const fileIndex = parseInt(e.target.dataset.file);
            const trackIndex = parseInt(e.target.dataset.trackIndex);
            const action = e.target.dataset.action;
            
            ensureFileAudioMix(fileIndex);
            
            if (action === 'mute') {
                state.files[fileIndex].audio_mix[trackIndex].mute = !state.files[fileIndex].audio_mix[trackIndex].mute;
            } else if (action === 'solo') {
                state.files[fileIndex].audio_mix[trackIndex].solo = !state.files[fileIndex].audio_mix[trackIndex].solo;
            }
            
            e.target.classList.toggle('active');
        });
    });
    
    // Preview settings toggle (collapsible)
    const previewToggle = document.getElementById('audio-preview-toggle');
    if (previewToggle) {
        previewToggle.addEventListener('click', () => {
            const settings = document.getElementById('audio-preview-settings');
            const chevron = previewToggle.querySelector('.audio-preview-chevron');
            if (settings) {
                const isExpanded = settings.style.display !== 'none';
                settings.style.display = isExpanded ? 'none' : 'block';
                if (chevron) chevron.textContent = isExpanded ? '▶' : '▼';
            }
        });
    }
    
    // Preview time inputs
    const previewStartInput = document.getElementById('audio-preview-start');
    const previewDurationInput = document.getElementById('audio-preview-duration');
    
    if (previewStartInput) {
        previewStartInput.addEventListener('change', (e) => {
            state.audioMixer.previewStart = parseFloat(e.target.value) || 0;
        });
    }
    if (previewDurationInput) {
        previewDurationInput.addEventListener('change', (e) => {
            state.audioMixer.previewDuration = parseInt(e.target.value) || 15;
        });
    }
    
    // Preview play button
    const previewBtn = document.getElementById('audio-preview-btn');
    if (previewBtn) {
        previewBtn.addEventListener('click', previewAudioMix);
    }
    
    // Preview stop button
    const stopBtn = document.getElementById('audio-preview-stop');
    if (stopBtn) {
        stopBtn.addEventListener('click', stopAudioPreview);
    }
    
    // Apply-all toggle
    const applyAllCheckbox = document.getElementById('audio-apply-all');
    if (applyAllCheckbox) {
        applyAllCheckbox.addEventListener('change', (e) => {
            state.audioMixer.applyToAll = e.target.checked;
            const perVideoList = document.getElementById('audio-per-video-list');
            if (perVideoList) {
                perVideoList.style.display = e.target.checked ? 'none' : 'block';
            }
            
            if (e.target.checked) {
                applyGlobalAudioMix();
            }
        });
    }
}

/**
 * Ensure a file has audio_mix array initialized
 */
function ensureFileAudioMix(fileIndex) {
    const file = state.files[fileIndex];
    if (!file.audio_mix) {
        file.audio_mix = file.audio_tracks.map((track, i) => ({
            track_index: i,
            volume: 1.0,
            mute: false,
            solo: false,
            trackType: state.audioMixer.globalSettings[getTrackDisplayName(track, i)]?.trackType || 'other'
        }));
    }
}

/**
 * Apply global audio mix settings to all files
 */
function applyGlobalAudioMix() {
    state.files.forEach((file, fileIndex) => {
        if (!file.audio_tracks || file.audio_tracks.length <= 1) return;
        
        file.audio_mix = file.audio_tracks.map((track, i) => {
            const trackName = getTrackDisplayName(track, i);
            const globalSettings = state.audioMixer.globalSettings[trackName] || { volume: 1.0, mute: false, solo: false, trackType: 'other' };
            
            return {
                track_index: i,
                volume: globalSettings.volume,
                mute: globalSettings.mute,
                solo: globalSettings.solo,
                trackType: globalSettings.trackType || 'other'
            };
        });
    });
}

/**
 * Preview audio mix for the first multi-track video
 */
async function previewAudioMix() {
    const previewBtn = document.getElementById('audio-preview-btn');
    const stopBtn = document.getElementById('audio-preview-stop');
    const statusEl = document.querySelector('.audio-preview-status');
    
    // Find first multi-track file
    const file = state.files.find(f => f.audio_tracks?.length > 1);
    if (!file) {
        showToast('No multi-track video to preview', 'warning');
        return;
    }
    
    // Stop any existing preview
    stopAudioPreview();
    
    // Get preview time settings
    const startTime = state.audioMixer.previewStart ?? (file.trim_start || 0);
    const duration = state.audioMixer.previewDuration ?? 15;
    
    // Build audio mix settings - MUST include trackType for voice effects to work
    const audioMix = file.audio_tracks.map((track, i) => {
        const trackName = getTrackDisplayName(track, i);
        const settings = state.audioMixer.globalSettings[trackName] || { volume: 1.0, mute: false, solo: false, trackType: 'other' };
        
        return {
            track_index: i,
            volume: settings.volume,
            mute: settings.mute,
            solo: settings.solo,
            trackType: settings.trackType || 'other'
        };
    });
    
    previewBtn.disabled = true;
    if (stopBtn) stopBtn.style.display = 'none';
    if (statusEl) statusEl.textContent = 'Generating...';
    
    try {
        // Get voice effects for preview (includes customSettings if user modified inline controls)
        const voiceEffectsData = getVoiceEffectsForAPI();
        
        // Debug: Log what we're sending
        console.log('[AudioPreview] Sending request:');
        console.log('  audioMix:', JSON.stringify(audioMix, null, 2));
        console.log('  voiceEffectsData:', voiceEffectsData);
        console.log('  normalize_first:', state.audioMixer.normalizeFirst);
        
        const response = await fetch('/api/audio/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path: file.path,
                audio_mix: audioMix,
                start_time: startTime,
                duration: duration,
                voice_effects_preset_id: voiceEffectsData.preset_id,
                voice_effects_settings: voiceEffectsData.settings,
                normalize_first: state.audioMixer.normalizeFirst
            })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Preview failed');
        }
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        const audio = new Audio(url);
        state.audioMixer.previewAudio = audio;
        
        audio.onended = () => {
            if (statusEl) statusEl.textContent = '';
            previewBtn.disabled = false;
            if (stopBtn) stopBtn.style.display = 'none';
            state.audioMixer.previewAudio = null;
        };
        
        audio.onerror = () => {
            if (statusEl) statusEl.textContent = 'Playback error';
            previewBtn.disabled = false;
            if (stopBtn) stopBtn.style.display = 'none';
        };
        
        if (statusEl) statusEl.textContent = 'Playing...';
        if (stopBtn) stopBtn.style.display = 'inline-flex';
        previewBtn.disabled = false;
        audio.play();
        
    } catch (err) {
        showToast(`Preview failed: ${err.message}`, 'error');
        if (statusEl) statusEl.textContent = '';
        previewBtn.disabled = false;
    }
}

/**
 * Stop audio preview playback
 */
function stopAudioPreview() {
    if (state.audioMixer.previewAudio) {
        state.audioMixer.previewAudio.pause();
        state.audioMixer.previewAudio = null;
    }
    
    const stopBtn = document.getElementById('audio-preview-stop');
    const statusEl = document.querySelector('.audio-preview-status');
    
    if (stopBtn) stopBtn.style.display = 'none';
    if (statusEl) statusEl.textContent = '';
}

/**
 * Get audio mix settings formatted for the API
 */
function buildAudioMixForFile(file) {
    if (!file.audio_tracks || file.audio_tracks.length <= 1) {
        return null;
    }

    // When applyToAll is true, ALWAYS read from globalSettings (same source as preview)
    // This prevents stale file.audio_mix from causing render vs preview mismatch
    if (state.audioMixer.applyToAll) {
        return file.audio_tracks.map((track, i) => {
            const trackName = getTrackDisplayName(track, i);
            const settings = state.audioMixer.globalSettings[trackName] || { volume: 1.0, mute: false, solo: false, trackType: 'other' };
            return {
                track_index: i,
                volume: settings.volume,
                mute: settings.mute,
                solo: settings.solo,
                trackType: settings.trackType || 'other'
            };
        });
    }

    // Per-file mode: use file-specific audio_mix if available
    if (file.audio_mix && file.audio_mix.length) {
        return file.audio_mix;
    }

    // Fallback: build from globalSettings
    return file.audio_tracks.map((track, i) => {
        const trackName = getTrackDisplayName(track, i);
        const settings = state.audioMixer.globalSettings[trackName] || { volume: 1.0, mute: false, solo: false, trackType: 'other' };
        return {
            track_index: i,
            volume: settings.volume,
            mute: settings.mute,
            solo: settings.solo,
            trackType: settings.trackType || 'other'
        };
    });
}

function getAudioMixSettings() {
    return state.files
        .map(f => ({
            path: f.path,
            tracks: buildAudioMixForFile(f)
        }))
        .filter(entry => Array.isArray(entry.tracks) && entry.tracks.length > 0);
}

/**
 * Load audio presets and track types from API
 */
async function loadAudioPresetsAndTypes() {
    try {
        const [presetsRes, typesRes, voicePresetsRes] = await Promise.all([
            fetch('/api/audio-presets'),
            fetch('/api/audio/track-types'),
            fetch('/api/voice-effects/presets')
        ]);
        
        if (presetsRes.ok) {
            state.audioMixer.presets = await presetsRes.json();
        }
        if (typesRes.ok) {
            state.audioMixer.trackTypes = await typesRes.json();
        }
        if (voicePresetsRes.ok) {
            state.audioMixer.voiceEffects.presets = await voicePresetsRes.json();
            // Default to first preset
            if (state.audioMixer.voiceEffects.presets.length > 0 && !state.audioMixer.voiceEffects.presetId) {
                state.audioMixer.voiceEffects.presetId = state.audioMixer.voiceEffects.presets[0].id;
            }
        }
    } catch (err) {
        console.error('Failed to load audio presets:', err);
    }
}

/**
 * Apply an audio preset to current settings
 */
async function applyAudioPreset(presetId) {
    const preset = state.audioMixer.presets.find(p => p.id === presetId);
    if (!preset) return;
    
    // Apply track settings from preset
    const presetTracks = preset.tracks || {};
    
    for (const [trackName, settings] of Object.entries(presetTracks)) {
        if (state.audioMixer.globalSettings[trackName]) {
            state.audioMixer.globalSettings[trackName] = {
                ...state.audioMixer.globalSettings[trackName],
                volume: settings.volume ?? 1.0,
                mute: settings.mute ?? false,
                solo: settings.solo ?? false,
                trackType: settings.trackType ?? 'other'
            };
        }
    }
    
    // Apply voice effects settings
    if (preset.voiceEffects) {
        state.audioMixer.voiceEffects.enabled = preset.voiceEffects.enabled ?? false;
        state.audioMixer.voiceEffects.presetId = preset.voiceEffects.presetId ?? null;
    }
    
    // Update UI
    if (state.audioMixer.applyToAll) {
        applyGlobalAudioMix();
    }
    renderAudioMixerContent();
}

/**
 * Save current audio settings as a new preset
 */
async function saveCurrentAudioPreset() {
    const name = prompt('Enter preset name:');
    if (!name || !name.trim()) return;
    
    const tracks = {};
    for (const [trackName, settings] of Object.entries(state.audioMixer.globalSettings)) {
        tracks[trackName] = {
            volume: settings.volume,
            mute: settings.mute,
            solo: settings.solo,
            trackType: settings.trackType
        };
    }
    
    try {
        const response = await fetch('/api/audio-presets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name.trim(),
                tracks,
                voiceEffects: {
                    enabled: state.audioMixer.voiceEffects.enabled,
                    presetId: state.audioMixer.voiceEffects.presetId
                }
            })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to save preset');
        }
        
        const newPreset = await response.json();
        state.audioMixer.presets.push(newPreset);
        state.audioMixer.selectedPresetId = newPreset.id;
        renderAudioMixerContent();
        showToast('Audio preset saved!', 'success');
    } catch (err) {
        showToast(`Failed to save preset: ${err.message}`, 'error');
    }
}

/**
 * Update current audio preset with new settings
 */
async function updateCurrentAudioPreset() {
    const presetId = state.audioMixer.selectedPresetId;
    if (!presetId) {
        showToast('No preset selected to update', 'warning');
        return;
    }
    
    const preset = state.audioMixer.presets.find(p => p.id === presetId);
    if (!preset || preset.is_default) {
        showToast('Cannot update default presets', 'warning');
        return;
    }
    
    const tracks = {};
    for (const [trackName, settings] of Object.entries(state.audioMixer.globalSettings)) {
        tracks[trackName] = {
            volume: settings.volume,
            mute: settings.mute,
            solo: settings.solo,
            trackType: settings.trackType
        };
    }
    
    try {
        const response = await fetch(`/api/audio-presets/${presetId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tracks,
                voiceEffects: {
                    enabled: state.audioMixer.voiceEffects.enabled,
                    presetId: state.audioMixer.voiceEffects.presetId
                }
            })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to update preset');
        }
        
        const updatedPreset = await response.json();
        const idx = state.audioMixer.presets.findIndex(p => p.id === presetId);
        if (idx >= 0) {
            state.audioMixer.presets[idx] = updatedPreset;
        }
        renderAudioMixerContent();
        showToast('Audio preset updated!', 'success');
    } catch (err) {
        showToast(`Failed to update preset: ${err.message}`, 'error');
    }
}

/**
 * Delete current audio preset
 */
async function deleteCurrentAudioPreset() {
    const presetId = state.audioMixer.selectedPresetId;
    if (!presetId) {
        showToast('No preset selected to delete', 'warning');
        return;
    }
    
    const preset = state.audioMixer.presets.find(p => p.id === presetId);
    if (!preset || preset.is_default) {
        showToast('Cannot delete default presets', 'warning');
        return;
    }
    
    if (!confirm(`Delete preset "${preset.name}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/audio-presets/${presetId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to delete preset');
        }
        
        state.audioMixer.presets = state.audioMixer.presets.filter(p => p.id !== presetId);
        state.audioMixer.selectedPresetId = null;
        renderAudioMixerContent();
        showToast('Audio preset deleted!', 'success');
    } catch (err) {
        showToast(`Failed to delete preset: ${err.message}`, 'error');
    }
}

/**
 * Apply auto-level based on LUFS analysis and track types
 */
async function applyAutoLevel() {
    const trackTypes = {};
    for (const [trackName, settings] of Object.entries(state.audioMixer.globalSettings)) {
        trackTypes[trackName] = settings.trackType || 'other';
    }
    
    // Get first multi-track file for analysis
    const multiTrackFiles = state.files.filter(f => f.audio_tracks?.length > 1);
    const videoPath = multiTrackFiles.length > 0 ? multiTrackFiles[0].path : null;
    
    const autoLevelBtn = document.getElementById('audio-auto-level');
    if (autoLevelBtn) {
        autoLevelBtn.disabled = true;
        autoLevelBtn.innerHTML = `
            <svg class="animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
                <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path>
            </svg>
            Analyzing...
        `;
    }
    
    try {
        const response = await fetch('/api/audio/auto-level', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                track_types: trackTypes,
                video_path: videoPath
            })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Auto-level failed');
        }
        
        const result = await response.json();
        const { levels, analyzed, analysis } = result;
        
        // Apply the calculated levels
        for (const [trackName, volume] of Object.entries(levels)) {
            if (state.audioMixer.globalSettings[trackName]) {
                state.audioMixer.globalSettings[trackName].volume = volume;
            }
        }
        
        state.audioMixer.selectedPresetId = null; // Custom settings now
        state.audioMixer.normalizeFirst = !analyzed;
        
        if (state.audioMixer.applyToAll) {
            applyGlobalAudioMix();
        }
        renderAudioMixerContent();
        
        if (analyzed && analysis) {
            // Show detailed analysis in toast
            const analysisText = analysis.map(t => 
                `${t.track_name}: ${t.loudness_lufs.toFixed(1)} LUFS`
            ).join(', ');
            showToast(`Levels set based on LUFS analysis (${analysisText})`, 'success');
        } else {
            showToast('Levels set based on track types (no analysis available)', 'info');
        }
    } catch (err) {
        showToast(`Auto-level failed: ${err.message}`, 'error');
    } finally {
        if (autoLevelBtn) {
            autoLevelBtn.disabled = false;
            autoLevelBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                    <path d="M12 20v-6M6 20V10M18 20V4"></path>
                </svg>
                Auto-Level
            `;
        }
    }
}

/**
 * Update the audio preset select dropdown
 */
function updateAudioPresetSelect() {
    const select = document.getElementById('audio-preset-select');
    if (select) {
        select.value = state.audioMixer.selectedPresetId || '';
    }
}

/**
 * Render inline voice effects settings (collapsible)
 */
function renderVoiceEffectsInlineSettings(settings) {
    if (!settings) return '<div class="voice-effects-empty">Select a preset first</div>';
    
    // Check if current preset is a custom preset (can be edited/deleted)
    const currentPresetId = state.audioMixer.voiceEffects.presetId;
    const currentPreset = state.audioMixer.voiceEffects.presets.find(p => p.id === currentPresetId);
    const isCustomPreset = currentPreset && !currentPreset.is_default;
    
    return `
        <div class="voice-effects-grid">
            <!-- Noise Reduction -->
            <div class="ve-card ${settings.noise_reduction?.enabled ? '' : 'off'}">
                <div class="ve-card-header">
                    <label class="ve-toggle">
                        <input type="checkbox" data-effect="noise_reduction" data-field="enabled" 
                               ${settings.noise_reduction?.enabled ? 'checked' : ''}>
                        <span class="ve-toggle-label">Noise Reduction</span>
                    </label>
                </div>
                <div class="ve-card-body">
                    <div class="ve-row">
                        <span class="ve-label">Strength</span>
                        <input type="range" class="ve-slider" data-effect="noise_reduction" data-field="nr" 
                               min="0" max="30" value="${settings.noise_reduction?.nr || 12}">
                        <span class="ve-value">${settings.noise_reduction?.nr || 12}</span>
                    </div>
                </div>
            </div>
            
            <!-- Gate -->
            <div class="ve-card ${settings.gate?.enabled ? '' : 'off'}">
                <div class="ve-card-header">
                    <label class="ve-toggle">
                        <input type="checkbox" data-effect="gate" data-field="enabled" 
                               ${settings.gate?.enabled ? 'checked' : ''}>
                        <span class="ve-toggle-label">Gate</span>
                    </label>
                </div>
                <div class="ve-card-body">
                    <div class="ve-row">
                        <span class="ve-label">Threshold</span>
                        <input type="range" class="ve-slider" data-effect="gate" data-field="threshold" 
                               min="0.005" max="0.05" step="0.001" value="${settings.gate?.threshold || 0.02}">
                        <span class="ve-value">${((settings.gate?.threshold || 0.02) * 1000).toFixed(0)}</span>
                    </div>
                </div>
            </div>
            
            <!-- Compressor -->
            <div class="ve-card ${settings.compressor?.enabled ? '' : 'off'}">
                <div class="ve-card-header">
                    <label class="ve-toggle">
                        <input type="checkbox" data-effect="compressor" data-field="enabled" 
                               ${settings.compressor?.enabled ? 'checked' : ''}>
                        <span class="ve-toggle-label">Compressor</span>
                    </label>
                </div>
                <div class="ve-card-body">
                    <div class="ve-row">
                        <span class="ve-label">Ratio</span>
                        <input type="range" class="ve-slider" data-effect="compressor" data-field="ratio" 
                               min="1" max="10" step="0.5" value="${settings.compressor?.ratio || 3}">
                        <span class="ve-value">${settings.compressor?.ratio || 3}:1</span>
                    </div>
                    <div class="ve-row">
                        <span class="ve-label">Makeup</span>
                        <input type="range" class="ve-slider" data-effect="compressor" data-field="makeup" 
                               min="1" max="4" step="0.1" value="${settings.compressor?.makeup || 1.5}">
                        <span class="ve-value">${(settings.compressor?.makeup || 1.5).toFixed(1)}x</span>
                    </div>
                </div>
            </div>
            
            <!-- Exciter -->
            <div class="ve-card ${settings.exciter?.enabled ? '' : 'off'}">
                <div class="ve-card-header">
                    <label class="ve-toggle">
                        <input type="checkbox" data-effect="exciter" data-field="enabled" 
                               ${settings.exciter?.enabled ? 'checked' : ''}>
                        <span class="ve-toggle-label">Exciter</span>
                    </label>
                </div>
                <div class="ve-card-body">
                    <div class="ve-row">
                        <span class="ve-label">Amount</span>
                        <input type="range" class="ve-slider" data-effect="exciter" data-field="amount" 
                               min="0.3" max="1.5" step="0.1" value="${settings.exciter?.amount || 0.6}">
                        <span class="ve-value">${(settings.exciter?.amount || 0.6).toFixed(1)}</span>
                    </div>
                </div>
            </div>
            
            <!-- De-esser -->
            <div class="ve-card ${settings.deesser?.enabled ? '' : 'off'}">
                <div class="ve-card-header">
                    <label class="ve-toggle">
                        <input type="checkbox" data-effect="deesser" data-field="enabled" 
                               ${settings.deesser?.enabled ? 'checked' : ''}>
                        <span class="ve-toggle-label">De-esser</span>
                    </label>
                </div>
                <div class="ve-card-body">
                    <div class="ve-row">
                        <span class="ve-label">Intensity</span>
                        <input type="range" class="ve-slider" data-effect="deesser" data-field="i" 
                               min="0" max="100" value="${Math.round((settings.deesser?.i || 0.25) * 100)}">
                        <span class="ve-value">${Math.round((settings.deesser?.i || 0.25) * 100)}%</span>
                    </div>
                </div>
            </div>
            
            <!-- Leveling -->
            <div class="ve-card ${settings.leveling?.enabled ? '' : 'off'}">
                <div class="ve-card-header">
                    <label class="ve-toggle">
                        <input type="checkbox" data-effect="leveling" data-field="enabled" 
                               ${settings.leveling?.enabled ? 'checked' : ''}>
                        <span class="ve-toggle-label">Auto-Level</span>
                    </label>
                </div>
                <div class="ve-card-body">
                    <div class="ve-row">
                        <span class="ve-label">Max Gain</span>
                        <input type="range" class="ve-slider" data-effect="leveling" data-field="maxgain" 
                               min="2" max="20" step="1" value="${settings.leveling?.maxgain || 10}">
                        <span class="ve-value">${settings.leveling?.maxgain || 10}dB</span>
                    </div>
                </div>
            </div>
            
            <!-- Limiter -->
            <div class="ve-card ${settings.limiter?.enabled ? '' : 'off'}">
                <div class="ve-card-header">
                    <label class="ve-toggle">
                        <input type="checkbox" data-effect="limiter" data-field="enabled" 
                               ${settings.limiter?.enabled ? 'checked' : ''}>
                        <span class="ve-toggle-label">Limiter</span>
                    </label>
                </div>
                <div class="ve-card-body">
                    <div class="ve-row">
                        <span class="ve-label">Ceiling</span>
                        <input type="range" class="ve-slider" data-effect="limiter" data-field="limit" 
                               min="80" max="100" value="${Math.round((settings.limiter?.limit || 0.98) * 100)}">
                        <span class="ve-value">${Math.round((settings.limiter?.limit || 0.98) * 100)}%</span>
                    </div>
                </div>
            </div>
            
            <!-- Deepening (Pitch Shift via Rubberband) -->
            <div class="ve-card ${settings.deepening?.enabled ? '' : 'off'}">
                <div class="ve-card-header">
                    <label class="ve-toggle">
                        <input type="checkbox" data-effect="deepening" data-field="enabled" 
                               ${settings.deepening?.enabled ? 'checked' : ''}>
                        <span class="ve-toggle-label">Deepening</span>
                    </label>
                </div>
                <div class="ve-card-body">
                    <div class="ve-row">
                        <span class="ve-label">Method</span>
                        <select class="ve-select" data-effect="deepening" data-field="method">
                            <option value="shelf" ${settings.deepening?.method === 'shelf' ? 'selected' : ''}>Bass Boost (natural)</option>
                            <option value="pitch" ${settings.deepening?.method !== 'shelf' ? 'selected' : ''}>Pitch Shift</option>
                        </select>
                    </div>
                    ${settings.deepening?.method === 'shelf' ? `
                    <div class="ve-row">
                        <span class="ve-label">Bass Gain</span>
                        <input type="range" class="ve-slider" data-effect="deepening" data-field="bass_gain_db" 
                               min="0" max="6" step="0.5" value="${settings.deepening?.bass_gain_db ?? 2}">
                        <span class="ve-value">+${settings.deepening?.bass_gain_db ?? 2}dB</span>
                    </div>
                    ` : `
                    <div class="ve-row">
                        <span class="ve-label">Semitones</span>
                        <input type="range" class="ve-slider" data-effect="deepening" data-field="semitones" 
                               min="-1" max="0" step="0.1" value="${settings.deepening?.semitones ?? -0.3}">
                        <span class="ve-value">${settings.deepening?.semitones ?? -0.3}</span>
                    </div>
                    `}
                </div>
            </div>
            
            <!-- Loudnorm -->
            <div class="ve-card ${settings.loudnorm?.enabled ? '' : 'off'}">
                <div class="ve-card-header">
                    <label class="ve-toggle">
                        <input type="checkbox" data-effect="loudnorm" data-field="enabled" 
                               ${settings.loudnorm?.enabled ? 'checked' : ''}>
                        <span class="ve-toggle-label">Loudness Norm</span>
                    </label>
                </div>
                <div class="ve-card-body">
                    <div class="ve-row">
                        <span class="ve-label">Target</span>
                        <input type="range" class="ve-slider" data-effect="loudnorm" data-field="I" 
                               min="-24" max="-10" value="${settings.loudnorm?.I || -16}">
                        <span class="ve-value">${settings.loudnorm?.I || -16} LUFS</span>
                    </div>
                </div>
            </div>
            
            <!-- Highpass -->
            <div class="ve-card">
                <div class="ve-card-header">
                    <span class="ve-toggle-label">Highpass</span>
                </div>
                <div class="ve-card-body">
                    <div class="ve-row">
                        <span class="ve-label">Cutoff</span>
                        <input type="range" class="ve-slider" data-effect="root" data-field="highpass_hz" 
                               min="20" max="200" value="${settings.highpass_hz || 80}">
                        <span class="ve-value">${settings.highpass_hz || 80}Hz</span>
                    </div>
                </div>
            </div>
        </div>
        <div class="ve-actions">
            <button class="btn btn-ghost btn-xs" id="ve-reset-preset">Reset</button>
            ${isCustomPreset ? `
                <button class="btn btn-ghost btn-xs ve-danger" id="ve-delete-preset" title="Delete this preset">🗑️</button>
                <button class="btn btn-outline btn-xs" id="ve-update-preset">Update Preset</button>
            ` : ''}
            <button class="btn btn-outline btn-xs" id="ve-save-preset">Save as New</button>
        </div>
    `;
}

/**
 * Initialize inline voice effects events
 */
function initVoiceEffectsInlineEvents() {
    const container = document.getElementById('voice-effects-inline-settings');
    if (!container) return;
    
    const settings = state.audioMixer.voiceEffects.customSettings;
    if (!settings) return;
    
    // Helper to get/set nested property
    function getNestedProp(obj, path) {
        return path.split('.').reduce((o, k) => o?.[k], obj);
    }
    function setNestedProp(obj, path, value) {
        const parts = path.split('.');
        const last = parts.pop();
        const parent = parts.reduce((o, k) => {
            if (!o[k]) o[k] = {};
            return o[k];
        }, obj);
        parent[last] = value;
    }
    
    // Toggle checkboxes
    container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const effect = e.target.dataset.effect;
            const field = e.target.dataset.field;
            const path = effect === 'root' ? field : `${effect}.${field}`;
            setNestedProp(settings, path, e.target.checked);
            
            // Update card styling
            const card = e.target.closest('.ve-card');
            if (card) card.classList.toggle('off', !e.target.checked);
        });
    });
    
    // Sliders
    container.querySelectorAll('.ve-slider').forEach(slider => {
        slider.addEventListener('input', (e) => {
            const effect = e.target.dataset.effect;
            const field = e.target.dataset.field;
            let value = parseFloat(e.target.value);
            
            // Handle percentage fields (convert from 0-100 to 0-1)
            if (['i', 'peak', 'limit'].includes(field)) {
                value = value / 100;
            }
            
            const path = effect === 'root' ? field : `${effect}.${field}`;
            if (field === 'highpass_hz' || field === 'lowpass_hz') {
                value = parseInt(e.target.value);
            }
            setNestedProp(settings, path, value);
            
            // Update display value
            const valueEl = e.target.nextElementSibling;
            if (valueEl) {
                if (['i', 'peak', 'limit'].includes(field)) {
                    valueEl.textContent = `${e.target.value}%`;
                } else if (field === 'ratio') {
                    valueEl.textContent = `${e.target.value}:1`;
                } else if (field === 'makeup' || field === 'amount') {
                    valueEl.textContent = `${parseFloat(e.target.value).toFixed(1)}x`;
                } else if (field === 'I') {
                    valueEl.textContent = `${e.target.value} LUFS`;
                } else if (field === 'highpass_hz') {
                    valueEl.textContent = `${e.target.value}Hz`;
                } else if (field === 'lowpass_hz') {
                    valueEl.textContent = `${Math.round(e.target.value / 1000)}kHz`;
                } else if (field === 'threshold' && effect === 'gate') {
                    valueEl.textContent = `${(parseFloat(e.target.value) * 1000).toFixed(0)}`;
                } else if (field === 'maxgain') {
                    valueEl.textContent = `${e.target.value}dB`;
                } else if (field === 'semitones') {
                    valueEl.textContent = e.target.value;
                } else if (field === 'bass_gain_db') {
                    valueEl.textContent = `+${e.target.value}dB`;
                } else {
                    valueEl.textContent = e.target.value;
                }
            }
        });
    });
    
    // Select dropdowns (like deepening method)
    container.querySelectorAll('.ve-select').forEach(select => {
        select.addEventListener('change', (e) => {
            const effect = e.target.dataset.effect;
            const field = e.target.dataset.field;
            const path = effect === 'root' ? field : `${effect}.${field}`;
            setNestedProp(settings, path, e.target.value);
            
            // Re-render the settings to show the correct controls for the new method
            const settingsContainer = document.getElementById('voice-effects-inline-settings');
            if (settingsContainer) {
                settingsContainer.innerHTML = renderVoiceEffectsInlineSettings(state.audioMixer.voiceEffects.customSettings);
                initVoiceEffectsInlineEvents();
            }
        });
    });
    
    // Reset button
    const resetBtn = document.getElementById('ve-reset-preset');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            const preset = state.audioMixer.voiceEffects.presets.find(p => p.id === state.audioMixer.voiceEffects.presetId);
            if (preset) {
                state.audioMixer.voiceEffects.customSettings = JSON.parse(JSON.stringify(preset));
                const settingsContainer = document.getElementById('voice-effects-inline-settings');
                if (settingsContainer) {
                    settingsContainer.innerHTML = renderVoiceEffectsInlineSettings(state.audioMixer.voiceEffects.customSettings);
                    initVoiceEffectsInlineEvents();
                }
                showToast('Reset to preset defaults', 'info');
            }
        });
    }
    
    // Save as preset button
    const saveBtn = document.getElementById('ve-save-preset');
    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            const name = prompt('Enter preset name:');
            if (!name?.trim()) return;
            
            try {
                const response = await fetch('/api/voice-effects/presets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name.trim(),
                        description: 'Custom preset',
                        settings: settings
                    })
                });
                
                if (!response.ok) throw new Error('Failed to save');
                
                const newPreset = await response.json();
                state.audioMixer.voiceEffects.presets.push(newPreset);
                state.audioMixer.voiceEffects.presetId = newPreset.id;
                state.audioMixer.voiceEffects.customSettings = JSON.parse(JSON.stringify(newPreset));
                renderAudioMixerContent();
                showToast('Preset saved!', 'success');
            } catch (err) {
                showToast('Failed to save preset', 'error');
            }
        });
    }
    
    // Update preset button (for custom presets)
    const updateBtn = document.getElementById('ve-update-preset');
    if (updateBtn) {
        updateBtn.addEventListener('click', async () => {
            const presetId = state.audioMixer.voiceEffects.presetId;
            
            try {
                const response = await fetch(`/api/voice-effects/presets/${presetId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });
                
                if (!response.ok) throw new Error('Failed to update');
                
                const updatedPreset = await response.json();
                // Update in local state
                const idx = state.audioMixer.voiceEffects.presets.findIndex(p => p.id === presetId);
                if (idx >= 0) {
                    state.audioMixer.voiceEffects.presets[idx] = updatedPreset;
                }
                showToast('Preset updated!', 'success');
            } catch (err) {
                showToast('Failed to update preset', 'error');
            }
        });
    }
    
    // Delete preset button (for custom presets)
    const deleteBtn = document.getElementById('ve-delete-preset');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', async () => {
            const presetId = state.audioMixer.voiceEffects.presetId;
            const preset = state.audioMixer.voiceEffects.presets.find(p => p.id === presetId);
            
            if (!confirm(`Delete preset "${preset?.name}"?`)) return;
            
            try {
                const response = await fetch(`/api/voice-effects/presets/${presetId}`, {
                    method: 'DELETE'
                });
                
                if (!response.ok) throw new Error('Failed to delete');
                
                // Remove from local state
                state.audioMixer.voiceEffects.presets = state.audioMixer.voiceEffects.presets.filter(p => p.id !== presetId);
                // Select first available preset
                const firstPreset = state.audioMixer.voiceEffects.presets[0];
                state.audioMixer.voiceEffects.presetId = firstPreset?.id || '';
                state.audioMixer.voiceEffects.customSettings = firstPreset ? JSON.parse(JSON.stringify(firstPreset)) : null;
                renderAudioMixerContent();
                showToast('Preset deleted!', 'success');
            } catch (err) {
                showToast('Cannot delete default preset', 'error');
            }
        });
    }
}

/**
 * Update voice effects section visibility based on voice tracks
 */
function updateVoiceEffectsVisibility() {
    const hasVoiceTracks = Object.values(state.audioMixer.globalSettings).some(s => s.trackType === 'voice');
    const section = document.querySelector('.voice-effects-section');
    const toggle = document.getElementById('voice-effects-enabled');
    const select = document.getElementById('voice-effects-preset-select');
    const previewBtn = document.getElementById('voice-effects-preview');
    
    if (section) {
        section.classList.toggle('disabled', !hasVoiceTracks);
    }
    if (toggle) {
        toggle.disabled = !hasVoiceTracks;
    }
    if (select) {
        select.disabled = !hasVoiceTracks;
    }
    if (previewBtn) {
        previewBtn.disabled = !hasVoiceTracks;
    }
    
    // Update hint text
    const hint = document.querySelector('.voice-effects-hint');
    if (hint) {
        hint.textContent = hasVoiceTracks ? 'Applied to voice-tagged tracks' : 'Tag a track as "Voice" to enable';
    }
}

/**
 * Update voice preset description
 */
function updateVoicePresetDescription() {
    const descEl = document.getElementById('voice-preset-description');
    if (!descEl) return;
    
    const preset = state.audioMixer.voiceEffects.presets.find(p => p.id === state.audioMixer.voiceEffects.presetId);
    descEl.textContent = preset?.description || '';
}

/**
 * Preview voice effects on ALL voice-tagged tracks mixed together
 */
async function previewVoiceEffects() {
    const multiTrackFiles = state.files.filter(f => f.audio_tracks?.length > 1);
    if (multiTrackFiles.length === 0) {
        showToast('No multi-track files available', 'error');
        return;
    }
    
    const file = multiTrackFiles[0];
    
    // Find ALL voice-tagged track indices AND their volume settings
    const voiceTrackIndices = [];
    const voiceTrackVolumes = [];
    for (const [trackName, settings] of Object.entries(state.audioMixer.globalSettings)) {
        if (settings.trackType === 'voice') {
            // Find the track index for this track name
            const tracks = file.audio_tracks || [];
            for (let i = 0; i < tracks.length; i++) {
                if (getTrackDisplayName(tracks[i], i) === trackName) {
                    voiceTrackIndices.push(i);
                    // Include volume settings (not mute/solo for voice-only preview)
                    voiceTrackVolumes.push(settings.mute ? 0 : settings.volume);
                    break;
                }
            }
        }
    }
    
    if (voiceTrackIndices.length === 0) {
        showToast('No voice-tagged tracks found', 'error');
        return;
    }
    
    const previewBtn = document.getElementById('voice-effects-preview');
    if (previewBtn) previewBtn.disabled = true;
    
    const startTime = state.audioMixer.previewStart ?? 0;
    const duration = state.audioMixer.previewDuration ?? 15;
    
    // Get voice effects settings - prefer customSettings over preset_id
    const voiceEffectsData = getVoiceEffectsForAPI();
    
    try {
        const response = await fetch('/api/voice-effects/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path: file.path,
                preset_id: voiceEffectsData.preset_id,
                settings: voiceEffectsData.settings,
                voice_track_indices: voiceTrackIndices,
                voice_track_volumes: voiceTrackVolumes,  // Include user's volume settings
                start_time: startTime,
                duration: duration
            })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Preview failed');
        }
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        
        // Stop any existing preview
        stopAudioPreview();
        
        const audio = new Audio(url);
        state.audioMixer.previewAudio = audio;
        
        audio.onended = () => {
            if (previewBtn) previewBtn.disabled = false;
            state.audioMixer.previewAudio = null;
        };
        
        audio.play();
        const trackCount = voiceTrackIndices.length;
        showToast(`Playing voice effects on ${trackCount} voice track${trackCount > 1 ? 's' : ''}...`, 'info');
        
    } catch (err) {
        showToast(`Voice preview failed: ${err.message}`, 'error');
    } finally {
        if (previewBtn) previewBtn.disabled = false;
    }
}

/**
 * Get voice effects settings for API calls - returns customSettings if available, otherwise preset_id
 */
function getVoiceEffectsForAPI() {
    if (!state.audioMixer.voiceEffects.enabled) {
        return { preset_id: null, settings: null };
    }
    
    // If we have custom settings (user has modified the inline controls), send those
    if (state.audioMixer.voiceEffects.customSettings) {
        return { preset_id: null, settings: state.audioMixer.voiceEffects.customSettings };
    }
    
    // Otherwise, just send the preset ID
    return { preset_id: state.audioMixer.voiceEffects.presetId, settings: null };
}

/**
 * Get voice effects preset ID for API calls (legacy - for render only)
 */
function getVoiceEffectsPresetId() {
    if (state.audioMixer.voiceEffects.enabled && state.audioMixer.voiceEffects.presetId) {
        return state.audioMixer.voiceEffects.presetId;
    }
    return null;
}

/**
 * Open voice effects editor modal
 */
function openVoiceEffectsEditor() {
    const modal = document.getElementById('voice-effects-modal');
    if (!modal) return;
    
    // Get current preset settings
    const presetId = state.audioMixer.voiceEffects.presetId;
    const preset = state.audioMixer.voiceEffects.presets.find(p => p.id === presetId);
    
    if (!preset) {
        showToast('No voice effects preset selected', 'error');
        return;
    }
    
    // Store a copy for editing
    state.audioMixer.voiceEffects.editingPreset = JSON.parse(JSON.stringify(preset));
    
    renderVoiceEffectsEditor();
    modal.classList.add('active');
    
    // Set up event listeners
    document.getElementById('voice-effects-modal-close')?.addEventListener('click', closeVoiceEffectsEditor);
    document.getElementById('voice-effects-reset')?.addEventListener('click', resetVoiceEffectsEditor);
    document.getElementById('voice-effects-apply')?.addEventListener('click', applyVoiceEffectsChanges);
    document.getElementById('voice-effects-save-preset')?.addEventListener('click', saveVoiceEffectsAsPreset);
}

/**
 * Close voice effects editor modal
 */
function closeVoiceEffectsEditor() {
    const modal = document.getElementById('voice-effects-modal');
    if (modal) modal.classList.remove('active');
    state.audioMixer.voiceEffects.editingPreset = null;
}

/**
 * Render voice effects editor content
 */
function renderVoiceEffectsEditor() {
    const editor = document.getElementById('voice-effects-editor');
    if (!editor) return;
    
    const preset = state.audioMixer.voiceEffects.editingPreset;
    if (!preset) return;
    
    editor.innerHTML = `
        <div class="voice-effect-preset-info">
            <div class="voice-effect-preset-name">${preset.name}</div>
            <div class="voice-effect-preset-desc">${preset.description || 'No description'}</div>
        </div>
        
        <div class="voice-effects-editor-grid">
            <!-- Highpass/Lowpass -->
            <div class="voice-effect-card">
                <div class="voice-effect-card-header">
                    <span class="voice-effect-card-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
                        </svg>
                        Frequency Cutoff
                    </span>
                </div>
                <div class="voice-effect-params">
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Highpass</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-highpass" min="20" max="200" value="${preset.highpass_hz || 80}">
                        <span class="voice-effect-param-value" id="ve-highpass-val">${preset.highpass_hz || 80} Hz</span>
                    </div>
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Lowpass</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-lowpass" min="8000" max="20000" value="${preset.lowpass_hz || 16000}">
                        <span class="voice-effect-param-value" id="ve-lowpass-val">${preset.lowpass_hz || 16000} Hz</span>
                    </div>
                </div>
            </div>
            
            <!-- Noise Reduction -->
            <div class="voice-effect-card ${preset.noise_reduction?.enabled ? '' : 'disabled'}" id="ve-nr-card">
                <div class="voice-effect-card-header">
                    <span class="voice-effect-card-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 18v-6a9 9 0 0 1 18 0v6"></path>
                            <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"></path>
                        </svg>
                        Noise Reduction
                    </span>
                    <label class="toggle voice-effect-toggle">
                        <input type="checkbox" id="ve-nr-enabled" ${preset.noise_reduction?.enabled ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="voice-effect-params">
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Strength</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-nr-strength" min="0" max="30" value="${preset.noise_reduction?.nr || 12}">
                        <span class="voice-effect-param-value" id="ve-nr-strength-val">${preset.noise_reduction?.nr || 12}</span>
                    </div>
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Floor</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-nr-floor" min="-80" max="-20" value="${preset.noise_reduction?.nf || -50}">
                        <span class="voice-effect-param-value" id="ve-nr-floor-val">${preset.noise_reduction?.nf || -50} dB</span>
                    </div>
                </div>
            </div>
            
            <!-- De-esser -->
            <div class="voice-effect-card ${preset.deesser?.enabled ? '' : 'disabled'}" id="ve-deesser-card">
                <div class="voice-effect-card-header">
                    <span class="voice-effect-card-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                            <line x1="12" y1="19" x2="12" y2="23"></line>
                        </svg>
                        De-esser
                    </span>
                    <label class="toggle voice-effect-toggle">
                        <input type="checkbox" id="ve-deesser-enabled" ${preset.deesser?.enabled ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="voice-effect-params">
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Intensity</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-deesser-i" min="0" max="1" step="0.05" value="${preset.deesser?.i || 0.25}">
                        <span class="voice-effect-param-value" id="ve-deesser-i-val">${((preset.deesser?.i || 0.25) * 100).toFixed(0)}%</span>
                    </div>
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Frequency</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-deesser-f" min="0.3" max="0.9" step="0.05" value="${preset.deesser?.f || 0.6}">
                        <span class="voice-effect-param-value" id="ve-deesser-f-val">${((preset.deesser?.f || 0.6) * 100).toFixed(0)}%</span>
                    </div>
                </div>
            </div>
            
            <!-- Compressor -->
            <div class="voice-effect-card ${preset.compressor?.enabled ? '' : 'disabled'}" id="ve-comp-card">
                <div class="voice-effect-card-header">
                    <span class="voice-effect-card-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect>
                            <line x1="9" y1="4" x2="9" y2="20"></line>
                            <line x1="15" y1="4" x2="15" y2="20"></line>
                        </svg>
                        Compressor
                    </span>
                    <label class="toggle voice-effect-toggle">
                        <input type="checkbox" id="ve-comp-enabled" ${preset.compressor?.enabled ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="voice-effect-params">
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Threshold</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-comp-threshold" min="0.01" max="0.5" step="0.01" value="${preset.compressor?.threshold || 0.1}">
                        <span class="voice-effect-param-value" id="ve-comp-threshold-val">${preset.compressor?.threshold || 0.1}</span>
                    </div>
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Ratio</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-comp-ratio" min="1" max="10" step="0.5" value="${preset.compressor?.ratio || 3}">
                        <span class="voice-effect-param-value" id="ve-comp-ratio-val">${preset.compressor?.ratio || 3}:1</span>
                    </div>
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Attack</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-comp-attack" min="1" max="100" value="${preset.compressor?.attack_ms || 20}">
                        <span class="voice-effect-param-value" id="ve-comp-attack-val">${preset.compressor?.attack_ms || 20} ms</span>
                    </div>
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Makeup</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-comp-makeup" min="1" max="4" step="0.1" value="${preset.compressor?.makeup || 1.5}">
                        <span class="voice-effect-param-value" id="ve-comp-makeup-val">${preset.compressor?.makeup || 1.5}x</span>
                    </div>
                </div>
            </div>
            
            <!-- Leveling -->
            <div class="voice-effect-card ${preset.leveling?.enabled ? '' : 'disabled'}" id="ve-level-card">
                <div class="voice-effect-card-header">
                    <span class="voice-effect-card-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 20v-6M6 20V10M18 20V4"></path>
                        </svg>
                        Dynamic Leveling
                    </span>
                    <label class="toggle voice-effect-toggle">
                        <input type="checkbox" id="ve-level-enabled" ${preset.leveling?.enabled ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="voice-effect-params">
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Peak</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-level-peak" min="0.5" max="1" step="0.01" value="${preset.leveling?.peak || 0.95}">
                        <span class="voice-effect-param-value" id="ve-level-peak-val">${((preset.leveling?.peak || 0.95) * 100).toFixed(0)}%</span>
                    </div>
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Compress</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-level-compress" min="1" max="15" step="0.5" value="${preset.leveling?.compress || 5}">
                        <span class="voice-effect-param-value" id="ve-level-compress-val">${preset.leveling?.compress || 5}</span>
                    </div>
                </div>
            </div>
            
            <!-- Limiter -->
            <div class="voice-effect-card ${preset.limiter?.enabled ? '' : 'disabled'}" id="ve-limiter-card">
                <div class="voice-effect-card-header">
                    <span class="voice-effect-card-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                        </svg>
                        Limiter
                    </span>
                    <label class="toggle voice-effect-toggle">
                        <input type="checkbox" id="ve-limiter-enabled" ${preset.limiter?.enabled ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="voice-effect-params">
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Limit</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-limiter-limit" min="0.8" max="1" step="0.01" value="${preset.limiter?.limit || 0.98}">
                        <span class="voice-effect-param-value" id="ve-limiter-limit-val">${((preset.limiter?.limit || 0.98) * 100).toFixed(0)}%</span>
                    </div>
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Attack</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-limiter-attack" min="1" max="20" value="${preset.limiter?.attack || 5}">
                        <span class="voice-effect-param-value" id="ve-limiter-attack-val">${preset.limiter?.attack || 5} ms</span>
                    </div>
                </div>
            </div>
            
            <!-- Voice Deepening (Subtle Gravitas) -->
            <div class="voice-effect-card ${preset.deepening?.enabled ? '' : 'disabled'}" id="ve-deep-card">
                <div class="voice-effect-card-header">
                    <span class="voice-effect-card-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                        </svg>
                        Voice Gravitas
                    </span>
                    <label class="toggle voice-effect-toggle">
                        <input type="checkbox" id="ve-deep-enabled" ${preset.deepening?.enabled ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="voice-effect-params">
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Depth</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-deep-semitones" min="-1.5" max="0" step="0.1" value="${preset.deepening?.semitones ?? -0.5}">
                        <span class="voice-effect-param-value" id="ve-deep-semitones-val">${preset.deepening?.semitones ?? -0.5}</span>
                    </div>
                </div>
            </div>
            
            <!-- Loudness Normalization -->
            <div class="voice-effect-card ${preset.loudnorm?.enabled ? '' : 'disabled'}" id="ve-loudnorm-card">
                <div class="voice-effect-card-header">
                    <span class="voice-effect-card-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                        </svg>
                        Loudness Norm
                    </span>
                    <label class="toggle voice-effect-toggle">
                        <input type="checkbox" id="ve-loudnorm-enabled" ${preset.loudnorm?.enabled ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="voice-effect-params">
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">Target LUFS</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-loudnorm-i" min="-24" max="-10" value="${preset.loudnorm?.I || -16}">
                        <span class="voice-effect-param-value" id="ve-loudnorm-i-val">${preset.loudnorm?.I || -16} LUFS</span>
                    </div>
                    <div class="voice-effect-param">
                        <span class="voice-effect-param-label">True Peak</span>
                        <input type="range" class="voice-effect-param-slider" 
                               id="ve-loudnorm-tp" min="-4" max="0" step="0.5" value="${preset.loudnorm?.TP || -1.5}">
                        <span class="voice-effect-param-value" id="ve-loudnorm-tp-val">${preset.loudnorm?.TP || -1.5} dB</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Attach event listeners to all sliders and toggles
    initVoiceEffectsEditorEvents();
}

/**
 * Initialize voice effects editor event listeners
 */
function initVoiceEffectsEditorEvents() {
    const preset = state.audioMixer.voiceEffects.editingPreset;
    if (!preset) return;
    
    // Highpass/Lowpass
    bindSlider('ve-highpass', 'Hz', v => preset.highpass_hz = parseInt(v));
    bindSlider('ve-lowpass', 'Hz', v => preset.lowpass_hz = parseInt(v));
    
    // Noise Reduction
    bindToggle('ve-nr-enabled', 've-nr-card', v => preset.noise_reduction.enabled = v);
    bindSlider('ve-nr-strength', '', v => preset.noise_reduction.nr = parseInt(v));
    bindSlider('ve-nr-floor', 'dB', v => preset.noise_reduction.nf = parseInt(v));
    
    // De-esser
    bindToggle('ve-deesser-enabled', 've-deesser-card', v => preset.deesser.enabled = v);
    bindSlider('ve-deesser-i', '%', v => preset.deesser.i = parseFloat(v), v => (v * 100).toFixed(0));
    bindSlider('ve-deesser-f', '%', v => preset.deesser.f = parseFloat(v), v => (v * 100).toFixed(0));
    
    // Compressor
    bindToggle('ve-comp-enabled', 've-comp-card', v => preset.compressor.enabled = v);
    bindSlider('ve-comp-threshold', '', v => preset.compressor.threshold = parseFloat(v));
    bindSlider('ve-comp-ratio', ':1', v => preset.compressor.ratio = parseFloat(v));
    bindSlider('ve-comp-attack', 'ms', v => preset.compressor.attack_ms = parseInt(v));
    bindSlider('ve-comp-makeup', 'x', v => preset.compressor.makeup = parseFloat(v));
    
    // Leveling
    bindToggle('ve-level-enabled', 've-level-card', v => preset.leveling.enabled = v);
    bindSlider('ve-level-peak', '%', v => preset.leveling.peak = parseFloat(v), v => (v * 100).toFixed(0));
    bindSlider('ve-level-compress', '', v => preset.leveling.compress = parseFloat(v));
    
    // Limiter
    bindToggle('ve-limiter-enabled', 've-limiter-card', v => preset.limiter.enabled = v);
    bindSlider('ve-limiter-limit', '%', v => preset.limiter.limit = parseFloat(v), v => (v * 100).toFixed(0));
    bindSlider('ve-limiter-attack', 'ms', v => preset.limiter.attack = parseInt(v));
    
    // Deepening
    bindToggle('ve-deep-enabled', 've-deep-card', v => preset.deepening.enabled = v);
    bindSlider('ve-deep-semitones', '', v => preset.deepening.semitones = parseFloat(v));
    
    // Loudnorm
    bindToggle('ve-loudnorm-enabled', 've-loudnorm-card', v => preset.loudnorm.enabled = v);
    bindSlider('ve-loudnorm-i', 'LUFS', v => preset.loudnorm.I = parseInt(v));
    bindSlider('ve-loudnorm-tp', 'dB', v => preset.loudnorm.TP = parseFloat(v));
}

function bindSlider(id, unit, setter, formatter = null) {
    const slider = document.getElementById(id);
    const valEl = document.getElementById(`${id}-val`);
    if (!slider || !valEl) return;
    
    slider.addEventListener('input', (e) => {
        const val = e.target.value;
        setter(val);
        const displayVal = formatter ? formatter(parseFloat(val)) : val;
        valEl.textContent = unit ? `${displayVal} ${unit}` : displayVal;
    });
}

function bindToggle(id, cardId, setter) {
    const toggle = document.getElementById(id);
    const card = document.getElementById(cardId);
    if (!toggle) return;
    
    toggle.addEventListener('change', (e) => {
        setter(e.target.checked);
        if (card) {
            card.classList.toggle('disabled', !e.target.checked);
        }
    });
}

/**
 * Reset voice effects editor to original preset
 */
function resetVoiceEffectsEditor() {
    const presetId = state.audioMixer.voiceEffects.presetId;
    const preset = state.audioMixer.voiceEffects.presets.find(p => p.id === presetId);
    if (preset) {
        state.audioMixer.voiceEffects.editingPreset = JSON.parse(JSON.stringify(preset));
        renderVoiceEffectsEditor();
        showToast('Reset to preset defaults', 'info');
    }
}

/**
 * Apply voice effects changes (custom settings for this session)
 */
function applyVoiceEffectsChanges() {
    // Store custom settings in state for use during processing
    state.audioMixer.voiceEffects.customSettings = state.audioMixer.voiceEffects.editingPreset;
    closeVoiceEffectsEditor();
    showToast('Voice effects settings applied!', 'success');
}

/**
 * Save current voice effects as a new preset
 */
async function saveVoiceEffectsAsPreset() {
    const name = prompt('Enter preset name:');
    if (!name || !name.trim()) return;
    
    const settings = state.audioMixer.voiceEffects.editingPreset;
    if (!settings) return;
    
    try {
        const response = await fetch('/api/voice-effects/presets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name.trim(),
                description: `Custom preset based on ${settings.name}`,
                settings: settings
            })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || 'Failed to save preset');
        }
        
        const newPreset = await response.json();
        state.audioMixer.voiceEffects.presets.push(newPreset);
        state.audioMixer.voiceEffects.presetId = newPreset.id;
        
        closeVoiceEffectsEditor();
        renderAudioMixerContent();
        showToast('Voice effects preset saved!', 'success');
    } catch (err) {
        showToast(`Failed to save preset: ${err.message}`, 'error');
    }
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
    
    // Mode change handler for batch settings
    document.querySelectorAll('input[name="mode"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            const batchSettings = document.getElementById('batch-settings');
            const episodicSettings = document.getElementById('episodic-settings');
            
            if (batchSettings) {
                batchSettings.style.display = e.target.value === 'batch' ? 'block' : 'none';
            }
            if (episodicSettings) {
                episodicSettings.style.display = e.target.value === 'episodic' ? 'flex' : 'none';
            }
        });
    });
    
    // Batch naming change handler
    const batchNaming = document.getElementById('batch-naming');
    if (batchNaming) {
        batchNaming.addEventListener('change', (e) => {
            const prefixRow = document.getElementById('batch-prefix-row');
            if (prefixRow) {
                prefixRow.style.display = ['prefix', 'suffix'].includes(e.target.value) ? 'flex' : 'none';
            }
        });
    }
}

async function startProcessing() {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    
    if (mode === 'batch') {
        await startBatchProcessing();
        return;
    }
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
    const applyGlobalTrimSetting = document.getElementById('trim-apply-all').checked;
    if (applyGlobalTrimSetting) {
        const trimStart = parseFloat(document.getElementById('trim-global-start').value) || 0;
        const trimEnd = parseFloat(document.getElementById('trim-global-end').value) || 0;
        state.files.forEach(f => {
            f.trim_start = trimStart;
            f.trim_end = trimEnd;
        });
    }
    
    // Apply global audio mix if enabled
    const applyGlobalAudioSetting = document.getElementById('audio-apply-all')?.checked ?? true;
    if (applyGlobalAudioSetting) {
        applyGlobalAudioMix();
    }
    
    // Get voice effects settings (includes custom inline settings if modified)
    const voiceEffectsData = getVoiceEffectsForAPI();
    
    const data = {
        video_paths: state.files.map(f => f.path),
        trim_settings: state.files.map(f => ({
            path: f.path,
            trim_start: f.trim_start || 0,
            trim_end: f.trim_end || 0
        })),
        audio_mix_settings: getAudioMixSettings(),
        voice_effects_preset_id: voiceEffectsData.preset_id,
        voice_effects_settings: voiceEffectsData.settings,
        normalize_first: state.audioMixer.normalizeFirst,
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
    
    // Debug: Log the audio mix settings being sent to the backend
    console.log('[Render] audio_mix_settings:', JSON.stringify(data.audio_mix_settings, null, 2));
    console.log('[Render] normalize_first:', data.normalize_first);
    console.log('[Render] globalSettings:', JSON.stringify(state.audioMixer.globalSettings, null, 2));
    
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
    // Also cancel batch processing if running
    if (state.batchProcessing) {
        state.batchProcessing.cancelled = true;
    }
}

/**
 * Process multiple videos as separate files with the same settings
 */
async function startBatchProcessing() {
    if (state.files.length === 0) {
        showToast('No files to process', 'warning');
        return;
    }
    
    const profileId = document.getElementById('profile-select').value;
    const transition = document.getElementById('transition-select').value;
    const transitionDuration = parseFloat(document.getElementById('transition-duration').value);
    const preset = document.getElementById('preset-select').value;
    const encoder = document.getElementById('encoder-select').value;
    const outputDir = document.getElementById('output-dir').value.trim();
    
    // Batch naming options
    const batchNaming = document.getElementById('batch-naming')?.value || 'original';
    const batchPrefixText = document.getElementById('batch-prefix-text')?.value || '';
    
    // Apply global trim if enabled
    const applyGlobalTrimSetting = document.getElementById('trim-apply-all').checked;
    if (applyGlobalTrimSetting) {
        const trimStart = parseFloat(document.getElementById('trim-global-start').value) || 0;
        const trimEnd = parseFloat(document.getElementById('trim-global-end').value) || 0;
        state.files.forEach(f => {
            f.trim_start = trimStart;
            f.trim_end = trimEnd;
        });
    }
    
    // Apply global audio mix if enabled
    const applyGlobalAudioSetting = document.getElementById('audio-apply-all')?.checked ?? true;
    if (applyGlobalAudioSetting) {
        applyGlobalAudioMix();
    }
    
    // Save last used settings
    API.post('/render-presets/last-used', getCurrentRenderSettings()).catch(() => {});
    
    // Initialize batch state
    state.batchProcessing = {
        total: state.files.length,
        current: 0,
        completed: 0,
        failed: 0,
        cancelled: false,
        jobs: []
    };
    
    showProgressOverlay(true);
    updateBatchProgress();
    
    // Process each file sequentially
    for (let i = 0; i < state.files.length; i++) {
        if (state.batchProcessing.cancelled) {
            break;
        }
        
        const file = state.files[i];
        state.batchProcessing.current = i + 1;
        
        // Generate output name based on naming strategy
        let outputName;
        const originalName = file.path.split(/[/\\]/).pop().replace(/\.[^.]+$/, '');
        
        switch (batchNaming) {
            case 'prefix':
                outputName = batchPrefixText + originalName;
                break;
            case 'suffix':
                outputName = originalName + batchPrefixText;
                break;
            case 'sequential':
                outputName = String(i + 1).padStart(2, '0');
                break;
            default:
                outputName = originalName;
        }
        
        // Get per-file audio mix settings
        const fileAudioMix = getAudioMixSettingsForFile(file);
        
        // Get voice effects settings (includes custom inline settings if modified)
        const voiceEffectsData = getVoiceEffectsForAPI();
        
        const data = {
            video_paths: [file.path],
            trim_settings: [{
                path: file.path,
                trim_start: file.trim_start || 0,
                trim_end: file.trim_end || 0
            }],
            audio_mix_settings: [{
                path: file.path,
                tracks: fileAudioMix
            }],
            voice_effects_preset_id: voiceEffectsData.preset_id,
            voice_effects_settings: voiceEffectsData.settings,
            normalize_first: state.audioMixer.normalizeFirst,
            profile_id: profileId || null,
            transition,
            transition_duration: transitionDuration,
            preset,
            encoder,
            output_name: outputName,
            output_dir: outputDir || null,
            apply_subscribe: false,
            subscribe_interval: 0
        };
        
        updateBatchProgress(`Processing ${i + 1}/${state.files.length}: ${originalName}`);
        
        try {
            const result = await API.post('/process/single', data);
            state.currentJob = result.job_id;
            
            // Poll until this job completes
            await pollBatchJobStatus(result.job_id, originalName);
            state.batchProcessing.completed++;
        } catch (err) {
            state.batchProcessing.failed++;
            console.error(`Batch processing failed for ${originalName}:`, err);
        }
        
        updateBatchProgress();
    }
    
    // Done
    showProgressOverlay(false);
    state.currentJob = null;
    
    if (state.batchProcessing.cancelled) {
        showToast(`Batch cancelled. Completed: ${state.batchProcessing.completed}/${state.batchProcessing.total}`, 'warning');
    } else if (state.batchProcessing.failed > 0) {
        showToast(`Batch completed with errors. Success: ${state.batchProcessing.completed}, Failed: ${state.batchProcessing.failed}`, 'warning');
    } else {
        showToast(`Batch processing completed! ${state.batchProcessing.completed} files processed.`, 'success');
    }
    
    state.batchProcessing = null;
    state.files = [];
    renderFileList();
    updateProcessButton();
}

/**
 * Get audio mix settings for a specific file
 */
function getAudioMixSettingsForFile(file) {
    const mix = buildAudioMixForFile(file);
    return mix || [];
}

/**
 * Poll job status for batch processing
 */
async function pollBatchJobStatus(jobId, fileName) {
    return new Promise((resolve, reject) => {
        const poll = async () => {
            if (state.batchProcessing?.cancelled) {
                try { await API.post(`/process/${jobId}/cancel`); } catch (e) {}
                resolve();
                return;
            }
            
            try {
                const status = await API.get(`/process/${jobId}/status`);
                
                // Update progress display
                const fileProgress = status.progress || 0;
                const overallProgress = ((state.batchProcessing.current - 1) / state.batchProcessing.total * 100) + 
                                        (fileProgress / state.batchProcessing.total);
                
                document.getElementById('progress-bar').style.width = `${overallProgress}%`;
                document.getElementById('progress-percent').textContent = `${Math.round(overallProgress)}%`;
                
                if (status.status === 'processing') {
                    setTimeout(poll, 500);
                } else if (status.status === 'completed') {
                    resolve();
                } else if (status.status === 'failed') {
                    reject(new Error(status.error || 'Processing failed'));
                } else if (status.status === 'cancelled') {
                    resolve();
                } else {
                    setTimeout(poll, 500);
                }
            } catch (err) {
                setTimeout(poll, 1000);
            }
        };
        poll();
    });
}

/**
 * Update batch progress display
 */
function updateBatchProgress(message) {
    if (!state.batchProcessing) return;
    
    const step = message || `Batch: ${state.batchProcessing.completed}/${state.batchProcessing.total} completed`;
    document.getElementById('progress-step').textContent = step;
    
    const overallProgress = (state.batchProcessing.completed / state.batchProcessing.total) * 100;
    document.getElementById('progress-bar').style.width = `${overallProgress}%`;
    document.getElementById('progress-percent').textContent = `${Math.round(overallProgress)}%`;
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

// ============== Thumbnails ==============
let studioDragState = null;
let studioTextEditor = null;

function loadThumbnailView() {
    if (!state.thumbnail.fonts.length) {
        loadThumbnailFonts();
    }
    if (!state.thumbnail.presets.length) {
        loadThumbnailPresets();
    }
    renderThumbnailImages();
    renderThumbnailVideos();
    renderThumbnailBackgrounds();
    updateThumbnailPreview();
    updateThumbnailGenerateButton();
    updateStudioCanvasDimensions();
}

function initThumbnailStudio() {
    initThumbnailSources();
    initThumbnailPresets();
    initThumbnailOverlay();
    initThumbnailOutputSettings();
    initStudioBuilder();
    initThumbnailGeneration();
    initThumbnailPresetModal();
}

function initThumbnailSources() {
    document.querySelectorAll('.thumb-source-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => setThumbnailSourceTab(btn.dataset.source));
    });

    const imageDrop = document.getElementById('thumb-image-drop');
    imageDrop.addEventListener('click', browseThumbnailImages);
    imageDrop.addEventListener('dragover', (e) => {
        e.preventDefault();
        imageDrop.classList.add('dragover');
    });
    imageDrop.addEventListener('dragleave', () => imageDrop.classList.remove('dragover'));
    imageDrop.addEventListener('drop', (e) => {
        e.preventDefault();
        imageDrop.classList.remove('dragover');

        const paths = [];
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
                if (path.match(/\.(jpg|jpeg|png|webp)$/i)) {
                    paths.push(path);
                }
            }
        }

        if (paths.length > 0) {
            addThumbnailImages(paths);
        } else {
            showToast('Drag not detected - opening file browser...', 'info');
            browseThumbnailImages();
        }
    });

    document.getElementById('thumb-browse-images').addEventListener('click', browseThumbnailImages);
    document.getElementById('thumb-browse-videos').addEventListener('click', browseThumbnailVideos);
    document.getElementById('thumb-clear-backgrounds').addEventListener('click', clearThumbnailBackgrounds);
}

function setThumbnailSourceTab(source) {
    document.querySelectorAll('.thumb-source-tabs .tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.source === source);
    });
    document.querySelectorAll('.thumb-source-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `thumb-source-${source}`);
    });
}

async function browseThumbnailImages() {
    try {
        const result = await API.post('/browse/images', {});
        if (result.cancelled) return;
        if (result.paths?.length) addThumbnailImages(result.paths);
    } catch (err) {
        showToast(`Failed to browse images: ${err.message}`, 'error');
    }
}

async function browseThumbnailVideos() {
    try {
        const result = await API.post('/browse/videos', {});
        if (result.cancelled) return;
        if (result.paths?.length) addThumbnailVideos(result.paths);
    } catch (err) {
        showToast(`Failed to browse videos: ${err.message}`, 'error');
    }
}

function addThumbnailImages(paths) {
    const added = [];
    for (const path of paths) {
        if (state.thumbnail.images.some(img => img.path.toLowerCase() === path.toLowerCase())) {
            continue;
        }
        const name = path.split(/[\\/]/).pop();
        state.thumbnail.images.push({ path, name });
        added.push({ path, name });
    }
    if (added.length) {
        added.forEach(item => addThumbnailBackground(item.path, item.name));
        renderThumbnailImages();
        renderThumbnailBackgrounds();
        updateThumbnailPreview();
        updateThumbnailGenerateButton();
    }
}

function addThumbnailVideos(paths) {
    let changed = false;
    for (const path of paths) {
        if (state.thumbnail.videos.some(v => v.path.toLowerCase() === path.toLowerCase())) {
            continue;
        }
        const name = path.split(/[\\/]/).pop();
        state.thumbnail.videos.push({ path, name });
        changed = true;
    }
    if (changed) {
        renderThumbnailVideos();
    }
}

function renderThumbnailImages() {
    const list = document.getElementById('thumb-image-list');
    if (!state.thumbnail.images.length) {
        list.innerHTML = '<div class="outputs-empty">No images added yet</div>';
        return;
    }
    list.innerHTML = state.thumbnail.images.map((img, index) => {
        const preview = getThumbnailPreviewUrl(img.path);
        return `
            <div class="thumb-source-item">
                <img class="thumb-source-thumb" src="${preview}" alt="${img.name}">
                <div class="thumb-source-name" title="${img.path}">${img.name}</div>
                <button class="file-remove" onclick="removeThumbnailImage(${index})" title="Remove">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;
    }).join('');
}

function removeThumbnailImage(index) {
    const removed = state.thumbnail.images.splice(index, 1)[0];
    if (removed) {
        removeThumbnailBackground(removed.path);
        renderThumbnailImages();
        renderThumbnailBackgrounds();
        updateThumbnailPreview();
        updateThumbnailGenerateButton();
    }
}

function removeThumbnailVideo(index) {
    const removed = state.thumbnail.videos.splice(index, 1)[0];
    if (!removed) return;
    const frames = state.thumbnail.framesByVideo[removed.path] || [];
    const framePaths = new Set(frames.map(f => f.path.toLowerCase()));
    state.thumbnail.backgrounds = state.thumbnail.backgrounds.filter(bg => !framePaths.has(bg.path.toLowerCase()));
    delete state.thumbnail.framesByVideo[removed.path];
    renderThumbnailVideos();
    renderThumbnailBackgrounds();
    updateThumbnailPreview();
    updateThumbnailGenerateButton();
}

function renderThumbnailVideos() {
    const list = document.getElementById('thumb-video-list');
    if (!state.thumbnail.videos.length) {
        list.innerHTML = '<div class="outputs-empty">No videos added yet</div>';
        return;
    }

    list.innerHTML = state.thumbnail.videos.map((video, index) => {
        const frames = state.thumbnail.framesByVideo[video.path] || [];
        return `
            <div class="thumb-video-item">
                <div class="thumb-video-header">
                    <div class="thumb-video-title" title="${video.path}">${video.name}</div>
                    <div class="output-actions">
                        <button class="btn btn-ghost btn-xs" onclick="removeThumbnailVideo(${index})">Remove</button>
                        <button class="btn btn-outline btn-xs" onclick="generateFramesForVideo(${index})">Generate Frames</button>
                    </div>
                </div>
                <div class="thumb-frame-strip" id="thumb-frames-${index}">
                    ${frames.length ? renderFrameStrip(frames, video.path) : '<div class="drop-hint">Generate a frame strip to pick thumbnails</div>'}
                </div>
            </div>
        `;
    }).join('');
}

function renderFrameStrip(frames, videoPath) {
    return frames.map((frame, idx) => {
        const preview = getThumbnailPreviewUrl(frame.path);
        const isSelected = state.thumbnail.backgrounds.some(bg => bg.path.toLowerCase() === frame.path.toLowerCase());
        const label = frame.timestamp_formatted || '';
        return `
            <div class="thumb-frame ${isSelected ? 'selected' : ''}" onclick='toggleThumbnailFrame(${JSON.stringify(videoPath)}, ${idx})'>
                <img src="${preview}" alt="Frame ${idx + 1}">
                <div class="thumb-frame-label">${label}</div>
            </div>
        `;
    }).join('');
}

async function generateFramesForVideo(index) {
    const video = state.thumbnail.videos[index];
    if (!video) return;

    const strip = document.getElementById(`thumb-frames-${index}`);
    strip.innerHTML = Array(6).fill('<div class="thumb-frame skeleton"></div>').join('');

    try {
        const frameCount = parseInt(document.getElementById('thumb-frame-count').value) || 12;
        const frameWidth = parseInt(document.getElementById('thumb-frame-width').value) || 320;
        const result = await API.post('/thumbnails/frames', {
            video_path: video.path,
            frame_count: frameCount,
            scale_width: frameWidth
        });
        state.thumbnail.framesByVideo[video.path] = result.frames || [];
        renderThumbnailVideos();
    } catch (err) {
        showToast(`Failed to extract frames: ${err.message}`, 'error');
        strip.innerHTML = '<div class="drop-hint">Failed to load frames</div>';
    }
}

function toggleThumbnailFrame(videoPath, frameIndex) {
    const frames = state.thumbnail.framesByVideo[videoPath] || [];
    const frame = frames[frameIndex];
    if (!frame) return;

    const exists = state.thumbnail.backgrounds.some(bg => bg.path.toLowerCase() === frame.path.toLowerCase());
    if (exists) {
        removeThumbnailBackground(frame.path);
    } else {
        const base = PathBasename(videoPath).replace(/\.[^/.]+$/, '');
        const name = `${base}_frame_${String(frameIndex + 1).padStart(2, '0')}`;
        addThumbnailBackground(frame.path, name);
    }
    renderThumbnailBackgrounds();
    renderThumbnailVideos();
    updateThumbnailPreview();
    updateThumbnailGenerateButton();
}

function addThumbnailBackground(path, name) {
    if (state.thumbnail.backgrounds.some(bg => bg.path.toLowerCase() === path.toLowerCase())) {
        return;
    }
    state.thumbnail.backgrounds.push({ path, name: name || PathBasename(path) });
}

function removeThumbnailBackground(path) {
    state.thumbnail.backgrounds = state.thumbnail.backgrounds.filter(bg => bg.path.toLowerCase() !== path.toLowerCase());
    state.thumbnail.images = state.thumbnail.images.filter(img => img.path.toLowerCase() !== path.toLowerCase());
}

function clearThumbnailBackgrounds() {
    state.thumbnail.backgrounds = [];
    state.thumbnail.images = [];
    renderThumbnailBackgrounds();
    renderThumbnailImages();
    renderThumbnailVideos();
    updateThumbnailPreview();
    updateThumbnailGenerateButton();
}

function renderThumbnailBackgrounds() {
    const list = document.getElementById('thumb-backgrounds-list');
    const summary = document.getElementById('thumb-backgrounds-summary');

    if (!state.thumbnail.backgrounds.length) {
        list.innerHTML = '<div class="outputs-empty">No backgrounds selected</div>';
        summary.textContent = '';
        return;
    }

    list.innerHTML = state.thumbnail.backgrounds.map(bg => {
        const preview = getThumbnailPreviewUrl(bg.path);
        return `
            <div class="thumb-background-card">
                <img src="${preview}" alt="${bg.name}">
                <div class="thumb-background-meta" title="${bg.path}">${bg.name}</div>
                <button class="thumb-background-remove" onclick='removeThumbnailBackgroundAction(${JSON.stringify(bg.path)})'>×</button>
            </div>
        `;
    }).join('');

    summary.textContent = `${state.thumbnail.backgrounds.length} background${state.thumbnail.backgrounds.length > 1 ? 's' : ''} selected`;
}

function removeThumbnailBackgroundAction(path) {
    removeThumbnailBackground(path);
    renderThumbnailBackgrounds();
    renderThumbnailVideos();
    updateThumbnailPreview();
    updateThumbnailGenerateButton();
}

function updateThumbnailPreview() {
    const canvas = document.getElementById('studio-canvas');
    const empty = document.getElementById('studio-empty');
    if (!canvas || !empty) return;

    if (state.thumbnail.backgrounds.length) {
        const bg = state.thumbnail.backgrounds[0];
        canvas.style.backgroundImage = `url('${getThumbnailPreviewUrl(bg.path)}')`;
        empty.style.display = 'none';
    } else {
        canvas.style.backgroundImage = 'none';
        empty.style.display = 'flex';
    }
}

function updateThumbnailGenerateButton() {
    const btn = document.getElementById('thumb-generate-btn');
    btn.disabled = state.thumbnail.backgrounds.length === 0;
}

function isValidHexColor(value) {
    return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(value || '');
}

function getNumberingElement() {
    return state.thumbnail.studio.elements.find(el => el.type === 'numbering');
}

function toggleNumberingElement(enabled) {
    const existing = getNumberingElement();
    if (enabled) {
        if (!existing) {
            const element = {
                id: `num-${Date.now()}`,
                type: 'numbering',
                text: '01',
                x: 980,
                y: 520,
                width: 180,
                height: 120,
                fontFamily: 'Inter',
                fontPath: document.getElementById('thumb-number-font').value || '',
                fontSize: parseInt(document.getElementById('thumb-number-size').value) || 64,
                fill: document.getElementById('thumb-number-fill').value || '#ffffff',
                fillEnabled: document.getElementById('thumb-number-fill-enabled').checked,
                stroke: document.getElementById('thumb-number-stroke').value || '#000000',
                strokeWidth: parseInt(document.getElementById('thumb-number-stroke-width').value) || 4,
                strokeEnabled: document.getElementById('thumb-number-stroke-enabled').checked,
                align: 'left',
                opacity: 1,
                lineHeight: parseFloat(document.getElementById('thumb-number-line-height').value) || 1.1,
                letterSpacing: parseFloat(document.getElementById('thumb-number-letter-spacing').value) || 0
            };
            state.thumbnail.studio.elements.push(element);
            selectStudioElement(element.id);
            document.getElementById('thumb-number-position').value = 'custom';
        }
    } else if (existing) {
        state.thumbnail.studio.elements = state.thumbnail.studio.elements.filter(el => el.type !== 'numbering');
        if (state.thumbnail.studio.selectedId === existing.id) {
            state.thumbnail.studio.selectedId = null;
        }
    }
    renderStudioElements();
    toggleThumbnailOverlayMode();
}

function syncNumberingElementFromForm() {
    const element = getNumberingElement();
    if (!element) return;

    const fillEnabled = document.getElementById('thumb-number-fill-enabled').checked;
    const strokeEnabled = document.getElementById('thumb-number-stroke-enabled').checked;
    document.getElementById('thumb-number-fill').disabled = !fillEnabled;
    document.getElementById('thumb-number-fill-picker').disabled = !fillEnabled;
    document.getElementById('thumb-number-stroke').disabled = !strokeEnabled;
    document.getElementById('thumb-number-stroke-picker').disabled = !strokeEnabled;

    element.fontPath = document.getElementById('thumb-number-font').value || '';
    element.fontFamily = getFontNameByPath(element.fontPath) || 'Inter';
    element.fontSize = parseInt(document.getElementById('thumb-number-size').value) || element.fontSize;
    element.lineHeight = parseFloat(document.getElementById('thumb-number-line-height').value) || element.lineHeight || 1.1;
    element.letterSpacing = parseFloat(document.getElementById('thumb-number-letter-spacing').value) || element.letterSpacing || 0;
    element.fill = document.getElementById('thumb-number-fill').value || element.fill;
    element.fillEnabled = fillEnabled;
    element.stroke = document.getElementById('thumb-number-stroke').value || element.stroke;
    element.strokeWidth = parseInt(document.getElementById('thumb-number-stroke-width').value) || element.strokeWidth;
    element.strokeEnabled = strokeEnabled;
    element.text = '01';

    renderStudioElements();
}

function applyNumberingPositionPreset(position) {
    const element = getNumberingElement();
    if (!element || position === 'custom') return;

    const margin = parseInt(document.getElementById('thumb-number-margin').value) || 24;
    const canvasW = state.thumbnail.studio.canvasWidth;
    const canvasH = state.thumbnail.studio.canvasHeight;

    if (position === 'top-left') {
        element.x = margin;
        element.y = margin;
    } else if (position === 'top-right') {
        element.x = Math.max(0, canvasW - element.width - margin);
        element.y = margin;
    } else if (position === 'bottom-left') {
        element.x = margin;
        element.y = Math.max(0, canvasH - element.height - margin);
    } else if (position === 'center') {
        element.x = Math.max(0, (canvasW - element.width) / 2);
        element.y = Math.max(0, (canvasH - element.height) / 2);
    } else {
        element.x = Math.max(0, canvasW - element.width - margin);
        element.y = Math.max(0, canvasH - element.height - margin);
    }

    renderStudioElements();
}

function initThumbnailOverlay() {
    document.querySelectorAll('input[name="thumb-overlay-mode"]').forEach(input => {
        input.addEventListener('change', () => {
            state.thumbnail.overlayMode = input.value;
            toggleThumbnailOverlayMode();
        });
    });

    document.getElementById('thumb-browse-overlay').addEventListener('click', browseThumbnailOverlayImage);
    document.getElementById('thumb-overlay-opacity').addEventListener('input', () => {
        state.thumbnail.overlayImage.opacity = (parseInt(document.getElementById('thumb-overlay-opacity').value) || 100) / 100;
    });
    document.getElementById('thumb-overlay-mode').addEventListener('change', (e) => {
        state.thumbnail.overlayImage.mode = e.target.value;
    });

    toggleThumbnailOverlayMode();
}

function initThumbnailPresets() {
    document.getElementById('thumb-preset-select').addEventListener('change', (e) => {
        const presetId = e.target.value || null;
        if (!presetId) {
            state.thumbnail.selectedPresetId = null;
            updateThumbnailPresetButtons();
            return;
        }
        const preset = state.thumbnail.presets.find(p => p.id === presetId);
        if (preset) applyThumbnailPreset(preset);
    });

    document.getElementById('thumb-save-preset').addEventListener('click', openThumbnailPresetModal);
    document.getElementById('thumb-update-preset').addEventListener('click', updateThumbnailPreset);
    document.getElementById('thumb-delete-preset').addEventListener('click', deleteThumbnailPreset);
}

async function loadThumbnailPresets() {
    try {
        const presets = await API.get('/thumbnails/presets');
        state.thumbnail.presets = presets || [];
        renderThumbnailPresets();
    } catch (err) {
        showToast('Failed to load thumbnail presets', 'error');
    }
}

function renderThumbnailPresets() {
    const select = document.getElementById('thumb-preset-select');
    select.innerHTML = '<option value="">Load Preset...</option>';
    state.thumbnail.presets.forEach(preset => {
        select.innerHTML += `<option value="${preset.id}">${preset.name}</option>`;
    });
    updateThumbnailPresetButtons();
}

function applyThumbnailPreset(preset) {
    state.thumbnail.selectedPresetId = preset.id;
    const settings = preset.settings || {};

    if (settings.resize) {
        document.getElementById('thumb-width').value = settings.resize.width || 1280;
        document.getElementById('thumb-height').value = settings.resize.height || 720;
        document.getElementById('thumb-fit-mode').value = settings.resize.fit_mode || 'cover';
        document.getElementById('thumb-bg-color').value = settings.resize.background || '#000000';
        document.getElementById('thumb-bg-color-picker').value = settings.resize.background || '#000000';
        updateStudioCanvasDimensions();
    }

    if (settings.output_format) {
        document.getElementById('thumb-output-format').value = settings.output_format;
    }
    if (settings.filename_suffix) {
        document.getElementById('thumb-filename-suffix').value = settings.filename_suffix;
    }
    document.getElementById('thumb-output-dir').value = settings.output_dir || '';
    document.getElementById('thumb-strip-metadata').checked = settings.strip_metadata !== false;

    if (settings.optimize) {
        document.getElementById('thumb-optimize').checked = settings.optimize.enabled !== false;
        document.getElementById('thumb-max-bytes').value = settings.optimize.max_bytes || 2097152;
    }
    document.getElementById('thumb-max-bytes-group').style.display =
        document.getElementById('thumb-optimize').checked ? 'block' : 'none';

    if (settings.overlay) {
        applyOverlaySettings(settings.overlay);
    }

    if (settings.numbering) {
        document.getElementById('thumb-numbering').checked = settings.numbering.enabled === true;
        document.getElementById('thumb-numbering-settings').style.display = settings.numbering.enabled ? 'block' : 'none';
        document.getElementById('thumb-number-start').value = settings.numbering.start || 1;
        document.getElementById('thumb-number-margin').value = settings.numbering.margin || 24;
        document.getElementById('thumb-number-position').value = settings.numbering.position || 'bottom-right';
        document.getElementById('thumb-number-size').value = settings.numbering.font_size || 0;
        document.getElementById('thumb-number-line-height').value = settings.numbering.line_height || 1.1;
        document.getElementById('thumb-number-letter-spacing').value = settings.numbering.letter_spacing || 0;
        document.getElementById('thumb-number-fill').value = settings.numbering.fill || '#ffffff';
        document.getElementById('thumb-number-fill-picker').value = settings.numbering.fill || '#ffffff';
        document.getElementById('thumb-number-fill-enabled').checked = settings.numbering.fill_enabled !== false;
        document.getElementById('thumb-number-stroke').value = settings.numbering.stroke_fill || '#000000';
        document.getElementById('thumb-number-stroke-picker').value = settings.numbering.stroke_fill || '#000000';
        document.getElementById('thumb-number-stroke-enabled').checked = settings.numbering.stroke_enabled !== false;
        document.getElementById('thumb-number-stroke-width').value = settings.numbering.stroke_width || 4;
        setFontPickerSelection('thumb-number-font', settings.numbering.font_path, 'Auto');

        toggleNumberingElement(settings.numbering.enabled === true);
        const numberElement = getNumberingElement();
        if (numberElement) {
            numberElement.x = settings.numbering.x ?? numberElement.x;
            numberElement.y = settings.numbering.y ?? numberElement.y;
            if (settings.numbering.element?.width) numberElement.width = settings.numbering.element.width;
            if (settings.numbering.element?.height) numberElement.height = settings.numbering.element.height;
            numberElement.lineHeight = settings.numbering.line_height ?? numberElement.lineHeight;
            numberElement.letterSpacing = settings.numbering.letter_spacing ?? numberElement.letterSpacing;
            syncNumberingElementFromForm();
        }
    }

    updateThumbnailPresetButtons();
}

function applyOverlaySettings(overlay) {
    if (!overlay || !overlay.type) return;
    state.thumbnail.overlayMode = overlay.type;
    const radio = document.querySelector(`input[name="thumb-overlay-mode"][value="${overlay.type}"]`);
    if (radio) radio.checked = true;

    if (overlay.type === 'image') {
        state.thumbnail.overlayImage.path = overlay.path || null;
        state.thumbnail.overlayImage.mode = overlay.mode || 'scale_to_canvas';
        state.thumbnail.overlayImage.opacity = overlay.opacity || 1;
        document.getElementById('thumb-overlay-mode').value = state.thumbnail.overlayImage.mode;
        document.getElementById('thumb-overlay-opacity').value = Math.round(state.thumbnail.overlayImage.opacity * 100);
        if (state.thumbnail.overlayImage.path) {
            const fileName = PathBasename(state.thumbnail.overlayImage.path);
            const content = document.getElementById('thumb-overlay-asset');
            const settings = document.getElementById('thumb-overlay-settings');
            content.innerHTML = `
                <div class="asset-uploaded">
                    <span class="asset-filename" title="${state.thumbnail.overlayImage.path}">${fileName}</span>
                    <button type="button" class="asset-remove" onclick="removeThumbnailOverlayImage()">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            `;
            settings.style.display = 'flex';
        }
    } else if (overlay.type === 'studio') {
        state.thumbnail.studio.canvasWidth = overlay.studio?.width || state.thumbnail.studio.canvasWidth;
        state.thumbnail.studio.canvasHeight = overlay.studio?.height || state.thumbnail.studio.canvasHeight;
        state.thumbnail.studio.elements = (overlay.studio?.elements || []).map(el => ({ ...el }));
        document.getElementById('thumb-width').value = state.thumbnail.studio.canvasWidth;
        document.getElementById('thumb-height').value = state.thumbnail.studio.canvasHeight;
        updateStudioCanvasDimensions();
        renderStudioElements();
    }

    toggleThumbnailOverlayMode();
}

function updateThumbnailPresetButtons() {
    const hasPreset = !!state.thumbnail.selectedPresetId;
    document.getElementById('thumb-update-preset').disabled = !hasPreset;
    document.getElementById('thumb-delete-preset').disabled = !hasPreset;
}

function initThumbnailPresetModal() {
    document.getElementById('thumb-preset-modal-close').addEventListener('click', closeThumbnailPresetModal);
    document.getElementById('thumb-preset-modal-cancel').addEventListener('click', closeThumbnailPresetModal);
    document.getElementById('thumb-preset-modal-save').addEventListener('click', saveThumbnailPreset);
    document.querySelector('#thumb-preset-modal .modal-backdrop').addEventListener('click', closeThumbnailPresetModal);
}

function openThumbnailPresetModal() {
    document.getElementById('thumb-preset-name').value = '';
    document.getElementById('thumb-preset-modal').classList.add('open');
}

function closeThumbnailPresetModal() {
    document.getElementById('thumb-preset-modal').classList.remove('open');
}

function buildThumbnailPresetSettings() {
    const payload = buildThumbnailPayload();
    const settings = { ...payload };
    delete settings.backgrounds;

    const numberElement = getNumberingElement();
    if (settings.numbering?.enabled && numberElement) {
        settings.numbering.element = {
            width: numberElement.width,
            height: numberElement.height
        };
    }
    return settings;
}

async function saveThumbnailPreset() {
    const name = document.getElementById('thumb-preset-name').value.trim();
    if (!name) {
        showToast('Enter a preset name', 'error');
        return;
    }
    try {
        const settings = buildThumbnailPresetSettings();
        const preset = await API.post('/thumbnails/presets', { name, settings });
        state.thumbnail.presets.push(preset);
        renderThumbnailPresets();
        document.getElementById('thumb-preset-select').value = preset.id;
        state.thumbnail.selectedPresetId = preset.id;
        updateThumbnailPresetButtons();
        closeThumbnailPresetModal();
        showToast('Thumbnail preset saved', 'success');
    } catch (err) {
        showToast(`Failed to save preset: ${err.message}`, 'error');
    }
}

async function updateThumbnailPreset() {
    if (!state.thumbnail.selectedPresetId) return;
    try {
        const settings = buildThumbnailPresetSettings();
        const preset = await API.put(`/thumbnails/presets/${state.thumbnail.selectedPresetId}`, { settings });
        const idx = state.thumbnail.presets.findIndex(p => p.id === preset.id);
        if (idx >= 0) state.thumbnail.presets[idx] = preset;
        renderThumbnailPresets();
        document.getElementById('thumb-preset-select').value = preset.id;
        showToast('Thumbnail preset updated', 'success');
    } catch (err) {
        showToast(`Failed to update preset: ${err.message}`, 'error');
    }
}

async function deleteThumbnailPreset() {
    if (!state.thumbnail.selectedPresetId) return;
    if (!confirm('Delete this thumbnail preset?')) return;
    try {
        await API.delete(`/thumbnails/presets/${state.thumbnail.selectedPresetId}`);
        state.thumbnail.presets = state.thumbnail.presets.filter(p => p.id !== state.thumbnail.selectedPresetId);
        state.thumbnail.selectedPresetId = null;
        renderThumbnailPresets();
        document.getElementById('thumb-preset-select').value = '';
        updateThumbnailPresetButtons();
        showToast('Thumbnail preset deleted', 'success');
    } catch (err) {
        showToast(`Failed to delete preset: ${err.message}`, 'error');
    }
}

function toggleThumbnailOverlayMode() {
    const imagePanel = document.getElementById('thumb-overlay-image');
    const studioCard = document.querySelector('.studio-card');
    const mode = state.thumbnail.overlayMode;
    const numberingEnabled = document.getElementById('thumb-numbering')?.checked;
    const allowStudio = mode === 'studio' || numberingEnabled;

    imagePanel.style.display = mode === 'image' ? 'block' : 'none';
    studioCard.style.opacity = allowStudio ? '1' : '0.4';
    studioCard.style.pointerEvents = allowStudio ? 'auto' : 'none';
}

async function browseThumbnailOverlayImage() {
    try {
        const result = await API.post('/browse/images', {});
        if (result.cancelled) return;
        if (!result.paths?.length) return;

        const filePath = result.paths[0];
        const fileName = PathBasename(filePath);
        state.thumbnail.overlayImage.path = filePath;

        const content = document.getElementById('thumb-overlay-asset');
        const settings = document.getElementById('thumb-overlay-settings');
        content.innerHTML = `
            <div class="asset-uploaded">
                <span class="asset-filename" title="${filePath}">${fileName}</span>
                <button type="button" class="asset-remove" onclick="removeThumbnailOverlayImage()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;
        settings.style.display = 'flex';
    } catch (err) {
        showToast(`Failed to browse overlay: ${err.message}`, 'error');
    }
}

function removeThumbnailOverlayImage() {
    state.thumbnail.overlayImage.path = null;
    const content = document.getElementById('thumb-overlay-asset');
    const settings = document.getElementById('thumb-overlay-settings');
    content.innerHTML = `
        <div class="asset-empty">
            <button type="button" class="btn btn-outline btn-sm" id="thumb-browse-overlay">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                Browse Overlay Image
            </button>
        </div>
    `;
    settings.style.display = 'none';
    document.getElementById('thumb-browse-overlay').addEventListener('click', browseThumbnailOverlayImage);
}

async function loadThumbnailFonts() {
    try {
        const fonts = await API.get('/thumbnails/fonts');
        state.thumbnail.fonts = fonts || [];
        populateFontSelects();
    } catch (err) {
        showToast('Failed to load fonts', 'error');
    }
}

// ============== Font Modal ==============
let fontModalState = {
    targetId: null,
    defaultLabel: 'Default',
    selectedFontPath: '',
    favorites: JSON.parse(localStorage.getItem('editflow_favorite_fonts') || '[]'),
    filter: 'all'
};

const fontFaceCache = new Map();

function hashString(value) {
    let hash = 0;
    for (let i = 0; i < value.length; i += 1) {
        hash = ((hash << 5) - hash) + value.charCodeAt(i);
        hash |= 0;
    }
    return Math.abs(hash);
}

function getFontCssFamily(font) {
    if (!font || !font.path) return '';
    if (font.cssFamily) return font.cssFamily;
    const id = hashString(font.path);
    font.cssFamily = `editflow-font-${id}`;
    return font.cssFamily;
}

function ensureFontLoaded(font) {
    if (!font || !font.path) return Promise.resolve(null);
    if (!window.FontFace) return Promise.resolve(null);

    if (fontFaceCache.has(font.path)) {
        return fontFaceCache.get(font.path);
    }

    const family = getFontCssFamily(font);
    const url = `/api/thumbnails/font?path=${encodeURIComponent(font.path)}`;
    const fontFace = new FontFace(family, `url(${url})`);
    const promise = fontFace.load()
        .then((loaded) => {
            document.fonts.add(loaded);
            return family;
        })
        .catch(() => null);

    fontFaceCache.set(font.path, promise);
    return promise;
}

function populateFontSelects() {
    // This is now just called to re-render if needed after fonts are loaded
    // The click handlers use event delegation on document
}

function initFontSelectors() {
    // Use event delegation on document body for font selector buttons
    // This works even for buttons that are inside hidden sections
    document.body.addEventListener('click', (e) => {
        const btn = e.target.closest('.font-selector-btn');
        if (!btn) return;
        
        e.preventDefault();
        e.stopPropagation();
        
        const targetId = btn.dataset.target;
        if (!targetId) return;
        
        const defaultLabel = targetId === 'thumb-number-font' ? 'Auto' : 'Default';
        
        // Make sure fonts are loaded first
        if (!state.thumbnail.fonts.length) {
            loadThumbnailFonts().then(() => {
                openFontModal(targetId, defaultLabel);
            });
        } else {
            openFontModal(targetId, defaultLabel);
        }
    });
    
    // Initialize modal event listeners
    initFontModal();
}

function initFontModal() {
    const modal = document.getElementById('font-modal');
    if (!modal) return;
    
    // Skip if already initialized
    if (modal.dataset.init === 'true') return;
    modal.dataset.init = 'true';
    
    const closeBtn = document.getElementById('font-modal-close');
    const cancelBtn = document.getElementById('font-modal-cancel');
    const selectBtn = document.getElementById('font-modal-select');
    const searchInput = document.getElementById('font-modal-search');
    const tabs = document.querySelectorAll('.font-modal-tab');
    const listEl = document.getElementById('font-modal-list');
    
    closeBtn.addEventListener('click', closeFontModal);
    cancelBtn.addEventListener('click', closeFontModal);
    modal.querySelector('.modal-backdrop').addEventListener('click', closeFontModal);
    
    selectBtn.addEventListener('click', () => {
        applyFontSelection();
        closeFontModal();
    });
    
    searchInput.addEventListener('input', () => renderFontList());
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            fontModalState.filter = tab.dataset.filter;
            renderFontList();
        });
    });
    
    // Lazy loading on scroll
    listEl.addEventListener('scroll', () => {
        if (listEl.scrollTop + listEl.clientHeight >= listEl.scrollHeight - 50) {
            renderMoreFonts();
        }
    });
}

function openFontModal(targetId, defaultLabel) {
    const modal = document.getElementById('font-modal');
    const hiddenInput = document.getElementById(targetId);
    
    fontModalState.targetId = targetId;
    fontModalState.defaultLabel = defaultLabel;
    fontModalState.selectedFontPath = hiddenInput?.value || '';
    fontModalState.filter = 'all';
    fontModalState.offset = 0;
    
    // Reset UI
    document.getElementById('font-modal-search').value = '';
    document.querySelectorAll('.font-modal-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.filter === 'all');
    });
    
    renderFontList();
    updateFontModalPreview();
    modal.classList.add('open');
    
    // Focus search
    setTimeout(() => document.getElementById('font-modal-search').focus(), 100);
}

function closeFontModal() {
    document.getElementById('font-modal').classList.remove('open');
    fontModalState.targetId = null;
}

function renderFontList() {
    const listEl = document.getElementById('font-modal-list');
    const emptyEl = document.getElementById('font-modal-empty');
    const searchTerm = document.getElementById('font-modal-search').value.trim().toLowerCase();
    
    // Build font list with default option first
    const allFonts = [
        { name: fontModalState.defaultLabel, path: '' },
        ...state.thumbnail.fonts
    ];
    
    // Filter fonts
    let filtered = allFonts;
    
    if (fontModalState.filter === 'favorites') {
        filtered = allFonts.filter(f => f.path === '' || fontModalState.favorites.includes(f.path));
    }
    
    if (searchTerm) {
        filtered = filtered.filter(f => f.name.toLowerCase().includes(searchTerm));
    }
    
    fontModalState.filteredFonts = filtered;
    fontModalState.offset = 0;
    
    listEl.innerHTML = '';
    
    if (filtered.length === 0) {
        emptyEl.style.display = 'flex';
        return;
    }
    
    emptyEl.style.display = 'none';
    renderMoreFonts();
}

function renderMoreFonts() {
    const listEl = document.getElementById('font-modal-list');
    const pageSize = 30;
    const start = fontModalState.offset || 0;
    const fonts = fontModalState.filteredFonts || [];
    const slice = fonts.slice(start, start + pageSize);
    
    slice.forEach(font => {
        const isFavorite = fontModalState.favorites.includes(font.path);
        const isSelected = fontModalState.selectedFontPath === font.path;
        const isDefault = font.path === '';
        const fallbackFamily = font.name || 'Inter';
        const cssFamily = getFontCssFamily(font) || fallbackFamily;
        
        const item = document.createElement('div');
        item.className = `font-modal-item ${isSelected ? 'active' : ''}`;
        item.dataset.fontPath = font.path;
        
        item.innerHTML = `
            ${!isDefault ? `
                <button type="button" class="font-modal-item-fav ${isFavorite ? 'favorited' : ''}" data-path="${font.path}" title="${isFavorite ? 'Remove from favorites' : 'Add to favorites'}">
                    <svg viewBox="0 0 16 16" fill="${isFavorite ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="1.5">
                        <path d="M8 1.5l2 4.5 5 .5-3.5 3.5 1 5-4.5-2.5-4.5 2.5 1-5L1 6.5l5-.5z"/>
                    </svg>
                </button>
            ` : '<div style="width: 20px;"></div>'}
            <div class="font-modal-item-info">
                <span class="font-modal-item-name">${font.name}</span>
                <span class="font-modal-item-preview" style="font-family: '${cssFamily}', Inter, sans-serif;">The quick brown fox jumps</span>
            </div>
        `;

        const previewEl = item.querySelector('.font-modal-item-preview');
        if (!isDefault && previewEl) {
            ensureFontLoaded(font).then((loadedFamily) => {
                if (loadedFamily) {
                    previewEl.style.fontFamily = `'${loadedFamily}', Inter, sans-serif`;
                }
            });
        }
        
        // Click to select
        item.addEventListener('click', (e) => {
            if (e.target.closest('.font-modal-item-fav')) return;
            
            listEl.querySelectorAll('.font-modal-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            fontModalState.selectedFontPath = font.path;
            updateFontModalPreview(font);
        });
        
        // Double-click to select and close
        item.addEventListener('dblclick', (e) => {
            if (e.target.closest('.font-modal-item-fav')) return;
            fontModalState.selectedFontPath = font.path;
            applyFontSelection();
            closeFontModal();
        });
        
        // Favorite button
        const favBtn = item.querySelector('.font-modal-item-fav');
        if (favBtn) {
            favBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleFontFavorite(font.path, favBtn);
            });
        }
        
        listEl.appendChild(item);
    });
    
    fontModalState.offset = start + slice.length;
}

function toggleFontFavorite(fontPath, btn) {
    const idx = fontModalState.favorites.indexOf(fontPath);
    if (idx >= 0) {
        fontModalState.favorites.splice(idx, 1);
        btn.classList.remove('favorited');
        btn.querySelector('svg').setAttribute('fill', 'none');
        btn.title = 'Add to favorites';
    } else {
        fontModalState.favorites.push(fontPath);
        btn.classList.add('favorited');
        btn.querySelector('svg').setAttribute('fill', 'currentColor');
        btn.title = 'Remove from favorites';
    }
    localStorage.setItem('editflow_favorite_fonts', JSON.stringify(fontModalState.favorites));
    
    // Re-render if in favorites tab
    if (fontModalState.filter === 'favorites') {
        renderFontList();
    }
}

function updateFontModalPreview(font) {
    const previewEl = document.getElementById('font-modal-preview');
    if (font) {
        const cssFamily = getFontCssFamily(font) || font.name || 'Inter';
        previewEl.style.fontFamily = `'${cssFamily}', Inter, sans-serif`;
        if (font.path) {
            ensureFontLoaded(font).then((loadedFamily) => {
                if (loadedFamily) {
                    previewEl.style.fontFamily = `'${loadedFamily}', Inter, sans-serif`;
                }
            });
        }
    } else {
        const selectedFont = state.thumbnail.fonts.find(f => f.path === fontModalState.selectedFontPath);
        if (selectedFont) {
            const cssFamily = getFontCssFamily(selectedFont) || selectedFont.name || 'Inter';
            previewEl.style.fontFamily = `'${cssFamily}', Inter, sans-serif`;
            ensureFontLoaded(selectedFont).then((loadedFamily) => {
                if (loadedFamily) {
                    previewEl.style.fontFamily = `'${loadedFamily}', Inter, sans-serif`;
                }
            });
        } else {
            previewEl.style.fontFamily = 'Inter, sans-serif';
        }
    }
}

function applyFontSelection() {
    const targetId = fontModalState.targetId;
    if (!targetId) return;
    
    const hiddenInput = document.getElementById(targetId);
    const selectedEl = document.getElementById(`${targetId}-selected`);
    
    if (hiddenInput) {
        hiddenInput.value = fontModalState.selectedFontPath;
    }
    
    if (selectedEl) {
        const fontName = getFontNameByPath(fontModalState.selectedFontPath);
        selectedEl.textContent = fontName || fontModalState.defaultLabel;
    }
    
    // Trigger update
    if (targetId === 'thumb-number-font') {
        syncNumberingElementFromForm();
    } else if (targetId === 'studio-font') {
        updateStudioFromInputs();
    }
}

function getFontNameByPath(path) {
    if (!path) return '';
    const match = state.thumbnail.fonts.find(f => f.path === path);
    return match?.name || '';
}

function setFontPickerSelection(targetId, fontPath, defaultLabel) {
    const hiddenInput = document.getElementById(targetId);
    const selectedEl = document.getElementById(`${targetId}-selected`);
    if (!hiddenInput || !selectedEl) return;
    hiddenInput.value = fontPath || '';
    selectedEl.textContent = getFontNameByPath(fontPath) || defaultLabel;
}


function initThumbnailOutputSettings() {
    document.getElementById('thumb-output-dir-browse').addEventListener('click', async () => {
        try {
            const result = await API.post('/browse/folder', {});
            if (!result.cancelled && result.path) {
                document.getElementById('thumb-output-dir').value = result.path;
            }
        } catch (err) {
            showToast('Failed to browse folder', 'error');
        }
    });

    document.getElementById('thumb-numbering').addEventListener('change', (e) => {
        document.getElementById('thumb-numbering-settings').style.display = e.target.checked ? 'block' : 'none';
        toggleNumberingElement(e.target.checked);
    });

    document.getElementById('thumb-bg-color-picker').addEventListener('input', (e) => {
        document.getElementById('thumb-bg-color').value = e.target.value;
    });
    document.getElementById('thumb-bg-color').addEventListener('input', (e) => {
        if (isValidHexColor(e.target.value)) {
            document.getElementById('thumb-bg-color-picker').value = e.target.value;
        }
    });

    document.getElementById('thumb-number-fill-picker').addEventListener('input', (e) => {
        document.getElementById('thumb-number-fill').value = e.target.value;
        syncNumberingElementFromForm();
    });
    document.getElementById('thumb-number-stroke-picker').addEventListener('input', (e) => {
        document.getElementById('thumb-number-stroke').value = e.target.value;
        syncNumberingElementFromForm();
    });
    document.getElementById('thumb-number-fill').addEventListener('input', (e) => {
        if (isValidHexColor(e.target.value)) {
            document.getElementById('thumb-number-fill-picker').value = e.target.value;
        }
        syncNumberingElementFromForm();
    });
    document.getElementById('thumb-number-stroke').addEventListener('input', (e) => {
        if (isValidHexColor(e.target.value)) {
            document.getElementById('thumb-number-stroke-picker').value = e.target.value;
        }
        syncNumberingElementFromForm();
    });
    document.getElementById('thumb-number-fill-enabled').addEventListener('change', syncNumberingElementFromForm);
    document.getElementById('thumb-number-stroke-enabled').addEventListener('change', syncNumberingElementFromForm);
    ['thumb-number-size', 'thumb-number-stroke-width', 'thumb-number-line-height', 'thumb-number-letter-spacing', 'thumb-number-font'].forEach(id => {
        document.getElementById(id).addEventListener('input', syncNumberingElementFromForm);
    });

    document.getElementById('thumb-number-position').addEventListener('change', (e) => {
        applyNumberingPositionPreset(e.target.value);
    });

    document.getElementById('thumb-optimize').addEventListener('change', (e) => {
        document.getElementById('thumb-max-bytes-group').style.display = e.target.checked ? 'block' : 'none';
    });

    document.getElementById('thumb-max-bytes-group').style.display =
        document.getElementById('thumb-optimize').checked ? 'block' : 'none';
    document.getElementById('thumb-numbering-settings').style.display =
        document.getElementById('thumb-numbering').checked ? 'block' : 'none';
    toggleNumberingElement(document.getElementById('thumb-numbering').checked);

    ['thumb-width', 'thumb-height'].forEach(id => {
        document.getElementById(id).addEventListener('input', updateStudioCanvasDimensions);
    });
}

function initStudioBuilder() {
    document.getElementById('studio-add-text').addEventListener('click', addStudioTextElement);
    document.getElementById('studio-add-image').addEventListener('click', addStudioImageElement);
    document.getElementById('studio-delete').addEventListener('click', deleteSelectedStudioElement);
    document.getElementById('studio-duplicate').addEventListener('click', duplicateSelectedStudioElement);

    document.querySelectorAll('.studio-mode-btn').forEach(btn => {
        btn.addEventListener('click', () => setStudioMode(btn.dataset.mode));
    });

    ['studio-text', 'studio-font', 'studio-font-size', 'studio-text-fill', 'studio-text-stroke', 'studio-text-stroke-width', 'studio-text-align', 'studio-line-height', 'studio-letter-spacing', 'studio-text-opacity'].forEach(id => {
        document.getElementById(id).addEventListener('input', updateStudioFromInputs);
    });

    document.getElementById('studio-text-fill-picker').addEventListener('input', (e) => {
        document.getElementById('studio-text-fill').value = e.target.value;
        updateStudioFromInputs();
    });
    document.getElementById('studio-text-stroke-picker').addEventListener('input', (e) => {
        document.getElementById('studio-text-stroke').value = e.target.value;
        updateStudioFromInputs();
    });
    document.getElementById('studio-fill-enabled').addEventListener('change', updateStudioFromInputs);
    document.getElementById('studio-stroke-enabled').addEventListener('change', updateStudioFromInputs);
    document.getElementById('studio-text-fill').addEventListener('input', (e) => {
        if (isValidHexColor(e.target.value)) {
            document.getElementById('studio-text-fill-picker').value = e.target.value;
        }
    });
    document.getElementById('studio-text-stroke').addEventListener('input', (e) => {
        if (isValidHexColor(e.target.value)) {
            document.getElementById('studio-text-stroke-picker').value = e.target.value;
        }
    });

    ['studio-image-opacity', 'studio-image-aspect'].forEach(id => {
        document.getElementById(id).addEventListener('input', updateStudioFromInputs);
    });

    ['studio-x', 'studio-y', 'studio-width', 'studio-height'].forEach(id => {
        document.getElementById(id).addEventListener('input', updateStudioFromInputs);
    });

    window.addEventListener('resize', updateStudioCanvasDimensions);
    updateStudioCanvasDimensions();
    renderStudioElements();
}

function setStudioMode(mode) {
    state.thumbnail.studio.transformMode = mode || 'resize';
    document.querySelectorAll('.studio-mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === state.thumbnail.studio.transformMode);
    });
    renderStudioElements();
}

function updateStudioCanvasDimensions() {
    const width = parseInt(document.getElementById('thumb-width').value) || 1280;
    const height = parseInt(document.getElementById('thumb-height').value) || 720;
    state.thumbnail.studio.canvasWidth = width;
    state.thumbnail.studio.canvasHeight = height;

    const wrap = document.getElementById('studio-canvas-wrap');
    wrap.style.setProperty('--canvas-aspect', `${width} / ${height}`);
    renderStudioElements();
}

function getStudioScale() {
    const wrap = document.getElementById('studio-canvas-wrap');
    const width = state.thumbnail.studio.canvasWidth;
    const wrapWidth = wrap.clientWidth || width;
    return wrapWidth / width;
}

function renderStudioElements() {
    const canvas = document.getElementById('studio-canvas');
    if (!canvas) return;
    if (state.thumbnail.studio.editingId) return;
    const scale = getStudioScale();
    canvas.innerHTML = '';

    state.thumbnail.studio.elements.forEach(element => {
        const el = document.createElement('div');
        el.className = `studio-element ${element.type} ${element.id === state.thumbnail.studio.selectedId ? 'selected' : ''}`;
        el.dataset.id = element.id;

        el.style.left = `${element.x * scale}px`;
        el.style.top = `${element.y * scale}px`;
        el.style.width = `${element.width * scale}px`;
        el.style.height = `${element.height * scale}px`;
        el.style.opacity = element.opacity ?? 1;

        if (element.type === 'text' || element.type === 'numbering') {
            const text = document.createElement('div');
            text.className = 'studio-text';
            text.textContent = element.text || '';
            text.style.fontSize = `${(element.fontSize || 48) * scale}px`;
            text.style.fontFamily = element.fontFamily || 'Inter';
            const fillEnabled = element.fillEnabled !== false;
            const strokeEnabled = element.strokeEnabled !== false;
            text.style.color = fillEnabled ? (element.fill || '#ffffff') : 'transparent';
            text.style.textAlign = element.align || 'left';
            text.style.lineHeight = element.lineHeight || 1.1;
            text.style.letterSpacing = `${(element.letterSpacing || 0) * scale}px`;
            const stroke = element.stroke || '#000000';
            const strokeWidth = strokeEnabled ? (element.strokeWidth || 0) * scale : 0;
            text.style.webkitTextStroke = strokeWidth > 0 ? `${strokeWidth}px ${stroke}` : '0px transparent';
            el.appendChild(text);
            if (element.type === 'text') {
                el.addEventListener('dblclick', () => openStudioTextEditor(element.id));
            }
        } else if (element.type === 'image') {
            const img = document.createElement('img');
            img.src = getThumbnailPreviewUrl(element.path);
            img.alt = 'Overlay';
            el.appendChild(img);
        }

        ['tl', 'tr', 'bl', 'br'].forEach(handle => {
            const h = document.createElement('div');
            h.className = `studio-handle ${handle}`;
            h.dataset.handle = handle;
            el.appendChild(h);
        });

        el.addEventListener('pointerdown', handleStudioPointerDown);
        canvas.appendChild(el);
    });

    updateStudioPropertiesPanel();
}

function openStudioTextEditor(id) {
    if (state.thumbnail.studio.editingId) return;
    const element = state.thumbnail.studio.elements.find(el => el.id === id);
    if (!element || element.type !== 'text') return;

    const canvas = document.getElementById('studio-canvas');
    const scale = getStudioScale();
    const editor = document.createElement('textarea');
    editor.className = 'studio-text-editor';
    editor.value = element.text || '';
    editor.style.left = `${element.x * scale}px`;
    editor.style.top = `${element.y * scale}px`;
    editor.style.width = `${element.width * scale}px`;
    editor.style.height = `${element.height * scale}px`;
    editor.style.fontSize = `${(element.fontSize || 48) * scale}px`;
    editor.style.fontFamily = element.fontFamily || 'Inter';
    const fillEnabled = element.fillEnabled !== false;
    editor.style.color = fillEnabled ? (element.fill || '#ffffff') : (element.stroke || '#ffffff');
    editor.style.lineHeight = element.lineHeight || 1.1;
    editor.style.letterSpacing = `${(element.letterSpacing || 0) * scale}px`;
    canvas.appendChild(editor);
    editor.focus();

    state.thumbnail.studio.editingId = id;
    studioTextEditor = editor;

    editor.addEventListener('blur', () => closeStudioTextEditor(true));
    editor.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            e.preventDefault();
            closeStudioTextEditor(false);
        }
    });
}

function closeStudioTextEditor(commit) {
    const editor = studioTextEditor;
    if (!editor) return;
    const id = state.thumbnail.studio.editingId;
    const element = state.thumbnail.studio.elements.find(el => el.id === id);
    if (commit && element) {
        element.text = editor.value;
    }
    editor.remove();
    studioTextEditor = null;
    state.thumbnail.studio.editingId = null;
    renderStudioElements();
}

function handleStudioPointerDown(e) {
    e.preventDefault();
    if (state.thumbnail.studio.editingId) {
        closeStudioTextEditor(true);
    }
    const target = e.currentTarget;
    const id = target.dataset.id;
    selectStudioElement(id);

    const handle = e.target.dataset?.handle;
    const transformMode = state.thumbnail.studio.transformMode || 'resize';
    const scale = getStudioScale();
    const element = getSelectedStudioElement();
    if (!element) return;

    studioDragState = {
        id,
        mode: handle ? transformMode : 'move',
        handle: handle || null,
        startX: e.clientX,
        startY: e.clientY,
        origX: element.x,
        origY: element.y,
        origW: element.width,
        origH: element.height,
        origFontSize: element.type === 'text' || element.type === 'numbering' ? (element.fontSize || 48) : null,
        scale
    };

    window.addEventListener('pointermove', handleStudioPointerMove);
    window.addEventListener('pointerup', handleStudioPointerUp, { once: true });
}

function handleStudioPointerMove(e) {
    if (!studioDragState) return;
    const element = getSelectedStudioElement();
    if (!element) return;

    const dx = (e.clientX - studioDragState.startX) / studioDragState.scale;
    const dy = (e.clientY - studioDragState.startY) / studioDragState.scale;
    const canvasW = state.thumbnail.studio.canvasWidth;
    const canvasH = state.thumbnail.studio.canvasHeight;

    if (studioDragState.mode === 'move') {
        element.x = Math.max(0, Math.min(canvasW - element.width, studioDragState.origX + dx));
        element.y = Math.max(0, Math.min(canvasH - element.height, studioDragState.origY + dy));
        if (element.type === 'numbering') {
            document.getElementById('thumb-number-position').value = 'custom';
        }
    } else {
        const handle = studioDragState.handle;
        let newW = studioDragState.origW;
        let newH = studioDragState.origH;
        let newX = studioDragState.origX;
        let newY = studioDragState.origY;
        const aspect = studioDragState.origW / studioDragState.origH;

        if (handle.includes('r')) {
            newW = Math.max(20, studioDragState.origW + dx);
        }
        if (handle.includes('l')) {
            newW = Math.max(20, studioDragState.origW - dx);
            newX = studioDragState.origX + dx;
        }
        if (handle.includes('b')) {
            newH = Math.max(20, studioDragState.origH + dy);
        }
        if (handle.includes('t')) {
            newH = Math.max(20, studioDragState.origH - dy);
            newY = studioDragState.origY + dy;
        }

        if (element.type === 'image' && element.preserveAspect) {
            if (newW / newH > aspect) {
                newW = newH * aspect;
            } else {
                newH = newW / aspect;
            }
        }

        if ((element.type === 'text' || element.type === 'numbering') && studioDragState.origFontSize) {
            if (studioDragState.mode === 'scale') {
                const scaleFactor = Math.max(newW / studioDragState.origW, newH / studioDragState.origH);
                element.fontSize = Math.max(8, Math.round(studioDragState.origFontSize * scaleFactor));
            }
        }


        element.width = Math.min(canvasW, Math.max(20, newW));
        element.height = Math.min(canvasH, Math.max(20, newH));
        element.x = Math.max(0, Math.min(canvasW - element.width, newX));
        element.y = Math.max(0, Math.min(canvasH - element.height, newY));
        if (element.type === 'numbering') {
            document.getElementById('thumb-number-position').value = 'custom';
        }
    }

    renderStudioElements();
}

function handleStudioPointerUp() {
    studioDragState = null;
    window.removeEventListener('pointermove', handleStudioPointerMove);
}

function addStudioTextElement() {
    const element = {
        id: `text-${Date.now()}`,
        type: 'text',
        text: 'New Text',
        x: 80,
        y: 80,
        width: 420,
        height: 140,
        fontFamily: 'Inter',
        fontPath: '',
        fontSize: 64,
        fill: '#ffffff',
        fillEnabled: true,
        stroke: '#000000',
        strokeWidth: 8,
        strokeEnabled: false,
        align: 'left',
        opacity: 1,
        lineHeight: 1.1,
        letterSpacing: 0
    };
    state.thumbnail.studio.elements.push(element);
    selectStudioElement(element.id);
    renderStudioElements();
}

async function addStudioImageElement() {
    try {
        const result = await API.post('/browse/images', {});
        if (result.cancelled || !result.paths?.length) return;
        const path = result.paths[0];
        const element = {
            id: `img-${Date.now()}`,
            type: 'image',
            path,
            x: 100,
            y: 100,
            width: 220,
            height: 220,
            opacity: 1,
            preserveAspect: true
        };
        state.thumbnail.studio.elements.push(element);
        selectStudioElement(element.id);
        renderStudioElements();
    } catch (err) {
        showToast(`Failed to add image: ${err.message}`, 'error');
    }
}

function selectStudioElement(id) {
    state.thumbnail.studio.selectedId = id;
    renderStudioElements();
}

function getSelectedStudioElement() {
    return state.thumbnail.studio.elements.find(el => el.id === state.thumbnail.studio.selectedId);
}

function updateStudioPropertiesPanel() {
    const element = getSelectedStudioElement();
    const placeholder = document.querySelector('.studio-placeholder');
    const textSection = document.getElementById('studio-text-section');
    const imageSection = document.getElementById('studio-image-section');
    const geometrySection = document.getElementById('studio-geometry-section');

    if (!element) {
        placeholder.style.display = 'block';
        textSection.style.display = 'none';
        imageSection.style.display = 'none';
        geometrySection.style.display = 'none';
        return;
    }

    placeholder.style.display = 'none';
    geometrySection.style.display = 'block';
    if (element.type === 'text' || element.type === 'numbering') {
        textSection.style.display = 'block';
        imageSection.style.display = 'none';
        const isNumbering = element.type === 'numbering';
        const textInput = document.getElementById('studio-text');
        textInput.value = isNumbering ? '01 (auto)' : (element.text || '');
        textInput.disabled = isNumbering;
        setFontPickerSelection('studio-font', element.fontPath, 'Default');
        document.getElementById('studio-font-size').value = element.fontSize || 64;
        document.getElementById('studio-text-fill').value = element.fill || '#ffffff';
        document.getElementById('studio-text-fill-picker').value = element.fill || '#ffffff';
        document.getElementById('studio-text-stroke').value = element.stroke || '#000000';
        document.getElementById('studio-text-stroke-picker').value = element.stroke || '#000000';
        const fillEnabled = element.fillEnabled !== false;
        const strokeEnabled = element.strokeEnabled !== false;
        document.getElementById('studio-fill-enabled').checked = fillEnabled;
        document.getElementById('studio-stroke-enabled').checked = strokeEnabled;
        document.getElementById('studio-text-fill').disabled = !fillEnabled;
        document.getElementById('studio-text-fill-picker').disabled = !fillEnabled;
        document.getElementById('studio-text-stroke').disabled = !strokeEnabled;
        document.getElementById('studio-text-stroke-picker').disabled = !strokeEnabled;
        document.getElementById('studio-text-stroke-width').value = element.strokeWidth || 0;
        document.getElementById('studio-text-align').value = element.align || 'left';
        document.getElementById('studio-line-height').value = element.lineHeight ?? 1.1;
        document.getElementById('studio-letter-spacing').value = element.letterSpacing ?? 0;
        document.getElementById('studio-text-opacity').value = Math.round((element.opacity ?? 1) * 100);
        if (isNumbering) {
            document.getElementById('thumb-number-fill').value = element.fill || '#ffffff';
            document.getElementById('thumb-number-fill-picker').value = element.fill || '#ffffff';
            document.getElementById('thumb-number-stroke').value = element.stroke || '#000000';
            document.getElementById('thumb-number-stroke-picker').value = element.stroke || '#000000';
            document.getElementById('thumb-number-size').value = element.fontSize || 64;
            document.getElementById('thumb-number-line-height').value = element.lineHeight ?? 1.1;
            document.getElementById('thumb-number-letter-spacing').value = element.letterSpacing ?? 0;
            document.getElementById('thumb-number-stroke-width').value = element.strokeWidth || 0;
            document.getElementById('thumb-number-fill-enabled').checked = element.fillEnabled !== false;
            document.getElementById('thumb-number-stroke-enabled').checked = element.strokeEnabled !== false;
            setFontPickerSelection('thumb-number-font', element.fontPath, 'Auto');
        }
    } else {
        textSection.style.display = 'none';
        imageSection.style.display = 'block';
        document.getElementById('studio-image-opacity').value = Math.round((element.opacity ?? 1) * 100);
        document.getElementById('studio-image-aspect').checked = element.preserveAspect !== false;
    }

    document.getElementById('studio-x').value = Math.round(element.x);
    document.getElementById('studio-y').value = Math.round(element.y);
    document.getElementById('studio-width').value = Math.round(element.width);
    document.getElementById('studio-height').value = Math.round(element.height);
}

function updateStudioFromInputs() {
    const element = getSelectedStudioElement();
    if (!element) return;

    element.x = parseFloat(document.getElementById('studio-x').value) || element.x;
    element.y = parseFloat(document.getElementById('studio-y').value) || element.y;
    element.width = Math.max(20, parseFloat(document.getElementById('studio-width').value) || element.width);
    element.height = Math.max(20, parseFloat(document.getElementById('studio-height').value) || element.height);

    if (element.type === 'text' || element.type === 'numbering') {
        if (element.type === 'text') {
            element.text = document.getElementById('studio-text').value;
        } else {
            element.text = '01';
        }
        const fontPath = document.getElementById('studio-font').value;
        element.fontPath = fontPath;
        element.fontFamily = getFontNameByPath(fontPath) || 'Inter';
        element.fontSize = parseInt(document.getElementById('studio-font-size').value) || element.fontSize;
        element.lineHeight = parseFloat(document.getElementById('studio-line-height').value) || element.lineHeight || 1.1;
        element.letterSpacing = parseFloat(document.getElementById('studio-letter-spacing').value) || element.letterSpacing || 0;
        element.fill = document.getElementById('studio-text-fill').value || element.fill;
        element.fillEnabled = document.getElementById('studio-fill-enabled').checked;
        element.stroke = document.getElementById('studio-text-stroke').value || element.stroke;
        element.strokeWidth = parseInt(document.getElementById('studio-text-stroke-width').value) || 0;
        element.strokeEnabled = document.getElementById('studio-stroke-enabled').checked;
        element.align = document.getElementById('studio-text-align').value || 'left';
        element.opacity = (parseInt(document.getElementById('studio-text-opacity').value) || 100) / 100;

        if (element.type === 'numbering') {
            document.getElementById('thumb-number-fill').value = element.fill;
            document.getElementById('thumb-number-fill-picker').value = element.fill;
            document.getElementById('thumb-number-stroke').value = element.stroke;
            document.getElementById('thumb-number-stroke-picker').value = element.stroke;
            document.getElementById('thumb-number-size').value = element.fontSize;
            document.getElementById('thumb-number-stroke-width').value = element.strokeWidth;
            document.getElementById('thumb-number-fill-enabled').checked = element.fillEnabled !== false;
            document.getElementById('thumb-number-stroke-enabled').checked = element.strokeEnabled !== false;
            setFontPickerSelection('thumb-number-font', element.fontPath, 'Auto');
        }
    } else {
        element.opacity = (parseInt(document.getElementById('studio-image-opacity').value) || 100) / 100;
        element.preserveAspect = document.getElementById('studio-image-aspect').checked;
    }

    renderStudioElements();
}

function deleteSelectedStudioElement() {
    if (!state.thumbnail.studio.selectedId) return;
    state.thumbnail.studio.elements = state.thumbnail.studio.elements.filter(el => el.id !== state.thumbnail.studio.selectedId);
    state.thumbnail.studio.selectedId = null;
    renderStudioElements();
}

function duplicateSelectedStudioElement() {
    const element = getSelectedStudioElement();
    if (!element) return;
    const copy = { ...element, id: `${element.type}-${Date.now()}`, x: element.x + 20, y: element.y + 20 };
    state.thumbnail.studio.elements.push(copy);
    selectStudioElement(copy.id);
    renderStudioElements();
}

function initThumbnailGeneration() {
    document.getElementById('thumb-generate-btn').addEventListener('click', startThumbnailGeneration);
    document.getElementById('thumb-cancel-btn').addEventListener('click', cancelThumbnailGeneration);
}

function buildThumbnailPayload() {
    const resize = {
        width: parseInt(document.getElementById('thumb-width').value) || 1280,
        height: parseInt(document.getElementById('thumb-height').value) || 720,
        fit_mode: document.getElementById('thumb-fit-mode').value,
        background: document.getElementById('thumb-bg-color').value || '#000000'
    };

    const overlay = { type: state.thumbnail.overlayMode };
    if (state.thumbnail.overlayMode === 'image') {
        overlay.path = state.thumbnail.overlayImage.path;
        overlay.mode = document.getElementById('thumb-overlay-mode').value;
        overlay.opacity = (parseInt(document.getElementById('thumb-overlay-opacity').value) || 100) / 100;
    } else if (state.thumbnail.overlayMode === 'studio') {
        const studioElements = state.thumbnail.studio.elements.filter(el => el.type !== 'numbering');
        overlay.studio = {
            width: state.thumbnail.studio.canvasWidth,
            height: state.thumbnail.studio.canvasHeight,
            elements: studioElements
        };
    }

    const numberingEnabled = document.getElementById('thumb-numbering').checked;
    const numbering = {
        enabled: numberingEnabled,
        start: parseInt(document.getElementById('thumb-number-start').value) || 1,
        position: document.getElementById('thumb-number-position').value,
        margin: parseInt(document.getElementById('thumb-number-margin').value) || 24,
        font_size: parseInt(document.getElementById('thumb-number-size').value) || 0,
        line_height: parseFloat(document.getElementById('thumb-number-line-height').value) || 1.1,
        letter_spacing: parseFloat(document.getElementById('thumb-number-letter-spacing').value) || 0,
        fill: document.getElementById('thumb-number-fill').value || '#ffffff',
        fill_enabled: document.getElementById('thumb-number-fill-enabled').checked,
        stroke_fill: document.getElementById('thumb-number-stroke').value || '#000000',
        stroke_width: parseInt(document.getElementById('thumb-number-stroke-width').value) || 4,
        stroke_enabled: document.getElementById('thumb-number-stroke-enabled').checked,
        font_path: document.getElementById('thumb-number-font').value || null
    };

    const numberElement = numberingEnabled ? getNumberingElement() : null;
    if (numberElement) {
        numbering.position = 'custom';
        numbering.x = Math.round(numberElement.x);
        numbering.y = Math.round(numberElement.y);
        numbering.font_size = numberElement.fontSize || numbering.font_size;
        numbering.line_height = numberElement.lineHeight || numbering.line_height;
        numbering.letter_spacing = numberElement.letterSpacing || numbering.letter_spacing;
        numbering.fill = numberElement.fill || numbering.fill;
        numbering.fill_enabled = numberElement.fillEnabled !== false;
        numbering.stroke_fill = numberElement.stroke || numbering.stroke_fill;
        numbering.stroke_width = numberElement.strokeWidth || numbering.stroke_width;
        numbering.stroke_enabled = numberElement.strokeEnabled !== false;
        numbering.font_path = numberElement.fontPath || numbering.font_path;
    }

    const optimizeEnabled = document.getElementById('thumb-optimize').checked;
    const optimize = {
        enabled: optimizeEnabled,
        max_bytes: parseInt(document.getElementById('thumb-max-bytes').value) || 2097152,
        allow_format_change_to_jpeg: true
    };

    return {
        backgrounds: state.thumbnail.backgrounds,
        output_dir: document.getElementById('thumb-output-dir').value.trim(),
        output_format: document.getElementById('thumb-output-format').value,
        resize,
        overlay,
        numbering,
        optimize,
        strip_metadata: document.getElementById('thumb-strip-metadata').checked,
        filename_suffix: document.getElementById('thumb-filename-suffix').value || '_thumb',
        background_for_flatten: document.getElementById('thumb-bg-color').value || '#000000'
    };
}

async function startThumbnailGeneration() {
    if (!state.thumbnail.backgrounds.length) {
        showToast('Add at least one background', 'warning');
        return;
    }
    if (state.thumbnail.overlayMode === 'image' && !state.thumbnail.overlayImage.path) {
        showToast('Select an overlay image', 'warning');
        return;
    }
    if (state.thumbnail.overlayMode === 'studio' && state.thumbnail.studio.elements.length === 0) {
        showToast('Add at least one studio element', 'warning');
        return;
    }

    try {
        const payload = buildThumbnailPayload();
        const result = await API.post('/thumbnails/generate', payload);
        state.thumbnail.jobId = result.job_id;
        showThumbnailProgressOverlay(true);
        pollThumbnailJobStatus();
    } catch (err) {
        showToast(`Failed to start job: ${err.message}`, 'error');
    }
}

async function pollThumbnailJobStatus() {
    if (!state.thumbnail.jobId) return;
    try {
        const status = await API.get(`/thumbnails/jobs/${state.thumbnail.jobId}`);
        updateThumbnailProgress(status);

        if (status.status === 'processing') {
            setTimeout(pollThumbnailJobStatus, 500);
        } else if (status.status === 'completed') {
            showThumbnailProgressOverlay(false);
            showToast('Thumbnails generated!', 'success');
            state.thumbnail.jobId = null;
        } else if (status.status === 'failed') {
            showThumbnailProgressOverlay(false);
            showToast(`Failed: ${status.error}`, 'error');
            state.thumbnail.jobId = null;
        } else if (status.status === 'cancelled') {
            showThumbnailProgressOverlay(false);
            showToast('Thumbnail job cancelled', 'warning');
            state.thumbnail.jobId = null;
        }
    } catch (err) {
        setTimeout(pollThumbnailJobStatus, 1000);
    }
}

function updateThumbnailProgress(status) {
    document.getElementById('thumb-progress-step').textContent = status.current_step || 'Working...';
    document.getElementById('thumb-progress-bar').style.width = `${status.progress}%`;
    document.getElementById('thumb-progress-percent').textContent = `${Math.round(status.progress)}%`;
}

function showThumbnailProgressOverlay(show) {
    const overlay = document.getElementById('thumb-progress-overlay');
    overlay.style.display = show ? 'flex' : 'none';
    if (show) {
        document.getElementById('thumb-progress-bar').style.width = '0%';
        document.getElementById('thumb-progress-percent').textContent = '0%';
        document.getElementById('thumb-progress-step').textContent = 'Initializing...';
    }
}

async function cancelThumbnailGeneration() {
    if (!state.thumbnail.jobId) return;
    try {
        await API.post(`/thumbnails/jobs/${state.thumbnail.jobId}/cancel`, {});
    } catch (err) {
        showToast('Failed to cancel job', 'error');
    }
}

function PathBasename(path) {
    return (path || '').split(/[\\/]/).pop() || '';
}

function getThumbnailPreviewUrl(path) {
    return `/api/thumbnails/file?path=${encodeURIComponent(path)}`;
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

// ============== Decimal Stepper ==============
function initDecimalSteppers() {
    // Initialize stepper buttons
    document.querySelectorAll('.decimal-stepper-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const step = parseFloat(btn.dataset.step) || 0.1;
            const direction = btn.dataset.direction;
            const input = document.getElementById(targetId);
            if (!input) return;
            
            let value = parseFloat(input.value) || 0;
            if (direction === 'up') {
                value += step;
            } else {
                value -= step;
            }
            // Round to avoid floating point issues
            value = Math.round(value * 100) / 100;
            input.value = value;
            
            // Trigger input event for any listeners
            input.dispatchEvent(new Event('input', { bubbles: true }));
        });
    });
    
    // Simple approach: just let the inputs accept any text
    // No special keydown handling needed for type="text" inputs
}

// ============== Init ==============
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initFileHandling();
    initSettings();
    initProcessing();
    initBrandingModal();
    initThumbnailStudio();
    initOutputs();
    initDecimalSteppers();
    initFontSelectors();
    loadProfileSelect();
    initCollapsibleCards();
    loadAudioPresetsAndTypes(); // Load audio presets and track types
    
    // Show onboarding for first-time users
    setTimeout(initOnboarding, 500);
});

/**
 * Initialize collapsible card behavior
 */
function initCollapsibleCards() {
    document.querySelectorAll('.card-header-collapsible').forEach(header => {
        header.addEventListener('click', (e) => {
            // Don't toggle if clicking on controls inside header
            if (e.target.closest('.toggle, .btn, input, select')) return;
            
            const card = header.closest('.collapsible-card');
            if (card) {
                card.classList.toggle('collapsed');
            }
        });
    });
}

// Global functions for onclick handlers
window.removeFile = removeFile;
window.editBranding = editBranding;
window.removeAsset = removeAsset;
window.deleteOutput = deleteOutput;
window.removeThumbnailImage = removeThumbnailImage;
window.removeThumbnailVideo = removeThumbnailVideo;
window.generateFramesForVideo = generateFramesForVideo;
window.toggleThumbnailFrame = toggleThumbnailFrame;
window.removeThumbnailBackgroundAction = removeThumbnailBackgroundAction;
window.removeThumbnailOverlayImage = removeThumbnailOverlayImage;

let pollingInterval = null;
let dlInterval = null;
let currentImageMeta = {};

// Refresh Lucide Icons safely
function refreshLucideIcons() {
    if (typeof lucide !== 'undefined' && lucide.createIcons) {
        lucide.createIcons();
    }
}

// Toggle Custom Dropdown
function toggleCustomDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;
    
    // Close other dropdowns
    document.querySelectorAll('.custom-dropdown').forEach(d => {
        if (d.id !== dropdownId) d.classList.remove('open');
    });

    dropdown.classList.toggle('open');
    refreshLucideIcons();
}

// Select Style Preset
function selectStylePreset(value, label, iconName, containerId = 'dropdown-style') {
    const dropdown = document.getElementById(containerId);
    if (!dropdown) return;

    // Update hidden input
    const hiddenInput = dropdown.querySelector('input[type="hidden"]') || document.getElementById('quality-preset');
    if (hiddenInput) hiddenInput.value = value;

    // Update label and icon
    const labelEl = dropdown.querySelector('#' + containerId.replace('dropdown-', '') + '-selected-label') || dropdown.querySelector('.custom-dropdown-trigger span');
    const iconEl = dropdown.querySelector('.dropdown-trigger-icon');

    if (labelEl) labelEl.innerText = label;
    if (iconEl) {
        iconEl.setAttribute('data-lucide', iconName);
    }

    // Update active class on items
    const menu = dropdown.querySelector('.custom-dropdown-menu');
    if (menu) {
        menu.querySelectorAll('.custom-dropdown-item').forEach(item => {
            if (item.getAttribute('onclick')?.includes(`'${value}'`)) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    dropdown.classList.remove('open');
    refreshLucideIcons();

    // Sync other style dropdowns if present
    const otherId = containerId === 'dropdown-style' ? 'dropdown-style-settings' : 'dropdown-style';
    const otherDropdown = document.getElementById(otherId);
    if (otherDropdown) {
        const otherInput = otherDropdown.querySelector('input[type="hidden"]');
        if (otherInput) otherInput.value = value;
        const otherLabel = otherDropdown.querySelector('.custom-dropdown-trigger span');
        const otherIcon = otherDropdown.querySelector('.dropdown-trigger-icon');
        if (otherLabel) otherLabel.innerText = label;
        if (otherIcon) otherIcon.setAttribute('data-lucide', iconName);
    }

    if (typeof saveAllSettings === 'function') {
        saveAllSettings();
    }
}

// Global click listener to close open dropdowns
document.addEventListener('click', (e) => {
    if (!e.target.closest('.custom-dropdown')) {
        document.querySelectorAll('.custom-dropdown').forEach(d => d.classList.remove('open'));
    }
});

// Aspect Ratio Preset Handler
function applyAspectRatio(ratio) {
    let w = 512, h = 512;
    switch(ratio) {
        case '1:1': w = 512; h = 512; break;
        case '16:9': w = 1024; h = 576; break;
        case '9:16': w = 576; h = 1024; break;
        case '4:3': w = 768; h = 576; break;
        case '3:4': w = 576; h = 768; break;
        case '1024:1024': w = 1024; h = 1024; break;
    }
    setDimensions(w, h);
}

function setDimensions(w, h) {
    const widthEl = document.getElementById('width');
    const heightEl = document.getElementById('height');
    if (widthEl) widthEl.value = w;
    if (heightEl) heightEl.value = h;
    
    const valWidth = document.getElementById('val-width');
    const valHeight = document.getElementById('val-height');
    if (valWidth) valWidth.innerText = w;
    if (valHeight) valHeight.innerText = h;
}

function setSteps(s) {
    const stepsEl = document.getElementById('steps');
    if (stepsEl) stepsEl.value = s;
    const valSteps = document.getElementById('val-steps');
    if (valSteps) valSteps.innerText = s;

    // Update active chip UI
    document.querySelectorAll('.quick-chips button').forEach(btn => {
        if (btn.innerText.includes(s.toString())) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

function setCFG(c) {
    const cfgEl = document.getElementById('cfg');
    if (cfgEl) cfgEl.value = c;
    const valCfg = document.getElementById('val-cfg');
    if (valCfg) valCfg.innerText = c;
}

function saveAllSettings() {
    // Load existing settings so we don't overwrite values for DOM elements
    // that don't exist on the current page (e.g., steps/cfg only on settings page)
    const existing = JSON.parse(localStorage.getItem('edgemind_settings') || '{}');

    const stepsEl = document.getElementById('steps');
    const cfgEl = document.getElementById('cfg');
    const samplerEl = document.getElementById('sampler');
    const seedEl = document.getElementById('seed');
    const cpuOffloadEl = document.getElementById('opt-cpu-offload');
    const vaeTilingEl = document.getElementById('opt-vae-tiling');
    const attnSlicingEl = document.getElementById('opt-attn-slicing');
    const fp16El = document.getElementById('opt-fp16');
    const autoEnhanceEl = document.getElementById('auto-enhance');
    const negPromptEl = document.getElementById('negative-prompt');

    const settings = {
        quality_preset: document.getElementById('quality-preset')?.value || existing.quality_preset || 'photorealistic',
        auto_enhance: autoEnhanceEl ? autoEnhanceEl.checked : (existing.auto_enhance ?? true),
        negative_prompt: negPromptEl ? negPromptEl.value : (existing.negative_prompt || ''),
        steps: stepsEl ? parseInt(stepsEl.value) : (existing.steps ?? 1),
        cfg_scale: cfgEl ? parseFloat(cfgEl.value) : (existing.cfg_scale ?? 1.0),
        sampler: samplerEl ? samplerEl.value : (existing.sampler || 'Euler'),
        seed: seedEl ? parseInt(seedEl.value) : (existing.seed ?? -1),
        opt_cpu_offload: cpuOffloadEl ? cpuOffloadEl.checked : (existing.opt_cpu_offload ?? true),
        opt_vae_tiling: vaeTilingEl ? vaeTilingEl.checked : (existing.opt_vae_tiling ?? true),
        opt_attn_slicing: attnSlicingEl ? attnSlicingEl.checked : (existing.opt_attn_slicing ?? true),
        opt_fp16: fp16El ? fp16El.checked : (existing.opt_fp16 ?? true)
    };

    localStorage.setItem('edgemind_settings', JSON.stringify(settings));

    const toast = document.getElementById('save-toast');
    if (toast) {
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
    }
}

function loadSavedSettings() {
    const raw = localStorage.getItem('edgemind_settings');
    if (!raw) return;
    try {
        const s = JSON.parse(raw);
        if (s.quality_preset) {
            const iconMap = {
                photorealistic: { label: 'Photorealistic', icon: 'sparkles' },
                cinematic: { label: 'Cinematic Film', icon: 'clapperboard' },
                anime: { label: 'Anime Visual', icon: 'palette' },
                cyberpunk: { label: 'Cyberpunk Neon', icon: 'zap' },
                '3d': { label: '3D Render', icon: 'box' }
            };
            const meta = iconMap[s.quality_preset];
            if (meta) {
                if (document.getElementById('dropdown-style')) {
                    selectStylePreset(s.quality_preset, meta.label, meta.icon, 'dropdown-style');
                }
                if (document.getElementById('dropdown-style-settings')) {
                    selectStylePreset(s.quality_preset, meta.label, meta.icon, 'dropdown-style-settings');
                }
            }
        }

        if (document.getElementById('auto-enhance')) document.getElementById('auto-enhance').checked = s.auto_enhance;
        if (document.getElementById('negative-prompt')) document.getElementById('negative-prompt').value = s.negative_prompt || '';
        
        if (s.steps !== undefined) setSteps(s.steps);
        if (s.cfg_scale !== undefined) setCFG(s.cfg_scale);
        
        if (document.getElementById('sampler') && s.sampler) document.getElementById('sampler').value = s.sampler;
        if (document.getElementById('seed') && s.seed !== undefined) document.getElementById('seed').value = s.seed;

        if (document.getElementById('opt-cpu-offload')) document.getElementById('opt-cpu-offload').checked = s.opt_cpu_offload;
        if (document.getElementById('opt-vae-tiling')) document.getElementById('opt-vae-tiling').checked = s.opt_vae_tiling;
        if (document.getElementById('opt-attn-slicing')) document.getElementById('opt-attn-slicing').checked = s.opt_attn_slicing;
        if (document.getElementById('opt-fp16')) document.getElementById('opt-fp16').checked = s.opt_fp16;

        refreshLucideIcons();
    } catch (e) {
        console.error('Error loading settings:', e);
    }
}

function resetDefaultSettings() {
    localStorage.removeItem('edgemind_settings');
    selectStylePreset('photorealistic', 'Photorealistic', 'sparkles', 'dropdown-style-settings');
    if (document.getElementById('auto-enhance')) document.getElementById('auto-enhance').checked = true;
    if (document.getElementById('negative-prompt')) document.getElementById('negative-prompt').value = '';
    setSteps(1);
    setCFG(1.0);
    if (document.getElementById('sampler')) document.getElementById('sampler').value = 'Euler';
    if (document.getElementById('seed')) document.getElementById('seed').value = '-1';
    if (document.getElementById('opt-cpu-offload')) document.getElementById('opt-cpu-offload').checked = true;
    if (document.getElementById('opt-vae-tiling')) document.getElementById('opt-vae-tiling').checked = true;
    if (document.getElementById('opt-attn-slicing')) document.getElementById('opt-attn-slicing').checked = true;
    if (document.getElementById('opt-fp16')) document.getElementById('opt-fp16').checked = true;

    saveAllSettings();
    alert('Settings reset to factory defaults (ByteDance Hyper-SD 1-Step active)!');
}

function renderSettingsModelsList() {
    const box = document.getElementById('models-list-box');
    if (!box) return;

    fetch('/api/models')
        .then(r => r.json())
        .then(data => {
            box.innerHTML = '';
            if (!data.models || data.models.length === 0) {
                box.innerHTML = `<div class="empty-models-hint"><i data-lucide="package-open"></i><span>No local models found in /models. Use Hugging Face downloader above to fetch one!</span></div>`;
            } else {
                data.models.forEach(m => {
                    const item = document.createElement('div');
                    item.className = 'model-row-item';
                    const isCurrent = data.current_model && data.current_model.name === m.name;
                    item.innerHTML = `
                        <div class="model-info">
                            <i data-lucide="box" class="model-icon"></i>
                            <div>
                                <div class="model-name">${m.name}</div>
                                <div class="model-path">${m.path}</div>
                            </div>
                        </div>
                        <div class="model-badges" style="display: flex; align-items: center; gap: 8px;">
                            ${isCurrent ? '<span class="badge-loaded">Active in Engine</span>' : '<span class="badge-idle">On Disk</span>'}
                            <button class="btn-secondary" style="padding: 4px 8px; color: #ff5555; border-color: rgba(255,85,85,0.3);" onclick="deleteModel('${m.path.replace(/\\/g, '\\\\')}', '${m.name}')">
                                <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
                            </button>
                        </div>
                    `;
                    box.appendChild(item);
                });
            }
            refreshLucideIcons();
        });
}

function deleteModel(path, name) {
    if (!confirm(`Are you sure you want to delete model "${name}"?`)) return;
    fetch('/api/delete-model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: path })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            alert(data.message || 'Model deleted.');
            refreshModels();
            renderSettingsModelsList();
        }
    })
    .catch(err => alert('Failed to delete model: ' + err));
}

function downloadHFModel() {
    const input = document.getElementById('hf-url-input');
    const url = input ? input.value.trim() : '';
    if (!url) {
        alert('Please enter a Hugging Face model URL or Repo ID (e.g., runwayml/stable-diffusion-v1-5).');
        return;
    }

    const btn = document.getElementById('btn-dl-hf');
    if (btn) btn.disabled = true;
    
    const container = document.getElementById('dl-status-container');
    if (container) container.style.display = 'block';
    
    document.getElementById('dl-msg').innerText = 'Connecting to Hugging Face...';
    document.getElementById('dl-stats-text').innerText = '0 MB | 0 MB/s';
    document.getElementById('dl-bar-fill').style.width = '5%';

    fetch('/api/download-hf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            resetDownloadUI();
        } else {
            pollDownloadStatus();
        }
    })
    .catch(err => {
        alert('Failed to initiate download: ' + err);
        resetDownloadUI();
    });
}

function pollDownloadStatus() {
    if (dlInterval) clearInterval(dlInterval);
    dlInterval = setInterval(() => {
        fetch('/api/download-status')
            .then(r => r.json())
            .then(st => {
                document.getElementById('dl-msg').innerText = st.message;
                document.getElementById('dl-stats-text').innerText = `${st.downloaded_mb || 0} MB | ${st.speed_mbps || 0} MB/s`;
                
                let pct = st.progress || 0;
                document.getElementById('dl-bar-fill').style.width = `${pct}%`;

                if (st.status === 'complete') {
                    clearInterval(dlInterval);
                    alert('Download Complete! Updating models list...');
                    resetDownloadUI();
                    refreshModels();
                    renderSettingsModelsList();
                } else if (st.status === 'error') {
                    clearInterval(dlInterval);
                    alert('Download Error:\n' + st.error);
                    resetDownloadUI();
                }
            });
    }, 1000);
}

function resetDownloadUI() {
    const btn = document.getElementById('btn-dl-hf');
    if (btn) btn.disabled = false;
    const container = document.getElementById('dl-status-container');
    if (container) container.style.display = 'none';
}

function updateSystemStats() {
    fetch('/api/system-stats')
        .then(r => r.json())
        .then(data => {
            const devEl = document.getElementById('device-name');
            if (devEl) devEl.innerText = data.device_name;

            const profEl = document.getElementById('profile-name');
            if (profEl) profEl.innerText = `${data.profile} • CPU+GPU Hybrid`;

            const vramVal = document.getElementById('vram-val');
            if (vramVal) vramVal.innerText = `${data.vram_used_gb} / ${data.vram_total_gb} GB`;
            
            const vramPct = data.vram_total_gb > 0 ? (data.vram_used_gb / data.vram_total_gb) * 100 : 0;
            const vramBar = document.getElementById('vram-bar');
            if (vramBar) vramBar.style.width = `${vramPct}%`;

            const ramVal = document.getElementById('ram-val');
            if (ramVal) ramVal.innerText = `${data.ram_used_gb} / ${data.ram_total_gb} GB`;
            
            const ramBar = document.getElementById('ram-bar');
            if (ramBar) ramBar.style.width = `${data.ram_percent}%`;
        });
}

function refreshModels() {
    fetch('/api/models')
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('model-select');
            if (!sel) return;
            sel.innerHTML = '<option value="">-- Select Local Model --</option>';
            
            const hint = document.getElementById('model-count-hint');
            if (hint) hint.innerText = `${data.models.length} model(s) ready`;

            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.path;
                opt.innerText = m.name;
                sel.appendChild(opt);
            });

            if (data.current_model && data.current_model.path) {
                sel.value = data.current_model.path;
                toggleHyperSdBadge(data.current_model.hyper_sd_active);
            } else if (data.models.length > 0) {
                sel.value = data.models[0].path;
            }
            refreshLucideIcons();
        });
}

function onModelChange() {
    toggleHyperSdBadge(false);
}

function toggleHyperSdBadge(active) {
    const badge = document.getElementById('hyper-sd-badge');
    if (badge) {
        badge.style.display = active ? 'flex' : 'none';
        refreshLucideIcons();
    }
}

function unloadModel() {
    fetch('/api/unload', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            alert(data.message || 'Model unloaded.');
            toggleHyperSdBadge(false);
            updateSystemStats();
            renderSettingsModelsList();
        });
}

function startGeneration() {
    const promptInput = document.getElementById('prompt');
    const prompt = promptInput ? promptInput.value.trim() : '';
    const modelSelect = document.getElementById('model-select');
    const modelPath = modelSelect ? modelSelect.value : '';

    if (!prompt) {
        alert('Please enter a description for your visual image.');
        return;
    }
    if (!modelPath) {
        alert('Please select a local model from the dropdown pill.');
        return;
    }

    const saved = JSON.parse(localStorage.getItem('edgemind_settings') || '{}');

    // Use DOM elements if present (settings page), otherwise reliably fallback to localStorage
    const stepsEl = document.getElementById('steps');
    const cfgEl = document.getElementById('cfg');
    const samplerEl = document.getElementById('sampler');
    const seedEl = document.getElementById('seed');
    const fp16El = document.getElementById('opt-fp16');
    const cpuOffloadEl = document.getElementById('opt-cpu-offload');
    const vaeTilingEl = document.getElementById('opt-vae-tiling');
    const attnSlicingEl = document.getElementById('opt-attn-slicing');
    const negPromptEl = document.getElementById('negative-prompt');
    const autoEnhanceEl = document.getElementById('auto-enhance');

    const payload = {
        prompt: prompt,
        negative_prompt: negPromptEl ? negPromptEl.value : (saved.negative_prompt || ''),
        auto_enhance: autoEnhanceEl ? autoEnhanceEl.checked : (saved.auto_enhance ?? true),
        quality_preset: document.getElementById('quality-preset')?.value || saved.quality_preset || 'photorealistic',
        width: parseInt(document.getElementById('width')?.value || 512),
        height: parseInt(document.getElementById('height')?.value || 512),
        steps: stepsEl ? parseInt(stepsEl.value) : (saved.steps ?? 1),
        cfg_scale: cfgEl ? parseFloat(cfgEl.value) : (saved.cfg_scale ?? 1.0),
        sampler: samplerEl ? samplerEl.value : (saved.sampler || 'Euler'),
        seed: seedEl ? parseInt(seedEl.value) : (saved.seed ?? -1),
        model_path: modelPath,
        precision: (fp16El ? fp16El.checked : (saved.opt_fp16 ?? true)) ? 'fp16' : 'fp32',
        cpu_offload: cpuOffloadEl ? cpuOffloadEl.checked : (saved.opt_cpu_offload ?? true),
        vae_tiling: vaeTilingEl ? vaeTilingEl.checked : (saved.opt_vae_tiling ?? true),
        attention_slicing: attnSlicingEl ? attnSlicingEl.checked : (saved.opt_attn_slicing ?? true)
    };

    // Trigger bottom floating dock animation mode
    document.body.classList.add('active-generation-mode');

    const btn = document.getElementById('btn-generate');
    if (btn) btn.disabled = true;
    
    const progressOverlay = document.getElementById('progress-overlay');
    if (progressOverlay) progressOverlay.style.display = 'flex';

    // Smoothly focus display canvas
    const displaySection = document.querySelector('.display-section');
    if (displaySection) {
        displaySection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            resetGenerateUI();
        } else {
            pollStatus();
        }
    })
    .catch(err => {
        alert('Error starting generation: ' + err);
        resetGenerateUI();
    });
}

function pollStatus() {
    if (pollingInterval) clearInterval(pollingInterval);
    
    pollingInterval = setInterval(() => {
        fetch('/api/status')
            .then(r => r.json())
            .then(st => {
                const msgEl = document.getElementById('status-msg');
                if (msgEl) msgEl.innerText = st.message;
                
                const pctEl = document.getElementById('status-percent');
                if (pctEl) pctEl.innerText = `${st.progress}%`;
                
                const barEl = document.getElementById('status-bar-fill');
                if (barEl) barEl.style.width = `${st.progress}%`;

                updateSystemStats();

                if (st.status === 'complete') {
                    clearInterval(pollingInterval);
                    resetGenerateUI();
                    showPreview(`/outputs/${st.output_image}`);
                    loadGallery();
                } else if (st.status === 'error') {
                    clearInterval(pollingInterval);
                    alert('Generation Failed:\n' + st.error);
                    resetGenerateUI();
                }
            });
    }, 800);
}

function resetGenerateUI() {
    const btn = document.getElementById('btn-generate');
    if (btn) btn.disabled = false;
    const progressOverlay = document.getElementById('progress-overlay');
    if (progressOverlay) progressOverlay.style.display = 'none';
}

function showPreview(url, metadata = {}) {
    document.body.classList.add('active-generation-mode');
    currentImageMeta = metadata;
    const placeholder = document.getElementById('placeholder-view');
    if (placeholder) placeholder.style.display = 'none';
    
    const img = document.getElementById('main-preview');
    if (img) {
        img.src = url;
        img.style.display = 'block';
    }

    const overlay = document.getElementById('canvas-overlay');
    if (overlay) overlay.style.display = 'flex';

    const metaBadge = document.getElementById('image-meta-badge');
    if (metaBadge) {
        const w = metadata.width || document.getElementById('width')?.value || '512';
        const h = metadata.height || document.getElementById('height')?.value || '512';
        metaBadge.innerText = `${w}×${h}`;
    }

    refreshLucideIcons();
}

function downloadCurrentImage() {
    const img = document.getElementById('main-preview');
    if (!img || !img.src) return;
    const a = document.createElement('a');
    a.href = img.src;
    a.download = `edgemind_${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function copyCurrentPrompt() {
    const promptInput = document.getElementById('prompt');
    const text = (currentImageMeta && currentImageMeta.prompt) ? currentImageMeta.prompt : (promptInput ? promptInput.value : '');
    if (text) {
        navigator.clipboard.writeText(text).then(() => {
            alert('Prompt copied to clipboard!');
        });
    }
}

function loadGallery() {
    fetch('/api/gallery')
        .then(r => r.json())
        .then(data => {
            const grid = document.getElementById('gallery-grid');
            const dockGrid = document.getElementById('recent-dock-grid');
            
            if (grid) grid.innerHTML = '';
            if (dockGrid) dockGrid.innerHTML = '';

            if (!data.images || data.images.length === 0) {
                if (dockGrid) {
                    dockGrid.innerHTML = `<div class="empty-gallery-hint"><i data-lucide="sparkles"></i><span>No recent generations yet. Type a prompt above to render your first visual!</span></div>`;
                }
            } else {
                data.images.forEach(imgData => {
                    const promptText = (imgData.metadata && imgData.metadata.prompt) ? imgData.metadata.prompt : 'Generated Visual';

                    if (grid) {
                        const item = document.createElement('div');
                        item.className = 'gallery-item';
                        item.onclick = () => showPreview(imgData.url, imgData.metadata);
                        item.innerHTML = `<img src="${imgData.url}" title="${promptText}">`;
                        grid.appendChild(item);
                    }

                    if (dockGrid) {
                        const item = document.createElement('div');
                        item.className = 'dock-gallery-item';
                        item.onclick = () => showPreview(imgData.url, imgData.metadata);
                        item.innerHTML = `<img src="${imgData.url}" title="${promptText}"><div class="dock-item-prompt">${promptText}</div>`;
                        dockGrid.appendChild(item);
                    }
                });
            }
            refreshLucideIcons();
        });
}

// Mobile Telemetry HUD Toggle
function toggleMobileHud() {
    const hud = document.querySelector('.telemetry-hud');
    if (hud) {
        hud.classList.toggle('mobile-open');
    }
}

// Close mobile HUD when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.telemetry-hud') && !e.target.closest('.mobile-hud-toggle')) {
        const hud = document.querySelector('.telemetry-hud');
        if (hud) hud.classList.remove('mobile-open');
    }
});

// Initial Boot Logic
document.addEventListener('DOMContentLoaded', () => {
    updateSystemStats();
    refreshModels();
    loadGallery();
    loadSavedSettings();
    refreshLucideIcons();
    setInterval(updateSystemStats, 3000);
});

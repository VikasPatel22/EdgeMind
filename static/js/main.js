let pollingInterval = null;
let liveTimerInterval = null;
let dlInterval = null;
let genStartTime = 0;
let currentImageMeta = {};
let activeLightboxData = { url: '', prompt: '' };

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

    evaluateProTipVisibility();
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
    let cssRatio = '1 / 1';
    switch(ratio) {
        case '1:1': w = 512; h = 512; cssRatio = '1 / 1'; break;
        case '16:9': w = 1024; h = 576; cssRatio = '16 / 9'; break;
        case '9:16': w = 576; h = 1024; cssRatio = '9 / 16'; break;
        case '4:3': w = 768; h = 576; cssRatio = '4 / 3'; break;
        case '3:4': w = 576; h = 768; cssRatio = '3 / 4'; break;
        case '1024:1024': w = 1024; h = 1024; cssRatio = '1 / 1'; break;
    }
    setDimensions(w, h);

    // Update shimmer placeholder aspect ratio
    const shimmer = document.getElementById('shimmer-placeholder');
    if (shimmer) {
        shimmer.style.aspectRatio = cssRatio;
    }

    if (typeof saveAllSettings === 'function') {
        saveAllSettings();
    }
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

    evaluateProTipVisibility();
}

function setCFG(c) {
    const cfgEl = document.getElementById('cfg');
    if (cfgEl) cfgEl.value = c;
    const valCfg = document.getElementById('val-cfg');
    if (valCfg) valCfg.innerText = c;
}

function saveAllSettings() {
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
    const modelSelectEl = document.getElementById('model-select');
    const widthEl = document.getElementById('width');
    const heightEl = document.getElementById('height');
    const aspectSelectEl = document.getElementById('aspect-ratio');

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
        opt_fp16: fp16El ? fp16El.checked : (existing.opt_fp16 ?? true),
        model_path: (modelSelectEl && modelSelectEl.value) ? modelSelectEl.value : (existing.model_path || null),
        width: widthEl ? parseInt(widthEl.value) : (existing.width || 512),
        height: heightEl ? parseInt(heightEl.value) : (existing.height || 512),
        aspect_ratio: aspectSelectEl ? aspectSelectEl.value : (existing.aspect_ratio || '1:1')
    };

    localStorage.setItem('edgemind_settings', JSON.stringify(settings));

    fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    }).catch(err => console.warn('Could not sync settings to server:', err));

    const toast = document.getElementById('save-toast');
    if (toast) {
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
    }

    evaluateProTipVisibility();
}

function loadSavedSettings() {
    function applySettingsToUI(s) {
        if (!s) return;
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

        if (document.getElementById('auto-enhance') && s.auto_enhance !== undefined) {
            document.getElementById('auto-enhance').checked = s.auto_enhance;
        }
        if (document.getElementById('negative-prompt') && s.negative_prompt !== undefined) {
            document.getElementById('negative-prompt').value = s.negative_prompt;
        }
        
        if (s.steps !== undefined) setSteps(s.steps);
        if (s.cfg_scale !== undefined) setCFG(s.cfg_scale);
        
        if (document.getElementById('sampler') && s.sampler) document.getElementById('sampler').value = s.sampler;
        if (document.getElementById('seed') && s.seed !== undefined) document.getElementById('seed').value = s.seed;

        if (document.getElementById('opt-cpu-offload') && s.opt_cpu_offload !== undefined) document.getElementById('opt-cpu-offload').checked = s.opt_cpu_offload;
        if (document.getElementById('opt-vae-tiling') && s.opt_vae_tiling !== undefined) document.getElementById('opt-vae-tiling').checked = s.opt_vae_tiling;
        if (document.getElementById('opt-attn-slicing') && s.opt_attn_slicing !== undefined) document.getElementById('opt-attn-slicing').checked = s.opt_attn_slicing;
        if (document.getElementById('opt-fp16') && s.opt_fp16 !== undefined) document.getElementById('opt-fp16').checked = s.opt_fp16;

        if (s.width && s.height && typeof setDimensions === 'function') {
            setDimensions(s.width, s.height);
        }
        if (s.aspect_ratio && document.getElementById('aspect-ratio')) {
            document.getElementById('aspect-ratio').value = s.aspect_ratio;
            applyAspectRatio(s.aspect_ratio);
        }

        refreshLucideIcons();
        evaluateProTipVisibility();
    }

    // 1. Instant local restore
    const raw = localStorage.getItem('edgemind_settings');
    if (raw) {
        try {
            applySettingsToUI(JSON.parse(raw));
        } catch (e) {}
    }

    // 2. Fetch server settings to stay in sync
    fetch('/api/settings')
        .then(r => r.json())
        .then(data => {
            if (data && data.settings) {
                applySettingsToUI(data.settings);
                localStorage.setItem('edgemind_settings', JSON.stringify(data.settings));
            }
        })
        .catch(err => console.warn('Could not fetch server settings:', err));
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
    alert('Settings reset to factory defaults!');
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
                            <button class="btn-secondary" style="padding: 4px 8px; color: #ff5555; border-color: rgba(255,85,85,0.3);" onclick="deleteModel('${m.path.replace(/\\/g, '\\\\')}', '${m.name}')" title="Delete Model" aria-label="Delete model ${m.name}">
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

// Item 6, 7, 8, 9: Hardware Telemetry HUD Update
function updateSystemStats() {
    fetch('/api/system-stats')
        .then(r => r.json())
        .then(data => {
            // Item 7: Merged Engine Status Chip
            const chip = document.getElementById('engine-status-chip');
            const chipText = document.getElementById('engine-status-text');
            if (chipText) {
                const isCpu = !data.vram_total_gb || data.vram_total_gb <= 0 || (data.device && data.device.toLowerCase() === 'cpu');
                if (isCpu) {
                    chipText.innerText = "CPU mode · Low VRAM";
                    if (chip) chip.title = `Engine: ${data.device_name || 'System CPU'} • Profile: ${data.profile || 'CPU Mode'} • Hybrid Offload Active`;
                } else {
                    chipText.innerText = `${data.device_name || 'GPU'} · ${data.profile || 'Engine'}`;
                    if (chip) chip.title = `Engine: ${data.device_name} • Profile: ${data.profile} • Hybrid Offload Active`;
                }
            }

            // Fallback for settings page if older elements are present
            const profEl = document.getElementById('profile-name');
            if (profEl) profEl.innerText = `${data.profile} • CPU+GPU Hybrid`;
            const devEl = document.getElementById('device-name');
            if (devEl) devEl.innerText = data.device_name;

            // Item 6: VRAM when 0/CPU mode -> show "N/A · CPU mode" with greyed-out bar
            const vramVal = document.getElementById('vram-val');
            const vramBar = document.getElementById('vram-bar');
            const isVramNA = !data.vram_total_gb || data.vram_total_gb <= 0;
            if (vramVal) {
                if (isVramNA) {
                    vramVal.innerText = "N/A · CPU mode";
                    vramVal.classList.add('val-disabled');
                } else {
                    vramVal.innerText = `${data.vram_used_gb} / ${data.vram_total_gb} GB`;
                    vramVal.classList.remove('val-disabled');
                }
            }
            if (vramBar) {
                if (isVramNA) {
                    vramBar.style.width = "100%";
                    vramBar.classList.add('meter-disabled');
                } else {
                    const vramPct = (data.vram_used_gb / data.vram_total_gb) * 100;
                    vramBar.style.width = `${vramPct}%`;
                    vramBar.classList.remove('meter-disabled');
                }
            }

            // Item 9: Free VRAM button disabled when VRAM is 0/N/A
            const freeVramBtn = document.getElementById('btn-free-vram');
            if (freeVramBtn) {
                if (isVramNA) {
                    freeVramBtn.disabled = true;
                    freeVramBtn.title = "Free VRAM is not applicable in CPU mode";
                } else {
                    freeVramBtn.disabled = false;
                    freeVramBtn.title = "Free VRAM & Unload Model from Memory";
                }
            }

            // Item 8: Color System RAM bar by usage: green <70%, amber 70-85%, red >85% + warning tooltip >85%
            const ramVal = document.getElementById('ram-val');
            const ramBar = document.getElementById('ram-bar');
            const ramStatItem = document.getElementById('ram-stat-item');
            const ramPct = data.ram_percent || 0;

            if (ramVal) ramVal.innerText = `${data.ram_used_gb} / ${data.ram_total_gb} GB`;
            if (ramBar) {
                ramBar.style.width = `${ramPct}%`;
                ramBar.classList.remove('bar-green', 'bar-amber', 'bar-red');
                if (ramPct < 70) {
                    ramBar.classList.add('bar-green');
                } else if (ramPct <= 85) {
                    ramBar.classList.add('bar-amber');
                } else {
                    ramBar.classList.add('bar-red');
                }
            }
            if (ramStatItem) {
                if (ramPct > 85) {
                    ramStatItem.title = `⚠️ High Memory Warning: System RAM usage is ${ramPct}% (${data.ram_used_gb}/${data.ram_total_gb} GB). Close memory-heavy apps to prevent OOM errors.`;
                    ramStatItem.classList.add('stat-warning');
                } else {
                    ramStatItem.title = `System RAM: ${data.ram_used_gb} GB of ${data.ram_total_gb} GB used (${ramPct}%)`;
                    ramStatItem.classList.remove('stat-warning');
                }
            }
        })
        .catch(err => console.warn('Telemetry update failed:', err));
}

// Items 10 & 16: Models refresh & display full model name
function refreshModels() {
    fetch('/api/models')
        .then(r => r.json())
        .then(data => {
            const sel = document.getElementById('model-select');
            if (!sel) return;
            sel.innerHTML = '<option value="">-- Select Local Model --</option>';
            
            // Item 16: Move model count hint to model dropdown area
            const hint = document.getElementById('model-count-hint');
            if (hint) {
                hint.innerText = `${data.models.length} ready`;
                hint.title = `${data.models.length} local model(s) installed`;
            }

            // Item 10: Show full model name with tooltip
            data.models.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.path;
                opt.innerText = m.name;
                opt.title = m.name; // Full tooltip
                sel.appendChild(opt);
            });

            if (data.current_model && data.current_model.path) {
                sel.value = data.current_model.path;
                toggleHyperSdBadge(data.current_model.hyper_sd_active);
            } else if (data.models.length > 0) {
                sel.value = data.models[0].path;
            }

            // Sync tooltip on select element itself
            if (sel.options[sel.selectedIndex]) {
                sel.title = sel.options[sel.selectedIndex].text;
            }

            refreshLucideIcons();
        })
        .catch(err => console.warn('Could not load models list:', err));
}

function onModelChange() {
    const sel = document.getElementById('model-select');
    if (sel && sel.options[sel.selectedIndex]) {
        sel.title = sel.options[sel.selectedIndex].text;
        const wrapper = document.getElementById('model-select-wrapper');
        if (wrapper) wrapper.title = `Model: ${sel.options[sel.selectedIndex].text}`;
    }
    toggleHyperSdBadge(false);
    if (typeof saveAllSettings === 'function') {
        saveAllSettings();
    }
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
        })
        .catch(err => alert('Failed to unload model: ' + err));
}

// Auto-growing textarea handler (Item 14)
function setupAutoGrowPrompt() {
    const promptArea = document.getElementById('prompt');
    if (!promptArea) return;

    function resize() {
        promptArea.style.height = 'auto';
        const minH = 48; // 2 rows
        const maxH = 144; // 6 rows
        const scrollH = promptArea.scrollHeight;
        const clamped = Math.min(Math.max(scrollH, minH), maxH);
        promptArea.style.height = `${clamped}px`;
        updateComposerBottomPadding();
    }

    promptArea.addEventListener('input', resize);
    
    // Ctrl/Cmd + Enter to trigger generation (Item 14)
    promptArea.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            startGeneration();
        }
    });

    resize();
}

// Bottom padding calculation for scroll container (Item 1)
function updateComposerBottomPadding() {
    const dock = document.getElementById('prompt-dock');
    const hero = document.querySelector('.hero-container');
    if (dock && hero) {
        const dockHeight = dock.offsetHeight;
        document.documentElement.style.setProperty('--composer-height', `${dockHeight}px`);
        if (document.body.classList.contains('active-generation-mode')) {
            hero.style.paddingBottom = `${dockHeight + 24}px`;
        } else {
            hero.style.paddingBottom = '48px';
        }
    }
}

// Pro Tip Banner Evaluation (Item 19)
function evaluateProTipVisibility() {
    const banner = document.getElementById('quality-tip-banner');
    if (!banner) return;

    const isDismissed = localStorage.getItem('edgemind_tip_dismissed') === 'true';
    if (isDismissed) {
        banner.style.display = 'none';
        updateComposerBottomPadding();
        return;
    }

    const saved = JSON.parse(localStorage.getItem('edgemind_settings') || '{}');
    const stepsEl = document.getElementById('steps');
    const steps = stepsEl ? parseInt(stepsEl.value) : (saved.steps ?? 1);
    const preset = document.getElementById('quality-preset')?.value || saved.quality_preset || 'photorealistic';

    // Tip asks for: Inference Steps (25-50) and Photorealistic mode
    const matchesTip = (steps >= 25 && preset === 'photorealistic');
    if (matchesTip) {
        banner.style.display = 'none';
    } else {
        banner.style.display = 'flex';
    }
    updateComposerBottomPadding();
    refreshLucideIcons();
}

function dismissProTip() {
    localStorage.setItem('edgemind_tip_dismissed', 'true');
    const banner = document.getElementById('quality-tip-banner');
    if (banner) {
        banner.style.opacity = '0';
        banner.style.transform = 'translateY(-6px)';
        setTimeout(() => {
            banner.style.display = 'none';
            updateComposerBottomPadding();
        }, 200);
    }
}

// Generation Execution (Items 2, 4, 12, 13, 14, 15)
function startGeneration() {
    const promptInput = document.getElementById('prompt');
    const prompt = promptInput ? promptInput.value.trim() : '';
    const modelSelect = document.getElementById('model-select');
    const modelPath = modelSelect ? modelSelect.value : '';

    if (!prompt) {
        alert('Please enter a description for your visual image.');
        if (promptInput) promptInput.focus();
        return;
    }
    if (!modelPath) {
        alert('Please select a local model from the dropdown pill.');
        if (modelSelect) modelSelect.focus();
        return;
    }

    const saved = JSON.parse(localStorage.getItem('edgemind_settings') || '{}');
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

    // Activate bottom dock mode
    document.body.classList.add('active-generation-mode');
    updateComposerBottomPadding();

    // Item 13: Replace Generate with Stop button
    const btnGen = document.getElementById('btn-generate');
    const btnStop = document.getElementById('btn-stop');
    if (btnGen) btnGen.style.display = 'none';
    if (btnStop) btnStop.style.display = 'inline-flex';

    // Item 4: Do not show stale previous image as current result
    // If previous image exists, dim to 40% with "Previous result" label
    // If no previous image, show shimmer placeholder at selected aspect ratio
    const previewContainer = document.getElementById('preview-container');
    const mainPreview = document.getElementById('main-preview');
    const placeholderView = document.getElementById('placeholder-view');
    const shimmer = document.getElementById('shimmer-placeholder');
    const staleBadge = document.getElementById('previous-result-badge');
    const canvasOverlay = document.getElementById('canvas-overlay');

    if (canvasOverlay) canvasOverlay.style.display = 'none';

    if (mainPreview && mainPreview.src && mainPreview.src.includes('/outputs/')) {
        // We have a previous image: dim it to 40% and label as previous result
        if (placeholderView) placeholderView.style.display = 'none';
        if (shimmer) shimmer.style.display = 'none';
        if (previewContainer) {
            previewContainer.style.display = 'block';
            previewContainer.classList.add('is-stale');
        }
        if (staleBadge) staleBadge.style.display = 'inline-flex';
    } else {
        // No previous image: show shimmer skeleton at selected aspect ratio
        if (placeholderView) placeholderView.style.display = 'none';
        if (previewContainer) previewContainer.style.display = 'none';
        if (shimmer) {
            const aspectVal = document.getElementById('aspect-ratio')?.value || '1:1';
            applyAspectRatio(aspectVal);
            shimmer.style.display = 'flex';
        }
    }

    // Item 2 & 15: Show Progress Card directly BELOW image in normal flow
    const progressCard = document.getElementById('progress-card');
    if (progressCard) progressCard.style.display = 'flex';

    // Reset progress stats & timers (Item 15)
    genStartTime = Date.now();
    const msgEl = document.getElementById('status-msg');
    const stepText = document.getElementById('step-text');
    const elapsedText = document.getElementById('elapsed-text');
    const etaText = document.getElementById('eta-text');
    const barFill = document.getElementById('status-bar-fill');

    if (msgEl) msgEl.innerText = "Initializing neural pipeline...";
    if (stepText) stepText.innerText = `Step 0 / ${payload.steps}`;
    if (elapsedText) elapsedText.innerText = "0.0s elapsed";
    if (etaText) etaText.innerText = "Estimating...";

    // Start indeterminate animation until first step reports (Item 15)
    if (barFill) {
        barFill.classList.add('indeterminate');
        barFill.style.width = '40%';
    }

    // Live elapsed timer ticking every 100ms
    if (liveTimerInterval) clearInterval(liveTimerInterval);
    liveTimerInterval = setInterval(() => {
        const sec = ((Date.now() - genStartTime) / 1000).toFixed(1);
        const el = document.getElementById('elapsed-text');
        if (el) el.innerText = `${sec}s elapsed`;
    }, 100);

    // Smoothly scroll display section into view without clipping (Item 3)
    const displaySection = document.getElementById('display-section');
    if (displaySection) {
        displaySection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    refreshLucideIcons();

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

// Stop / Cancel Generation (Items 13 & 15)
function cancelGeneration() {
    if (pollingInterval) clearInterval(pollingInterval);
    if (liveTimerInterval) clearInterval(liveTimerInterval);

    const msgEl = document.getElementById('status-msg');
    if (msgEl) msgEl.innerText = "Stopping generation...";

    fetch('/api/cancel', { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            resetGenerateUI();
            const shimmer = document.getElementById('shimmer-placeholder');
            if (shimmer) shimmer.style.display = 'none';

            const previewContainer = document.getElementById('preview-container');
            const staleBadge = document.getElementById('previous-result-badge');
            if (previewContainer) previewContainer.classList.remove('is-stale');
            if (staleBadge) staleBadge.style.display = 'none';

            const mainPreview = document.getElementById('main-preview');
            if (!mainPreview || !mainPreview.src || !mainPreview.src.includes('/outputs/')) {
                const placeholder = document.getElementById('placeholder-view');
                if (placeholder) placeholder.style.display = 'flex';
            } else {
                const canvasOverlay = document.getElementById('canvas-overlay');
                if (canvasOverlay) canvasOverlay.style.display = 'flex';
            }
        })
        .catch(() => resetGenerateUI());
}

// Poll Generation Status (Item 15)
function pollStatus() {
    if (pollingInterval) clearInterval(pollingInterval);
    
    pollingInterval = setInterval(() => {
        fetch('/api/status')
            .then(r => r.json())
            .then(st => {
                const msgEl = document.getElementById('status-msg');
                if (msgEl && st.message) msgEl.innerText = st.message;
                
                const stepText = document.getElementById('step-text');
                const etaText = document.getElementById('eta-text');
                const barFill = document.getElementById('status-bar-fill');

                const curStep = st.current_step || 0;
                const totalSteps = st.total_steps || 1;
                const elapsedSec = (Date.now() - genStartTime) / 1000;

                // Once step 1 or more reports, switch from indeterminate to measured progress (Item 15)
                if (curStep > 0 && barFill) {
                    barFill.classList.remove('indeterminate');
                    barFill.style.width = `${st.progress || 0}%`;
                }

                if (stepText) {
                    stepText.innerText = `Step ${curStep} / ${totalSteps}`;
                }

                // Estimated time remaining (Item 15)
                if (etaText) {
                    if (curStep > 0 && curStep < totalSteps) {
                        const secPerStep = elapsedSec / curStep;
                        const remainingSec = Math.max(0, Math.round(secPerStep * (totalSteps - curStep)));
                        etaText.innerText = `~${remainingSec}s remaining`;
                    } else if (curStep >= totalSteps) {
                        etaText.innerText = "Finalizing image...";
                    } else {
                        etaText.innerText = "Estimating...";
                    }
                }

                updateSystemStats();

                if (st.status === 'complete') {
                    clearInterval(pollingInterval);
                    if (liveTimerInterval) clearInterval(liveTimerInterval);
                    resetGenerateUI();
                    showPreview(`/outputs/${st.output_image}`);
                    loadGallery();
                } else if (st.status === 'error') {
                    clearInterval(pollingInterval);
                    if (liveTimerInterval) clearInterval(liveTimerInterval);
                    alert('Generation Failed:\n' + st.error);
                    resetGenerateUI();
                } else if (st.status === 'idle') {
                    // Cancelled or stopped
                    clearInterval(pollingInterval);
                    if (liveTimerInterval) clearInterval(liveTimerInterval);
                    resetGenerateUI();
                }
            })
            .catch(err => console.warn('Status poll error:', err));
    }, 600);
}

function resetGenerateUI() {
    if (pollingInterval) clearInterval(pollingInterval);
    if (liveTimerInterval) clearInterval(liveTimerInterval);

    const btnGen = document.getElementById('btn-generate');
    const btnStop = document.getElementById('btn-stop');
    if (btnGen) {
        btnGen.style.display = 'inline-flex';
        btnGen.disabled = false;
    }
    if (btnStop) btnStop.style.display = 'none';

    const progressCard = document.getElementById('progress-card');
    if (progressCard) progressCard.style.display = 'none';
    
    refreshLucideIcons();
}

// Show Preview (Item 4)
function showPreview(url, metadata = {}) {
    document.body.classList.add('active-generation-mode');
    updateComposerBottomPadding();
    currentImageMeta = metadata;

    const placeholder = document.getElementById('placeholder-view');
    if (placeholder) placeholder.style.display = 'none';

    const shimmer = document.getElementById('shimmer-placeholder');
    if (shimmer) shimmer.style.display = 'none';

    const previewContainer = document.getElementById('preview-container');
    const staleBadge = document.getElementById('previous-result-badge');
    if (previewContainer) {
        previewContainer.style.display = 'block';
        previewContainer.classList.remove('is-stale'); // Full opacity
    }
    if (staleBadge) staleBadge.style.display = 'none';
    
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
    downloadImageFromUrl(img.src);
}

function downloadImageFromUrl(url) {
    if (!url) return;
    const a = document.createElement('a');
    a.href = url;
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

// Gallery & Recent Generations Grid (Items 16 & 17)
function loadGallery() {
    fetch('/api/gallery')
        .then(r => r.json())
        .then(data => {
            const grid = document.getElementById('gallery-grid');
            const dockGrid = document.getElementById('recent-dock-grid');
            const countHint = document.getElementById('gallery-count-hint');
            
            if (grid) grid.innerHTML = '';
            if (dockGrid) dockGrid.innerHTML = '';

            const images = data.images || [];
            if (countHint) {
                countHint.innerText = `${images.length} generation${images.length === 1 ? '' : 's'}`;
            }

            // Item 17: Empty State
            if (images.length === 0) {
                if (grid) {
                    grid.innerHTML = `
                        <div class="gallery-empty-state">
                            <i data-lucide="image"></i>
                            <h3>No generations yet</h3>
                            <p>Your generated visuals will appear here. Enter a prompt above and click <strong>Generate</strong> to render your first masterpiece.</p>
                        </div>
                    `;
                }
                if (dockGrid) {
                    dockGrid.innerHTML = `<div class="empty-gallery-hint"><i data-lucide="sparkles"></i><span>No recent generations yet. Type a prompt above to render your first visual!</span></div>`;
                }
            } else {
                // Item 17: Responsive CSS grid with fixed aspect-ratio thumbnails & hover actions (open, download, delete)
                images.forEach(imgData => {
                    const promptText = (imgData.metadata && imgData.metadata.prompt) ? imgData.metadata.prompt : 'Generated Visual';
                    const filename = imgData.filename || imgData.url.split('/').pop();

                    if (grid) {
                        const card = document.createElement('div');
                        card.className = 'gallery-card';
                        card.title = promptText;
                        card.setAttribute('tabindex', '0');
                        card.setAttribute('role', 'button');
                        card.setAttribute('aria-label', `View generation: ${promptText}`);

                        // Click to enlarge (Item 17)
                        card.onclick = (e) => {
                            if (e.target.closest('.gallery-action-btn')) return;
                            openLightbox(imgData.url, promptText);
                        };
                        card.onkeydown = (e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                                if (e.target.closest('.gallery-action-btn')) return;
                                openLightbox(imgData.url, promptText);
                            }
                        };

                        card.innerHTML = `
                            <img src="${imgData.url}" alt="${promptText}" class="gallery-thumb" loading="lazy">
                            <div class="gallery-card-overlay">
                                <div class="gallery-overlay-actions">
                                    <button type="button" class="gallery-action-btn btn-open" title="Enlarge image" aria-label="Enlarge image" onclick="openLightbox('${imgData.url}', '${promptText.replace(/'/g, "\\'")}')">
                                        <i data-lucide="maximize-2"></i>
                                    </button>
                                    <button type="button" class="gallery-action-btn btn-download" title="Download image" aria-label="Download image" onclick="downloadImageFromUrl('${imgData.url}')">
                                        <i data-lucide="download"></i>
                                    </button>
                                    <button type="button" class="gallery-action-btn btn-delete" title="Delete image" aria-label="Delete image" onclick="deleteGeneratedImage('${filename}', event)">
                                        <i data-lucide="trash-2"></i>
                                    </button>
                                </div>
                                <div class="gallery-card-prompt">${promptText}</div>
                            </div>
                        `;
                        grid.appendChild(card);
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
            updateComposerBottomPadding();
        })
        .catch(err => console.warn('Could not load gallery:', err));
}

// Delete Image from Gallery (Item 17)
function deleteGeneratedImage(filename, event) {
    if (event) event.stopPropagation();
    if (!confirm(`Are you sure you want to delete this image?`)) return;

    fetch('/api/delete-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: filename })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            // Check if current preview was this image
            const mainPreview = document.getElementById('main-preview');
            if (mainPreview && mainPreview.src.includes(filename)) {
                mainPreview.src = '';
                const previewContainer = document.getElementById('preview-container');
                if (previewContainer) previewContainer.style.display = 'none';
                const overlay = document.getElementById('canvas-overlay');
                if (overlay) overlay.style.display = 'none';
                const placeholder = document.getElementById('placeholder-view');
                if (placeholder) placeholder.style.display = 'flex';
            }
            loadGallery();
        }
    })
    .catch(err => alert('Failed to delete image: ' + err));
}

// Fullscreen Lightbox Modal (Item 17)
function openLightbox(url, prompt) {
    activeLightboxData = { url, prompt };
    const modal = document.getElementById('lightbox-modal');
    const img = document.getElementById('lightbox-img');
    const promptEl = document.getElementById('lightbox-prompt');

    if (modal && img) {
        img.src = url;
        if (promptEl) promptEl.innerText = prompt || 'Generated Visual';
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
        refreshLucideIcons();
    }
}

function openLightboxFromPreview() {
    const img = document.getElementById('main-preview');
    const promptInput = document.getElementById('prompt');
    const text = (currentImageMeta && currentImageMeta.prompt) ? currentImageMeta.prompt : (promptInput ? promptInput.value : '');
    if (img && img.src) {
        openLightbox(img.src, text);
    }
}

function closeLightbox(e) {
    if (e) e.stopPropagation();
    const modal = document.getElementById('lightbox-modal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

function downloadLightboxImage() {
    if (activeLightboxData.url) {
        downloadImageFromUrl(activeLightboxData.url);
    }
}

function copyLightboxPrompt() {
    if (activeLightboxData.prompt) {
        navigator.clipboard.writeText(activeLightboxData.prompt).then(() => {
            alert('Prompt copied to clipboard!');
        });
    }
}

// Close lightbox on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeLightbox();
    }
});

// Mobile Telemetry HUD Toggle (Item 5)
function toggleMobileHud() {
    const hud = document.getElementById('telemetry-hud');
    if (hud) {
        hud.classList.toggle('mobile-open');
    }
}

document.addEventListener('click', (e) => {
    if (!e.target.closest('#telemetry-hud') && !e.target.closest('.mobile-hud-toggle')) {
        const hud = document.getElementById('telemetry-hud');
        if (hud) hud.classList.remove('mobile-open');
    }
});

// Window resize listener to recalculate padding
window.addEventListener('resize', () => {
    updateComposerBottomPadding();
});

// Initial Boot Logic
document.addEventListener('DOMContentLoaded', () => {
    setupAutoGrowPrompt();
    updateSystemStats();
    refreshModels();
    loadGallery();
    loadSavedSettings();
    evaluateProTipVisibility();
    updateComposerBottomPadding();
    refreshLucideIcons();

    // Resize observer on prompt dock for responsive bottom padding (Item 1)
    const dockEl = document.getElementById('prompt-dock');
    if (dockEl && window.ResizeObserver) {
        new ResizeObserver(() => updateComposerBottomPadding()).observe(dockEl);
    }

    setInterval(updateSystemStats, 3000);
});

import os
import json
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
settings_lock = threading.RLock()

DEFAULT_SETTINGS = {
    "model_path": None,
    "quality_preset": "photorealistic",
    "auto_enhance": True,
    "negative_prompt": "",
    "steps": 1,
    "cfg_scale": 1.0,
    "sampler": "Euler",
    "seed": -1,
    "width": 512,
    "height": 512,
    "aspect_ratio": "1:1",
    "opt_cpu_offload": True,
    "opt_vae_tiling": True,
    "opt_attn_slicing": True,
    "opt_fp16": True
}

_cached_settings = None

def get_settings():
    """Retrieves current EdgeMind settings from settings.json or defaults."""
    global _cached_settings
    with settings_lock:
        if _cached_settings is not None:
            return dict(_cached_settings)

        settings = dict(DEFAULT_SETTINGS)
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        settings.update(loaded)
            except Exception as e:
                print(f"[EdgeMind] Warning: Could not read settings.json ({e}). Using defaults.")
        
        _cached_settings = settings
        return dict(_cached_settings)

def update_settings(updates):
    """Updates current EdgeMind settings and persists them to settings.json."""
    global _cached_settings
    with settings_lock:
        current = get_settings()
        if isinstance(updates, dict):
            for k, v in updates.items():
                if k in DEFAULT_SETTINGS or k == "model_path":
                    current[k] = v
        
        _cached_settings = current
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(_cached_settings, f, indent=4)
        except Exception as e:
            print(f"[EdgeMind] Error saving settings.json: {e}")
            
        return dict(_cached_settings)

def get_active_model_path(models_dir=None):
    """
    Resolves the active model path in EdgeMind:
    1. Currently loaded model in memory.
    2. Configured model_path in settings.json (if exists on disk).
    3. First available model checkpoint in the models directory.
    """
    from engine.model_manager import current_model_info, scan_models

    # 1. Currently loaded model in engine
    if current_model_info.get("loaded") and current_model_info.get("path"):
        return current_model_info["path"]

    # 2. Configured model in settings
    settings = get_settings()
    configured_model = settings.get("model_path")
    if configured_model and os.path.exists(configured_model):
        return configured_model

    # 3. Fast direct check in models_dir
    if models_dir is None:
        models_dir = os.path.join(BASE_DIR, "models")
    if os.path.exists(models_dir):
        for item in os.listdir(models_dir):
            if item.endswith((".safetensors", ".ckpt")) and "hyper" not in item.lower():
                return os.path.join(models_dir, item)
            sub = os.path.join(models_dir, item)
            if os.path.isdir(sub) and os.path.exists(os.path.join(sub, "model_index.json")):
                return sub

    # 4. Fallback to full multi-directory scanned models
    scanned = scan_models(models_dir)
    if scanned:
        return scanned[0]["path"]

    return None

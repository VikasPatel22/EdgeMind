import os
import gc
import time
import json
import torch
import traceback
import threading
from engine.telemetry import get_hardware_specs

# Global State for Model & Downloads
current_model_info = {
    "path": None,
    "name": None,
    "precision": None,
    "device": None,
    "loaded": False,
    "pipeline": None,
    "profile": "Unknown",
    "hyper_sd_active": False,
    "hyper_sd_path": None
}

def find_hyper_sd_lora(model_path=""):
    """Finds Hyper-SD 1-step LoRA safetensors file in models directory, environment variables, or adjacent paths."""
    candidates = []
    
    # 1. Environment variable check
    env_hyper = os.environ.get("HYPER_SD_LORA_PATH")
    if env_hyper and os.path.exists(env_hyper):
        candidates.append(env_hyper)

    # 2. Check edgemind/models directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(base_dir, "models")
    if os.path.exists(models_dir):
        # Direct filename match
        direct_candidate = os.path.join(models_dir, "Hyper-SD15-1step-lora.safetensors")
        if os.path.exists(direct_candidate):
            candidates.append(direct_candidate)

        for f in os.listdir(models_dir):
            if f.endswith(".safetensors") and ("hyper" in f.lower() or "1step" in f.lower()):
                candidate_path = os.path.join(models_dir, f)
                if candidate_path not in candidates:
                    candidates.append(candidate_path)
                
    # 3. Check custom models directory from environment
    custom_models_dir = os.environ.get("EDGEMIND_MODELS_DIR") or os.environ.get("MODELS_DIR")
    if custom_models_dir and os.path.exists(custom_models_dir):
        for f in os.listdir(custom_models_dir):
            if f.endswith(".safetensors") and ("hyper" in f.lower() or "1step" in f.lower()):
                candidate_path = os.path.join(custom_models_dir, f)
                if candidate_path not in candidates:
                    candidates.append(candidate_path)

    # 4. Check directory of current model_path if provided
    if model_path and os.path.isfile(model_path):
        model_dir = os.path.dirname(model_path)
        if os.path.exists(model_dir):
            for f in os.listdir(model_dir):
                if f.endswith(".safetensors") and ("hyper" in f.lower() or "1step" in f.lower()):
                    candidate_path = os.path.join(model_dir, f)
                    if candidate_path not in candidates:
                        candidates.append(candidate_path)
                
    # 5. Local workspace fallback if explicit file exists
    explicit_hyper = r"C:\Users\vikas\Desktop\Vikas Patel\Project Vorenthos-4\edgemind\models\Hyper-SD15-1step-lora.safetensors"
    if os.path.exists(explicit_hyper) and explicit_hyper not in candidates:
        candidates.append(explicit_hyper)

    return candidates[0] if candidates else None


download_status = {
    "status": "idle", # idle, downloading, complete, error
    "progress": 0, # 0 to 100
    "message": "No active downloads.",
    "repo_id": None,
    "downloaded_mb": 0.0,
    "total_mb": 0.0,
    "speed_mbps": 0.0,
    "current_file": "",
    "error": None
}

def is_video_model(root, files):
    """Checks whether a folder or checkpoint is for video generation rather than image generation."""
    norm_root = root.replace("\\", "/").lower()
    video_keywords = ["video", "animatediff", "cogvideo", "hunyuanvideo", "ltx", "svd", "stable-video", "mochi", "wan-2", "wan2"]
    if any(k in norm_root for k in video_keywords):
        return True

    if "model_index.json" in files:
        try:
            with open(os.path.join(root, "model_index.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
                class_name = str(data.get("_class_name", "")).lower()
                if any(k in class_name for k in ["video", "animate", "ltx", "svd", "cogvideo", "hunyuan"]):
                    return True
                for k, v in data.items():
                    if isinstance(v, list) and len(v) >= 2:
                        comp_class = str(v[1]).lower()
                        if "video" in comp_class or "3d" in comp_class:
                            return True
        except Exception:
            pass

    return False

def scan_models(models_dir):
    """Scans local directories for downloaded image models (.safetensors, .ckpt, Diffusers format), excluding LoRA adapters and video generation models."""
    found_models = []
    seen_paths = set()
    
    scan_paths = []
    if models_dir and os.path.exists(models_dir):
        scan_paths.append(models_dir)

    # Environment variable custom directory (Linux, macOS, Windows)
    custom_models_env = os.environ.get("EDGEMIND_MODELS_DIR") or os.environ.get("MODELS_DIR")
    if custom_models_env and os.path.exists(custom_models_env) and custom_models_env not in scan_paths:
        scan_paths.append(custom_models_env)
    
    # Hugging Face default cache
    hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
    if os.path.exists(hf_cache) and hf_cache not in scan_paths:
        scan_paths.append(hf_cache)

    # Cross-platform common WebUI, Fooocus, and ComfyUI checkpoints
    home_dir = os.path.expanduser("~")
    common_search_paths = [
        # Linux & macOS home directories
        os.path.join(home_dir, "stable-diffusion-webui", "models", "Stable-diffusion"),
        os.path.join(home_dir, "Fooocus", "models", "checkpoints"),
        os.path.join(home_dir, "ComfyUI", "models", "checkpoints"),
        os.path.join(home_dir, "models"),
        # Windows default paths
        "C:/stable-diffusion-webui/models/Stable-diffusion",
        "C:/Fooocus/models/checkpoints",
        "C:/ComfyUI/models/checkpoints",
        "D:/stable-diffusion-webui/models/Stable-diffusion",
        "D:/Fooocus/models/checkpoints",
        "D:/ComfyUI/models/checkpoints",
        # Linux /opt paths
        "/opt/stable-diffusion-webui/models/Stable-diffusion",
        "/opt/ComfyUI/models/checkpoints"
    ]
    for p in common_search_paths:
        if os.path.exists(p) and p not in scan_paths:
            scan_paths.append(p)

    for base_path in scan_paths:
        if not os.path.exists(base_path):
            continue

        for root, dirs, files in os.walk(base_path):
            # Exclude video generation models (e.g. LTX-Video, CogVideoX, SVD)
            if is_video_model(root, files):
                dirs.clear()
                continue

            # Check if this directory is a diffusers model
            if "model_index.json" in files:
                if root in seen_paths:
                    dirs.clear()
                    continue
                seen_paths.add(root)
                
                # Derive a clean human-readable name for diffusers folders
                clean_name = os.path.basename(root)
                
                # Handle Hugging Face hub cache paths (e.g. models--org--repo/snapshots/hash)
                norm_root = root.replace("\\", "/")
                if "models--" in norm_root:
                    parts = norm_root.split("/")
                    for p in parts:
                        if p.startswith("models--"):
                            repo_parts = p.replace("models--", "").split("--")
                            if len(repo_parts) >= 2:
                                clean_name = f"{repo_parts[0]}/{repo_parts[1]}"
                            else:
                                clean_name = repo_parts[0]
                            break

                found_models.append({
                    "name": clean_name,
                    "path": root,
                    "type": "Diffusers Folder",
                    "format": "diffusers"
                })
                dirs.clear()
                continue
            
            for file in files:
                file_lower = file.lower()
                # Exclude LoRAs and 1-step adapters from base model selector
                if "lora" in file_lower or "hyper-sd" in file_lower or file_lower.endswith(".lora.safetensors"):
                    continue

                if any(k in file_lower for k in ["video", "animatediff", "cogvideo", "hunyuanvideo", "svd"]):
                    continue

                if file.endswith((".safetensors", ".ckpt")):
                    full_path = os.path.join(root, file)
                    if full_path in seen_paths:
                        continue
                    seen_paths.add(full_path)
                    
                    found_models.append({
                        "name": file,
                        "path": full_path,
                        "type": "Single File Checkpoint",
                        "format": "safetensors" if file.endswith(".safetensors") else "ckpt"
                    })

    return found_models

# Model Keep-Alive & Auto-Unload Timer State
model_timer_lock = threading.Lock()
model_unload_timer = None
model_auto_unload_time = None

def cancel_auto_unload_timer():
    """Cancels any pending auto-unload countdown."""
    global model_unload_timer, model_auto_unload_time
    with model_timer_lock:
        if model_unload_timer is not None:
            try:
                model_unload_timer.cancel()
            except Exception:
                pass
            model_unload_timer = None
        model_auto_unload_time = None

def schedule_auto_unload(mins):
    """
    Schedules an automatic model unload after `mins` minutes of inactivity.
    If mins <= 0: unloads immediately.
    If mins is None: leaves loaded without timer.
    """
    global model_unload_timer, model_auto_unload_time
    cancel_auto_unload_timer()
    
    if mins is None:
        return None
        
    try:
        mins = float(mins)
    except (ValueError, TypeError):
        return None
        
    if mins <= 0:
        unload_model()
        return "unloaded_now"
        
    seconds = mins * 60.0
    with model_timer_lock:
        model_auto_unload_time = time.time() + seconds
        
        def timer_callback():
            print(f"[EdgeMind] Auto-unload timer expired ({mins} mins). Unloading model...")
            unload_model()
            
        model_unload_timer = threading.Timer(seconds, timer_callback)
        model_unload_timer.daemon = True
        model_unload_timer.start()
        
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(model_auto_unload_time))

def get_model_lifecycle_status():
    """Returns the current model memory status and auto-unload countdown."""
    global model_auto_unload_time
    is_loaded = current_model_info.get("loaded", False)
    remaining_secs = 0
    unload_at = None
    if is_loaded and model_auto_unload_time:
        remaining_secs = max(0, int(model_auto_unload_time - time.time()))
        unload_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(model_auto_unload_time))
    return {
        "loaded": is_loaded,
        "model": current_model_info.get("name"),
        "path": current_model_info.get("path"),
        "hyper_sd_active": current_model_info.get("hyper_sd_active", False),
        "auto_unload_at": unload_at,
        "remaining_seconds": remaining_secs,
        "remaining_minutes": round(remaining_secs / 60.0, 1) if remaining_secs > 0 else 0
    }

def unload_model():
    """Smart offloading: Frees GPU VRAM and clears CUDA / System memory."""
    global current_model_info
    cancel_auto_unload_timer()
    if current_model_info["pipeline"] is not None:
        try:
            del current_model_info["pipeline"]
        except Exception:
            pass
    
    current_model_info["pipeline"] = None
    current_model_info["path"] = None
    current_model_info["name"] = None
    current_model_info["loaded"] = False
    current_model_info["hyper_sd_active"] = False
    current_model_info["hyper_sd_path"] = None
    
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

def load_diffusers_pipeline(model_path, precision="fp16", cpu_offload=True, vae_tiling=True, attention_slicing=True):
    """Loads a Diffusers pipeline with automated optimizations and Hyper-SD 1-step acceleration."""
    global current_model_info
    
    unload_model()
    specs = get_hardware_specs()
    device = specs["device"]

    dtype = torch.float32
    if precision == "fp16" and device in ["cuda", "mps"]:
        dtype = torch.float16
    elif precision == "bf16" and device in ["cuda", "mps"]:
        dtype = torch.bfloat16

    try:
        from diffusers import AutoPipelineForText2Image, StableDiffusionPipeline, StableDiffusionXLPipeline

        if os.path.isfile(model_path):
            if "xl" in model_path.lower():
                pipe = StableDiffusionXLPipeline.from_single_file(
                    model_path, 
                    torch_dtype=dtype,
                    use_safetensors=model_path.endswith(".safetensors")
                )
            else:
                pipe = StableDiffusionPipeline.from_single_file(
                    model_path, 
                    torch_dtype=dtype,
                    use_safetensors=model_path.endswith(".safetensors")
                )
        else:
            try:
                pipe = AutoPipelineForText2Image.from_pretrained(
                    model_path,
                    torch_dtype=dtype,
                    use_safetensors=True
                )
            except Exception as se:
                print(f"[EdgeMind] Notice: Loading with use_safetensors=True failed ({se}). Retrying auto-detection...")
                pipe = AutoPipelineForText2Image.from_pretrained(
                    model_path,
                    torch_dtype=dtype
                )

        # Automatic Hyper-SD 1-Step LoRA integration for Lightning Fast Generation
        hyper_sd_active = False
        hyper_sd_path = find_hyper_sd_lora(model_path)

        if hyper_sd_path and not ("xl" in model_path.lower() or "sdxl" in str(type(pipe)).lower()):
            try:
                print(f"[EdgeMind] [FAST] Applying Hyper-SD 1-Step LoRA from: {hyper_sd_path}")
                pipe.load_lora_weights(hyper_sd_path)
                if hasattr(pipe, "fuse_lora"):
                    try:
                        pipe.fuse_lora(lora_scale=1.0)
                    except Exception as fe:
                        print(f"[EdgeMind] LoRA fuse notice: {fe}")

                from diffusers import EulerDiscreteScheduler
                pipe.scheduler = EulerDiscreteScheduler.from_config(
                    pipe.scheduler.config,
                    timestep_spacing="trailing"
                )
                hyper_sd_active = True
                print("[EdgeMind] [FAST] Hyper-SD 1-Step LoRA applied successfully!")
            except Exception as le:
                print(f"[EdgeMind] Warning: Could not apply Hyper-SD LoRA: {le}")

        if device == "cuda":
            if cpu_offload:
                try:
                    pipe.enable_model_cpu_offload()
                except Exception:
                    pipe.enable_sequential_cpu_offload()
            else:
                pipe = pipe.to("cuda")

            if vae_tiling and hasattr(pipe, "enable_vae_tiling"):
                pipe.enable_vae_tiling()
            
            if attention_slicing and hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing()
        else:
            pipe = pipe.to(device)

        current_model_info["pipeline"] = pipe
        current_model_info["path"] = model_path
        current_model_info["name"] = os.path.basename(model_path)
        current_model_info["precision"] = precision
        current_model_info["device"] = device
        current_model_info["loaded"] = True
        current_model_info["profile"] = specs["profile"]
        current_model_info["hyper_sd_active"] = hyper_sd_active
        current_model_info["hyper_sd_path"] = hyper_sd_path if hyper_sd_active else None

        msg = "Model loaded successfully with Hyper-SD 1-Step Fast Generation!" if hyper_sd_active else "Model loaded successfully."
        return True, msg
    except Exception as e:
        err_msg = f"Failed to load model: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        unload_model()
        return False, err_msg


# Optimize PyTorch CPU Multi-threading & GPU TF32 acceleration
try:
    import psutil
    cpu_cores = psutil.cpu_count(logical=True) or 4
    torch.set_num_threads(cpu_cores)
    if hasattr(torch, 'set_num_interop_threads'):
        torch.set_num_interop_threads(max(2, cpu_cores // 2))
except Exception:
    pass

if torch.cuda.is_available():
    try:
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
    except Exception as _e:
        pass
def parse_hf_url(url_or_repo):
    """Extracts clean HuggingFace repo_id from full URL or repo string."""
    clean = url_or_repo.strip()
    if clean.startswith("https://huggingface.co/"):
        clean = clean.replace("https://huggingface.co/", "")
    elif clean.startswith("huggingface.co/"):
        clean = clean.replace("huggingface.co/", "")
        
    parts = clean.split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return clean

class RealtimeHFProgressTracker:
    """Monitors directory download growth in real-time to compute speed and progress percentage."""
    def __init__(self, target_dir):
        self.target_dir = target_dir
        self.running = False
        self.thread = None

    def _monitor(self):
        start_time = time.time()
        prev_size = 0
        
        while self.running:
            time.sleep(1.0)
            current_size = 0
            if os.path.exists(self.target_dir):
                for root, _, files in os.walk(self.target_dir):
                    for f in files:
                        try:
                            fp = os.path.join(root, f)
                            current_size += os.path.getsize(fp)
                        except Exception:
                            pass
            
            elapsed = max(1.0, time.time() - start_time)
            bytes_added = max(0, current_size - prev_size)
            speed_mbps = round((bytes_added / (1024 * 1024)), 2) # MB/s in last second
            prev_size = current_size
            
            downloaded_mb = round(current_size / (1024 * 1024), 2)
            
            # Estimate percentage based on typical model sizes if total unknown
            download_status["downloaded_mb"] = downloaded_mb
            download_status["speed_mbps"] = speed_mbps
            download_status["message"] = f"Downloaded {downloaded_mb} MB ({speed_mbps} MB/s)"

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._monitor)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False

def run_hf_download_task(repo_id, models_dir):
    global download_status
    download_status["status"] = "downloading"
    download_status["progress"] = 5
    download_status["repo_id"] = repo_id
    download_status["message"] = f"Connecting to HuggingFace for {repo_id}..."
    download_status["downloaded_mb"] = 0.0
    download_status["speed_mbps"] = 0.0
    download_status["error"] = None

    folder_name = repo_id.replace("/", "--")
    target_dir = os.path.join(models_dir, folder_name)

    tracker = RealtimeHFProgressTracker(target_dir)
    tracker.start()

    try:
        from huggingface_hub import snapshot_download
        download_status["progress"] = 15
        
        snapshot_download(
            repo_id=repo_id,
            local_dir=target_dir,
            local_dir_use_symlinks=False,
            ignore_patterns=["*.msgpack", "*.h5", "*.ot", "*.onnx"]
        )

        tracker.stop()
        download_status["status"] = "complete"
        download_status["progress"] = 100
        download_status["message"] = f"Successfully downloaded {repo_id}!"
    except Exception as e:
        tracker.stop()
        err_msg = f"Download failed: {str(e)}"
        print(err_msg)
        download_status["status"] = "error"
        download_status["error"] = err_msg

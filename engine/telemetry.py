import torch
import psutil

def get_hardware_specs():
    """Detects CPU, RAM, GPU, VRAM and computes optimal execution profile."""
    cpu_count = psutil.cpu_count(logical=True)
    cpu_percent = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    ram_total_gb = round(ram.total / (1024 ** 3), 2)
    ram_used_gb = round(ram.used / (1024 ** 3), 2)
    ram_percent = ram.percent

    device_type = "cpu"
    device_name = "System CPU"
    vram_total_gb = 0.0
    vram_used_gb = 0.0
    vram_free_gb = 0.0

    if torch.cuda.is_available():
        device_type = "cuda"
        device_name = torch.cuda.get_device_name(0)
        vram_total_bytes = torch.cuda.get_device_properties(0).total_memory
        vram_allocated_bytes = torch.cuda.memory_allocated(0)
        vram_reserved_bytes = torch.cuda.memory_reserved(0)
        
        vram_total_gb = round(vram_total_bytes / (1024 ** 3), 2)
        vram_used_gb = round((vram_allocated_bytes + vram_reserved_bytes) / (1024 ** 3), 2)
        vram_free_gb = round(max(0.0, vram_total_gb - vram_used_gb), 2)
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device_type = "mps"
        device_name = "Apple Silicon (MPS)"
        vram_total_gb = ram_total_gb
        vram_used_gb = ram_used_gb
        vram_free_gb = round(ram_total_gb - ram_used_gb, 2)
    elif hasattr(torch, 'xpu') and torch.xpu.is_available():
        device_type = "xpu"
        device_name = "Intel Graphics (XPU)"

    # Auto Profile Recommendation
    if device_type == "cpu":
        profile = "Low VRAM (CPU)"
        rec_precision = "fp32"
        cpu_offload = True
        vae_tiling = True
        attention_slicing = True
    elif vram_total_gb < 4.5:
        profile = "Low VRAM (<4GB)"
        rec_precision = "fp16"
        cpu_offload = True
        vae_tiling = True
        attention_slicing = True
    elif vram_total_gb < 8.5:
        profile = "Medium VRAM (4-8GB)"
        rec_precision = "fp16"
        cpu_offload = True
        vae_tiling = True
        attention_slicing = False
    elif vram_total_gb < 16.5:
        profile = "High VRAM (8-16GB)"
        rec_precision = "fp16"
        cpu_offload = False
        vae_tiling = False
        attention_slicing = False
    else:
        profile = "Ultra VRAM (>16GB)"
        rec_precision = "fp16"
        cpu_offload = False
        vae_tiling = False
        attention_slicing = False

    return {
        "device": device_type,
        "device_name": device_name,
        "cpu_count": cpu_count,
        "cpu_percent": cpu_percent,
        "ram_total_gb": ram_total_gb,
        "ram_used_gb": ram_used_gb,
        "ram_percent": ram_percent,
        "vram_total_gb": vram_total_gb,
        "vram_used_gb": vram_used_gb,
        "vram_free_gb": vram_free_gb,
        "profile": profile,
        "rec_precision": rec_precision,
        "rec_cpu_offload": cpu_offload,
        "rec_vae_tiling": vae_tiling,
        "rec_attention_slicing": attention_slicing
    }

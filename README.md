# 🚀 EdgeMind AI Studio

**EdgeMind** is a self-optimizing, single-file local AI image generation studio built with Python Flask and a cybernetic dark-mode HTML5/CSS3 dashboard. It is engineered to load, optimize, and run any local or Hugging Face text-to-image model (ranging from 1B to 1T parameter architectures including SD 1.5, SD 2.1, SDXL, Flux, and SD3) without overflowing system VRAM or RAM.

---

## ✨ Features

- **All-in-One Architecture**: Python Flask backend and cybernetic dark-mode web dashboard integrated into a single file (`app.py`).
- **Hugging Face Downloader**: Download any model directly from Hugging Face by pasting its full URL (e.g., `https://huggingface.co/runwayml/stable-diffusion-v1-5`) or Repo ID into the UI.
- **Hardware Telemetry & Auto-Optimization**:
  - Live probing of CPU Cores, System RAM, and GPU VRAM (NVIDIA CUDA, AMD ROCm, Apple Silicon MPS, or CPU).
  - Multi-tier optimization profiles:
    - 🟢 `Ultra VRAM` (>16GB VRAM)
    - 🔵 `High VRAM` (8–16GB VRAM)
    - 🟡 `Medium VRAM` (4–8GB VRAM): Auto Model CPU Offloading & VAE Tiling
    - 🟠 `Low VRAM` (<4GB VRAM or CPU): Sequential CPU Offloading, VAE Tiling & Attention Slicing
- **Smart Memory Lifecycle Manager**:
  - Automatic VRAM model swapping and memory garbage collection (`torch.cuda.empty_cache()` & `gc.collect()`).
- **Configurable Inference Parameters**:
  - Prompt & Negative Prompt textareas
  - Width & Height (256px to 2048px with quick presets)
  - Inference Steps (1–150)
  - Guidance Scale / CFG (1–30)
  - Samplers / Schedulers (Euler, Euler Ancestral, DPM++ 2M, UniPC, DDIM, Heun)
  - Precision modes (`FP16`, `BF16`, `FP32`)
  - Random or fixed Seed locking
- **Gallery & PNG Metadata**:
  - Automatically saves generated images to `./outputs/` with PNG metadata chunks storing prompt, seed, model, sampler, and CFG scale.

---

## 🛠️ Quick Start

### 1. Requirements
Ensure you have **Python 3.10+** and optionally an NVIDIA GPU with PyTorch CUDA installed.

Must have **models/Hyper-SD15-1step-lora.safetensors** installed for single step generation

```bash
cd edgemind
pip install -r requirements.txt
```

### 2. Run EdgeMind
- **Windows**: Double click `start.bat` or run:
  ```cmd
  python app.py
  ```
- **Linux / macOS**:
  ```bash
  chmod +x start.sh
  ./start.sh
  ```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 📁 Model Scanning & Storage

EdgeMind automatically scans the following locations for `.safetensors`, `.ckpt`, or Diffusers format checkpoint directories:
1. `./edgemind/models/` (Local model folder)
2. `~/.cache/huggingface/hub/` (Hugging Face default cache)
3. Common WebUI checkpoint paths if present on your machine.

---

## 📄 License & Credits

Built as part of **Vorenthic Labs** technology suite. Precision, control, and scalability in edge AI computing.

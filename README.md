# 🚀 EdgeMind AI Studio

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-ee4c2c.svg)](https://pytorch.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000.svg)](https://palletsprojects.com/p/flask/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](#-platform--hardware-support)
[![Hardware](https://img.shields.io/badge/Hardware-NVIDIA%20CUDA%20%7C%20Apple%20MPS%20%7C%20AMD%20ROCm%20%7C%20CPU-success.svg)](#-platform--hardware-support)

**A high-performance, self-optimizing local AI image generation studio and REST API engine.**  
Engineered to run seamlessly across any operating system, custom hardware configuration, or path setup without overflowing VRAM or system memory.

[Features](#-key-features) • [Platform Support](#-platform--hardware-support) • [Installation](#-installation--setup) • [Model Management](#-model-setup--scanning) • [REST API](#-rest-api--developer-integration) • [Configuration](#-configuration--environment-variables) • [Troubleshooting](#-troubleshooting)

</div>

---

## ✨ Key Features

- **🌐 Cross-Platform & Universal Paths**: Runs natively on **Windows**, **Linux**, and **macOS** (including Apple Silicon M-series). Automatically discovers models across custom directories, environment variables, Hugging Face caches, and external WebUI installations.
- **⚡ 1-Step Hyper-SD Acceleration**: Generates photorealistic high-fidelity images in just **1 inference step** with zero quality loss using Hyper-SD LoRA optimization.
- **🧠 Hardware Telemetry & Dynamic Profiling**:
  - Live hardware probing for CPU cores, available system RAM, and GPU VRAM.
  - Automatic selection of optimization profiles:
    - 🟢 **Ultra VRAM** (>16GB VRAM): Full pipeline caching and native batch processing.
    - 🔵 **High VRAM** (8–16GB VRAM): FP16 / BF16 mixed-precision acceleration.
    - 🟡 **Medium VRAM** (4–8GB VRAM): Automated model CPU offloading and VAE tiling.
    - 🟠 **Low VRAM / CPU** (<4GB VRAM): Sequential sub-module CPU offloading, VAE slicing, and attention slicing.
- **🧹 Zero-Leak Memory Lifecycle Manager**:
  - Configurable auto-unload timers (1m, 5m, 15m, 30m, 60m, or keep active).
  - Explicit cache eviction (`torch.cuda.empty_cache()`, `torch.cuda.ipc_collect()`, and Python GC).
  - One-click manual VRAM purge button directly in the HUD.
- **🎨 Cybernetic Dark HUD Dashboard**: Clean, responsive UI with real-time prompt feedback, aspect ratio selectors, preset styles, sampler controls, and an instant gallery viewer.
- **🔌 Streamlined REST API**:
  - Generate images with minimal parameters: only `api_key` and `prompt` required.
  - Automatically inherits current studio settings (model, steps, guidance scale, negative prompt, sampler).
  - Direct binary image streaming (`image/png`) for effortless embedding into frontend apps, bots, or scripts.
  - Interactive Swagger/OpenAPI documentation built-in at `/docs`.

---

## 💻 Platform & Hardware Support

EdgeMind automatically detects your hardware architecture and applies the most efficient backend:

| Hardware Tier | Platform | Acceleration Backend | Precision Supported |
| :--- | :--- | :--- | :--- |
| **NVIDIA GPU** | Windows / Linux | CUDA (11.8, 12.1, 12.4+) | FP16, BF16, FP32 |
| **Apple Silicon (M1/M2/M3/M4)** | macOS | Metal Performance Shaders (MPS) | FP16, FP32 |
| **AMD GPU** | Linux / Windows | ROCm / DirectML | FP16, FP32 |
| **CPU Only** | All Platforms | PyTorch CPU with CPU Offload & Slicing | FP32 |

---

## 🛠️ Installation & Setup

### 1. Prerequisites
- **Python 3.10, 3.11, or 3.12** installed.
- **Git** installed.
- *(Recommended for NVIDIA users)* NVIDIA GPU with recent graphics drivers.

---

### 2. Clone the Repository

```bash
git clone https://github.com/VikasPatel22/EdgeMind-AI-Studio.git
cd EdgeMind-AI-Studio
```

---

### 3. Create a Virtual Environment (Recommended)

#### On Windows (PowerShell / Command Prompt):
```powershell
python -m venv venv
.\venv\Scripts\activate
```

#### On Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 4. Install PyTorch for Your Hardware

To ensure optimal performance, install the version of PyTorch tailored to your hardware before installing other requirements:

#### Option A: NVIDIA GPU (CUDA 12.1 - Recommended for modern GPUs)
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

#### Option B: NVIDIA GPU (CUDA 11.8 - For legacy GPUs)
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

#### Option C: Apple Silicon (macOS MPS) or CPU-Only
```bash
pip install torch torchvision
```

#### Option D: AMD GPU (Linux ROCm 6.0)
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.0
```

---

### 5. Install Studio Dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Running EdgeMind

### One-Click Launchers

- **Windows**: Double-click `start.bat` or run:
  ```cmd
  start.bat
  ```
- **Linux / macOS**: Make executable and run `start.sh`:
  ```bash
  chmod +x start.sh
  ./start.sh
  ```

### Manual Command Line Launch

```bash
# Windows
python app.py

# Linux / macOS
python3 app.py
```

Once running, open your web browser and navigate to:
👉 **`http://127.0.0.1:7265`**

---

## 📁 Model Setup & Scanning

EdgeMind supports **`.safetensors`**, **`.ckpt`**, and **Diffusers format** folders (Stable Diffusion 1.5, SD 2.1, SDXL, SDXL Turbo, Flux, etc.).

### Option A: Local Models Folder
Place your downloaded models into the `./models/` directory:
```text
edgemind/
└── models/
    ├── dreamshaper_8.safetensors
    ├── Hyper-SD15-1step-lora.safetensors
    └── stabilityai--sdxl-turbo/
```

### Option B: Automatic Cross-Platform Discovery
EdgeMind automatically detects models in common installation directories across Windows, macOS, and Linux without requiring duplicate downloads:
- `~/.cache/huggingface/hub/` (Hugging Face default hub cache)
- `~/stable-diffusion-webui/models/Stable-diffusion`
- `~/Fooocus/models/checkpoints`
- `~/ComfyUI/models/checkpoints`
- `C:/stable-diffusion-webui/models/Stable-diffusion` (Windows)
- `C:/Fooocus/models/checkpoints` (Windows)
- `C:/ComfyUI/models/checkpoints` (Windows)
- `D:/...` drive roots on Windows

### Option C: Custom Models Path via Environment Variable
Point EdgeMind to an existing models collection on any drive or directory:

```bash
# Windows (PowerShell)
$env:EDGEMIND_MODELS_DIR="D:\AI_Models\Checkpoints"
python app.py

# Windows (CMD)
set EDGEMIND_MODELS_DIR=D:\AI_Models\Checkpoints
python app.py

# Linux / macOS
export EDGEMIND_MODELS_DIR="/mnt/data/models"
python3 app.py
```

### ⚡ Recommended: 1-Step Hyper-SD LoRA
For near-instant 1-step generation:
1. Download `Hyper-SD15-1step-lora.safetensors` from Hugging Face:
   ```bash
   # Using curl
   curl -L -o models/Hyper-SD15-1step-lora.safetensors "https://huggingface.co/ByteDance/Hyper-SD/resolve/main/Hyper-SD15-1step-lora.safetensors"
   ```
2. Place it in `./models/` or set the path via environment variable:
   ```bash
   export HYPER_SD_LORA_PATH="/path/to/Hyper-SD15-1step-lora.safetensors"
   ```
3. Set **Steps** to `1` and **CFG** to `1.0` in the EdgeMind HUD.

---

## ⚙️ Configuration & Environment Variables

You can configure EdgeMind using environment variables or a local `settings.json` file. A clean template is provided in `settings.example.json`.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `EDGEMIND_HOST` | `0.0.0.0` | Network binding host (`127.0.0.1` for local only, `0.0.0.0` for LAN). |
| `EDGEMIND_PORT` | `7265` | Port number for the web dashboard and REST API. |
| `EDGEMIND_API_KEY` | `edgemind` | Authentication key required for API access. |
| `EDGEMIND_MODELS_DIR` | `./models` | Custom path to scan for model checkpoints. |
| `HYPER_SD_LORA_PATH` | *(Auto-detect)* | Explicit path to the Hyper-SD 1-step LoRA checkpoint. |

---

## 🔌 REST API & Developer Integration

EdgeMind includes a high-performance REST API. By default, API generation returns the **synthesized PNG image binary stream directly**, making integration effortless.

### Authentication
Authenticate with API key `edgemind` via:
- Header: `X-API-Key: edgemind`
- Header: `Authorization: Bearer edgemind`
- Query parameter: `?api_key=edgemind`

### 1. cURL Example
```bash
curl -X POST "http://127.0.0.1:7265/api/v1/generate" \
  -H "X-API-Key: edgemind" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Cyberpunk samurai cat in neon rain, cinematic lighting, 8k"}' \
  --output output.png
```

### 2. Python Example
```python
import requests

url = "http://127.0.0.1:7265/api/v1/generate"
headers = {"X-API-Key": "edgemind"}
payload = {
    "prompt": "Ethereal crystal castle floating in clouds, golden hour, masterpiece"
}

response = requests.post(url, headers=headers, json=payload)
if response.status_code == 200:
    with open("artwork.png", "wb") as f:
        f.write(response.content)
    print("Image generated and saved as artwork.png!")
else:
    print(f"Error {response.status_code}: {response.text}")
```

### 3. JavaScript / Fetch Example
```javascript
const response = await fetch("http://127.0.0.1:7265/api/v1/generate", {
  method: "POST",
  headers: {
    "X-API-Key": "edgemind",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    prompt: "Cyberpunk skyline with flying cars at midnight, ultra realistic"
  })
});

const blob = await response.blob();
const imageUrl = URL.createObjectURL(blob);
document.getElementById("myImage").src = imageUrl;
```

### 4. Interactive API Documentation
EdgeMind includes interactive OpenAPI documentation and a live test sandbox:
- Live Interactive Docs: **`http://127.0.0.1:7265/docs`**
- OpenAPI 3.0 JSON Spec: **`http://127.0.0.1:7265/api/v1/docs`**
- Comprehensive API Guide: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

---

## 📂 Project Structure

```text
edgemind/
├── app.py                      # Flask backend, REST API routes & app lifecycle
├── config.json                 # (Optional) Local configuration overrides
├── settings.example.json       # Clean template for engine settings
├── start.bat                   # One-click Windows launcher (venv auto-detect)
├── start.sh                    # One-click Linux / macOS launcher (venv auto-detect)
├── requirements.txt            # Python package dependencies
├── API_DOCUMENTATION.md        # Comprehensive REST API reference guide
├── LICENSE                     # MIT License
├── README.md                   # Project documentation
├── engine/
│   ├── generator.py            # Image generation pipeline, sampling & PNG metadata
│   ├── model_manager.py        # Model loading, HF hub downloader & memory cleanup
│   ├── settings_manager.py     # Settings persistence and active model resolution
│   └── telemetry.py            # Hardware probing (CUDA, MPS, ROCm, RAM, CPU)
├── models/                     # Local directory for checkpoints (.safetensors, .ckpt)
├── outputs/                    # Output directory for generated images
├── static/
│   ├── css/style.css           # Cybernetic dark HUD styling & responsive layouts
│   └── js/main.js              # Real-time studio dashboard logic & gallery
└── templates/
    ├── index.html              # Studio HUD frontend dashboard
    ├── settings.html           # Engine preferences & auto-unload configuration
    └── docs.html               # Interactive Swagger API documentation & test sandbox
```

---

## ❓ Troubleshooting

### 1. CUDA Out of Memory (OOM)
- In the Studio HUD or `settings.json`, enable **CPU Offload** (`opt_cpu_offload: true`), **VAE Tiling** (`opt_vae_tiling: true`), and **Attention Slicing** (`opt_attn_slicing: true`).
- Reduce the target image resolution (e.g. from 1024×1024 to 512×512 or 768×768).
- Use `FP16` precision instead of `FP32`.
- Click the **"Purge VRAM"** button in the HUD or call `/api/v1/model/unload`.

### 2. PyTorch Not Detecting GPU (`CUDA: False`)
- Verify your GPU driver is installed and updated.
- Verify PyTorch was installed with CUDA support:
  ```bash
  python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
  ```
- If it returns `False`, reinstall PyTorch using the exact CUDA wheel command in [Step 4](#4-install-pytorch-for-your-hardware).

### 3. Apple Silicon MPS Fallback
- On macOS, PyTorch utilizes Metal Performance Shaders (MPS). EdgeMind automatically sets `device = "mps"` and uses `FP16` or `FP32` precision.

### 4. Port Conflict (`Port 7265 in use`)
- If port 7265 is already used by another application, launch EdgeMind on a custom port:
  ```bash
  # Windows
  set EDGEMIND_PORT=8080 && python app.py

  # Linux / macOS
  EDGEMIND_PORT=8080 python3 app.py
  ```

### 5. Linux / macOS Permission Denied on `start.sh`
- Grant execute permissions to the launcher script:
  ```bash
  chmod +x start.sh
  ```

---

## 📜 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for complete details.

Built as part of the **Vorenthic Labs** technology suite. Precision, control, and scalability in edge AI computing.

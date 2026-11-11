# EdgeMind AI Studio — Image Generation API Documentation

Welcome to the **EdgeMind AI Studio REST API**. This endpoint enables programmatic, hardware-accelerated local text-to-image synthesis with minimal friction: **only the API key and prompt are required**, all generation settings are automatically inherited from your **current EdgeMind studio settings**, and the **generated image is directly returned as a PNG image stream**.

---

## 🚀 Key Highlights

- **Requires Only `api_key` and `prompt`**: No need to configure or pass complex parameters.
- **Inherits Current EdgeMind Settings**: Uses the active model, inference steps, guidance scale (CFG), sampler, resolution, style preset, auto-enhancement, and negative prompt currently configured in EdgeMind.
- **Direct Image Delivery**: Directly returns the synthesized PNG image (`image/png`), ready to save or display immediately.
- **Diagnostic Headers**: Always includes headers reporting sampling steps completed (`X-Steps-Done`), execution time (`X-Elapsed-Time`), and active model (`X-Model`).

---

## 📍 Base URL & Endpoints

| Protocol | Base URL |
| :--- | :--- |
| Local HTTP | `http://127.0.0.1:7265` |

### Primary Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/generate` | Primary streamlined image synthesis endpoint (returns PNG image binary) |
| `GET` | `/api/v1/generate` | Convenience GET endpoint (supports direct browser image rendering & HTML embedding) |
| `GET` | `/api/image-gen` | Compatibility alias for `/api/v1/generate` |
| `GET` / `POST` | `/api/settings` | Retrieve or update current EdgeMind engine settings |
| `GET` | `/docs` | Interactive in-browser documentation & live tester |
| `GET` | `/api/v1/docs` | OpenAPI 3.0 specification JSON |

---

## 🔑 Authentication

Authentication requires the API key **`edgemind`**.

Pass it using any of the following methods:

### 1. HTTP Header (Recommended)
```http
X-API-Key: edgemind
```
or
```http
Authorization: Bearer edgemind
```

### 2. URL Query Parameter
```http
?api_key=edgemind
```

### 3. JSON Request Body
```json
{
  "api_key": "edgemind",
  "prompt": "Your image description"
}
```

> **Error 401 Unauthorized**: If the API key is missing or invalid, the API returns HTTP 401:
> ```json
> {
>   "error": "Unauthorized",
>   "message": "Invalid or missing API key. Please authenticate with API key 'edgemind' via 'X-API-Key' header or '?api_key=edgemind' query parameter."
> }
> ```

---

## ⚙️ Parameters

| Parameter | Location | Type | Requirement | Description |
| :--- | :--- | :--- | :--- | :--- |
| `api_key` | Header / Query / Body | `string` | **REQUIRED** | Must match `"edgemind"`. |
| `prompt` | Body / Query | `string` | **REQUIRED** | Text description of the image you want to generate. |
| `format` | Body / Query | `string` | Optional | Defaults to raw image stream (`image/png`). Pass `"json"` only if JSON metadata/Base64 is explicitly needed. |

### ⚡ Automatic EdgeMind Settings Inheritance
When this endpoint is called, EdgeMind automatically applies all current settings configured in your studio:
- **Active Model**: Currently active or selected checkpoint in EdgeMind.
- **Inference Steps**: Current step setting (e.g. 1-step Hyper-SD or 25-step quality mode).
- **CFG Guidance Scale**: Current CFG scale setting (e.g. 1.0 or 7.5).
- **Sampler**: Current scheduler (`Euler`, `DPM++ 2M`, `DDIM`, `UniPC`, etc.).
- **Dimensions**: Current width & height (e.g. 512×512, 1024×576).
- **Auto Quality Enhancer & Style Preset**: Applied if enabled in settings (`photorealistic`, `cinematic`, `anime`, `cyberpunk`, `3d`).
- **Negative Prompt**: Current negative prompt configured in EdgeMind.

---

## 📥 Response Format

### 1. Default: Direct Binary Image Stream (`image/png`)

By default, the endpoint immediately responds with the synthesized PNG image:

```http
HTTP/1.1 200 OK
Content-Type: image/png
X-Steps-Done: 1
X-Elapsed-Time: 3.45s
X-Model: dreamshaper_8.safetensors
X-Image-Filename: edgemind_api_1725450123_456789.png

[Binary PNG Image Stream]
```

### 2. Optional JSON Response (`?format=json`)

If `format=json` is explicitly requested, EdgeMind returns metadata and URL:

```json
{
  "success": true,
  "message": "Image generated successfully.",
  "steps_done": 1,
  "image_url": "/outputs/edgemind_api_1725450123_456789.png",
  "full_url": "http://127.0.0.1:7265/outputs/edgemind_api_1725450123_456789.png",
  "filename": "edgemind_api_1725450123_456789.png",
  "prompt": "A cybernetic wolf in a neon rainforest",
  "model": "dreamshaper_8.safetensors",
  "elapsed_seconds": 3.45,
  "width": 512,
  "height": 512,
  "seed": 1829402941,
  "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAYAAAD0eNT6..."
}
```

---

## 💻 Quick Code Examples

### 1. cURL

#### Generate and Save Image to File:
```bash
curl -X POST http://127.0.0.1:7265/api/v1/generate \
  -H "X-API-Key: edgemind" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A cybernetic wolf in a neon rainforest, 8k resolution"}' \
  --output image.png
```

#### Via GET (Direct Download or Browser View):
```bash
curl -X GET "http://127.0.0.1:7265/api/v1/generate?api_key=edgemind&prompt=cyberpunk+city" \
  --output city.png
```

---

### 2. Python (`requests`)

```python
import requests

URL = "http://127.0.0.1:7265/api/v1/generate"
HEADERS = {"X-API-Key": "edgemind"}
DATA = {"prompt": "A futuristic floating island with waterfalls, ultra detailed"}

# Endpoint generates image with current EdgeMind settings and directly returns PNG
response = requests.post(URL, headers=HEADERS, json=DATA)

if response.status_code == 200:
    with open("output.png", "wb") as f:
        f.write(response.content)
    print(f"Image saved! Steps done: {response.headers.get('X-Steps-Done')} ({response.headers.get('X-Elapsed-Time')})")
else:
    print("Error:", response.json())
```

---

### 3. JavaScript / Node.js (`fetch`)

```javascript
async function generateArtwork(prompt) {
  const response = await fetch("http://127.0.0.1:7265/api/v1/generate", {
    method: "POST",
    headers: {
      "X-API-Key": "edgemind",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ prompt: prompt })
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  // Directly returns the generated PNG image binary
  const imageBlob = await response.blob();
  const imageUrl = URL.createObjectURL(imageBlob);

  const img = document.createElement("img");
  img.src = imageUrl;
  document.body.appendChild(img);
}

generateArtwork("A bioluminescent astronaut exploring a neon jungle, 8k resolution");
```

---

### 4. Direct HTML `<img>` Tag

Embed generated images directly in web pages:

```html
<img 
  src="http://127.0.0.1:7265/api/v1/generate?api_key=edgemind&prompt=cyberpunk+samurai" 
  alt="EdgeMind AI Generated Image"
/>
```

---

## 📊 Diagnostic Headers

Every response includes HTTP response headers:

- **`X-Steps-Done`**: The integer count of diffusion steps completed during generation.
- **`X-Elapsed-Time`**: The total execution time in seconds.
- **`X-Model`**: The local model name used for generation.
- **`X-Image-Filename`**: The filename of the saved output in the `outputs/` directory.

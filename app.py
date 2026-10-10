import os
import threading
from flask import Flask, render_template, jsonify, request, send_from_directory

from engine.telemetry import get_hardware_specs
from engine.model_manager import (
    scan_models,
    unload_model,
    schedule_auto_unload,
    get_model_lifecycle_status,
    parse_hf_url,
    run_hf_download_task,
    current_model_info,
    download_status
)
from engine.generator import (
    run_generation_task,
    generate_image_sync,
    preload_model_sync,
    get_gallery_images,
    generation_status,
    engine_lock
)
from engine.settings_manager import (
    get_settings,
    update_settings,
    get_active_model_path
)

EDGEMIND_API_KEY = os.environ.get("EDGEMIND_API_KEY", "edgemind")

def validate_edgemind_api_key(req):
    """
    Validates that the incoming request supplies the required 'edgemind' API key.
    Accepts the key from:
      1. Header 'X-API-Key: edgemind'
      2. Header 'Authorization: Bearer edgemind'
      3. Header 'edgemind-api-key: edgemind'
      4. Query parameter '?api_key=edgemind' or '?key=edgemind'
      5. JSON body {"api_key": "edgemind"}
    """
    # 1. Header: X-API-Key
    auth_key = req.headers.get("X-API-Key", "").strip()
    if auth_key == EDGEMIND_API_KEY:
        return True

    # 2. Header: Authorization (Bearer or direct)
    auth_header = req.headers.get("Authorization", "").strip()
    if auth_header:
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if token == EDGEMIND_API_KEY:
                return True
        elif auth_header == EDGEMIND_API_KEY:
            return True

    # 3. Header: edgemind-api-key
    custom_hdr = req.headers.get("edgemind-api-key", "").strip()
    if custom_hdr == EDGEMIND_API_KEY:
        return True

    # 4. Query param
    query_key = (req.args.get("api_key") or req.args.get("key") or "").strip()
    if query_key == EDGEMIND_API_KEY:
        return True

    # 5. JSON body
    if req.is_json:
        try:
            body = req.get_json(silent=True) or {}
            body_key = str(body.get("api_key", "")).strip()
            if body_key == EDGEMIND_API_KEY:
                return True
        except Exception:
            pass

    return False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# ---------------------------------------------------------------------------
# ROUTES & REST APIS
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/settings")
def settings():
    return render_template("settings.html")

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, "static"), "favicon.svg", mimetype="image/svg+xml")

@app.route("/api/system-stats", methods=["GET"])
def api_system_stats():
    return jsonify(get_hardware_specs())

@app.route("/api/models", methods=["GET"])
def api_models():
    models = scan_models(MODELS_DIR)
    active_path = get_active_model_path(MODELS_DIR)
    active_name = current_model_info["name"]
    if not active_name and active_path:
        active_name = os.path.basename(active_path)
    return jsonify({
        "models": models,
        "current_model": {
            "name": active_name,
            "path": active_path,
            "loaded": current_model_info["loaded"],
            "precision": current_model_info["precision"],
            "hyper_sd_active": current_model_info.get("hyper_sd_active", False)
        }
    })

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        updated = update_settings(data)
        return jsonify({"success": True, "settings": updated})
    
    settings = get_settings()
    active_path = get_active_model_path(MODELS_DIR)
    return jsonify({
        "settings": settings,
        "current_model": {
            "name": current_model_info["name"] or (os.path.basename(active_path) if active_path else None),
            "path": active_path,
            "loaded": current_model_info["loaded"]
        }
    })

@app.route("/api/unload", methods=["POST"])
def api_unload():
    with engine_lock:
        unload_model()
    return jsonify({"success": True, "message": "Model unloaded and memory cleared."})

@app.route("/api/delete-model", methods=["POST"])
def api_delete_model():
    data = request.json or {}
    model_path = data.get("path", "").strip()
    if not model_path or not os.path.exists(model_path):
        return jsonify({"error": "Invalid or missing model path."}), 400

    with engine_lock:
        if current_model_info.get("path") == model_path:
            unload_model()

    try:
        import shutil
        if os.path.isdir(model_path):
            shutil.rmtree(model_path)
        else:
            os.remove(model_path)
        return jsonify({"success": True, "message": "Model deleted successfully."})
    except Exception as e:
        return jsonify({"error": f"Failed to delete model: {str(e)}"}), 500

@app.route("/api/download-hf", methods=["POST"])
def api_download_hf():
    if download_status["status"] == "downloading":
        return jsonify({"error": "A model download is already in progress."}), 400

    data = request.json or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "Please provide a valid Hugging Face URL or Repo ID."}), 400

    repo_id = parse_hf_url(url)
    if "/" not in repo_id:
        return jsonify({"error": "Invalid Hugging Face Repo format. Must be 'username/repo-name' or a valid URL."}), 400

    t = threading.Thread(target=run_hf_download_task, args=(repo_id, MODELS_DIR))
    t.daemon = True
    t.start()

    return jsonify({"success": True, "message": f"Download initiated for {repo_id}."})

@app.route("/api/download-status", methods=["GET"])
def api_download_status():
    return jsonify(download_status)

@app.route("/api/generate", methods=["POST"])
def api_generate():
    if generation_status["status"] in ["generating", "loading_model"]:
        return jsonify({"error": "Engine is currently busy with another task."}), 400
        
    data = request.json or {}
    if not data.get("prompt"):
        return jsonify({"error": "Prompt cannot be empty."}), 400
    if not data.get("model_path"):
        return jsonify({"error": "No model selected."}), 400

    t = threading.Thread(target=run_generation_task, args=(data, OUTPUTS_DIR))
    t.daemon = True
    t.start()

    return jsonify({"success": True, "message": "Generation started."})

@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify(generation_status)

@app.route("/api/gallery", methods=["GET"])
def api_gallery():
    return jsonify({"images": get_gallery_images(OUTPUTS_DIR)})

@app.route("/outputs/<filename>")
def serve_output_image(filename):
    return send_from_directory(OUTPUTS_DIR, filename)

@app.route("/docs")
def documentation():
    return render_template("docs.html")

@app.route("/api/v1/docs", methods=["GET"])
@app.route("/api/docs", methods=["GET"])
def api_docs_json():
    host_url = request.host_url.rstrip("/")
    return jsonify({
        "openapi": "3.0.3",
        "info": {
            "title": "EdgeMind AI Studio API",
            "version": "1.1.0",
            "description": "Streamlined local AI image generation endpoint requiring only API key 'edgemind' and 'prompt'. Automatically uses the current settings configured in EdgeMind and returns the generated image directly."
        },
        "servers": [{"url": host_url}],
        "paths": {
            "/api/v1/generate": {
                "post": {
                    "summary": "Generate Image (Streamlined)",
                    "description": "Requires only API key 'edgemind' and 'prompt'. Automatically uses the current settings in EdgeMind and directly returns the generated image binary (image/png).",
                    "security": [
                        {"ApiKeyHeader": []},
                        {"ApiKeyQuery": []},
                        {"BearerAuth": []}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["prompt"],
                                    "properties": {
                                        "prompt": {"type": "string", "description": "Text description of the image to generate."},
                                        "api_key": {"type": "string", "description": "API Key ('edgemind') if not passed in headers"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Generated PNG image binary",
                            "content": {
                                "image/png": {
                                    "schema": {
                                        "type": "string",
                                        "format": "binary"
                                    }
                                }
                            },
                            "headers": {
                                "X-Steps-Done": {"schema": {"type": "integer"}, "description": "Sampling steps completed"},
                                "X-Elapsed-Time": {"schema": {"type": "string"}, "description": "Total execution time in seconds"},
                                "X-Model": {"schema": {"type": "string"}, "description": "Model used for synthesis"},
                                "X-Image-Filename": {"schema": {"type": "string"}, "description": "Filename of generated PNG image"}
                            }
                        },
                        "400": {
                            "description": "Bad Request - Missing or empty prompt"
                        },
                        "401": {
                            "description": "Unauthorized - Missing or invalid API key"
                        }
                    }
                },
                "get": {
                    "summary": "Generate Image via GET",
                    "description": "Convenience GET endpoint. Directly returns the generated image.",
                    "parameters": [
                        {"name": "api_key", "in": "query", "required": True, "schema": {"type": "string", "default": "edgemind"}},
                        {"name": "prompt", "in": "query", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Generated PNG image binary",
                            "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}}
                        }
                    }
                }
            }
        }
    })

@app.route("/api/v1/generate", methods=["GET", "POST"])
@app.route("/api/image-gen", methods=["GET", "POST"])
def api_v1_generate():
    """
    Streamlined image generation endpoint.
    Requires only the API key 'edgemind' and 'prompt'.
    Uses current settings configured in EdgeMind (model, steps, cfg, sampler, dimensions, preset, negative prompt).
    Directly returns the generated image binary (image/png) by default.
    """
    # 1. Authenticate API Key
    if not validate_edgemind_api_key(request):
        return jsonify({
            "error": "Unauthorized",
            "message": "Invalid or missing API key. Please authenticate with API key 'edgemind' via 'X-API-Key' header, 'Authorization: Bearer edgemind', or '?api_key=edgemind' query parameter."
        }), 401

    # 2. Extract parameters
    params = {}
    if request.method == "POST":
        if request.is_json:
            params = request.get_json(silent=True) or {}
        elif request.form:
            params = request.form.to_dict()

        for k, v in request.args.items():
            if k not in params:
                params[k] = v
    else:
        params = request.args.to_dict()

    # 3. Check for direct Lifecycle directives (load now / unload now) if requested
    action = (params.get("action") or "").lower().strip()
    is_unload_now = params.get("unload_now") in [True, "true", "1", 1] or action in ["unload", "unload_now", "free"]
    is_load_now = params.get("load_now") in [True, "true", "1", 1] or action in ["load", "load_now", "preload"]

    if is_unload_now:
        with engine_lock:
            unload_model()
        return jsonify({
            "success": True,
            "action": "unload",
            "message": "Model unloaded immediately and system memory freed.",
            "lifecycle": get_model_lifecycle_status()
        }), 200

    if is_load_now:
        res = preload_model_sync(params)
        status_code = 200 if res.get("success") else 500
        return jsonify(res), status_code

    # 4. Validate prompt (required)
    prompt = (params.get("prompt") or "").strip()
    if not prompt:
        return jsonify({
            "error": "Missing prompt",
            "message": "The 'prompt' parameter is required. Please provide a description of the image to generate."
        }), 400

    # 5. Inherit current settings in EdgeMind
    current_settings = get_settings()
    for k, v in current_settings.items():
        if k not in params or params[k] is None or params[k] == "":
            params[k] = v

    if not params.get("model_path"):
        params["model_path"] = get_active_model_path(MODELS_DIR)

    # 6. Execute generation task
    result = generate_image_sync(params, OUTPUTS_DIR)

    if not result.get("success"):
        return jsonify({
            "error": "Generation failed",
            "message": result.get("error", "An error occurred during image synthesis.")
        }), 500

    # 7. Deliver response: by default, give back the generated image directly
    format_opt = (params.get("format") or "").lower()
    
    # If caller explicitly asked for JSON (e.g. ?format=json), return JSON
    if format_opt == "json":
        host_url = request.host_url.rstrip("/")
        rel_url = f"/outputs/{result['filename']}"
        full_url = f"{host_url}{rel_url}"

        response_payload = {
            "success": True,
            "message": "Image generated successfully.",
            "steps_done": result.get("steps_done", 1),
            "image_url": rel_url,
            "full_url": full_url,
            "filename": result["filename"],
            "prompt": result.get("prompt", prompt),
            "model": result.get("model", "Unknown"),
            "elapsed_seconds": result.get("elapsed_time", 0),
            "width": result.get("width", 512),
            "height": result.get("height", 512),
            "seed": result.get("seed", -1),
            "lifecycle": result.get("lifecycle"),
            "image_base64": f"data:image/png;base64,{result['image_base64']}" if result.get("image_base64") else None
        }

        resp = jsonify(response_payload)
        resp.headers["X-Steps-Done"] = str(result["steps_done"])
        resp.headers["X-Elapsed-Time"] = f"{result['elapsed_time']}s"
        resp.headers["X-Model"] = result["model"]
        resp.headers["X-Image-URL"] = full_url
        return resp, 200

    # Default: Return the image binary directly!
    resp = send_from_directory(OUTPUTS_DIR, result["filename"], mimetype="image/png")
    resp.headers["X-Steps-Done"] = str(result["steps_done"])
    resp.headers["X-Elapsed-Time"] = f"{result['elapsed_time']}s"
    resp.headers["X-Model"] = result["model"]
    resp.headers["X-Image-Filename"] = result["filename"]
    return resp

# ---------------------------------------------------------------------------
# MODEL LIFECYCLE CONTROLLER ENDPOINTS (Load Now / Unload Now / Status)
# ---------------------------------------------------------------------------
@app.route("/api/v1/model/load", methods=["GET", "POST"])
def api_v1_model_load():
    """Immediately preloads model with optional keep-alive mins."""
    if not validate_edgemind_api_key(request):
        return jsonify({"error": "Unauthorized", "message": "API key 'edgemind' required."}), 401
    params = request.get_json(silent=True) or {}
    for k, v in request.args.items():
        if k not in params:
            params[k] = v
    res = preload_model_sync(params)
    code = 200 if res.get("success") else 500
    return jsonify(res), code

@app.route("/api/v1/model/unload", methods=["GET", "POST"])
def api_v1_model_unload():
    """Immediately unloads model from RAM/VRAM."""
    if not validate_edgemind_api_key(request):
        return jsonify({"error": "Unauthorized", "message": "API key 'edgemind' required."}), 401
    with engine_lock:
        unload_model()
    return jsonify({
        "success": True,
        "action": "unload",
        "message": "Model unloaded now and memory freed.",
        "lifecycle": get_model_lifecycle_status()
    }), 200

@app.route("/api/v1/model/status", methods=["GET"])
def api_v1_model_status():
    """Gets model status and remaining minutes until auto-unload."""
    if not validate_edgemind_api_key(request):
        return jsonify({"error": "Unauthorized", "message": "API key 'edgemind' required."}), 401
    return jsonify({
        "success": True,
        "lifecycle": get_model_lifecycle_status()
    }), 200

# ---------------------------------------------------------------------------
# APPLICATION ENTRYPOINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print(" EDGEMIND AI STUDIO - MODULAR LOCAL IMAGE GENERATOR")
    print("=" * 60)
    specs = get_hardware_specs()
    print(f" Device Engine  : {specs['device_name']} ({specs['device'].upper()})")
    print(f" Memory Profile : {specs['profile']}")
    print(f" System RAM     : {specs['ram_used_gb']} GB / {specs['ram_total_gb']} GB")
    print(f" GPU VRAM       : {specs['vram_used_gb']} GB / {specs['vram_total_gb']} GB")
    host = os.environ.get("EDGEMIND_HOST", os.environ.get("HOST", "0.0.0.0"))
    port = int(os.environ.get("EDGEMIND_PORT", os.environ.get("PORT", "7265")))
    display_host = "127.0.0.1" if host in ["0.0.0.0", "::"] else host
    print(f" Local Web App  : http://{display_host}:{port}")
    print("=" * 60)
    app.run(host=host, port=port, debug=False)

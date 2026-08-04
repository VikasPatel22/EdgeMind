import os
import threading
from flask import Flask, render_template, jsonify, request, send_from_directory

from engine.telemetry import get_hardware_specs
from engine.model_manager import (
    scan_models,
    unload_model,
    parse_hf_url,
    run_hf_download_task,
    current_model_info,
    download_status
)
from engine.generator import (
    run_generation_task,
    get_gallery_images,
    generation_status,
    engine_lock
)

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
    return jsonify({
        "models": models,
        "current_model": {
            "name": current_model_info["name"],
            "path": current_model_info["path"],
            "loaded": current_model_info["loaded"],
            "precision": current_model_info["precision"],
            "hyper_sd_active": current_model_info.get("hyper_sd_active", False)
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
    print("-" * 60)
    print(" Local Web App  : http://127.0.0.1:7265")
    print("=" * 60)
    app.run(host="0.0.0.0", port=7265, debug=False)

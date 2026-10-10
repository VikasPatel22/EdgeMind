import os
import glob
import time
import json
import torch
import traceback
import threading
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from engine.model_manager import current_model_info, load_diffusers_pipeline

generation_status = {
    "status": "idle", # idle, loading_model, generating, complete, error
    "progress": 0,
    "current_step": 0,
    "total_steps": 0,
    "message": "System Ready",
    "output_image": None,
    "error": None,
    "start_time": 0,
    "elapsed_time": 0
}

engine_lock = threading.Lock()

def diffusers_step_callback(pipe, step, timestep, callback_kwargs):
    global generation_status
    current_step = step + 1
    total_steps = generation_status["total_steps"]
    progress = int((current_step / max(1, total_steps)) * 100)
    
    generation_status["current_step"] = current_step
    generation_status["progress"] = progress
    generation_status["message"] = f"Sampling Step {current_step} / {total_steps} ({progress}%)"
    generation_status["elapsed_time"] = round(time.time() - generation_status["start_time"], 2)
    return callback_kwargs

def run_generation_task(params, outputs_dir):
    global generation_status, current_model_info
    
    with engine_lock:
        generation_status["status"] = "generating"
        generation_status["progress"] = 0
        generation_status["message"] = "Initializing inference task..."
        generation_status["error"] = None
        generation_status["start_time"] = time.time()
        
        prompt = params.get("prompt", "")
        negative_prompt = params.get("negative_prompt", "")
        auto_enhance = params.get("auto_enhance", True)
        quality_preset = params.get("quality_preset", "photorealistic")

        # Apply Quality Enhancements
        if auto_enhance:
            enhancers = {
                "photorealistic": "masterpiece, ultra-realistic, RAW photo, 8k resolution, photorealistic, sharp focus, professional photography, natural lighting, highly detailed",
                "cinematic": "masterpiece, cinematic film frame, dramatic lighting, 8k, photorealistic, depth of field, anamorphic, color graded",
                "anime": "masterpiece, anime visual, vibrant colors, clean lineart, high dynamic range, intricate details, anime artstyle",
                "cyberpunk": "masterpiece, cyberpunk neon aesthetic, glowing lights, futuristic detail, sharp resolution, volumetric fog, octane render",
                "3d": "masterpiece, 3D digital art, octane render, Unreal Engine 5 render, raytracing, PBR materials, ultra detailed"
            }
            preset_suffix = enhancers.get(quality_preset, enhancers["photorealistic"])
            if preset_suffix and preset_suffix not in prompt.lower():
                prompt = f"{prompt.rstrip('.')}, {preset_suffix}"

            if not negative_prompt:
                negative_prompt = "blurry, low quality, distorted, bad anatomy, ugly, extra limbs, watermark, text, grainy, lowres, oversaturated"
            elif "blurry" not in negative_prompt.lower():
                negative_prompt = f"{negative_prompt}, blurry, low quality, distorted, bad anatomy, ugly"

        width = int(params.get("width", 512))
        height = int(params.get("height", 512))
        steps = int(params.get("steps", 25))
        cfg_scale = float(params.get("cfg_scale", 7.5))
        seed = int(params.get("seed", -1))
        sampler_name = params.get("sampler", "Euler")
        model_path = params.get("model_path")
        precision = params.get("precision", "fp16")
        cpu_offload = params.get("cpu_offload", True)
        vae_tiling = params.get("vae_tiling", True)
        attention_slicing = params.get("attention_slicing", True)

        generation_status["total_steps"] = steps

        if seed == -1 or seed is None:
            seed = torch.randint(0, 2**32 - 1, (1,)).item()

        generator = torch.Generator(device="cpu").manual_seed(seed)

        # Ensure model is loaded
        if not current_model_info["loaded"] or current_model_info["path"] != model_path or current_model_info["precision"] != precision:
            success, msg = load_diffusers_pipeline(
                model_path, 
                precision=precision, 
                cpu_offload=cpu_offload, 
                vae_tiling=vae_tiling, 
                attention_slicing=attention_slicing
            )
            if not success:
                generation_status["status"] = "error"
                generation_status["error"] = msg
                return

        pipe = current_model_info["pipeline"]
        if pipe is None:
            generation_status["status"] = "error"
            generation_status["error"] = "Pipeline not loaded. Please select a valid model."
            return

        # Configure Sampler / Scheduler
        try:
            from diffusers import (
                EulerDiscreteScheduler, 
                DPMSolverMultistepScheduler, 
                DDIMScheduler, 
                UniPCMultistepScheduler,
                HeunDiscreteScheduler,
                EulerAncestralDiscreteScheduler
            )
            
            sched_kwargs = {}
            if current_model_info.get("hyper_sd_active"):
                sched_kwargs["timestep_spacing"] = "trailing"

            if sampler_name == "DPM++ 2M":
                pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
            elif sampler_name == "DDIM":
                pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
            elif sampler_name == "UniPC":
                pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
            elif sampler_name == "Heun":
                pipe.scheduler = HeunDiscreteScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
            elif sampler_name == "Euler a":
                pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
            else:
                pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
        except Exception as e:
            print(f"Scheduler configuration warning: {e}")

        try:
            generation_status["message"] = "Generating Image..."
            
            output = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=cfg_scale,
                generator=generator,
                callback_on_step_end=diffusers_step_callback
            )
            
            image = output.images[0]
            
            filename = f"edgemind_{int(time.time())}_{seed}.png"
            filepath = os.path.join(outputs_dir, filename)

            png_info = PngInfo()
            metadata = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "seed": seed,
                "sampler": sampler_name,
                "width": width,
                "height": height,
                "model": current_model_info["name"],
                "hyper_sd_active": current_model_info.get("hyper_sd_active", False),
                "precision": precision,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            png_info.add_text("edgemind_metadata", json.dumps(metadata))
            
            image.save(filepath, pnginfo=png_info)
            
            generation_status["status"] = "complete"
            generation_status["progress"] = 100
            generation_status["message"] = "Generation finished!"
            generation_status["output_image"] = filename
            generation_status["elapsed_time"] = round(time.time() - generation_status["start_time"], 2)
            
        except Exception as e:
            err_msg = f"Generation error: {str(e)}\n{traceback.format_exc()}"
            print(err_msg)
            generation_status["status"] = "error"
            generation_status["error"] = err_msg

def get_gallery_images(outputs_dir):
    files = glob.glob(os.path.join(outputs_dir, "*.png"))
    files.sort(key=os.path.getmtime, reverse=True)
    images = []
    for f in files:
        filename = os.path.basename(f)
        meta = {}
        try:
            with Image.open(f) as img:
                if "edgemind_metadata" in img.info:
                    meta = json.loads(img.info["edgemind_metadata"])
        except Exception:
            pass
            
        images.append({
            "filename": filename,
            "url": f"/outputs/{filename}",
            "created_at": time.ctime(os.path.getmtime(f)),
            "metadata": meta
        })
    return images

def generate_image_sync(params, outputs_dir):
    """
    Synchronous image generation endpoint handler.
    Inherits all generation parameters from current EdgeMind settings (active model,
    steps, sampler, cfg, resolution, auto-enhancement, negative prompt, and optimizations).
    Returns a dict with image details, steps_done, and base64 encoding.
    """
    global generation_status, current_model_info
    import io
    import base64
    from engine.settings_manager import get_settings, get_active_model_path
    
    with engine_lock:
        start_time = time.time()
        current_settings = get_settings()
        
        # 1. Resolve prompt & quality enhancements
        prompt = (params.get("prompt") or "").strip()
        auto_enhance = params.get("auto_enhance", current_settings.get("auto_enhance", True))
        quality_preset = params.get("quality_preset", current_settings.get("quality_preset", "photorealistic"))
        negative_prompt = params.get("negative_prompt", current_settings.get("negative_prompt", ""))
        
        if auto_enhance:
            enhancers = {
                "photorealistic": "masterpiece, ultra-realistic, RAW photo, 8k resolution, photorealistic, sharp focus, professional photography, natural lighting, highly detailed",
                "cinematic": "masterpiece, cinematic film frame, dramatic lighting, 8k, photorealistic, depth of field, anamorphic, color graded",
                "anime": "masterpiece, anime visual, vibrant colors, clean lineart, high dynamic range, intricate details, anime artstyle",
                "cyberpunk": "masterpiece, cyberpunk neon aesthetic, glowing lights, futuristic detail, sharp resolution, volumetric fog, octane render",
                "3d": "masterpiece, 3D digital art, octane render, Unreal Engine 5 render, raytracing, PBR materials, ultra detailed"
            }
            preset_suffix = enhancers.get(quality_preset, enhancers["photorealistic"])
            if preset_suffix and preset_suffix.lower() not in prompt.lower():
                prompt = f"{prompt.rstrip('.')}, {preset_suffix}" if prompt else preset_suffix

            if not negative_prompt:
                negative_prompt = "blurry, low quality, distorted, bad anatomy, ugly, extra limbs, watermark, text, grainy, lowres, oversaturated"
            elif "blurry" not in negative_prompt.lower():
                negative_prompt = f"{negative_prompt}, blurry, low quality, distorted, bad anatomy, ugly"

        if not prompt:
            prompt = "A masterpiece cinematic landscape, ultra-detailed digital art, 8k resolution, photorealistic"
            
        # 2. Resolve model from active EdgeMind selection
        model_path = params.get("model_path") or get_active_model_path()
        if not model_path:
            return {
                "success": False,
                "error": "No Stable Diffusion model found in the models directory or selected in EdgeMind."
            }
        
        # 3. Resolve precision & device optimizations from current settings
        from engine.telemetry import get_hardware_specs
        specs = get_hardware_specs()
        default_precision = "fp16" if current_settings.get("opt_fp16", True) else "fp32"
        precision = params.get("precision", default_precision)
        cpu_offload = params.get("cpu_offload", current_settings.get("opt_cpu_offload", specs.get("rec_cpu_offload", True)))
        vae_tiling = params.get("vae_tiling", current_settings.get("opt_vae_tiling", specs.get("rec_vae_tiling", True)))
        attention_slicing = params.get("attention_slicing", current_settings.get("opt_attn_slicing", specs.get("rec_attention_slicing", True)))
        
        # Load model pipeline if needed
        if not current_model_info.get("loaded") or current_model_info.get("path") != model_path or current_model_info.get("precision") != precision:
            generation_status["status"] = "loading_model"
            generation_status["message"] = f"Loading model: {os.path.basename(model_path)}"
            success, msg = load_diffusers_pipeline(
                model_path, 
                precision=precision, 
                cpu_offload=cpu_offload, 
                vae_tiling=vae_tiling, 
                attention_slicing=attention_slicing
            )
            if not success:
                generation_status["status"] = "error"
                generation_status["error"] = msg
                return {
                    "success": False,
                    "error": msg
                }
                
        pipe = current_model_info.get("pipeline")
        if pipe is None:
            return {
                "success": False,
                "error": "Pipeline could not be initialized."
            }
            
        # 4. Resolve steps & guidance scale from current EdgeMind settings
        is_hyper = current_model_info.get("hyper_sd_active", False)
        
        # Hyper-SD 1-Step LoRA requires exactly 1 step and low/zero CFG.
        # Force these values when the LoRA is active to prevent stale settings
        # (e.g. settings.json still saying 12 steps) from overriding the LoRA's
        # optimal configuration.
        if is_hyper:
            steps = 1
            cfg_scale = 0.0
        else:
            default_steps = current_settings.get("steps", 20)
            if "steps" in params and params["steps"] is not None:
                try:
                    steps = max(1, int(params["steps"]))
                except (ValueError, TypeError):
                    steps = max(1, int(default_steps))
            else:
                steps = max(1, int(default_steps))
                
            default_cfg = current_settings.get("cfg_scale", 7.0)
            if "cfg_scale" in params and params["cfg_scale"] is not None:
                try:
                    cfg_scale = float(params["cfg_scale"])
                except (ValueError, TypeError):
                    cfg_scale = float(default_cfg)
            else:
                cfg_scale = float(default_cfg)
            
        width = int(params.get("width") or current_settings.get("width", 512))
        height = int(params.get("height") or current_settings.get("height", 512))
        
        seed = params.get("seed") if params.get("seed") is not None else current_settings.get("seed", -1)
        try:
            seed = int(seed) if seed is not None and int(seed) >= 0 else torch.randint(0, 2**32 - 1, (1,)).item()
        except (ValueError, TypeError):
            seed = torch.randint(0, 2**32 - 1, (1,)).item()
            
        generator = torch.Generator(device="cpu").manual_seed(seed)
        
        # Configure scheduler
        sampler_name = params.get("sampler") or current_settings.get("sampler", "Euler")
        try:
            from diffusers import (
                EulerDiscreteScheduler, 
                DPMSolverMultistepScheduler, 
                DDIMScheduler, 
                UniPCMultistepScheduler,
                HeunDiscreteScheduler,
                EulerAncestralDiscreteScheduler
            )
            sched_kwargs = {}
            if is_hyper:
                sched_kwargs["timestep_spacing"] = "trailing"

            if sampler_name == "DPM++ 2M":
                pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
            elif sampler_name == "DDIM":
                pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
            elif sampler_name == "UniPC":
                pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
            elif sampler_name == "Heun":
                pipe.scheduler = HeunDiscreteScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
            elif sampler_name == "Euler a":
                pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
            else:
                pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, **sched_kwargs)
        except Exception as e:
            print(f"Scheduler configuration warning: {e}")
            
        # Step tracking callback
        steps_executed = 0
        def sync_step_callback(pipe, step, timestep, callback_kwargs):
            nonlocal steps_executed
            steps_executed = step + 1
            generation_status["current_step"] = steps_executed
            generation_status["total_steps"] = steps
            generation_status["progress"] = int((steps_executed / max(1, steps)) * 100)
            return callback_kwargs
            
        generation_status["status"] = "generating"
        generation_status["start_time"] = start_time
        generation_status["total_steps"] = steps
        generation_status["current_step"] = 0
        generation_status["progress"] = 0
        
        try:
            output = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=cfg_scale,
                generator=generator,
                callback_on_step_end=sync_step_callback
            )
            image = output.images[0]
            
            actual_steps = steps_executed if steps_executed > 0 else steps
            
            filename = f"edgemind_api_{int(time.time())}_{seed}.png"
            filepath = os.path.join(outputs_dir, filename)
            
            png_info = PngInfo()
            metadata = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": actual_steps,
                "cfg_scale": cfg_scale,
                "seed": seed,
                "sampler": sampler_name,
                "width": width,
                "height": height,
                "model": current_model_info.get("name", "Unknown"),
                "hyper_sd_active": is_hyper,
                "precision": precision,
                "source": "api_v1_generate",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            png_info.add_text("edgemind_metadata", json.dumps(metadata))
            image.save(filepath, pnginfo=png_info)
            
            # Encode image to Base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            b64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            elapsed = round(time.time() - start_time, 2)
            
            generation_status["status"] = "complete"
            generation_status["progress"] = 100
            generation_status["message"] = "Generation finished!"
            generation_status["output_image"] = filename
            generation_status["elapsed_time"] = elapsed
            
            # Model Lifecycle management: unload_now or keep_alive_mins
            from engine.model_manager import unload_model, schedule_auto_unload, get_model_lifecycle_status
            
            unload_now = params.get("unload_now") in [True, "true", "1", 1] or params.get("action") == "unload"
            keep_alive_mins = params.get("keep_alive_mins") or params.get("load_mins") or params.get("mins")
            
            if unload_now:
                unload_model()
            elif keep_alive_mins is not None:
                schedule_auto_unload(keep_alive_mins)
                
            lifecycle = get_model_lifecycle_status()
            
            return {
                "success": True,
                "filename": filename,
                "filepath": filepath,
                "steps_done": actual_steps,
                "elapsed_time": elapsed,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "model": current_model_info.get("name", "Unknown"),
                "hyper_sd_active": is_hyper,
                "width": width,
                "height": height,
                "seed": seed,
                "image_base64": b64_str,
                "lifecycle": lifecycle
            }
        except Exception as e:
            err_msg = f"Generation error: {str(e)}\n{traceback.format_exc()}"
            print(err_msg)
            generation_status["status"] = "error"
            generation_status["error"] = err_msg
            return {
                "success": False,
                "error": str(e)
            }

def preload_model_sync(params):
    """
    Explicitly preloads the model into memory with optional keep-alive minutes.
    """
    global current_model_info
    with engine_lock:
        model_path = params.get("model_path")
        if not model_path:
            if current_model_info.get("loaded") and current_model_info.get("path"):
                model_path = current_model_info["path"]
            else:
                from engine.model_manager import scan_models
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                models_dir = os.path.join(base_dir, "models")
                available_models = scan_models(models_dir)
                if available_models:
                    model_path = available_models[0]["path"]
                else:
                    return {"success": False, "error": "No model found to load."}

        from engine.telemetry import get_hardware_specs
        specs = get_hardware_specs()
        default_precision = specs.get("rec_precision", "fp16")
        precision = params.get("precision", default_precision)
        cpu_offload = params.get("cpu_offload", specs.get("rec_cpu_offload", True))
        vae_tiling = params.get("vae_tiling", specs.get("rec_vae_tiling", True))
        attention_slicing = params.get("attention_slicing", specs.get("rec_attention_slicing", True))

        if not current_model_info.get("loaded") or current_model_info.get("path") != model_path or current_model_info.get("precision") != precision:
            success, msg = load_diffusers_pipeline(
                model_path, 
                precision=precision, 
                cpu_offload=cpu_offload, 
                vae_tiling=vae_tiling, 
                attention_slicing=attention_slicing
            )
            if not success:
                return {"success": False, "error": msg}

        # Schedule auto-unload if keep_alive_mins provided
        keep_alive_mins = params.get("keep_alive_mins") or params.get("load_mins") or params.get("mins")
        from engine.model_manager import schedule_auto_unload, get_model_lifecycle_status
        if keep_alive_mins is not None:
            schedule_auto_unload(keep_alive_mins)

        return {
            "success": True,
            "message": f"Model '{current_model_info.get('name')}' loaded successfully.",
            "lifecycle": get_model_lifecycle_status()
        }

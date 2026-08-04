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

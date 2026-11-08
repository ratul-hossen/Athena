"""
Modal Serverless GPU Worker for Athina Consistent Character Image Generation
Loads Stable Diffusion 1.5 + Realistic Vision v5.1 + LCM-LoRA + Athina LoRA
Scales to zero when idle (0 cost), executes in ~1.5s on GPU.
"""

import os
import io
import modal

# Define Modal container image with diffusers, accelerate, and PyTorch
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.2.0",
        "diffusers>=0.29.0",
        "transformers>=4.40.0",
        "accelerate>=0.29.0",
        "peft>=0.10.0",
        "safetensors>=0.4.3",
        "Pillow>=10.2.0"
    )
)

app = modal.App("athina-image-worker")
volume = modal.Volume.from_name("athina-weights-vol", create_if_missing=True)

MODEL_ID = "SG161222/Realistic_Vision_V5.1_noVAE"
LCM_LORA_ID = "latent-consistency/lcm-lora-sdv1-5"
ATHINA_LORA_FILENAME = "athina_lora_v1.safetensors"

@app.cls(gpu="T4", image=image, volumes={"/weights": volume}, container_idle_timeout=60)
class AthinaGenerator:
    @modal.enter()
    def load_pipeline(self):
        import torch
        from diffusers import StableDiffusionPipeline, LCMScheduler, AutoencoderKL

        print("Loading Realistic Vision base pipeline on GPU...")
        self.pipe = StableDiffusionPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            safety_checker=None
        ).to("cuda")

        # Load high-definition VAE to fix flat contrast and dark eyes
        print("Loading official photorealistic VAE (sd-vae-ft-mse)...")
        self.pipe.vae = AutoencoderKL.from_pretrained(
            "stabilityai/sd-vae-ft-mse",
            torch_dtype=torch.float16
        ).to("cuda")

        # Set fast LCM Scheduler (4 - 8 steps inference)
        self.pipe.scheduler = LCMScheduler.from_config(self.pipe.scheduler.config)

        # Load LCM LoRA for rapid inference
        print("Loading LCM-LoRA...")
        self.pipe.load_lora_weights(LCM_LORA_ID, adapter_name="lcm")

        # Load Athina Custom Face LoRA if uploaded to volume
        athina_lora_path = os.path.join("/weights", ATHINA_LORA_FILENAME)
        if os.path.exists(athina_lora_path):
            print(f"Loading Athina LoRA from {athina_lora_path}...")
            self.pipe.load_lora_weights(athina_lora_path, adapter_name="athina")
            # Combine LCM and Athina adapters
            self.pipe.set_adapters(["lcm", "athina"], adapter_weights=[0.8, 1.0])
        else:
            print(f"Warning: {athina_lora_path} not found in volume. Running base LCM.")
            self.pipe.set_adapters(["lcm"], adapter_weights=[1.0])

        self.pipe.fuse_lora()
        print("Athina Image Generator Ready!")

    @modal.method()
    def generate(self, prompt: str, seed: int = None, steps: int = 8, guidance_scale: float = 2.0) -> bytes:
        import torch

        if seed is None:
            generator = None
        else:
            generator = torch.Generator(device="cuda").manual_seed(seed)

        negative_prompt = (
            "deformed, bad anatomy, bad hands, distorted face, extra limbs, "
            "mutated, blurry, low quality, anime, cartoon, 3d render"
        )

        image = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            generator=generator,
            height=512,
            width=512
        ).images[0]

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=92)
        return buffer.getvalue()

@app.function(image=image)
@modal.web_endpoint(method="POST")
def api_generate(data: dict):
    prompt = data.get("prompt", "photo of athina_woman, smiling, natural sunlight")
    seed = data.get("seed")
    generator = AthinaGenerator()
    img_bytes = generator.generate.remote(prompt=prompt, seed=seed)
    from fastapi import Response
    return Response(content=img_bytes, media_type="image/jpeg")

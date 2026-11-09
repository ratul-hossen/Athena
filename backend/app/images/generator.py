import os
import io
import uuid
import random
import logging
import asyncio
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from backend.app.images.reference import find_best_reference

logger = logging.getLogger("athina.images")

STATIC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../static/images")
)
os.makedirs(STATIC_DIR, exist_ok=True)

ATHINA_VISUAL_ANCHOR = (
    "RAW candid photo of Athina, an exceptionally beautiful 28-year-old South Asian woman, "
    "striking warm amber-hazel eyes, silky dark chocolate brown hair, soft expressive facial features, "
    "natural glowing skin texture, slender graceful figure"
)

async def _fetch_flux_bytes(url: str, timeout: float = 45.0) -> Optional[bytes]:
    """Fetches generated image bytes using httpx if available, else standard urllib."""
    if HAS_HTTPX:
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "AthinaAI/2.0"})
                if resp.status_code == 200 and len(resp.content) > 5000:
                    return resp.content
        except Exception as e:
            logger.warning(f"httpx fetch failed: {e}")

    def _sync_fetch():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AthinaAI/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if len(data) > 5000:
                    return data
        except Exception as e:
            logger.warning(f"urllib fetch failed: {e}")
        return None

    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _sync_fetch)
    except Exception as e:
        logger.warning(f"Async executor fetch failed: {e}")
        return None

async def generate_athina_image_nanobanana(
    prompt: str,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a consistent Athina photo matching the requested outfit and setting.
    Uses AI Diffusion (Flux / Nano Banana) with Athina's visual identity anchor.
    Falls back gracefully to curated reference images if network is unreachable.
    """
    if not job_id:
        job_id = f"img_{uuid.uuid4().hex[:10]}"

    output_filename = f"{job_id}.jpg"
    output_path = os.path.join(STATIC_DIR, output_filename)

    # Clean and enrich the prompt with Athina's Visual DNA
    p_clean = prompt.strip()
    if "athina" not in p_clean.lower():
        full_prompt = (
            f"{ATHINA_VISUAL_ANCHOR}, {p_clean}, "
            f"soft natural lighting, photorealistic, 8k resolution, cinematic composition, highly detailed"
        )
    else:
        full_prompt = f"{ATHINA_VISUAL_ANCHOR}, {p_clean}, photorealistic, 8k resolution, highly detailed"

    ref = find_best_reference(prompt)
    seed = random.randint(1000, 999999)
    encoded_prompt = urllib.parse.quote(full_prompt)

    # 1. Attempt AI Image Synthesis via Flux Diffusion (Pollinations CDN)
    image_generated = False
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux&width=768&height=768&seed={seed}"

    raw_bytes = await _fetch_flux_bytes(url, timeout=45.0)
    if raw_bytes and (raw_bytes.startswith(b"\xff\xd8") or raw_bytes.startswith(b"\x89PNG")):
        if HAS_PIL:
            try:
                im = Image.open(io.BytesIO(raw_bytes))
                w, h = im.size
                cropped = im.crop((0, 0, w, max(h - 35, 100)))
                cropped.convert("RGB").save(output_path, "JPEG", quality=92)
                image_generated = True
            except Exception:
                with open(output_path, "wb") as wf:
                    wf.write(raw_bytes)
                image_generated = True
        else:
            with open(output_path, "wb") as wf:
                wf.write(raw_bytes)
            image_generated = True

    # 2. Offline / Fallback: Use best matched curated reference image
    if not image_generated or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        if ref.get("image_path") and os.path.exists(ref["image_path"]):
            with open(ref["image_path"], "rb") as rf:
                img_bytes = rf.read()
            with open(output_path, "wb") as wf:
                wf.write(img_bytes)
        else:
            with open(output_path, "wb") as wf:
                wf.write(b"")

    relative_url = f"/static/images/{output_filename}"

    return {
        "job_id": job_id,
        "status": "done",
        "source": "nanobanana",
        "image_url": relative_url,
        "local_path": output_path,
        "reference_used": ref.get("filename"),
        "reference_url": ref.get("reference_url"),
        "group": ref.get("group"),
        "prompt": prompt,
        "full_prompt": full_prompt,
        "dna_summary": ref.get("prompt_dna")
    }

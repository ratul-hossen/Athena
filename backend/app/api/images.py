import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from backend.app.images.jobs import create_and_run_image_job
from backend.app.images.reference import load_manifest

router = APIRouter(prefix="/api/images", tags=["images"])

class ImageGenerateRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = "main"
    send_telegram: Optional[bool] = True

@router.post("/generate")
async def generate_image_endpoint(req: ImageGenerateRequest):
    """Triggers reference-driven Nano Banana image generation."""
    try:
        result = await create_and_run_image_job(
            prompt=req.prompt,
            session_id=req.session_id,
            send_telegram=req.send_telegram
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gallery")
async def get_gallery_samples(limit: int = 20):
    """Returns curated reference samples and generated images."""
    manifest = load_manifest()
    samples = []
    for item in manifest[:limit]:
        samples.append({
            "id": item.get("id"),
            "filename": item.get("filename"),
            "group": item.get("group"),
            "caption": item.get("detailed_prompt"),
            "tags": item.get("tags")
        })
    return {"total": len(manifest), "samples": samples}

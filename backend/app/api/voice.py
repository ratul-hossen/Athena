from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from backend.app.voice.stt import transcribe_audio_groq

router = APIRouter(prefix="/api/voice", tags=["voice"])

@router.post("/transcribe")
async def transcribe_voice(file: UploadFile = File(...)):
    """Transcribes uploaded audio using Groq Whisper Large-v3."""
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty audio file")

        text = await transcribe_audio_groq(content, filename=file.filename or "audio.wav")
        if text is None:
            raise HTTPException(status_code=500, detail="Transcription service unavailable or no Groq keys configured")

        return {
            "text": text,
            "language": "en"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

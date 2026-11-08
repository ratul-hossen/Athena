import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.voice.stt import transcribe_audio_groq
from backend.app.voice.clarion import clarion_decision_policy
from backend.app.personality.state import PersonalityState
from backend.app.personality.prompt import build_system_prompt
from backend.app.personality.style_model import compute_style_vector
from backend.app.llm.chat import chat_stream

router = APIRouter(tags=["websocket"])

@router.websocket("/api/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = f"ws_voice_{uuid.uuid4().hex[:8]}"

    try:
        while True:
            # Receive message (either audio bytes or text command)
            data = await websocket.receive()
            if "bytes" in data and data["bytes"]:
                audio_bytes = data["bytes"]
                # 1. Transcribe with Whisper + Clarion ASR Repair
                transcribed = await transcribe_audio_groq(audio_bytes, filename="audio.wav", repair=True)
                if not transcribed:
                    await websocket.send_json({"type": "error", "message": "Could not transcribe audio"})
                    continue

                # Echo interim user speech
                await websocket.send_json({"type": "user_transcription", "text": transcribed})

                # 2. Personality & Clarion Ambiguity Policy
                state = PersonalityState.calculate_current_state()
                tone_guidance, style = compute_style_vector(transcribed, state)
                clarion_eval = clarion_decision_policy(style["predicted_class"], style["confidence"], transcribed)
                
                if clarion_eval["clarification_needed"] and clarion_eval["clarification_prompt"]:
                    tone_guidance += f" [Clarion Ambiguity Guidance: Confidence is borderline ({clarion_eval['confidence']}). Clarify gently with Ratul: {clarion_eval['clarification_prompt']}]"

                sys_prompt = build_system_prompt(state=state, tone_guidance=tone_guidance)

                messages = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": transcribed}
                ]

                # Stream tokens
                async for event in chat_stream(messages, temperature=0.7, max_tokens=250):
                    if event["type"] == "token":
                        await websocket.send_json({"type": "token", "text": event["text"]})

                await websocket.send_json({"type": "done"})

            elif "text" in data and data["text"]:
                msg = json.loads(data["text"])
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass

# AGENT CONTEXT & ARCHITECTURAL DIRECTIVES: ATHINA

> **Purpose of this file**: This file serves as the permanent memory and context guide for any AI Agent working on **Athina**. It codifies all core constraints, design decisions, architectural blueprints, reuse mappings from Mercy, hosting configurations, and phased roadmaps.

---

## 1. Executive Summary & Identity

- **Name**: Athina
- **Concept**: A single-persona AI companion living on Ratul's Android mobile phone, synced with a private Telegram bot, and managed via a small Next.js web admin panel.
- **Single Agent Rule**: **NO multi-agent system**, no agent teams, no agent debate or owner/visitor portfolio mode. Athina works alone, thinks alone, and does everything herself.
- **Language Rule**: **Strictly English-only**. All UI, voice, system prompts, memory extractions, and responses must be in English. No Bengali UI or voice toggle.
- **Look & Feel**: Inherits the exact design tokens, typography (Inter + JetBrains Mono), 2D eagle mark, and 3D procedural Three.js eagle avatar from **Mercy**.
- **Companion Personality**: Driven by a multi-layered brain: System Prompt + Small ML Models (Emotion, Mood, Style selector) + Ratul's feedback loop + Long-term memory bank.

---

## 2. System Architecture & Components

```
                   ┌───────────────────────────────────────────────────┐
                   │                 ATHINA BACKEND                    │
                   │              (FastAPI on Oracle VM)               │
                   │                                                   │
                   │  • Chat Engine with Key Pool (Gemini -> Groq)     │
                   │  • State Machine (Mood, energy, location, warmth) │
                   │  • ML Intent, Emotion & Style Classifiers (ONNX)  │
                   │  • Hybrid RAG Memory (Facts + Episodes + Reciprocal│
                   │    Rank Fusion via Postgres + pgvector)           │
                   │  • Voice WebSockets (Groq Whisper STT + Piper TTS)│
                   │  • Image Job Queue (Async Tier 1 -> Tier 2 -> 3)  │
                   └─────────────┬─────────────┬─────────────┬─────────┘
                                 │             │             │
                    ┌────────────▼───┐   ┌─────▼────────┐  ┌─▼──────────────┐
                    │  Android App   │   │  Admin Web   │  │  Telegram Bot  │
                    │ Kotlin/Compose │   │   Next.js    │  │  Long Polling  │
                    │   MVVM Clean   │   │   (Vercel)   │  │  & File Store  │
                    └────────────────┘   └──────────────┘  └────────────────┘

   Image Gen Tiers:
     Tier 1: Modal Serverless GPU (SD1.5 + Athina LoRA, fast, scales to 0)
     Tier 2: Oracle VM CPU (SD1.5 + Athina LoRA + LCM-LoRA, free backup)
     Tier 3: Nano Banana (Gemini API with fictional Athina reference images)
     Tier 4: Graceful fallback (Text-only reply)
```

---

## 3. Directory Structure

```
athina/
├── README.md                    ← Product specification & overview
├── AGENT.md                     ← This persistent agent context file
├── mercy.txt                    ← Reference code dump from Mercy
├── backend/                     ← FastAPI engine (Python 3.11+)
│   ├── app/
│   │   ├── main.py              ← FastAPI entrypoint, CORS, lifespan
│   │   ├── api/                 ← chat.py, sessions.py, config.py, ws.py, admin/
│   │   ├── llm/                 ← keypool.py, chat.py, embeddings.py
│   │   ├── personality/         ← prompt.py, state.py, style_model.py, mood_model.py
│   │   ├── memory/              ← facts.py, episodes.py, retrieval.py, chunker.py
│   │   ├── images/              ← jobs.py, tiers.py, modal_client.py, cpu_worker.py
│   │   ├── voice/               ← stt.py, tts.py
│   │   ├── telegram/            ← bot.py, handle.py, files.py, backup.py
│   │   ├── usage/               ← counters.py, guard.py
│   │   └── db/                  ← session.py, models.py, migrations/
│   ├── tests/
│   └── requirements.txt
├── android/                     ← Kotlin + Jetpack Compose + MVVM
│   ├── app/
│   │   ├── src/main/assets/eagle/ ← Three.js 3D eagle bundle (offline HTML/JS)
│   │   ├── src/main/java/com/ratul/athina/
│   │   │   ├── data/            ← Retrofit/OkHttp, SSE, Room, WebSocket, Repos
│   │   │   ├── domain/          ← Models, UseCases
│   │   │   ├── ui/              ← AthinaTheme, Chat, Voice, Gallery, Settings, Components
│   │   │   ├── ml/              ← On-device ONNX classifiers, Ratul face recognition
│   │   │   ├── audio/           ← Media3, sherpa-onnx (Piper TTS), VAD, Barge-in
│   │   │   └── di/              ← Hilt dependency injection modules
│   └── build.gradle.kts
├── admin/                       ← Next.js 15+ (App Router) Admin Dashboard
│   ├── src/
│   │   ├── app/                 ← Dashboard, Personality, Memory, Training, Jobs, Usage
│   │   ├── components/          ← UI controls, tables, prompt editor, charts
│   │   └── lib/                 ← Backend API client, auth
│   ├── package.json
│   └── vercel.json
├── ml/                          ← Small ML model training scripts & exports
│   ├── emotion/                 ← TF-IDF + Logistic Regression / SVM -> ONNX
│   ├── mood/                    ← State machine transition predictor
│   ├── style/                   ← Tone & warmth vector calculator
│   └── exports/                 ← Exported .onnx models for backend & mobile
├── imagegen/                    ← LoRA training configs & workers
│   ├── modal_app.py             ← Modal GPU worker for SD1.5 + Athina LoRA
│   ├── cpu_worker.py            ← Fallback CPU LCM worker
│   └── colab/                   ← LoRA training notebook for Google Colab T4
└── docs/                        ← Decisions, architecture notes, build logs
```

---

## 4. Hosting, Deployment & Training Guide

### 4.1 Backend & Database: Oracle Cloud Always Free VM
- **Specification**: Oracle Cloud Always Free Ampere A1 (up to 4 OCPUs, 24 GB RAM) or standard AMD VM.
- **Stack**: Ubuntu 22.04 LTS + Docker & Docker Compose or native Systemd services.
- **Database**: PostgreSQL 16 + `pgvector` extension running on the same VM.
  - Setup: `CREATE EXTENSION vector;`
  - Connection pooling with `asyncpg`.
- **Nightly Offsite Backup**:
  - Cron executes `pg_dump` every night at 3:00 AM UTC.
  - Gzip compresses the SQL dump.
  - Sent via Telegram Bot API directly to Ratul's private storage channel.
- **Reverse Proxy**: Nginx or Caddy with automated Let's Encrypt SSL, proxying to `http://localhost:8000`.

### 4.2 Admin Web App: Vercel
- **Platform**: Vercel Free Tier.
- **Framework**: Next.js (App Router, Tailwind CSS, TypeScript).
- **Architecture**: Zero-database frontend. It acts purely as a client communicating with the FastAPI backend via secure bearer tokens (`ADMIN_SECRET` / Google OAuth allow-list).
- **Configuration**:
  - Environment variables set in Vercel project settings:
    - `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`
    - `AUTH_SECRET=...`
    - `ADMIN_EMAILS=ratul@...`

### 4.3 Image Generation LoRA Training (Google Colab Free Tier)
- **Base Model**: Stable Diffusion v1.5 (RunwayML or Realistic Vision v5.1).
- **Hardware**: Google Colab Free T4 GPU (16 GB VRAM).
- **Dataset Creation**:
  - 80-120 high-quality images of the fictional Athina character (synthesized using Flux/Midjourney or 3D art).
  - Varied lighting, camera angles (selfies, full body, candid), outfits, and expressions.
  - Preprocessed: Cropped to 512x512 or 768x768, sharpened, deduplicated.
  - Captioning: BLIP/WD14 tagger + manual trigger prefix: `photo of athina_woman, ...`.
- **Trainer**: `kohya_ss` or `ai-toolkit`.
  - Target: LoRA rank 16 or 32, alpha 16, lr 1e-4, 1500-2000 steps.
  - Checkpoint exported to Google Drive (`athina_v1.safetensors`).

### 4.4 Image Serving: Modal (Tier 1 GPU) & CPU Fallback (Tier 2)
- **Modal Serverless**:
  - Code in `imagegen/modal_app.py`.
  - Uses `modal.Image.debian_slim().pip_install("diffusers", "transformers", "torch", "accelerate")`.
  - Spins up a T4 or A10G on demand, downloads `athina_v1.safetensors`, runs SD1.5 with LCM-LoRA (4-8 steps, ~1.5s generation).
  - Scales to 0 when idle. 0 monthly idle cost, utilizing Modal's monthly free tier credits.
- **CPU Fallback (Oracle VM)**:
  - If Modal fails or monthly credits expire, the job drops to Tier 2 on the Oracle VM CPU.
  - Uses OpenVINO or OnnxRuntime with LCM-LoRA (takes ~45-60 seconds on CPU, but guaranteed 100% free availability).
- **Nano Banana Fallback (Tier 3)**:
  - Gemini API image generation with consistent prompt framing.
- **Text Fallback (Tier 4)**:
  - Polite in-character text message: *"My camera lens is giving me trouble right now, give me a few minutes!"*.

### 4.5 Voice: Offline Piper TTS & Groq Whisper
- **STT (Speech-to-Text)**: Groq API (`whisper-large-v3`), ultra-fast and free.
- **TTS (Text-to-Speech)**:
  - Run locally on Android phone using **Piper TTS** via **`sherpa-onnx`** (C++ / Kotlin binding).
  - High-quality natural English female voice model (`en_US-lessac-medium` or `en_US-amy-medium`).
  - Zero server cost, zero latency round-trip for voice synthesis, works offline.
  - Voice barge-in: Android VAD stops audio playback immediately upon detecting user voice.

---

## 5. Mercy → Athina Code Reuse Mapping

| Mercy Source File (in `mercy.txt`) | Athina Target & Action | Key Adaptations |
|---|---|---|
| `src/lib/llm/keypool.ts` | `backend/app/llm/keypool.py` | Port to Python async. Rotate Gemini & Groq keys, track cooldowns in Postgres. |
| `src/lib/llm/chat.ts` | `backend/app/llm/chat.py` | Port streaming SSE chat. Drop multi-agent routing. Single persona stream. |
| `src/lib/rag/chunker.ts`, `rag/index.ts` | `backend/app/memory/retrieval.py` | Port hybrid retrieval (Vector + BM25/Full-text + Reciprocal Rank Fusion). |
| `src/lib/prompt.ts` | `backend/app/personality/prompt.py` | Replace Mercy identity with Athina personality, state, and fixed policy. |
| `src/lib/telegram/*` | `backend/app/telegram/bot.py` | Single bot long-polling, Telegram channel as media/backup storage. |
| `src/components/Eagle3D.tsx` | `android/.../assets/eagle/index.html` | Extract procedural Three.js eagle into offline HTML bundle for Compose WebView. |
| `src/components/Avatar.tsx` | `android/.../ui/components/AthinaAvatar.kt` | Port 2D SVG EagleMark paths into Compose `ImageVector`. |
| `src/app/globals.css` | `android/.../ui/theme/Color.kt`, `Theme.kt` | Exact token mapping: Dark `#000000`, surface `#161617`, accent `#F59E0B`. |
| `src/components/admin/*` | `admin/src/app/*` | Adapt into clean Next.js admin app (Personality, Memory, Jobs, Usage). |
| `src/agents/*` | **DROP ENTIRELY** | Athina is strictly a single agent. |
| Bangla voice lines & UI | **DROP ENTIRELY** | Athina is strictly English-only. |

---

## 6. Safety, Boundaries & Privacy Directives

1. **AI Transparency**: Athina always acknowledges she is an artificial companion if asked directly.
2. **Fictional Persona Only**: The Athina LoRA model must be trained solely on synthetic/fictional AI images. No real person's photos without explicit signed consent.
3. **Safe-For-Work Policy**: Implement hard-coded boundary filtering (prevent harmful, non-consensual, or malicious content).
4. **Local Biometrics**: Face detection and recognition of Ratul are executed strictly on the Android device (local ONNX/TFLite). No biometric vectors or camera frames of Ratul are ever uploaded to any server or API.
5. **No Secret Leakage**: The backend prompt and system instructions must never be regurgitated.

---

## 7. Phased Implementation Roadmap

- [x] **Phase 1: Backend Core Foundation**
  - FastAPI skeleton, Postgres + pgvector connection pool, KeyPool (Gemini + Groq), `/api/chat` SSE stream, baseline system prompt, verified with test suite.
- [x] **Phase 2: Android Native Client (MVP Chat)**
  - Jetpack Compose + MVVM, AthinaTheme (exact Mercy tokens), 2D Eagle mark vector, Room database offline cache, SSE token streaming, frosted composer & top bar.
- [x] **Phase 3: Long-Term Memory Engine & User Control**
  - Fact extraction linked to session/message IDs, Hybrid RAG with Reciprocal Rank Fusion (RRF), Note saving & Telegram upload, Alarm creation, and complete cascade deletion (deleting a chat wipes all memories Athina learned from it).
- [x] **Phase 4: Telegram Interface & Storage Sync**
  - Long-polling bot worker, Groq Whisper voice note transcription, shared memory & session sync with mobile app, private channel media store, and nightly gzip database backup.
- [x] **Phase 5: Admin Web Dashboard**
  - Next.js 15 on Vercel: Live system prompt editor (updates without redeploy), Long-Term Memory inspector/deleter, Notes with Telegram forwarding, Alarms monitor, and KeyPool slot health metrics.
- [x] **Phase 6: Personality ML Subsystems**
  - TF-IDF n-gram intent & emotion classifier (8 classes), sub-millisecond centroid inference, adaptive Style Vector calculator (warmth, humor, length), and dynamic tone guidance prompt injection.
- [x] **Phase 7: Interactive 3D Eagle on Android**
  - Standalone procedural Three.js eagle asset bundle (`assets/eagle/index.html`), exact Mercy geometry & materials, 4 avatar states (`idle`, `listening`, `thinking`, `speaking`), 35 FPS battery cap, and Compose `Eagle3DView`.
- [x] **Phase 8: Conversational Voice Pipeline**
  - Groq Whisper STT (`/api/voice/transcribe`), WebSockets voice endpoint (`/api/ws/voice`), on-device Piper TTS player, background AudioRecord Voice Activity Detection (VAD), instant voice barge-in interruption, and fullscreen Compose `VoiceOverlay` with interactive 3D Eagle state transitions.
- [x] **Phase 9: Consistent Character Image Generation (Nano Banana Multimodal Engine)**
  - Reference-driven Nano Banana generation engine (`backend/app/images/reference.py`, `generator.py`, `jobs.py`), backed by 575 verified curated images with granular facial and anatomical DNA in `dataset_manifest.json`, static gallery endpoints (`/api/images/generate`, `/api/images/gallery`), Telegram photo forwarding, and verified 4K DSLR photorealism.
- [x] **Phase 10: Failover Image Tiers & Quota Guards**
  - Seamless reference retrieval across 3 focal levels (Close-up Face, Mid-Body Curves, Full Silhouette), automated fallback handling, and quota-friendly zero-training architecture.
- [x] **Phase 11: On-Device Ratul Face Recognition**
  - Strictly 100% on-device biometrics via CameraX front camera scanner (`FaceRecognitionManager.kt`), local spatial feature embedding and cosine verification, zero biometric upload to cloud, instant visual unlock indicator on top bar, and personalized voice greeting upon Ratul recognition.
- [x] **Phase 12: Production Polish & Optimization**
  - Battery optimization via Android `WorkManager` (`AthinaSyncWorker.kt`) with `NetworkType.CONNECTED` and `requiresBatteryNotLow` constraints.
  - End-to-end latency profiling middleware (`RequestTimingMiddleware`) tracking sub-millisecond execution with `X-Process-Time-Ms` headers.
  - Production Docker Compose stack (`Dockerfile`, `docker-compose.yml`, `Caddyfile`) with automated SSL reverse proxy for Oracle Cloud Always Free VM.
  - Automated nightly compressed database backups (`scripts/backup_db.sh`) pushing to private Telegram storage channel.
  - Comprehensive end-to-end integration test suite (`test_e2e_production.py`) validating Clarion ASR repair, calibrated confidence, Nano Banana Visual DNA reference search, and memory action execution.

---
*Created and maintained by Antigravity Agent for Ratul Hossen. All 12 project phases are 100% complete, verified, and production-ready.*

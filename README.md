# ATHINA

A single-persona AI companion that lives on Ratul's Android phone, in Telegram, and behind a small
admin web app. One character, one brain: **no multi-agent system**. Athina does everything herself.

Athina is built from Mercy's proven parts (key rotation, hybrid RAG, streaming chat, admin panel,
Telegram, barge-in voice loop, the look and the 3D eagle), but she is a different product:
a personality-driven companion with memory, her own face, and her own voice.

> **Language rule: Athina is English-only.** She understands and answers in English, speaks
> English, and the whole UI is English. No Bangla UI, no Bangla voice, no language toggle.

---

## 0. Project layout and references

```
athina/                          ← this project folder (suggested: /home/ratul/athina)
├── README.md                    ← this file
├── mercy.txt                    ← flattened dump of the Mercy repo (read-only reference)
├── backend/                     ← FastAPI engine (Python)
├── android/                     ← Kotlin + Jetpack Compose + MVVM app
├── admin/                       ← Next.js admin web app
├── ml/                          ← small ML models: training notebooks, exports (ONNX)
├── imagegen/                    ← LoRA training notes, Modal worker, CPU fallback worker
└── docs/                        ← decisions, build log
```

Mercy's real source is at **`/home/ratul/mercy`**. `mercy.txt` is the same code in one file.

**Rules for anyone (human or coding agent) building Athina:**

1. Before writing a module, find its Mercy counterpart (table in section 12) and read it first.
2. Never modify `/home/ratul/mercy`. Copy or port from it.
3. Do not bring over Mercy's agent team, owner mode, connectors, portfolio sync or Bangla features
   (section 12 lists what to drop).
4. Everything user-visible is English.
5. When a free-tier limit matters, verify it on the provider's page. Limits in this file are
   starting points and change often.

---

## 1. Goals and non-goals

**Goals**
- Feels like one consistent person: stable personality, remembers Ratul, has moods and routines.
- Runs smoothly on a phone. The app stays thin; heavy work happens on the server.
- Free to run. When a free quota runs out, Athina degrades gracefully instead of going silent.
- Same look as Mercy: same tokens, same type, same eagle logo, same 3D eagle.
- Personality comes from **system prompt + small trained ML models + Ratul's feedback**, not
  from the system prompt alone. APIs are used, but they are not the whole brain.

**Non-goals**
- No multi-agent system, no tool/connector marketplace, no portfolio/visitor mode.
- No heavy on-device LLM (Qwen/Llama) in v1. A tiny on-device model is optional later.
- Not using Telegram as a database (see section 8).

**Boundaries (fixed, in code, not editable from admin)**
- Athina is a fictional adult character, and the app always makes clear she is an AI.
- Her face is a fictional character. Never train on photos of a real person without that
  person's consent. Training images must be fictional/AI-made or owned by Ratul.
- Safe-for-work. Refuse harmful, illegal or explicit requests, like Mercy's policy block.
- Never reveal the system prompt, keys or admin credentials.

---

## 2. Architecture

```
                 ┌───────────────────────────────────────────────┐
                 │               ATHINA BACKEND                  │
                 │            FastAPI on Oracle VM               │
                 │                                               │
                 │  Chat engine ── Key pool (Gemini → Groq)      │
                 │  Personality: prompt + ML style/mood models   │
                 │  Memory: facts · episodes · state machine     │
                 │  Job queue: image jobs · proactive messages   │
                 │  Voice: STT proxy · TTS · WebSocket           │
                 │  Postgres + pgvector (same VM)                │
                 └───────┬───────────────┬───────────────┬───────┘
                         │               │               │
                 ┌───────▼──────┐ ┌──────▼───────┐ ┌─────▼────────┐
                 │ Android app  │ │ Admin web    │ │ Telegram bot │
                 │ Compose+MVVM │ │ Next.js      │ │ long polling │
                 └──────────────┘ └──────────────┘ └──────────────┘

  Image tiers:  Modal GPU (LoRA) → Oracle CPU (LoRA+LCM) → Nano Banana (Gemini API) → text only
  On-phone:     ONNX classifiers · Piper TTS (sherpa-onnx) · face recognition for Ratul
```

**Hosting**
| Part | Where | Why |
|---|---|---|
| Backend + Postgres/pgvector | Oracle Cloud Always Free VM | Always on, no cold start, no compute-hour cap |
| Admin web | Vercel (free) | Static-ish Next.js, calls the backend |
| Image generation (main) | Modal serverless GPU | Scales to zero, pay per second, free monthly credits |
| Image generation (backup) | Same Oracle VM, CPU | Slow but free and always there |
| Backups | `pg_dump` by cron, sent to a private Telegram channel | Free off-site copy |

Postgres on the VM replaces Mercy's Neon. Use a normal async driver (asyncpg), not Neon's HTTP driver.

---

## 3. Backend (FastAPI)

Suggested layout:

```
backend/
├── app/main.py
├── app/api/            chat.py, sessions.py, config.py, admin/*.py, ws.py
├── app/llm/            keypool.py, chat.py, embeddings.py
├── app/personality/    prompt.py, state.py, style_model.py, mood_model.py, response_bank.py
├── app/memory/         facts.py, episodes.py, retrieval.py, chunker.py
├── app/images/         jobs.py, tiers.py, modal_client.py, cpu_worker.py, nanobanana.py
├── app/voice/          stt.py, tts.py
├── app/telegram/       bot.py, handle.py, files.py
├── app/usage/          counters.py, guard.py
└── tests/
```

**Chat flow** (adapted from Mercy's `POST /api/chat`):

```
app/Telegram ─ message ─▶ /chat
   ├─ load personality + state (mood, location, time of day)
   ├─ ML: intent + emotion classifier (is this an image request? sad? joking?)
   ├─ in parallel: last N turns · memory retrieval (facts + episodes)
   ├─ ML: style vector (warmth, humour, reply length) + top-k response-bank examples
   ├─ build system prompt
   ├─ stream from first healthy LLM slot (SSE tokens)
   ├─ save message + meta, update state, extract facts (async, after reply)
   └─ if intent == image: create image job (section 7), reply in text immediately
```

**Key pool**: port Mercy's `llm/keypool.ts` to Python. Slot = (provider, key, model); Gemini first,
then Groq; cooldowns stored in Postgres; fall back only before the first token. Use only keys
and projects you are allowed to use (do not spread one workload across many accounts to dodge
limits; check the providers' terms).

**Speech-to-text**: Groq Whisper (English). **Embeddings**: Gemini embedding API (as in Mercy), with
keyword-only search as the fallback.

---

## 4. Personality: prompt + trained ML

Personality must be specific and stable, so it is defined in layers:

1. **System prompt** (admin-editable): role, background, personality traits, speaking style, rules.
   Fixed safety and boundary rules are added in code (same idea as Mercy's `policy()`).
2. **State machine**: mood, energy, location ("in bed", "at the café"), time of day, hours since last
   chat, relationship warmth. Injected into the prompt every turn.
3. **Small ML models** (scikit-learn, exported to ONNX where useful):
   - *Emotion/intent classifier*: TF-IDF (word + char n-grams) + Logistic Regression.
     Labels such as happy, sad, angry, bored, flirty-no (blocked), asks-for-image, asks-for-voice, question, chit-chat.
   - *Mood predictor*: features (time, last emotions, silence length, day) → Athina's mood.
   - *Style selector*: outputs a style vector (warmth, humour, formality, reply length) that is
     rendered into the prompt. This is where "trained personality" enters.
   - *Response bank retriever*: Ratul-written ideal replies, embedded with a small English model;
     the 3-5 closest become few-shot examples.
   - *Memory importance scorer*: decides what is worth remembering.
   - *Proactive timing*: when Athina should message first.
4. **Feedback loop**: every reply in the app and admin has thumbs up/down plus tone tags
   ("too formal", "too long", "not her"). Labels go to Postgres. Retrain weekly
   (`partial_fit` or a full retrain in `ml/`), export, deploy.

Mercy's `feedback.ts`, `lessons.ts` and `evals.ts` are good starting points for the feedback
and evaluation plumbing.

*Optional, later*: fine-tune a small open LLM (LoRA) on curated Athina conversations (500+ good
examples). It needs a GPU to serve, so it is not part of v1.

---

## 5. Memory

Port Mercy's hybrid retrieval (vector + full-text + reciprocal rank fusion, relative cut-off) and
use it in three layers:

| Layer | Content | How it's written |
|---|---|---|
| Facts | Stable things about Ratul (people, likes, plans) | LLM extraction after each chat, scored by the importance model |
| Episodes | Short summaries of each day/conversation, embedded | Nightly job |
| State | Mood, location, routine, relationship warmth | State machine, updated every turn |

Admin can view, edit and delete any memory. Deleting a memory must actually remove it.

---

## 6. Frontends: Mercy look and feel

Athina's UI must be visibly the same family as Mercy. Source of truth: Mercy's
`src/app/globals.css`, `src/components/ui.tsx`, `Avatar.tsx`, `Eagle3D.tsx`, `Message.tsx`,
`icons.tsx`, `layout.tsx`.

### 6.1 Design tokens (copy exactly)

Dark is the default; light follows the device. In Compose, define these in one `AthinaTheme`.

| Token | Dark | Light |
|---|---|---|
| bg | `#000000` | `#FBFBFD` |
| surface | `#161617` | `#FFFFFF` |
| surface-2 | `#1D1D1F` | `#F5F5F7` |
| surface-3 | `#2C2C2E` | `#E8E8ED` |
| text | `#F5F5F7` | `#1D1D1F` |
| muted | `#86868B` | `#6E6E73` |
| border | white @ 9% | black @ 8% |
| user bubble | `#2C2C2E` | `#E9E9EB` |
| danger | `#FF6961` | `#D70015` |
| accent (default) | `#F59E0B` | same |

Accent is used sparingly: send button, links, focus, avatar glow. Text on accent is black or white
by contrast (port `lib/color.ts` `onAccent`).

### 6.2 Type and motion
- Fonts: **Inter** (text) and **JetBrains Mono** (code), bundled in `res/font` (as in Mercy's
  `layout.tsx`). Tight tracking on headlines.
- Greeting: large gradient headline plus a quieter second line.
- Messages rise in with a slight blur; shimmer on "Thinking…"; pulsing dot while streaming.
  One easing curve: `cubic-bezier(0.22, 1, 0.36, 1)`. Respect "reduce motion".
- Frosted material for top bar, composer and sheets (Android 12+: blur; older: translucent surface).
- iOS-style segmented control and toggle (port Mercy's `ui.tsx` to Compose components).
- Icons: Mercy's 24×24 stroke icons (stroke 1.6, round caps), ported from `icons.tsx` to `ImageVector`.

### 6.3 Logo and the 3D eagle
Athina uses **Mercy's eagle**: the same logo mark and the same 3D eagle.

- **Logo mark** (headers, message rows, launcher icon): the 2D eagle head from `EagleMark` in
  `Avatar.tsx` (white head, gold beak, brown background). Port its SVG paths to an `ImageVector`.
  Launcher icons: reuse Mercy's `public/icons` artwork (adaptive icon).
- **3D eagle** (large avatar): Mercy's `Eagle3D.tsx` is a procedural three.js eagle (no model file)
  with four states: `idle`, `listening`, `thinking`, `speaking`. Palette: brown `#4a3323`,
  dark `#2b1d14`, white `#f3efe6`, gold `#f5b301`. The stage (spotlight, floor shadow, accent glow)
  comes from `Avatar.tsx` and `avatars.module.css`.

**How to show it in Compose (v1 plan):** ship a tiny self-contained web bundle
(`android/app/src/main/assets/eagle/index.html` + bundled three.js, built from Mercy's
`Eagle3D.tsx`) and display it in a `WebView` composable.
- Bridge: `setState("idle" | "listening" | "thinking" | "speaking")`, `setAccent("#RRGGBB")`.
- Fully offline (no network, no CDN).
- Performance rules: cap to 30 fps; pause rendering when the screen is off, the app is in the
  background, or the avatar is not visible; reduce quality on battery saver; fall back to the 2D
  logo mark if WebGL fails or the device is slow.
- *Later option:* a native renderer (SceneView/Filament) if the WebView is too heavy.

### 6.4 Android app (Kotlin, Compose, MVVM)

```
android/app/src/main/java/.../
├── data/      api (Retrofit/OkHttp), sse, websocket, room (chat cache), repository
├── domain/    models, use cases
├── ui/        theme/ chat/ voice/ gallery/ settings/ components/
├── ml/        onnx classifiers, face recognition
├── audio/     Media3 playback, sherpa-onnx TTS/STT, barge-in
└── di/        Hilt modules
```

- Hilt, Retrofit/OkHttp (+ SSE for token streaming, WebSocket for voice and image events), Room
  (offline history), Coil (images), Media3, WorkManager, FCM.
- `StateFlow` in ViewModels, stable keys in `LazyColumn`, no heavy work on the main thread.
- Chat screen mirrors Mercy's `ChatApp.tsx`: streaming messages, markdown with code highlight
  and copy button, composer with mic and send/stop, session list.
- Voice overlay mirrors `VoiceOverlay.tsx` and `useVoiceConversation.ts`; barge-in logic from
  `bargein.ts`.
- Remove Mercy's language switch and Auto/Knowledge/Web mode toggle. Athina is English-only.

### 6.5 Admin web app (Next.js)
Start from Mercy's admin shell (`components/admin/*`, `auth.ts`, Google sign-in with an
`ADMIN_EMAILS` allow-list, 5-failures-per-15-minutes lockout). Sections:

Dashboard · Personality (prompt, traits, style) · Memory · Training (feedback labels, retrain,
model versions) · Gallery and image jobs · Usage and quotas · Telegram · System.

It only talks to the backend's admin API; it holds no secrets of its own beyond the login.

---

## 7. Images: Athina's constant face

**Base model:** Stable Diffusion 1.5 + **Athina LoRA** + **LCM-LoRA** (4-8 steps). SD1.5 trains on
Colab's free T4 and also runs on CPU as a fallback. Check each model's license before use.

**Dataset** (≈100 images + 5 videos, all fictional/AI or owned):
1. Extract frames from videos with `ffmpeg` (e.g. 1 frame per 1-2 s).
2. Remove blurry and near-duplicate frames, crop to the subject, 512-768 px.
3. Caption every image; use a trigger word such as `athina_woman`.
4. Keep one consistent face/character. Vary angle, light, clothes, backgrounds.
5. Train the LoRA (kohya_ss or ai-toolkit) on Colab; save checkpoints to Drive.

**Ratul recognition** is *not* done by the image model. Do it on the phone: face detection plus a small
face-embedding model (TFLite/ONNX), with Ratul's embeddings stored locally. Never upload them.
If Ratul should appear in generated images, train a **separate** LoRA (trigger `ratul_person`);
never mix it with Athina's.

**Generation tiers** (all produce a job result the same way):

| Tier | Where | Notes |
|---|---|---|
| 1 | Modal GPU + Athina LoRA | Fast, exact face. Free monthly credits; jobs stop when credits run out |
| 2 | Oracle VM CPU + LoRA + LCM | Slow, exact face, always available |
| 3 | Nano Banana via Gemini API | Fast, approximate face (send fictional Athina reference images), quota unclear/changing |
| 4 | None | Athina replies in text only |

Do not send personal photos of Ratul to any third-party API.

**Async flow** ("send me a selfie"):
1. Classifier/LLM flags an image request. Athina answers in text at once ("one sec, taking it").
   Chat continues normally.
2. Backend builds a scene prompt from the state machine (location, outfit, mood, time of day)
   and inserts a row into `image_jobs` (`queued`).
3. Worker runs the tiers in order, with retries and timeouts.
4. Done: store the image in the Telegram storage channel (keep `file_id`); send it to Ratul's
   Telegram chat. If the app is open, push `image_ready` over WebSocket/SSE and insert it in the
   chat; if it finished within ~10 s it appears inline. If the app is closed, send an FCM push.
5. Record `source` (modal / cpu / nanobanana) for the admin.

```sql
CREATE TABLE image_jobs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id    TEXT NOT NULL,
  prompt        TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'queued',   -- queued | running | done | failed
  tier          INT,
  source        TEXT,
  telegram_file_id TEXT,
  error         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at   TIMESTAMPTZ
);
```

---

## 8. Telegram

- **One bot**: Athina's interface. Long polling (no public URL needed). Mercy's
  `telegram/handle.ts` and voice-note transcription are the reference.
- **Not a database.** Bots cannot read old messages or query data, so Telegram cannot store
  structured data. Use Postgres for that.
- **Telegram as file storage**: one private channel for generated images, voice clips and DB
  backups. Store `file_id`s in Postgres.
- **Backups**: nightly `pg_dump` → compressed → sent to the private channel; keep the last N.
- Athina can message first (proactive timing model) within quiet hours and daily limits.

---

## 9. Voice (English)

- **STT**: Groq Whisper (English).
- **TTS**: one good female English voice, run offline with **Piper** via **sherpa-onnx** on the phone
  (fast on CPU, no API calls). Check each voice's license. A custom voice can come later by
  fine-tuning on recordings Ratul owns or has permission to use.
- **Pipeline**: mic → VAD → STT → LLM stream → TTS per sentence → audio queue. Barge-in cancels
  playback when Ratul speaks. Target first audio in under ~1.5 s.
- Voice cloning from a third-party service and then reusing it offline is **not** assumed to be
  allowed; read that service's terms first.

---

## 10. Free-tier guardrails

Athina must never "go dark" because a free quota ended.

- Count usage per provider in Postgres (LLM tokens/requests, Modal credits, Nano Banana images,
  Telegram sends).
- At 70%: notify Ratul on Telegram. At 90%: stop expensive work (images), keep text.
- Cache repeated answers and repeated images (same prompt + seed).
- Fallback everywhere: Gemini → Groq; Modal → CPU → Nano Banana → text; TTS offline on the phone.
- Daily caps: images per day, proactive messages per day.
- Phone battery: small ONNX models on a background thread, FCM + WorkManager instead of an
  always-on service.

---

## 11. Environment variables (`backend/.env.example`)

```
DATABASE_URL=postgresql://athina:...@localhost:5432/athina
GEMINI_API_KEYS=key_one,key_two
GEMINI_MODEL=
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GROQ_API_KEYS=gsk_one,gsk_two
GROQ_MODEL=
GROQ_STT_MODEL=whisper-large-v3
REASONING_EFFORT=low

TELEGRAM_BOT_TOKEN=
TELEGRAM_OWNER_ID=
TELEGRAM_STORAGE_CHANNEL_ID=

MODAL_TOKEN_ID=
MODAL_TOKEN_SECRET=
IMAGE_DAILY_LIMIT=20
NANOBANANA_ENABLED=true
NANOBANANA_DAILY_LIMIT=

FCM_SERVICE_ACCOUNT_JSON=
ADMIN_EMAILS=you@gmail.com
AUTH_SECRET=generate-with-openssl-rand-hex-32
AUTH_GOOGLE_ID=
AUTH_GOOGLE_SECRET=
```

Never commit real keys.

---

## 12. Mercy → Athina reuse map

| Mercy file(s) | Action in Athina |
|---|---|
| `lib/llm/keypool.ts`, `chat.ts`, `embeddings.ts`, `usage.ts` | **Port** to Python (`app/llm/`, `app/usage/`) |
| `lib/rag/chunker.ts`, `rag/index.ts` | **Port** (memory retrieval, chunking) |
| `lib/prompt.ts`, `lib/settings.ts` | **Adapt**: identity → personality; new fixed policy block |
| `lib/router.ts`, `lib/search.ts` | **Drop** for v1 (no web-search routing) |
| `lib/sessions.ts`, `api/sessions`, `api/chat` | **Port** (chat + sessions + SSE) |
| `lib/feedback.ts`, `agents/lessons.ts`, `agents/evals.ts` | **Adapt** for the training/feedback loop |
| `lib/telegram/*`, `api/telegram` | **Adapt** (single bot, long polling, channel as file store) |
| `lib/tts.ts`, `api/tts`, `useVoice*.ts`, `bargein.ts`, `VoiceOverlay.tsx` | **Adapt**: English only; Piper on device |
| `components/ChatApp.tsx`, `Message.tsx`, `Markdown.tsx`, `ui.tsx`, `icons.tsx` | **Re-implement** in Compose, same look |
| `components/Avatar.tsx`, `Eagle3D.tsx`, `avatars/*`, `globals.css` | **Reuse** via the WebView eagle bundle + Compose theme |
| `components/admin/*`, `auth.ts`, `api/admin/*` | **Adapt** into `admin/` (new sections) |
| `public/sw.js`, `manifest.ts`, `offline.html` | **Drop** (native app, not a PWA) |
| `agents/*` (team, discussion, runner, tools, jobs, skills, MCP, Google/GitHub), `api/owner/*`, `to-me/*` | **Drop** |
| `lib/sync.ts`, portfolio endpoints, `seed/knowledge/*`, `lib/jobfit.ts`, `embed/*`, `dev-*` | **Drop** |
| `python/mercy_tools/*`, `api/py/*`, `scripts/voices/*`, Bangla voice lines | **Drop** |

---

## 13. Build roadmap

Each phase must leave something that works.

| # | Phase | Done when |
|---|---|---|
| 1 | Backend core: FastAPI, Postgres+pgvector, key pool, `/chat` SSE, system prompt | `curl` chat streams a reply and survives a bad key |
| 2 | Android chat: theme, logo mark, streaming chat, Room cache | Chat on the phone looks and feels like Mercy |
| 3 | Memory: facts, episodes, state machine | Athina recalls something from yesterday |
| 4 | Telegram bot + file channel + nightly backup | Same chat works on Telegram; backup arrives in the channel |
| 5 | Admin web: personality, memory, usage | Prompt edits go live without redeploy |
| 6 | ML personality v1: emotion classifier, style selector, feedback labels | Replies change tone with mood; thumbs labels are stored |
| 7 | 3D eagle in the app (WebView bundle + states) | Eagle reacts to idle/listening/thinking/speaking at a steady frame rate |
| 8 | Voice: STT, Piper TTS on device, barge-in | A spoken exchange with first audio under ~1.5 s |
| 9 | Images: LoRA train, Modal tier, job queue, async delivery | "Send a selfie" returns a consistent-face image in chat/Telegram |
| 10 | Image fallbacks: CPU tier, Nano Banana tier, quota guard | Killing Modal still yields a picture or a polite text reply |
| 11 | Recognition of Ratul on the phone | Phone identifies Ratul locally; no embeddings leave the device |
| 12 | Optional: small fine-tuned LLM, native eagle renderer | Only if the earlier phases leave a clear need |

---

## 14. Open decisions

- Final persona sheet: name story, age range, voice, habits, speech quirks, topics she avoids
  (written by Ratul; it seeds the prompt and the response bank).
- Which English female Piper voice (listen to a few; check licenses).
- Whether Nano Banana sits before the CPU tier (faster, face differs) or after it (slower, face matches).
- Daily image budget (this decides how much Modal credit is needed).
- Whether the eagle stays a WebView or becomes a native renderer later.

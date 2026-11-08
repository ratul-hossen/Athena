import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.db.session import init_db
from backend.app.llm.keypool import key_pool
from backend.app.telegram.bot import telegram_worker
from backend.app.api.chat import router as chat_router
from backend.app.api.sessions import router as sessions_router
from backend.app.api.health import router as health_router
from backend.app.api.memories import router as memories_router
from backend.app.api.admin import router as admin_router
from backend.app.api.voice import router as voice_router
from backend.app.api.ws import router as ws_router
from backend.app.api.images import router as images_router

logger = logging.getLogger("athina.latency")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database schema, key pool, and Telegram long-polling worker
    await init_db()
    await key_pool.load_state_from_db()
    telegram_worker.start()
    yield
    # Shutdown: Stop long-polling loop cleanly
    telegram_worker.stop()

app = FastAPI(
    title="Athina Engine",
    description="Single-Persona AI Companion Backend Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Latency Profiling Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000.0  # in milliseconds
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    
    if process_time > 1500:
        logger.warning(f"High latency on {request.method} {request.url.path}: {process_time:.1f}ms")
    return response

# CORS configuration for Android app & Vercel Admin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(health_router)
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(memories_router)
app.include_router(admin_router)
app.include_router(voice_router)
app.include_router(ws_router)
app.include_router(images_router)

# Mount static images directory for generated photos
static_images_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../static/images"))
os.makedirs(static_images_dir, exist_ok=True)
app.mount("/static/images", StaticFiles(directory=static_images_dir), name="static_images")

@app.get("/")
async def root():
    return {
        "companion": "Athina",
        "description": "I am Athina, Ratul's personal AI companion.",
        "status": "active",
        "docs": "/docs"
    }

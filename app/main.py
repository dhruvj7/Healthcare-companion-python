from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.api.v1.routes import appointment_scheduler, auth, symptom_analysis
from app.api.v1.routes import hospital_guidance
from app.api.v1.routes import insurance
from app.api.v1.routes import unified_chat
from app.api.middleware.error_handler import error_handler_middleware
from app.api.middleware.logging_middleware import logging_middleware
from app.core.config import settings
from app.core.logging import setup_logging

from app.data.schemas.appointment import init_db, seed_sample_data

import logging

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown"""
    logger.info("Starting Healthcare AI Service...")
    # Startup logic here
    await init_db()
    await seed_sample_data()
    logger.info("Database initialized and sample data seeded successfully")

    yield
    # Shutdown logic here
    logger.info("Shutting down Healthcare AI Service...")

# Create FastAPI app
app = FastAPI(
    title="Healthcare AI Service",
    description="AI-powered healthcare companion system",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Middleware
app.middleware("http")(logging_middleware)
app.middleware("http")(error_handler_middleware)

# Include routers
app.include_router(
    symptom_analysis.router,
    prefix="/api/v1",
    tags=["Symptom Analysis"]
)

app.include_router(
    appointment_scheduler.router,
    prefix="/api/v1",
    tags=["Appointment Scheduler"]
)

app.include_router(
    hospital_guidance.router,
    prefix="/api/v1",
    tags=["Hospital Guidance"]
)

app.include_router(
    insurance.router,
    prefix="/api/v1/insurance",
    tags=["Insurance Validation"]
)

app.include_router(
    auth.router, 
    prefix="/api/v1", 
    tags=["Authentication"])

# ===== UNIFIED CHAT ENDPOINT (Main Entry Point) =====
app.include_router(
    unified_chat.router,
    prefix="/api/v1/public",
    tags=["Unified Chat (AI Orchestrator)"]
)

# Share active sessions with insurance router
insurance.set_active_sessions(hospital_guidance.get_active_sessions())

@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "symptom-analysis"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
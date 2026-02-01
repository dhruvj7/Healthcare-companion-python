from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.api.v1.routes import symptom_analysis
from app.api.middleware.error_handler import error_handler_middleware
from app.api.middleware.logging_middleware import logging_middleware
from app.core.config import settings
from app.core.logging import setup_logging

import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown"""
    logger.info("Starting Healthcare AI Service...")
    # Startup logic here
    yield
    # Shutdown logic here
    logger.info("Shutting down Healthcare AI Service...")

# Create FastAPI app
app = FastAPI(
    title="Healthcare AI Service",
    description="AI-powered healthcare companion system",
    version=settings.VERSION,
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
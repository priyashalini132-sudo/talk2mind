import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api import auth_routes, assessment_routes, chatbot_routes, dashboard_routes, reports_routes
from .database import Base, engine

# Ensure all tables exist on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Talk2Mind – Multimodal AI-Based Mental Well-Being Assessment and Support System.\n\n"
        "⚠️ **Medical Disclaimer:** This application is for educational and research purposes only. "
        "It is NOT a substitute for professional medical advice, diagnosis, or treatment. "
        "Always seek the advice of a qualified mental health professional."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Restrict to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ──────────────────────────────────────────────────────────
app.include_router(auth_routes.router,       prefix=settings.API_V1_STR)
app.include_router(assessment_routes.router, prefix=settings.API_V1_STR)
app.include_router(chatbot_routes.router,    prefix=settings.API_V1_STR)
app.include_router(dashboard_routes.router,  prefix=settings.API_V1_STR)
app.include_router(reports_routes.router,    prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def read_root():
    return {
        "status": "online",
        "project": "Talk2Mind – Multimodal Mental Well-Being AI",
        "version": "2.0.0",
        "documentation": "/docs",
        "disclaimer": "Educational tool only. Not a medical service.",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "timestamp": __import__("datetime").datetime.utcnow().isoformat()}

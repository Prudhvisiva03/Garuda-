from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database import init_db
from backend.app.routes import health, evidence, analysis, reports, video, audio, cases, audit

# Ensure database tables exist
init_db()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Garuda Digital Forensics Engine & Integrity Verification API (Bihar Cyber Hackathon 2026 - PS-05)",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration for development and local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount versioned API routes under /api/v1
api_v1 = FastAPI(title="Garuda API v1")
api_v1.include_router(health.router)
api_v1.include_router(evidence.router)
api_v1.include_router(analysis.router)
api_v1.include_router(reports.router)
api_v1.include_router(video.router)
api_v1.include_router(audio.router)
api_v1.include_router(cases.router)
api_v1.include_router(audit.router)

app.mount(settings.API_V1_STR, api_v1)

# Also include routes directly under root for convenient direct routing
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(evidence.router, prefix=settings.API_V1_STR)
app.include_router(analysis.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(video.router, prefix=settings.API_V1_STR)
app.include_router(audio.router, prefix=settings.API_V1_STR)
app.include_router(cases.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "documentation": "/docs",
        "api_v1": settings.API_V1_STR,
        "status": "operational",
    }

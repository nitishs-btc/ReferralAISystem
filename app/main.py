"""FastAPI application entrypoint for the referral automation backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.referral import router as referral_router
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging(settings.LOG_LEVEL)

app = FastAPI(title=settings.APP_NAME)

# Allow the local dashboard to talk to the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(referral_router)


@app.get("/")
def health_check():
    # Lightweight health endpoint used by local checks and deployment probes.
    return {
        "status": "running",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.referral import router as referral_router

app = FastAPI(
    title="Referral AI System"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(referral_router)


@app.get("/")
def health_check():
    return {
        "status": "running"
    }
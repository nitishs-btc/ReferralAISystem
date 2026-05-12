from fastapi import FastAPI

from app.api.routes.referral import router as referral_router

app = FastAPI(
    title="Referral AI System"
)

app.include_router(referral_router)


@app.get("/")
def health_check():
    return {
        "status": "running"
    }
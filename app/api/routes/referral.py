from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from app.pipelines.referral_pipeline import ReferralPipeline

router = APIRouter(
    prefix="/referrals",
    tags=["Referrals"]
)


@router.post("/analyze")
async def analyze_referral(
    file: UploadFile = File(...)
):

    result = await ReferralPipeline.process(file)

    return result
from fastapi import APIRouter, File, UploadFile

from app.pipelines.referral_pipeline import ReferralPipeline
from app.services.file_handler_service import FileHandlerService

router = APIRouter(prefix="/referrals", tags=["Referrals"])


@router.post("/analyze")
async def analyze_referral(file: UploadFile = File(...)):
    """
    Analyze a single upload.
    Archive uploads are expanded and returned as a batch response.
    """

    if FileHandlerService.is_archive(file.filename or ""):
        result = await ReferralPipeline.process_archive(file)
        return result.model_dump()

    result = await ReferralPipeline.process(file)
    return result


@router.post("/analyze-batch")
async def analyze_referrals_batch(files: list[UploadFile] = File(...)):
    """
    Analyze many uploads concurrently with fault isolation per file.
    """

    result = await ReferralPipeline.process_batch(files)
    return result.model_dump()

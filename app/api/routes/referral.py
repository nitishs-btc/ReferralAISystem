from typing import List
from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from app.pipelines.referral_pipeline import ReferralPipeline
from app.pipelines.file_handler import FileHandler

router = APIRouter(
    prefix="/referrals",
    tags=["Referrals"]
)


@router.post("/analyze")
async def analyze_referral(
    file: UploadFile = File(...)
):
    """
    Analyze single referral document.
    Supports: PDF, images, Word docs, ZIP, TAR archives.
    """

    if FileHandler.is_archive(file.filename):
        results = await ReferralPipeline.process_archive(file)
        return results

    result = await ReferralPipeline.process(file)

    return result


@router.post("/analyze-batch")
async def analyze_referrals_batch(
    files: List[UploadFile] = File(...)
):
    """
    Analyze multiple referral documents.
    
    Upload options:
    - Multiple files selected together
    - Folder contents (use webkitdirectory in frontend)
    - ZIP or TAR archive files
    
    Returns array of results for each file.
    """

    results = await ReferralPipeline.process_batch(files)

    return results
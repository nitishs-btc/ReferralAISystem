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
    files: List[UploadFile] = File(..., description="Select multiple files (Ctrl+Click for multi-select, supports 100+ files)")
):
    """
    Analyze multiple referral documents (supports 100+ files).
    
    **Swagger UI:** Use Ctrl+Click or Shift+Click to select multiple files.
    
    **Frontend folder upload:** Use webkitdirectory attribute:
    ```html
    <input type="file" webkitdirectory multiple>
    ```
    
    Supports: PDF, images, Word docs, ZIP/TAR archives.
    
    Returns array of results for each file.
    """

    results = await ReferralPipeline.process_batch(files)

    return results
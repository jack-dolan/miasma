"""
Profile generation endpoints
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_required_user_id
from app.core.config import settings
from app.schemas.generator import GeneratePreviewRequest, GeneratePreviewResponse
from app.services.data_generator_service import DataGeneratorService

router = APIRouter()


@router.post("/preview", response_model=GeneratePreviewResponse)
async def generate_preview(
    request: GeneratePreviewRequest,
    user_id: int = Depends(get_required_user_id),
):
    """Generate sample fake profiles without persisting them."""
    svc = DataGeneratorService(locale=settings.FAKER_LOCALE)
    if request.target_first_name and request.target_last_name:
        profiles = svc.generate_poisoning_profiles(
            first_name=request.target_first_name,
            last_name=request.target_last_name,
            count=request.count,
            real_state=request.target_state,
            real_age=request.target_age,
        )
    else:
        profiles = svc.generate_profiles(count=request.count, template=request.template)
    return GeneratePreviewResponse(profiles=profiles)

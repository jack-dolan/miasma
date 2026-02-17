from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_campaigns():
    """List user campaigns - placeholder"""
    return {"message": "Campaigns endpoint - coming soon"}
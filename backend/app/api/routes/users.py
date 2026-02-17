from fastapi import APIRouter

router = APIRouter()

@router.get("/profile")
async def get_profile():
    """Get user profile - placeholder"""
    return {"message": "User profile endpoint - coming soon"}
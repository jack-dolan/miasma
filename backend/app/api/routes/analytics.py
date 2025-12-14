from fastapi import APIRouter

router = APIRouter()

@router.get("/dashboard")
async def get_analytics():
    """Get analytics dashboard - placeholder"""
    return {"message": "Analytics endpoint - coming soon"}

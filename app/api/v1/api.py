from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    users,
    facilities,
    patients,
    referrals,
    documents,
    voice_notes,
    ai,
    analytics,
    notifications,
    duplicates,
    analytics,
)
from app.api.v1 import websocket

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(facilities.router, prefix="/facilities", tags=["facilities"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(referrals.router, prefix="/referrals", tags=["referrals"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(
    voice_notes.router, prefix="/voice-notes", tags=["voice-notes"]
)
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(websocket.router, prefix="/websocket", tags=["websocket"])
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["notifications"]
)
# Include v2 enhancements within the standard ecosystem mapping
api_router.include_router(duplicates.router, prefix="/duplicates", tags=["V2 - Patient Deduplication"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["V2 - Analytics & AI Intelligence"])


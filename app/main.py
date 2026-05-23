from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.core.config import settings
from app.db.seed_initial_admin import create_initial_super_admin

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Powered Healthcare Referral System API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def startup_event():
    try:
        create_initial_super_admin()
    except Exception as e:
        print(f"Super admin seed failed: {e}")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "mediflow-backend"}

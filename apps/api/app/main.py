from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.config import settings
from app.library.routes import router as library_router
from app.pipeline.routes import router as generate_router
from app.profile.routes import router as profile_router

app = FastAPI(title="PromptForge API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(generate_router)
app.include_router(profile_router)
app.include_router(library_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

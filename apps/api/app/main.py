from fastapi import FastAPI

from app.auth.routes import router as auth_router
from app.pipeline.routes import router as generate_router

app = FastAPI(title="PromptForge API")
app.include_router(auth_router)
app.include_router(generate_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

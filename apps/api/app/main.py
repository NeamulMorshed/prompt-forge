from fastapi import FastAPI

from app.auth.routes import router as auth_router

app = FastAPI(title="PromptForge API")
app.include_router(auth_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

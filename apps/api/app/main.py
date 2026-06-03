from fastapi import FastAPI

app = FastAPI(title="PromptForge API")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

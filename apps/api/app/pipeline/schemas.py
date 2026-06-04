from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=2000)
    ignore_profile: bool = False


class AnswerRequest(BaseModel):
    session_id: str
    slot_id: str
    answer: str


class QuestionOut(BaseModel):
    slot_id: str
    question: str
    chips: list[str]
    allow_freetext: bool


class ScoreOut(BaseModel):
    composite: float
    dimensions: dict[str, float]
    suggestions: list[str]
    scored: bool = True


class GenerationResultOut(BaseModel):
    prompt: str
    score: ScoreOut
    prompt_version_id: str


class TurnResponse(BaseModel):
    session_id: str
    status: str
    question: QuestionOut | None = None
    result: GenerationResultOut | None = None
    suggest_profile_save: bool = False
    extractable_slots: dict[str, str] = {}
    profile_loaded: bool = False


class RunRequest(BaseModel):
    prompt_version_id: str


class RunResponse(BaseModel):
    output: str


class RateRequest(BaseModel):
    prompt_version_id: str
    rating: int
    feedback: str | None = None


class RateResponse(BaseModel):
    ok: bool


class BranchRequest(BaseModel):
    prompt_version_id: str

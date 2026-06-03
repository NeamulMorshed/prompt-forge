from pydantic import BaseModel


class StartRequest(BaseModel):
    input: str


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


class GenerationResultOut(BaseModel):
    prompt: str
    score: ScoreOut
    prompt_version_id: str


class TurnResponse(BaseModel):
    session_id: str
    status: str
    question: QuestionOut | None = None
    result: GenerationResultOut | None = None


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

from pydantic import BaseModel, Field


class EmbedStartRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=2000)
    model_target: str | None = None


class EmbedAnswerRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    slot_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


class EmbedQuestionOut(BaseModel):
    slot_id: str
    question: str
    chips: list[str]
    allow_freetext: bool


class EmbedScoreOut(BaseModel):
    composite: float
    suggestions: list[str]


class EmbedResultOut(BaseModel):
    prompt: str
    score: EmbedScoreOut
    prompt_version_id: str


class EmbedTurnResponse(BaseModel):
    session_id: str
    status: str              # "needs_question" | "done"
    question: EmbedQuestionOut | None = None
    result: EmbedResultOut | None = None

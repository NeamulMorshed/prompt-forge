from typing import Literal

from pydantic import BaseModel, Field

_VALID_MODELS = Literal["gemini-2.0-flash", "gpt-4o", "claude-sonnet-4-6"]


class StartRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=2000)
    ignore_profile: bool = False
    model_target: _VALID_MODELS | None = None


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


_VALID_MODULES = Literal[
    "role", "objective", "context", "task", "format",
    "patterns", "examples", "reasoning", "guardrails"
]


class EditModuleRequest(BaseModel):
    prompt_version_id: str
    module_name: _VALID_MODULES
    new_text: str = Field(..., min_length=1, max_length=5000)


class EditModuleResponse(BaseModel):
    new_prompt_version_id: str
    score: ScoreOut
    full_prompt: str


class AutoImproveRequest(BaseModel):
    prompt_version_id: str


class AutoImproveResponse(BaseModel):
    new_prompt_version_id: str
    improved: bool          # False if already high-scoring (≥85), no rewrite done
    score: ScoreOut
    full_prompt: str
    rewritten_module: str | None = None   # which module was changed, if any

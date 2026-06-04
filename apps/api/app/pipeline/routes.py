import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, get_optional_user
from app.config import settings
from app.db.base import get_db
from app.db.models import OutcomeRating, Prompt, PromptVersion, User
from app.db.models import Session as SessionModel
from app.llm.factory import build_router
from app.pipeline.orchestrator import Orchestrator
from app.pipeline.schemas import (
    AnswerRequest,
    BranchRequest,
    GenerationResultOut,
    QuestionOut,
    RateRequest,
    RateResponse,
    RunRequest,
    RunResponse,
    ScoreOut,
    StartRequest,
    TurnResponse,
)
from app.pipeline.session import SessionStore

router = APIRouter(prefix="/generate", tags=["generate"])

_llm_router = build_router(
    groq_api_key=settings.groq_api_key,
    gemini_api_key=settings.gemini_api_key,
)
_session_store = SessionStore()


def _turn_to_response(turn) -> TurnResponse:
    question_out = None
    if turn.question:
        question_out = QuestionOut(
            slot_id=turn.question.slot_id,
            question=turn.question.question,
            chips=turn.question.chips,
            allow_freetext=turn.question.allow_freetext,
        )
    result_out = None
    if turn.result:
        result_out = GenerationResultOut(
            prompt=turn.result.prompt,
            score=ScoreOut(
                composite=turn.result.score.composite,
                dimensions=turn.result.score.dimensions,
                suggestions=turn.result.score.suggestions,
            ),
            prompt_version_id=turn.result.prompt_version_id,
        )
    return TurnResponse(
        session_id=turn.session_id,
        status=turn.status,
        question=question_out,
        result=result_out,
        suggest_profile_save=turn.suggest_profile_save,
        extractable_slots=turn.extractable_slots,
        profile_loaded=turn.profile_loaded,
    )


@router.post("/start", response_model=TurnResponse)
def start_generation(
    body: StartRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> TurnResponse:
    orch = Orchestrator(router=_llm_router, store=_session_store, db=db)
    user_id = str(current_user.id) if current_user else None
    turn = orch.start(
        initial_input=body.input,
        user_id=user_id,
        ignore_profile=body.ignore_profile,
    )
    return _turn_to_response(turn)


@router.post("/answer", response_model=TurnResponse)
def submit_answer(
    body: AnswerRequest,
    db: Session = Depends(get_db),
) -> TurnResponse:
    orch = Orchestrator(router=_llm_router, store=_session_store, db=db)
    try:
        turn = orch.answer(session_id=body.session_id, slot_id=body.slot_id, answer=body.answer)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _turn_to_response(turn)


@router.post("/run", response_model=RunResponse)
def run_prompt(body: RunRequest, db: Session = Depends(get_db)) -> RunResponse:
    version = db.get(PromptVersion, uuid.UUID(body.prompt_version_id))
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PromptVersion not found")
    result = _llm_router.complete("construct", [{"role": "user", "content": version.content}])
    return RunResponse(output=result.text)


@router.post("/rate", response_model=RateResponse)
def rate_prompt(body: RateRequest, db: Session = Depends(get_db)) -> RateResponse:
    version = db.get(PromptVersion, uuid.UUID(body.prompt_version_id))
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PromptVersion not found")
    rating = OutcomeRating(
        prompt_version_id=uuid.UUID(body.prompt_version_id),
        rating=body.rating,
        feedback=body.feedback,
    )
    db.add(rating)
    db.commit()
    return RateResponse(ok=True)


@router.post("/branch", response_model=TurnResponse)
def branch_prompt(
    body: BranchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TurnResponse:
    try:
        version_id = uuid.UUID(body.prompt_version_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    version = db.get(PromptVersion, version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    prompt = db.get(Prompt, version.prompt_id)
    if prompt is None or prompt.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    db_session = db.get(SessionModel, prompt.session_id) if prompt.session_id else None
    pre_filled_slots: dict[str, str] = {}
    initial_input = ""
    if db_session:
        pre_filled_slots = db_session.filled_slots or {}
        initial_input = db_session.initial_input or ""

    if not initial_input:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Original session has no input — cannot branch",
        )

    orch = Orchestrator(router=_llm_router, store=_session_store, db=db)
    turn = orch.start(
        initial_input=initial_input,
        user_id=str(current_user.id),
        pre_filled_slots=pre_filled_slots,
        branched_from_version_id=str(version_id),
    )
    return _turn_to_response(turn)

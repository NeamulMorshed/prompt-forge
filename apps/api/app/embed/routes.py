import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.api_key_deps import validate_api_key
from app.db.base import get_db
from app.embed.schemas import (
    EmbedAnswerRequest, EmbedStartRequest,
    EmbedTurnResponse, EmbedQuestionOut, EmbedResultOut, EmbedScoreOut,
)
from app.llm.factory import build_router
from app.config import settings
from app.pipeline.orchestrator import Orchestrator
from app.pipeline.session import SessionStore

router = APIRouter(prefix="/v1/generate", tags=["embed"])

_store = SessionStore()


def _orch_for_user(db: Session) -> Orchestrator:
    llm_router = build_router(
        groq_api_key=settings.groq_api_key,
        gemini_api_key=settings.gemini_api_key,
    )
    return Orchestrator(router=llm_router, store=_store, db=db)


def _turn_to_embed(turn: "TurnResult") -> EmbedTurnResponse:
    question_out = None
    if turn.question:
        question_out = EmbedQuestionOut(
            slot_id=turn.question.slot_id,
            question=turn.question.question,
            chips=turn.question.chips,
            allow_freetext=turn.question.allow_freetext,
        )
    result_out = None
    if turn.result:
        result_out = EmbedResultOut(
            prompt=turn.result.prompt,
            score=EmbedScoreOut(
                composite=turn.result.score.composite,
                suggestions=turn.result.score.suggestions,
            ),
            prompt_version_id=turn.result.prompt_version_id,
        )
    return EmbedTurnResponse(
        session_id=turn.session_id,
        status=turn.status,
        question=question_out,
        result=result_out,
    )


@router.post("/start", response_model=EmbedTurnResponse)
def embed_start(
    body: EmbedStartRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(validate_api_key),
) -> EmbedTurnResponse:
    orch = _orch_for_user(db)
    turn = orch.start(
        initial_input=body.input,
        user_id=str(user_id),
        model_target=body.model_target,
    )
    return _turn_to_embed(turn)


@router.post("/answer", response_model=EmbedTurnResponse)
def embed_answer(
    body: EmbedAnswerRequest,
    db: Session = Depends(get_db),
    user_id: uuid.UUID = Depends(validate_api_key),
) -> EmbedTurnResponse:
    orch = _orch_for_user(db)
    try:
        turn = orch.answer(session_id=body.session_id, slot_id=body.slot_id, answer=body.answer)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return _turn_to_embed(turn)

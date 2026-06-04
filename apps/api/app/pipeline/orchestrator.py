import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.llm.router import LLMRouter
from app.pipeline.assembler import ContextObject, assemble
from app.pipeline.ccs import compute_ccs
from app.pipeline.classifier import classify
from app.pipeline.constructor import construct
from app.pipeline.crs_loader import load_crs, load_domain_defaults
from app.pipeline.discovery import Question, apply_answer, next_question
from app.pipeline.evaluator import ScoreResult, score
from app.pipeline.session import SessionState, SessionStore


@dataclass
class GenerationResult:
    prompt: str
    score: ScoreResult
    prompt_version_id: str


@dataclass
class TurnResult:
    session_id: str
    status: str  # "needs_question" | "done"
    question: Question | None
    result: GenerationResult | None
    suggest_profile_save: bool = False
    extractable_slots: dict[str, str] = field(default_factory=dict)
    profile_loaded: bool = False


class Orchestrator:
    def __init__(self, router: LLMRouter, store: SessionStore, db: DBSession | None = None):
        self._router = router
        self._store = store
        self._db = db

    def start(self, initial_input: str, user_id: str | None, ignore_profile: bool = False) -> TurnResult:
        classification = classify(initial_input, self._router)
        profile_snapshot: dict[str, str] = {}
        if user_id and not ignore_profile:
            profile_snapshot = self._load_profile(user_id, classification.domain)
        session = self._store.create(
            domain=classification.domain,
            initial_input=initial_input,
            intent=classification.intent,
            clarity=classification.clarity,
            user_id=user_id,
            profile_snapshot=profile_snapshot,
        )
        return self._next_turn(session)

    def answer(self, session_id: str, slot_id: str, answer: str) -> TurnResult:
        session = self._store.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")
        session.filled_slots = apply_answer(slot_id, answer, session.filled_slots)
        session.questions_asked += 1
        slots = load_crs(session.domain)
        session.ccs = compute_ccs(slots, session.filled_slots)
        self._store.update(session)
        return self._next_turn(session)

    def _load_profile(self, user_id: str, domain: str) -> dict[str, str]:
        if self._db is None:
            return {}
        from app.db.models import ContextProfile
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return {}
        profile = self._db.scalar(
            select(ContextProfile).where(
                ContextProfile.user_id == user_uuid,
                ContextProfile.is_default.is_(True),
            )
        )
        if profile is None:
            return {}
        merged = dict(profile.core_context or {})
        merged.update((profile.domain_overrides or {}).get(domain, {}))
        return merged

    def _next_turn(self, session: SessionState) -> TurnResult:
        slots = load_crs(session.domain)
        question = next_question(
            slots=slots,
            filled=session.filled_slots,
            history=[],
            questions_asked=session.questions_asked,
            router=self._router,
        )
        if question is not None:
            return TurnResult(
                session_id=session.id,
                status="needs_question",
                question=question,
                result=None,
                profile_loaded=bool(session.profile_snapshot),
            )
        return self._generate(session)

    def _generate(self, session: SessionState) -> TurnResult:
        slots = load_crs(session.domain)
        session.ccs = compute_ccs(slots, session.filled_slots)
        domain_defaults = load_domain_defaults(session.domain)
        ctx = assemble(
            session_slots=session.filled_slots,
            domain=session.domain,
            intent=session.intent,
            clarity=session.clarity,
            questions_asked=session.questions_asked,
            final_ccs=session.ccs,
            profile=session.profile_snapshot or None,
            domain_defaults=domain_defaults,
        )
        prompt_text = construct(ctx, model="construct")
        score_result = score(prompt_text, ctx, self._router)

        if score_result.gate_failures:
            suggestions_note = "Improve: " + ", ".join(score_result.gate_failures)
            prompt_text = construct(ctx, model="construct") + f"\n\n[Self-check: {suggestions_note}]"
            score_result = score(prompt_text, ctx, self._router)

        prompt_version_id = self._flush_to_db(session, ctx, prompt_text, score_result)
        session.generated_prompt = prompt_text
        session.prompt_version_id = prompt_version_id
        session.status = "complete"
        self._store.update(session)

        suggest_save = session.user_id is not None and not session.profile_snapshot
        extractable = dict(session.filled_slots) if suggest_save else {}

        return TurnResult(
            session_id=session.id,
            status="done",
            question=None,
            result=GenerationResult(
                prompt=prompt_text,
                score=score_result,
                prompt_version_id=prompt_version_id,
            ),
            suggest_profile_save=suggest_save,
            extractable_slots=extractable,
            profile_loaded=bool(session.profile_snapshot),
        )

    def _flush_to_db(
        self,
        session: SessionState,
        ctx: ContextObject,
        prompt_text: str,
        score_result: ScoreResult,
    ) -> str:
        if self._db is None:
            return str(uuid.uuid4())

        from app.db.models import Prompt, PromptVersion
        from app.db.models import Session as DBSessionModel

        db_session_id = uuid.UUID(session.id)
        try:
            db_user_id = uuid.UUID(session.user_id) if session.user_id else None
        except ValueError:
            db_user_id = None

        db_session = DBSessionModel(
            id=db_session_id,
            user_id=db_user_id,
            domain=session.domain,
            initial_input=session.initial_input,
            filled_slots=session.filled_slots,
            questions_asked=session.questions_asked,
            ccs=session.ccs,
            status="complete",
        )
        self._db.merge(db_session)
        self._db.flush()

        prompt_id = uuid.uuid4()
        db_prompt = Prompt(
            id=prompt_id,
            session_id=db_session_id,
            user_id=db_user_id,
            domain=session.domain,
            skills_applied=ctx.skills_applied,
            score=score_result.composite,
        )
        self._db.add(db_prompt)

        version_id = uuid.uuid4()
        db_version = PromptVersion(
            id=version_id,
            prompt_id=prompt_id,
            content=prompt_text,
            score_json={
                "composite": score_result.composite,
                "dimensions": score_result.dimensions,
                "suggestions": score_result.suggestions,
            },
        )
        self._db.add(db_version)
        self._db.commit()
        return str(version_id)

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import redis as redis_lib

from app.config import settings

SESSION_TTL = 3600


@dataclass
class SessionState:
    id: str
    domain: str
    initial_input: str
    intent: str
    clarity: float
    user_id: str | None = None
    filled_slots: dict[str, str] = field(default_factory=dict)
    questions_asked: int = 0
    ccs: float = 0.0
    status: str = "active"
    generated_prompt: str | None = None
    prompt_version_id: str | None = None
    profile_snapshot: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SessionStore:
    def __init__(self, redis_client=None):
        self._r = redis_client or redis_lib.from_url(settings.redis_url, decode_responses=True)

    def _key(self, session_id: str) -> str:
        return f"pf:session:{session_id}"

    def create(
        self,
        domain: str,
        initial_input: str,
        intent: str,
        clarity: float,
        user_id: str | None = None,
        profile_snapshot: dict[str, str] | None = None,
    ) -> SessionState:
        s = SessionState(
            id=str(uuid.uuid4()),
            domain=domain,
            initial_input=initial_input,
            intent=intent,
            clarity=clarity,
            user_id=user_id,
            profile_snapshot=profile_snapshot or {},
        )
        self.update(s)
        return s

    def get(self, session_id: str) -> SessionState | None:
        raw = self._r.get(self._key(session_id))
        if raw is None:
            return None
        return SessionState(**json.loads(raw))

    def update(self, session: SessionState) -> None:
        self._r.set(self._key(session.id), json.dumps(asdict(session)), ex=SESSION_TTL)

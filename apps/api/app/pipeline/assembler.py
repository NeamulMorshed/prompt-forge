from dataclasses import dataclass, field


@dataclass
class ContextValue:
    value: str
    source: str  # "session" | "saved_profile" | "domain_default"


@dataclass
class ContextObject:
    domain: str
    intent: str
    clarity: float
    questions_asked: int
    final_ccs: float
    slots: dict[str, ContextValue] = field(default_factory=dict)
    skills_applied: list[str] = field(default_factory=list)


def assemble(
    session_slots: dict[str, str],
    domain: str,
    intent: str,
    clarity: float,
    questions_asked: int,
    final_ccs: float,
    profile: dict[str, str] | None = None,
    domain_defaults: dict[str, str] | None = None,
) -> ContextObject:
    merged: dict[str, ContextValue] = {}
    for k, v in (domain_defaults or {}).items():
        merged[k] = ContextValue(value=v, source="domain_default")
    for k, v in (profile or {}).items():
        merged[k] = ContextValue(value=v, source="saved_profile")
    for k, v in session_slots.items():
        merged[k] = ContextValue(value=v, source="session")
    return ContextObject(
        domain=domain,
        intent=intent,
        clarity=clarity,
        questions_asked=questions_asked,
        final_ccs=final_ccs,
        slots=merged,
    )

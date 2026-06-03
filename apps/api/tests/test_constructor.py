from app.pipeline.assembler import ContextObject, ContextValue, assemble
from app.pipeline.constructor import construct


def _ctx(domain="marketing_content", slots: dict | None = None) -> ContextObject:
    return assemble(
        session_slots=slots or {},
        domain=domain,
        intent="write a LinkedIn post",
        clarity=0.8,
        questions_asked=2,
        final_ccs=0.75,
        domain_defaults={"tone": "professional and engaging"},
    )


def test_construct_returns_non_empty_string():
    prompt = construct(_ctx(), model="groq/llama-3.1-8b-instant")
    assert isinstance(prompt, str)
    assert len(prompt) > 50


def test_construct_includes_role_for_domain():
    prompt = construct(_ctx(domain="marketing_content"), model="mock")
    assert "marketing" in prompt.lower() or "expert" in prompt.lower()


def test_construct_includes_goal_when_provided():
    ctx = _ctx(slots={"goal": "get newsletter signups", "audience": "indie hackers"})
    prompt = construct(ctx, model="mock")
    assert "newsletter signups" in prompt


def test_construct_includes_format_instruction_for_email():
    ctx = _ctx(slots={"channel": "email"})
    prompt = construct(ctx, model="mock")
    assert "email" in prompt.lower()


def test_construct_adds_reasoning_directive_for_large_model():
    prompt = construct(_ctx(), model="groq/llama-3.1-70b-versatile")
    assert "think" in prompt.lower() or "reasoning" in prompt.lower() or "consider" in prompt.lower()


def test_construct_no_meta_commentary():
    prompt = construct(_ctx(), model="mock")
    assert "here is" not in prompt.lower()
    assert "here's" not in prompt.lower()


def test_construct_academic_domain():
    ctx = _ctx(
        domain="writing_academic",
        slots={"goal": "literature review", "topic": "climate change", "level": "PhD"},
    )
    prompt = construct(ctx, model="mock")
    assert "academic" in prompt.lower() or "scholar" in prompt.lower() or "research" in prompt.lower()

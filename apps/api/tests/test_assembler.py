from app.pipeline.assembler import assemble


def test_session_overrides_domain_default():
    ctx = assemble(
        session_slots={"tone": "edgy and bold"},
        domain="marketing_content",
        intent="write a post",
        clarity=0.8,
        questions_asked=2,
        final_ccs=0.75,
        domain_defaults={"tone": "professional and engaging"},
    )
    assert ctx.slots["tone"].value == "edgy and bold"
    assert ctx.slots["tone"].source == "session"


def test_domain_default_fills_missing_slots():
    ctx = assemble(
        session_slots={},
        domain="marketing_content",
        intent="write a post",
        clarity=0.8,
        questions_asked=0,
        final_ccs=0.40,
        domain_defaults={"tone": "professional and engaging"},
    )
    assert ctx.slots["tone"].value == "professional and engaging"
    assert ctx.slots["tone"].source == "domain_default"


def test_profile_overrides_domain_default_but_not_session():
    ctx = assemble(
        session_slots={"goal": "get leads"},
        domain="marketing_content",
        intent="y",
        clarity=0.7,
        questions_asked=1,
        final_ccs=0.6,
        profile={"tone": "casual"},
        domain_defaults={"tone": "professional"},
    )
    assert ctx.slots["tone"].value == "casual"
    assert ctx.slots["tone"].source == "saved_profile"
    assert ctx.slots["goal"].source == "session"


def test_context_object_carries_metadata():
    ctx = assemble(
        session_slots={},
        domain="writing_academic",
        intent="write a thesis intro",
        clarity=0.9,
        questions_asked=3,
        final_ccs=0.82,
    )
    assert ctx.domain == "writing_academic"
    assert ctx.intent == "write a thesis intro"
    assert ctx.clarity == 0.9
    assert ctx.questions_asked == 3
    assert ctx.final_ccs == 0.82

from app.pipeline.assembler import ContextObject

_DOMAIN_ROLES = {
    "marketing_content": "direct-response marketing and content strategy",
    "writing_academic": "academic research and scholarly writing",
    "real_estate_listing": "property marketing and real estate copywriting",
    "d2c_ad_creative": "direct-to-consumer advertising and conversion copywriting",
    "general": "versatile assistant",
}

_REASONING_MODELS = {"70b", "claude", "gpt-4", "gemini-pro", "gemini-2.5"}


def build_modules(ctx: ContextObject, model: str) -> dict[str, str]:
    def get(slot_id: str, default: str = "") -> str:
        v = ctx.slots.get(slot_id)
        return v.value if v else default

    raw_parts = [
        ("role",       _role_module(ctx.domain)),
        ("objective",  _objective_module(get)),
        ("context",    _context_module(get)),
        ("task",       _task_module(get)),
        ("format",     _format_module(get)),
        ("patterns",   _patterns_module(ctx.domain)),
        ("examples",   _examples_module(get)),
        ("reasoning",  _reasoning_module(model)),
        ("guardrails", _guardrails_module(get)),
    ]
    ctx.skills_applied = [name for name, part in raw_parts if part.strip()]
    return {name: part for name, part in raw_parts}


def construct(ctx: ContextObject, model: str) -> str:
    modules = build_modules(ctx, model)
    return "\n\n".join(part for part in modules.values() if part.strip())


def _role_module(domain: str) -> str:
    label = _DOMAIN_ROLES.get(domain, domain.replace("_", " "))
    return f"You are an expert {label} specialist."


def _objective_module(get) -> str:
    goal = get("goal")
    if not goal:
        return ""
    return (
        f"Goal: {goal}\n\n"
        "Define success as: achieving this goal in the first attempt, with minimal revision needed."
    )


def _context_module(get) -> str:
    parts = []
    audience = get("audience")
    topic = get("topic")
    tone = get("tone")
    if audience:
        parts.append(f"Target audience: {audience}")
    if topic:
        parts.append(f"Topic/subject: {topic}")
    if tone:
        parts.append(f"Tone/voice: {tone}")
    return "\n".join(parts)


def _task_module(get) -> str:
    channel = get("channel")
    level = get("level")
    length = get("length")
    property_info = get("property")
    highlights = get("highlights")
    product = get("product")
    offer = get("offer")
    lines = []
    if channel:
        lines.append(f"Format/channel: {channel}")
    if level:
        lines.append(f"Academic level: {level}")
    if length:
        lines.append(f"Target length: {length}")
    if property_info:
        lines.append(f"Property: {property_info}")
    if highlights:
        lines.append(f"Key highlights to feature: {highlights}")
    if product:
        lines.append(f"Product being advertised: {product}")
    if offer:
        lines.append(f"Offer/incentive: {offer}")
    return "\n".join(lines)


def _format_module(get) -> str:
    channel = get("channel", "").lower()
    sources = get("sources", "")
    _FORMAT_MAP = {
        "email": "Write as a complete, send-ready email: subject line, body, sign-off. No preamble.",
        "linkedin": "Write as a LinkedIn post: strong hook on the first line, body, CTA. Under 300 words.",
        "twitter": "Write as a tweet or thread. Each tweet ≤280 characters.",
        "blog": "Structure with: compelling H1, 3–5 H2 sections, conclusion with CTA.",
        "instagram": "Write as an Instagram caption: hook, body, CTA, relevant hashtags.",
        "mls": "Write as MLS-ready listing: headline (15 words max), description (150-200 words), bullet highlights.",
        "zillow": "Write as a Zillow listing: 250-word max description, punchy opening, highlight 3 top features.",
        "facebook": "Write as Facebook ad copy: primary text (125 chars visible), headline (27 chars), description (27 chars). State benefit first.",
        "google": "Write as Google Search ad: 3 headlines (30 chars each), 2 descriptions (90 chars each). Every character counts.",
    }
    for key, instruction in _FORMAT_MAP.items():
        if key in channel:
            result = instruction
            if sources:
                result += f"\n\nInclude or reference: {sources}"
            return result
    base = "Output must be copy-ready. No meta-commentary. No preamble like 'I've written...' or 'Below is...'. Start immediately with the content."
    if sources:
        base += f"\n\nInclude or reference: {sources}"
    return base


def _examples_module(get) -> str:
    examples = get("examples")
    if not examples:
        return ""
    return f"Examples of the style/quality you're aiming for:\n{examples}"


def _reasoning_module(model: str) -> str:
    model_lower = model.lower()
    if any(m in model_lower for m in _REASONING_MODELS):
        return (
            "Before writing, consider and briefly note the key decisions you're making "
            "(angle, structure, tone calibration). Then write the output."
        )
    return ""


def _patterns_module(domain: str) -> str:
    from app.registry.loader import get_top_patterns
    patterns = get_top_patterns(domain, limit=3)
    if not patterns:
        return ""
    lines = ["Proven structural patterns for this domain:"]
    for p in patterns:
        lines.append(f"- {p.structure}: {p.abstraction}")
    return "\n".join(lines)


def _guardrails_module(get) -> str:
    constraints = get("constraints", "")
    lines = []
    if constraints:
        lines.append(f"Hard constraints: {constraints}")
    lines.append("If anything is ambiguous, state your assumption explicitly rather than guessing silently.")
    return "\n".join(lines)

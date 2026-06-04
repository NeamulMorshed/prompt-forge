import uuid

from sqlalchemy.orm import Session as DBSession

from app.db.models import Prompt, PromptVersion
from app.llm.router import LLMRouter
from app.pipeline.assembler import ContextObject, ContextValue
from app.pipeline.evaluator import ScoreResult, score


def edit_module(
    version_id: uuid.UUID,
    module_name: str,
    new_text: str,
    router: LLMRouter,
    db: DBSession,
) -> tuple[PromptVersion, ScoreResult]:
    version = db.get(PromptVersion, version_id)
    if version is None:
        raise ValueError(f"PromptVersion {version_id} not found")

    prompt_record = db.get(Prompt, version.prompt_id)
    domain = prompt_record.domain if prompt_record else "general"

    modules: dict[str, str] = dict(version.modules_json or {})
    modules[module_name] = new_text

    full_prompt = "\n\n".join(part for part in modules.values() if part.strip())

    ctx = ContextObject(
        domain=domain,
        intent="",
        clarity=1.0,
        questions_asked=0,
        final_ccs=1.0,
        slots={},
    )
    score_result = score(full_prompt, ctx, router)

    new_version = PromptVersion(
        id=uuid.uuid4(),
        prompt_id=version.prompt_id,
        content=full_prompt,
        score_json={
            "composite": score_result.composite,
            "dimensions": score_result.dimensions,
            "suggestions": score_result.suggestions,
        },
        modules_json=modules,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version, score_result

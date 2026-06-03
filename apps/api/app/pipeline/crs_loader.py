import json
from dataclasses import dataclass
from pathlib import Path

_SCHEMAS_DIR = Path(__file__).parent.parent.parent.parent.parent / "packages" / "schemas"


@dataclass(frozen=True)
class Slot:
    id: str
    weight: float
    required: bool
    hint: str


def load_crs(domain: str) -> list[Slot]:
    path = _SCHEMAS_DIR / f"{domain}.json"
    if not path.exists():
        raise FileNotFoundError(f"CRS schema not found: {path}")
    data = json.loads(path.read_text())
    return [
        Slot(id=s["id"], weight=s["weight"], required=s["required"], hint=s["hint"])
        for s in data["slots"]
    ]


def load_domain_defaults(domain: str) -> dict[str, str]:
    path = _SCHEMAS_DIR / f"{domain}.json"
    if not path.exists():
        raise FileNotFoundError(f"CRS schema not found: {path}")
    data = json.loads(path.read_text())
    return data.get("domain_defaults", {})

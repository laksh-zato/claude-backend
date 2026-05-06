import re
from pathlib import Path
from typing import TypedDict


SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)


class SubagentSpec(TypedDict):
    name: str
    description: str
    system_prompt: str
    web: bool


def load_skill_prompt(skill_dir: str) -> str:
    path = SKILLS_DIR / skill_dir / "SKILL.md"
    raw = path.read_text(encoding="utf-8")
    return FRONTMATTER_RE.sub("", raw, count=1).strip()


def build_subagent_spec(name: str, skill_dir: str, web: bool, description: str) -> SubagentSpec:
    return {
        "name": name,
        "description": description,
        "system_prompt": load_skill_prompt(skill_dir),
        "web": web,
    }

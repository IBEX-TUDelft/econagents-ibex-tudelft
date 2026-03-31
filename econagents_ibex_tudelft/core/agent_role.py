from pathlib import Path
from typing import Literal, Optional

from econagents.core.agent_role import AgentRole


class PersonaAgentRole(AgentRole):
    """
    AgentRole subclass that supports persona-specific prompt overrides.

    If `personality` is set, prompt resolution first looks inside
    `{prompts_dir}/personas/{personality}/` using the same file naming
    conventions as the base class. If no persona-specific file is found
    for a given role/phase combination, it falls back to the standard
    resolution logic (game-level prompts).

    Directory layout example::

        prompts/
        ├── trader_system.jinja2
        ├── trader_user_phase_1.jinja2
        └── personas/
            └── aggressive/
                ├── trader_system.jinja2
                └── trader_user_phase_1.jinja2
    """

    def __init__(self, personality: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.personality = personality

    def _resolve_prompt_file(
        self, prompt_type: Literal["system", "user"], phase: int, role: str, prompts_path: Path
    ) -> Optional[Path]:
        if self.personality:
            persona_dir = prompts_path / "personas" / self.personality
            phase_file = persona_dir / f"{role.lower()}_{prompt_type}_phase_{phase}.jinja2"
            if phase_file.exists():
                return phase_file
            general_file = persona_dir / f"{role.lower()}_{prompt_type}.jinja2"
            if general_file.exists():
                return general_file

        return super()._resolve_prompt_file(prompt_type, phase, role, prompts_path)

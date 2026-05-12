"""
Prompt Manager

"""

from pathlib import Path
from typing import Dict, Optional
import string


class PromptManager:

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def load_prompt(self, prompt_path: str, use_cache: bool = True) -> str:
        if use_cache and prompt_path in self._cache:
            return self._cache[prompt_path]

        full_path = self.prompts_dir / prompt_path
        if not full_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {full_path}")

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if use_cache:
            self._cache[prompt_path] = content

        return content

    def format_prompt(self, prompt_path: str, **kwargs) -> str:
        template = self.load_prompt(prompt_path)
        return template.format(**kwargs)

    def clear_cache(self):
        self._cache.clear()

    # ==================== Rubric Generator Prompts ====================

    def get_system_prompt(self) -> str:
        return self.load_prompt("prompts/rubric_generator/system.txt")

    def get_generic_prompt(self, **kwargs) -> str:
        return self.format_prompt("prompts/rubric_generator/generic.txt", **kwargs)

    def get_task_prompt(self, **kwargs) -> str:

        return self.format_prompt("prompts/rubric_generator/task_specific.txt", **kwargs)

    # ==================== Evaluation Prompts ====================
    def get_dag_generate_prompt(self, **kwargs) -> str:

        return self.format_prompt("prompts/dag_generator/dag_generate.txt", **kwargs)
    def get_evaluation_prompt(self, **kwargs) -> str:
        return self.format_prompt("prompts/evaluation/dag_evaluation.txt", **kwargs)

    # ==================== Utility Methods ====================

    def list_available_prompts(self) -> Dict[str, list]:
        prompts = {}

        for category_dir in self.prompts_dir.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                prompts[category] = []

                for prompt_file in category_dir.glob("*.txt"):
                    prompts[category].append(prompt_file.name)

        return prompts

    def reload_prompt(self, prompt_path: str):
        if prompt_path in self._cache:
            del self._cache[prompt_path]

        self.load_prompt(prompt_path, use_cache=True)

    def print_prompt_structure(self):
        print("\n" + "="*70)
        print("Prompts Directory Structure:")
        print("="*70)

        for category_dir in sorted(self.prompts_dir.iterdir()):
            if category_dir.is_dir():
                print(f"\n{category_dir.name}/")
                for prompt_file in sorted(category_dir.glob("*.txt")):
                    print(f"  - {prompt_file.name}")

        print("\n" + "="*70)


_global_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager(prompts_dir: str = "prompts") -> PromptManager:
    global _global_prompt_manager

    if _global_prompt_manager is None:
        _global_prompt_manager = PromptManager(prompts_dir)

    return _global_prompt_manager

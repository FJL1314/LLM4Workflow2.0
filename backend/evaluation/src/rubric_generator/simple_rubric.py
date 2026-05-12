"""
Simple Rubric Generator
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import re
import json

from ..llm_factory.factory import LLMFactory
from ..llm_factory.base import Message
from ..utils import ToolDescriptionLoader, get_prompt_manager


@dataclass
class RubricDimension:
    theme: str
    tips: List[str]
    weight: float = 1.0
    description: str = ""


@dataclass
class Rubric:
    """Complete Rubric"""

    task_id: str
    task_description: str
    dimensions: List[RubricDimension]
    min_score: int = 0
    max_score: int = 5
    metadata: Dict = None

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "dimensions": [
                {
                    "theme": dim.theme,
                    "tips": dim.tips,
                    "weight": dim.weight,
                    "description": dim.description,
                }
                for dim in self.dimensions
            ],
            "min_score": self.min_score,
            "max_score": self.max_score,
            "metadata": self.metadata or {},
        }

    def to_markdown(self) -> str:
        """Markdown"""
        lines = [
            f"# Evaluation Rubric for Task: {self.task_id}",
            "",
            f"**Task Description:** {self.task_description}",
            "",
            f"**Score Range:** {self.min_score} - {self.max_score}",
            "",
            "## Evaluation Dimensions",
            "",
        ]

        for i, dim in enumerate(self.dimensions, 1):
            lines.append(f"### Dimension {i}: {dim.theme} (weight: {dim.weight})")
            if dim.description:
                lines.append(f"*{dim.description}*")
            lines.append("")
            for tip in dim.tips:
                lines.append(f"- {tip}")
            lines.append("")

        return "\n".join(lines)


class SimpleRubricGenerator:
    """
    Simple Rubric（ref OpenJudge）
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        stage: str = "generic",
        tool_desc_path: str = "/data/raw/tool_desc.json",
        prompts_dir: str = "prompts",
    ):

        if provider is None and model is None:
            self.llm = LLMFactory.get_rubric_client(stage)
            config = LLMFactory.get_rubric_generator_config(stage)
            self.provider = config["provider"]
        else:
            self.llm = LLMFactory.get_client(provider or "gemini", model)
            self.provider = provider or "gemini"

        self.stage = stage

        self.tool_loader = ToolDescriptionLoader(tool_desc_path)
        self.tools = self.tool_loader.get_all_tools()

        self.prompt_manager = get_prompt_manager(prompts_dir)

    async def generate_generic_rubric(
        self, dataset_stats: Dict, task_domain: str = "multimedia_processing"
    ) -> Rubric:
        prompt = self._get_generic_prompt(dataset_stats, task_domain)

        messages = [
            Message(role="system", content=self._get_system_prompt()),
            Message(role="user", content=prompt),
        ]

        try:
            response = await self.llm.acomplete(
                messages, temperature=0.3, max_tokens=2000
            )

            rubric = self._parse_rubric(response.content, task_id="generic")
            rubric.task_description = f"generic rubric for {task_domain} tasks"
            rubric.metadata = {
                "type": "generic",
                "domain": task_domain,
                "dataset_stats": dataset_stats,
            }

            return rubric

        except Exception as e:
            print(f"Error generating generic rubric: {e}")
            return self._get_default_generic_rubric(task_domain)

    async def generate_task_rubric(
        self, task: Dict, context: Optional[Dict] = None
    ) -> Rubric:
        prompt = self._get_task_prompt(task, context)

        messages = [
            Message(role="system", content=self._get_system_prompt()),
            Message(role="user", content=prompt),
        ]

        try:
            response = await self.llm.acomplete(
                messages, temperature=0.3, max_tokens=2000
            )

            rubric = self._parse_rubric(
                response.content, task_id=task.get("id", "unknown")
            )
            rubric.task_description = task.get("user_request", "")
            rubric.metadata = {
                "type": "task_specific",
                "task_id": task.get("id"),
                "n_tools": task.get("n_tools"),
                "context": context,
            }

            return rubric

        except Exception as e:
            return self._get_default_task_rubric(task)

    def _get_system_prompt(self) -> str:
        return self.prompt_manager.get_system_prompt()

    def _get_generic_prompt(self, stats: Dict, domain: str) -> str:
        tool_summary = self.tool_loader.get_tool_summary()
        params = {
            "domain": domain,
            "total_tasks": stats.get("total_tasks", "N/A"),
            "task_types": ", ".join(stats.get("task_types", ["N/A"])),
            "common_tools": ", ".join(stats.get("common_tools", ["N/A"])[:10]),
            "avg_complexity": stats.get("avg_complexity", "N/A"),
            "tool_diversity": stats.get("tool_diversity", "N/A"),
            "num_tools": tool_summary["total_tools"],
            "input_modalities": ", ".join(tool_summary["input_modalities"]),
            "output_modalities": ", ".join(tool_summary["output_modalities"]),
            "num_input_modalities": tool_summary["modality_count"]["input"],
            "num_output_modalities": tool_summary["modality_count"]["output"],
            "num_dimensions": stats.get("num_dimensions", 6),
        }

        return self.prompt_manager.get_generic_prompt(**params)

    def _get_task_prompt(self, task: Dict, context: Optional[Dict]) -> str:
        params = {
            "user_request": task["user_request"],
            "task_steps": self._format_steps(task.get("task_steps", [])),
            "available_tools": self._format_tools(task.get("sampled_nodes", [])),
            "num_nodes": len(task.get("task_nodes", [])),
            "task_nodes": self._format_nodes(task.get("task_nodes", [])),
            "num_links": len(task.get("task_links", [])),
            "task_links": self._format_links(task.get("task_links", [])),
        }

        return self.prompt_manager.get_task_prompt(**params)

    def _format_steps(self, steps: List[str]) -> str:
        return "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])

    def _format_tools(self, tools: List[Dict]) -> str:
        formatted_tools = []
        for tool in tools[:10]:
            tool_name = tool["task"]
            tool_desc = self.tools.get(tool_name)

            if tool_desc:
                formatted_tools.append(
                    f"- **{tool_name}**: {tool_desc.desc}\n"
                    f"  Input: {', '.join(tool_desc.input_types)}\n"
                    f"  Output: {', '.join(tool_desc.output_types)}"
                )
            else:
                input_types = tool.get("input-type", [])
                output_types = tool.get("output-type", [])
                formatted_tools.append(
                    f"- **{tool_name}**: input={input_types}, output={output_types}"
                )

        return "\n".join(formatted_tools)

    def _format_nodes(self, nodes: List[Dict]) -> str:
        return "\n".join(
            [f"- {node['task']}: {node.get('arguments', [])}" for node in nodes[:10]]
        )

    def _format_links(self, links: List[Dict]) -> str:
        return "\n".join(
            [f"- {link['source']} → {link['target']}" for link in links[:10]]
        )

    def _parse_rubric(self, response: str, task_id: str) -> Rubric:
        lines = response.strip().split("\n")
        dimensions = []
        current_theme = None
        current_description = None
        current_tips = []

        for line in lines:
            line_stripped = line.strip()

            if line_stripped.startswith("Dimension ") or line_stripped.startswith(
                "Theme:"
            ):
                if current_theme and current_tips:
                    dimensions.append(
                        RubricDimension(
                            theme=current_theme,
                            tips=current_tips,
                            description=current_description or "",
                        )
                    )
                if "Theme:" in line_stripped:
                    current_theme = line_stripped.split("Theme:", 1)[1].strip()
                else:
                    current_theme = line_stripped
                current_description = None
                current_tips = []

            elif line_stripped.startswith("Description:"):
                current_description = line_stripped.split("Description:", 1)[1].strip()

            elif line_stripped.startswith("- Tip:") or line_stripped.startswith("-"):
                if "Tip:" in line_stripped:
                    tip = line_stripped.split("Tip:", 1)[1].strip()
                else:
                    tip = line_stripped[1:].strip()
                if tip:
                    current_tips.append(tip)

        if current_theme and current_tips:
            dimensions.append(
                RubricDimension(
                    theme=current_theme,
                    tips=current_tips,
                    description=current_description or "",
                )
            )

        return Rubric(
            task_id=task_id,
            task_description="",
            dimensions=dimensions,
            min_score=0,
            max_score=5,
        )


    def _get_default_task_rubric(self, task: Dict) -> Rubric:
        return Rubric(
            task_id=task.get("id", "unknown"),
            task_description=task.get("user_request", ""),
            dimensions=[
                RubricDimension(
                    theme="Step Completeness",
                    description="Checks if all required steps are present",
                    tips=[
                        "All user requirements are addressed",
                        "Task steps are complete",
                        "No critical functionality is missing",
                    ],
                    weight=1.0,
                ),
                RubricDimension(
                    theme="Tool Selection",
                    description="Evaluates appropriateness of tool selection",
                    tips=[
                        "Tools match the required operations",
                        "Tool parameters are correctly set",
                        "Tool sequence is logical",
                    ],
                    weight=1.0,
                ),
                RubricDimension(
                    theme="DAG Structure",
                    description="Evaluates DAG structural validity",
                    tips=[
                        "DAG is acyclic",
                        "Nodes are properly connected",
                        "Data flow is coherent",
                    ],
                    weight=1.0,
                ),
            ],
            metadata={"type": "task_default"},
        )

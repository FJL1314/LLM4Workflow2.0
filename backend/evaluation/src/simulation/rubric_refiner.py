"""
Rubric Refiner
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..rubric_generator.simple_rubric import Rubric, RubricDimension
from .discrepancy_analyzer import DiscrepancyReport
from ..llm_factory.factory import LLMFactory
from ..llm_factory.base import Message


@dataclass
class RefinementConfig:
    high_discrimination_multiplier: float = 1.5
    low_discrimination_multiplier: float = 0.5
    error_point_multiplier: float = 2.0
    add_error_tips: bool = True


import json
import re
from typing import List, Dict, Optional


class RubricRefiner:


    def __init__(self,
                 provider: Optional[str] = None,
                 model: Optional[str] = None,
                 config: Optional[RefinementConfig] = None,
                 use_llm: bool = True):
        self.use_llm = use_llm

        if use_llm:
            if provider is None and model is None:
                self.llm = LLMFactory.get_rubric_client('refinement')
            else:
                self.llm = LLMFactory.get_client(provider or 'gemini', model)
        else:
            self.llm = None

        self.config = config or RefinementConfig()

    async def refine_rubric(self,
                            draft_rubric: Rubric,
                            discrepancy_report: DiscrepancyReport,
                            task: Dict) -> Rubric:

        refined_dimensions = self._adjust_weights(
            draft_rubric.dimensions,
            discrepancy_report
        )

        if self.use_llm:
            refined_dimensions = await self._rewrite_all_dimension_tips(
                refined_dimensions,
                discrepancy_report,
                task
            )

        if self.use_llm and self.config.add_error_tips:
            refined_dimensions = await self._add_error_tips(
                refined_dimensions,
                discrepancy_report,
                task
            )

        refined_rubric = Rubric(
            task_id=draft_rubric.task_id,
            task_description=draft_rubric.task_description,
            dimensions=refined_dimensions,
            min_score=draft_rubric.min_score,
            max_score=draft_rubric.max_score,
            metadata={
                **(draft_rubric.metadata or {}),
                'refinement': True,
                'discrepancy_analysis': {
                    'high_discrimination_steps': discrepancy_report.high_discrimination_steps,
                    'low_discrimination_steps': discrepancy_report.low_discrimination_steps,
                    'model_rankings': discrepancy_report.model_rankings
                }
            }
        )

        return refined_rubric

    def _adjust_weights(self,
                        dimensions: List[RubricDimension],
                        report: DiscrepancyReport) -> List[RubricDimension]:
        refined = []

        for dim in dimensions:
            new_weight = dim.weight

            for high_step in report.high_discrimination_steps:
                if self._is_dimension_related_to_step(dim, high_step):
                    new_weight *= self.config.high_discrimination_multiplier
                    break

            for low_step in report.low_discrimination_steps:
                if self._is_dimension_related_to_step(dim, low_step):
                    new_weight *= self.config.low_discrimination_multiplier
                    break

            refined.append(RubricDimension(
                theme=dim.theme,
                tips=list(dim.tips),
                weight=min(3.0, max(0.1, new_weight)),
                description=dim.description
            ))

        return refined

    async def _rewrite_all_dimension_tips(
            self,
            dimensions: List[RubricDimension],
            report: DiscrepancyReport,
            task: Dict
    ) -> List[RubricDimension]:
        refined_dimensions = []

        for dim in dimensions:
            rewritten_tips = await self._rewrite_tips_for_dimension(
                dimension=dim,
                report=report,
                task=task
            )

            refined_dimensions.append(
                RubricDimension(
                    theme=dim.theme,
                    tips=rewritten_tips,
                    weight=dim.weight,
                    description=dim.description
                )
            )

        return refined_dimensions

    async def _rewrite_tips_for_dimension(
            self,
            dimension: RubricDimension,
            report: DiscrepancyReport,
            task: Dict
    ) -> List[str]:
        high_steps = report.high_discrimination_steps[:3]
        task_steps = task.get("task_steps", []) or []

        step_texts = []
        for step in high_steps:
            if "_" in step:
                try:
                    step_num = int(step.split("_")[1])
                    if 1 <= step_num <= len(task_steps):
                        step_texts.append(task_steps[step_num - 1])
                    else:
                        step_texts.append(step)
                except Exception:
                    step_texts.append(step)
            else:
                step_texts.append(step)

        if not step_texts:
            step_texts = task_steps[:3] if task_steps else ["critical workflow step"]

        discrimination_context = "\n".join(f"- {s}" for s in step_texts)

        prompt = f"""You are refining the evaluation tips of a rubric dimension for workflow evaluation.

    User Request:
    {task.get('user_request', '')}

    High-discrimination workflow steps:
    {discrimination_context}

    Rubric Dimension Theme:
    {dimension.theme}

    Rubric Dimension Description:
    {dimension.description}

    Original Tips:
    {chr(10).join(f"- {tip}" for tip in dimension.tips)}

    Your task:
    Rewrite the tips so they become more specific, discriminative, and actionable.

    Requirements:
    1. Rewrite the tips instead of simply copying them.
    2. Focus on what distinguishes strong workflow execution from weak execution.
    3. Emphasize common failure modes and key evaluation signals.
    4. Keep the core meaning aligned with the original dimension.
    5. Return 3 to 4 tips.

    Output JSON only:
    {{
      "tips": ["...", "...", "..."]
    }}
    """

        try:
            response = await self.llm.acomplete(
                [Message(role="user", content=prompt)],
                temperature=0.7,
                max_tokens=16800
            )

            content = response.content.strip()
            data = self._safe_load_json(content)

            new_tips = data.get("tips") or []
            new_tips = [str(t).strip() for t in new_tips if str(t).strip()]

            if not new_tips or new_tips == dimension.tips:
                new_tips = list(dimension.tips) + [
                    "Check whether this dimension clearly distinguishes strong workflow execution from weak execution.",
                    "Inspect common failure modes relevant to this criterion."
                ]

            return new_tips[:5]

        except Exception as e:
            print(f"Warning: Failed to rewrite tips for dimension '{dimension.theme}': {e}")
            return (list(dimension.tips) + [
                "Check whether this dimension clearly distinguishes strong workflow execution from weak execution.",
                "Inspect common failure modes relevant to this criterion."
            ])[:5]
    async def _rewrite_dimension_for_step(
        self,
        step: str,
        task: Dict,
        dimension: RubricDimension
    ) -> RubricDimension:
        step_num = int(step.split('_')[1]) if '_' in step else 1
        task_steps = task.get('task_steps', []) or []
        gt_step = task_steps[step_num - 1] if step_num <= len(task_steps) else step

        prompt = f"""You are refining a rubric dimension for workflow evaluation.

User Request:
{task.get('user_request', '')}

High-discrimination step:
{gt_step}

Original rubric dimension:
Theme: {dimension.theme}
Description: {dimension.description}
Tips:
{chr(10).join(f"- {tip}" for tip in dimension.tips)}

Context:
This step is a high-discrimination step, meaning different models show meaningful differences on this step.

Your task:
Rewrite the ENTIRE rubric dimension so that it becomes more specific, discriminative, and actionable for evaluating this step.

Requirements:
1. Rewrite the theme. It must NOT be identical to the original theme.
2. Rewrite the description. It must NOT be identical to the original description.
3. Rewrite the tips. They must NOT simply repeat the original tips with minor wording changes.
4. The rewritten dimension should focus on:
   - what makes this step difficult,
   - common failure modes,
   - concrete quality signals for good vs bad execution.
5. Keep the semantics aligned with the original dimension, but make it more step-specific.
6. Return 3 to 5 tips.

Output JSON only:
{{
  "theme": "...",
  "description": "...",
  "tips": ["...", "...", "..."]
}}
"""

        try:
            response = await self.llm.acomplete(
                [Message(role="user", content=prompt)],
                temperature=0.7,
                max_tokens=800
            )

            content = response.content.strip()
            data = self._safe_load_json(content)

            new_theme = (data.get("theme") or "").strip()
            new_description = (data.get("description") or "").strip()
            new_tips = data.get("tips") or []

            new_tips = [str(t).strip() for t in new_tips if str(t).strip()]

            if not new_theme or new_theme == dimension.theme:
                new_theme = f"{dimension.theme} for {step.replace('_', ' ').title()}"

            if not new_description or new_description == dimension.description:
                new_description = f"Refined evaluation dimension focusing on {gt_step}. {dimension.description}".strip()

            if not new_tips or new_tips == dimension.tips:
                new_tips = list(dimension.tips) + [
                    f"Check whether '{gt_step}' is completed exactly as intended.",
                    f"Inspect common failure patterns specifically related to '{gt_step}'.",
                ]

            return RubricDimension(
                theme=new_theme,
                tips=new_tips[:5],
                weight=dimension.weight,
                description=new_description
            )

        except Exception as e:
            print(f"Warning: Failed to rewrite dimension for {step}: {e}")

            fallback_theme = f"{dimension.theme} for {step.replace('_', ' ').title()}"
            fallback_description = f"Refined dimension focusing on {gt_step}. {dimension.description}"
            fallback_tips = list(dimension.tips) + [
                f"Verify whether '{gt_step}' is completed correctly and completely.",
                f"Check whether execution quality on '{gt_step}' distinguishes strong and weak workflows.",
            ]

            return RubricDimension(
                theme=fallback_theme,
                tips=fallback_tips[:5],
                weight=dimension.weight,
                description=fallback_description
            )

    def _safe_load_json(self, text: str) -> Dict:
        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass

        return {}

    async def _add_error_tips(self,
                              dimensions: List[RubricDimension],
                              report: DiscrepancyReport,
                              task: Dict) -> List[RubricDimension]:
        for dim in dimensions:
            error_tip = self._generate_common_error_tip(dim, task)
            if error_tip:
                dim.tips.append(error_tip)

        return dimensions

    def _generate_common_error_tip(self, dim: RubricDimension, task: Dict) -> Optional[str]:
        theme_lower = dim.theme.lower()

        if 'correctness' in theme_lower or 'logical' in theme_lower:
            return "Common error: Incorrect tool selection or parameter type mismatch"
        elif 'coverage' in theme_lower or 'complete' in theme_lower:
            return "Common error: Missing critical steps or incomplete output"
        elif 'efficiency' in theme_lower:
            return "Common error: Redundant operations or inefficient tool usage"
        elif 'robustness' in theme_lower:
            return "Common error: Not handling edge cases or input validation issues"
        else:
            return None

    def _is_dimension_related_to_step(self,
                                      dimension: RubricDimension,
                                      step: str) -> bool:
        theme_lower = dimension.theme.lower()
        step_num = step.split('_')[1] if '_' in step else '1'

        if step_num in theme_lower:
            return True

        if 'correctness' in theme_lower or 'logical' in theme_lower:
            return True

        return False

    def _find_related_dimension(self,
                                dimensions: List[RubricDimension],
                                step: str) -> Optional[RubricDimension]:
        for dim in dimensions:
            if self._is_dimension_related_to_step(dim, step):
                return dim
        return None
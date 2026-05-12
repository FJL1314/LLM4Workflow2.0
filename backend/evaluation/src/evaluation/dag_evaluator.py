"""
DAG Evaluator - Phase
Using Refined Rubric to evaluate the rationality of DAG
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path

import json_repair

from src.llm_factory import LLMFactory, Message
from src.rubric_generator import Rubric, RubricDimension
from src.utils import ToolDescriptionLoader, get_prompt_manager


@dataclass
class DimensionScore:
    """Single dimension rating"""
    dimension_name: str
    score: float  # 1-5
    weight: float
    weighted_score: float  # score * weight
    reasoning: str


@dataclass
class EvaluationResult:
    """Evaluation results"""
    task_id: str
    task_description: str

    dimension_scores: List[DimensionScore]

    total_weighted_score: float
    normalized_score: float  #

    rubric_metadata: Optional[Dict] = None
    evaluator_model: Optional[str] = None
    evaluation_timestamp: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'task_id': self.task_id,
            'task_description': self.task_description,
            'dimension_scores': [
                {
                    'dimension_name': ds.dimension_name,
                    'score': ds.score,
                    'weight': ds.weight,
                    'weighted_score': ds.weighted_score,
                    'reasoning': ds.reasoning
                }
                for ds in self.dimension_scores
            ],
            'total_weighted_score': self.total_weighted_score,
            'normalized_score': self.normalized_score,
            'rubric_metadata': self.rubric_metadata,
            'evaluator_model': self.evaluator_model,
            'evaluation_timestamp': self.evaluation_timestamp
        }


class DAGEvaluator:
    """DAG evaluator"""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        stage: str = 'evaluation',
        tool_desc_path: str = "data/raw/tool_desc.json",
        prompts_dir: str = "prompts"
    ):

        if provider is None and model is None:
            self.llm = LLMFactory.get_rubric_client(stage)
            config = LLMFactory.get_rubric_generator_config(stage)
            self.provider = config['provider']
            self.model = config['model']
        else:
            self.llm = LLMFactory.get_client(provider, model)
            self.provider = provider
            self.model = model

        self.tool_loader = ToolDescriptionLoader(tool_desc_path)
        self.tools = self.tool_loader.get_all_tools()

        self.prompt_manager = get_prompt_manager(prompts_dir)

    async def evaluate_dag(
        self,
        task: Dict,
        rubric: Rubric,
        include_reasoning: bool = True
    ) -> EvaluationResult:

        from datetime import datetime

        prompt = self._build_evaluation_prompt(task, rubric)

        # 调用LLM
        messages = [
            Message(role="user", content=prompt)
        ]

        response = await self.llm.acomplete(
            messages,
            temperature=0.3,
            max_tokens=16800
        )


        dimension_scores = self._parse_evaluation_response(
            response.content,
            rubric.dimensions,
            include_reasoning
        )


        expected_dimensions = len(rubric.dimensions)
        actual_dimensions = len(dimension_scores)

        if actual_dimensions < expected_dimensions:
            missing_count = expected_dimensions - actual_dimensions


        if dimension_scores:
            normalized_score = sum(ds.score for ds in dimension_scores) / len(dimension_scores)
        else:
            normalized_score = 0

        total_weight = sum(dim.weight for dim in rubric.dimensions)
        total_weighted_score = sum(ds.weighted_score for ds in dimension_scores)

        result = EvaluationResult(
            task_id=task['id'],
            task_description=task.get('user_request', ''),
            dimension_scores=dimension_scores,
            total_weighted_score=total_weighted_score,
            normalized_score=normalized_score,
            rubric_metadata=rubric.metadata,
            evaluator_model=f"{self.provider}/{self.model}",
            evaluation_timestamp=datetime.now().isoformat()
        )

        return result

    def _build_evaluation_prompt(self, task: Dict, rubric: Rubric) -> str:
        """Build assessment prompts"""
        user_request = task.get('user_request', '')
        task_steps = task.get('task_steps', [])
        task_nodes = task.get('task_nodes', [])
        task_links = task.get('task_links', [])

        rubric_desc = "## Evaluation criteria (Rubric)\n\n"
        for i, dim in enumerate(rubric.dimensions, 1):
            rubric_desc += f"### {i}. {dim.theme} (Weight: {dim.weight})\n\n"
            rubric_desc += f"**Assessment Focus**: {dim.description}\n\n"
            if dim.tips:
                rubric_desc += "**Inspection Items**:\n"
                for tip in dim.tips:
                    rubric_desc += f"- {tip}\n"
            rubric_desc += "\n"

        dag_desc = "## DAG task structure\n\n"
        dag_desc += f"**User needs**: {user_request}\n\n"
        dag_desc += f"**Task Steps**: {len(task_steps)}\n"
        dag_desc += f"**Number of nodes**: {len(task_nodes)}\n"
        dag_desc += f"**Number of connections**: {len(task_links)}\n\n"

        dag_desc += "### Task Step Details\n\n"
        for i, step in enumerate(task_steps, 1):
            if isinstance(step, dict):
                step_name = step.get('name', f'Step {i}')
                step_desc = step.get('description', 'N/A')
                step_tool = step.get('tool', 'N/A')
                step_input = step.get('input_types', [])
                step_output = step.get('output_types', [])

                dag_desc += f"{i}. **{step_name}**\n"
                dag_desc += f"   - describe: {step_desc}\n"
                dag_desc += f"   - tool: {step_tool}\n"
                dag_desc += f"   - input: {step_input}\n"
                dag_desc += f"   - output: {step_output}\n\n"
            elif isinstance(step, str):
                dag_desc += f"{i}. {step}\n\n"
            else:
                dag_desc += f"{i}. (Unknown format)\n\n"

        tool_validation = self._validate_tool_usage(task)

        dimension_params = {}
        for i, dim in enumerate(rubric.dimensions):
            dimension_params[f'dimension_{i+1}'] = dim.theme

        return self.prompt_manager.get_evaluation_prompt(
            rubric_description=rubric_desc,
            dag_description=dag_desc,
            tool_validation=tool_validation,
            num_dimensions=len(rubric.dimensions),
            **dimension_params
        )

    def _validate_tool_usage(self, task: Dict) -> str:
        """Verification tool usage legitimacy"""
        task_nodes = task.get('task_nodes', [])
        task_links = task.get('task_links', [])

        validation_results = []
        total_links = len(task_links)
        valid_links = 0
        invalid_links = 0
        missing_tools = []

        for link in task_links:
            source_tool = link.get('source', '')
            target_tool = link.get('target', '')

            source_node = next((node for node in task_nodes if node.get('task') == source_tool), None)
            target_node = next((node for node in task_nodes if node.get('task') == target_tool), None)

            if not source_node:
                invalid_links += 1
                validation_results.append(f"[!] Source tool not found in nodes: {source_tool}")
                continue

            if not target_node:
                invalid_links += 1
                validation_results.append(f"[!] Target tool not found in nodes: {target_tool}")
                continue

            if source_tool not in self.tools:
                missing_tools.append(source_tool)
                validation_results.append(f"[!] Tool description missing: {source_tool}")

            if target_tool not in self.tools:
                missing_tools.append(target_tool)
                validation_results.append(f"[!] Tool description missing: {target_tool}")

            if source_tool in self.tools and target_tool in self.tools:
                source_desc = self.tools[source_tool]
                target_desc = self.tools[target_tool]

                is_compatible = False
                for output_type in source_desc.output_types:
                    if target_desc.accepts_input(output_type):
                        is_compatible = True
                        break

                if is_compatible:
                    valid_links += 1
                else:
                    invalid_links += 1
                    validation_results.append(
                        f"[X] Type mismatch: {source_tool} ({', '.join(source_desc.output_types)}) -> "
                        f"{target_tool} (needs: {', '.join(target_desc.input_types)})"
                    )

        report = f"**Total connections**: {total_links}\n"
        report += f"**Valid connections**: {valid_links}\n"
        report += f"**Invalid connections**: {invalid_links}\n"

        if missing_tools:
            unique_missing = list(set(missing_tools))
            report += f"\n**Missing tool descriptions**: {len(unique_missing)}\n"
            for tool in unique_missing[:5]:  # Show max 5
                report += f"   - {tool}\n"

        if invalid_links > 0:
            report += f"\n**Type mismatch details**:\n"
            for result in validation_results[:10]:  # Show max 10
                if '[X]' in result:
                    report += f"   {result}\n"

        if valid_links == total_links and total_links > 0:
            report += f"\n**Validation result**: [OK] All tool connections are type-compatible"
        elif invalid_links > 0:
            report += f"\n**Validation result**: [!] Found {invalid_links} type mismatch issues"

        return report

    def _parse_evaluation_response(
        self,
        response_content: str,
        dimensions: List[RubricDimension],
        include_reasoning: bool
    ) -> List[DimensionScore]:

        dim_map = {dim.theme: dim for dim in dimensions}

        result = self._try_parse_json(response_content, dim_map, include_reasoning)
        if result:
            return result

        fixed_json = self._fix_json_advanced(response_content)
        result = self._try_parse_json(fixed_json, dim_map, include_reasoning)
        if result:
            return result

        result = self._parse_with_regex(response_content, dim_map, include_reasoning)
        if result:
            return result

        return [
            DimensionScore(
                dimension_name=dim.theme,
                score=3.0,
                weight=dim.weight,
                weighted_score=3.0 * dim.weight,
                reasoning="Parsing failed"
            )
            for dim in dimensions
        ]

    def _try_parse_json(
        self,
        json_str: str,
        dim_map: Dict,
        include_reasoning: bool
    ) -> Optional[List[DimensionScore]]:
        try:
            json_str = json_str.strip()

            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            data = json_repair.loads(json_str)

            if isinstance(data, list):
                evaluations = data
            elif isinstance(data, dict):
                evaluations = data.get('evaluations', [])
            else:
                return None

            dimension_scores = []
            for eval_item in evaluations:
                dim_name = eval_item.get('dimension', '')
                score = float(eval_item.get('score', 3.0))
                reasoning = eval_item.get('reasoning', '') if include_reasoning else ''

                if dim_name in dim_map:
                    dimension = dim_map[dim_name]
                    weighted_score = score * dimension.weight
                    dimension_scores.append(DimensionScore(
                        dimension_name=dim_name,
                        score=score,
                        weight=dimension.weight,
                        weighted_score=weighted_score,
                        reasoning=reasoning
                    ))

            if dimension_scores:
                return dimension_scores
            else:
                print(f"  [DEBUG] No dimensions found in parsed data")
                return None

        except Exception as e:
            preview = json_str[:200] if json_str else "empty"
            print(f"  [DEBUG] json_repair failed: {e}")
            print(f"  [DEBUG] JSON preview: {preview}...")
            return None

    def _fix_json_advanced(self, response_content: str) -> str:
        import re

        json_str = response_content.strip()

        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()
        def escape_reasoning(content):
            content = content.replace('\\', '\\\\')
            content = content.replace('"', '\\"')
            content = content.replace("'", "\\'")
            content = content.replace('\n', ' ')
            content = content.replace('\r', ' ')
            content = content.replace('\t', ' ')
            if len(content) > 500:
                content = content[:500] + "..."
            return f'"{content}"'

        json_str = re.sub(
            r'"reasoning":\s*"((?:[^"\\]|\\.)*)"(?=\s*[},])',
            lambda m: f'"reasoning": {escape_reasoning(m.group(1))}',
            json_str,
            flags=re.DOTALL
        )

        lines = json_str.split('\n')
        fixed_lines = []
        for line in lines:
            if len(line) > 500 and line.count('"') % 2 != 0:
                last_complete = line.rfind('},')
                if last_complete > 0:
                    line = line[:last_complete + 2]
            fixed_lines.append(line)

        json_str = '\n'.join(fixed_lines)

        json_str = ''.join(
            char for char in json_str
            if char.isprintable() or char in '\n\r\t'
        )

        return json_str

    def _parse_with_regex(
        self,
        response_content: str,
        dim_map: Dict,
        include_reasoning: bool
    ) -> Optional[List[DimensionScore]]:
        import re

        try:
            json_str = response_content.strip()

            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()

            pattern = r'"dimension":\s*"([^"]+)"\s*,\s*"score":\s*([0-9.]+)\s*,\s*"reasoning":\s*"([^"]*)"'

            matches = re.findall(pattern, json_str, re.DOTALL)

            if not matches:
                return None

            dimension_scores = []
            for match in matches:
                dim_name = match[0]
                score = float(match[1])
                reasoning = match[2] if include_reasoning else ''

                if dim_name in dim_map:
                    dimension = dim_map[dim_name]
                    weighted_score = score * dimension.weight
                    dimension_scores.append(DimensionScore(
                        dimension_name=dim_name,
                        score=score,
                        weight=dimension.weight,
                        weighted_score=weighted_score,
                        reasoning=reasoning[:500] if len(reasoning) > 500 else reasoning
                    ))

            if dimension_scores:
                return dimension_scores
            else:
                return None

        except Exception as e:
            return None

    def _fix_json_common_errors(self, json_str: str) -> str:

        lines = []
        for line in json_str.split('\n'):
            if '"reasoning":' in line:
                if '"reasoning": "' in line:
                    parts = line.split('"reasoning": "', 1)
                    if len(parts) == 2:
                        prefix, rest = parts
                        in_string = True
                        value_end = -1
                        escape_next = False
                        for i, char in enumerate(rest):
                            if escape_next:
                                escape_next = False
                                continue
                            if char == '\\':
                                escape_next = True
                            elif char == '"':
                                value_end = i
                                break
                            elif char in ',}' and i > 0:
                                if rest[i-1] != '\\':
                                    value_end = i - 1
                                    break

                        if value_end > 0:
                            value = rest[:value_end]
                            remaining = rest[value_end:]

                            value = value.replace('\\', '\\\\')
                            value = value.replace('"', '\\"')
                            value = value.replace("'", "\\'")
                            value = value.replace('\n', ' ')
                            value = value.replace('\r', ' ')
                            value = value.replace('\t', ' ')

                            line = f'{prefix}"reasoning": "{value}"{remaining}'

            lines.append(line)

        return '\n'.join(lines)


class BatchDAGEvaluator:

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        stage: str = 'evaluation'
    ):

        self.evaluator = DAGEvaluator(provider, model, stage)

    async def evaluate_batch(
        self,
        tasks: List[Dict],
        rubrics: Dict[str, Rubric],
        progress_callback: Optional[callable] = None
    ) -> List[EvaluationResult]:
        results = []
        total = len(tasks)

        for i, task in enumerate(tasks, 1):
            task_id = task['id']

            if task_id not in rubrics:
                print(f"[WARN] Skip task {task_id}: No rubric found")
                continue

            rubric = rubrics[task_id]

            if progress_callback:
                progress_callback(i, total)
            else:
                print(f"[PROGRESS] Evaluating: {i}/{total} ({task_id})")

            try:
                result = await self.evaluator.evaluate_dag(task, rubric)
                results.append(result)
            except Exception as e:
                print(f"[ERROR] Evaluation failed for task {task_id}: {e}")
                continue

        return results

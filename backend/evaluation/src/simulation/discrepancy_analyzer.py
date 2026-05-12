"""
Discrepancy Analyzer
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import numpy as np

from .model_executor import ModelSimulationResult


@dataclass
class DiscrepancyReport:
    task_id: str
    step_scores: Dict[str, Dict[str, float]]
    discriminatory_power: Dict[str, float]
    high_discrimination_steps: List[str]
    low_discrimination_steps: List[str]
    model_rankings: Dict[str, float]
    summary: Dict[str, Any]


class DiscrepancyAnalyzer:


    def analyze_task(self,
                    ground_truth: Dict,
                    model_results: List[ModelSimulationResult]) -> DiscrepancyReport:
        task_id = ground_truth['id']
        step_scores = self._calculate_step_scores(ground_truth, model_results)
        print("step_scores",step_scores)

        discriminatory_power = self._calculate_discriminatory_power(step_scores)

        median_power = np.median(list(discriminatory_power.values())) if discriminatory_power else 0
        high_discrimination = [
            step for step, power in discriminatory_power.items()
            if power > median_power * 1.2
        ]
        low_discrimination = [
            step for step, power in discriminatory_power.items()
            if power < median_power * 0.8
        ]

        model_rankings = self._calculate_model_rankings(step_scores, model_results)

        summary = {
            'n_models': len(model_results),
            'n_steps': len(step_scores),
            'avg_discriminatory_power': np.mean(list(discriminatory_power.values())) if discriminatory_power else 0,
            'high_discrimination_count': len(high_discrimination),
            'low_discrimination_count': len(low_discrimination)
        }

        return DiscrepancyReport(
            task_id=task_id,
            step_scores=step_scores,
            discriminatory_power=discriminatory_power,
            high_discrimination_steps=high_discrimination,
            low_discrimination_steps=low_discrimination,
            model_rankings=model_rankings,
            summary=summary
        )

    def _calculate_step_scores(self,
                               gt: Dict,
                               model_results: List[ModelSimulationResult]) -> Dict[str, Dict[str, float]]:

        step_scores = {}

        gt_steps = gt.get('task_steps', [])

        for i, gt_step in enumerate(gt_steps):
            step_key = f"step_{i+1}"
            step_scores[step_key] = {}

            gt_keywords = self._extract_keywords(gt_step)

            for model_result in model_results:
                model_name = model_result.model_name

                score = 0.0

                if model_result.execution_result.success:
                    score += 0.5

                gt_dag = self._normalize_dag(gt)
                model_dag = self._normalize_dag(model_result.generated_dag or {})

                similarity = self._calculate_dag_similarity(gt_dag, model_dag, gt_keywords)
                score += similarity * 0.5

                step_scores[step_key][model_name] = score

        return step_scores

    def _calculate_discriminatory_power(self,
                                         step_scores: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        discriminatory_power = {}

        for step, scores in step_scores.items():
            if not scores:
                continue

            scores_list = list(scores.values())
            variance = np.var(scores_list) if len(scores_list) > 1 else 0

            step_num = int(step.split('_')[1])
            importance = 1.0 / step_num

            power = variance * importance

            discriminatory_power[step] = power

        return discriminatory_power

    def _calculate_model_rankings(self,
                                   step_scores: Dict[str, Dict[str, float]],
                                   model_results: List[ModelSimulationResult]) -> Dict[str, float]:
        model_scores = {}

        for model_result in model_results:
            model_scores[model_result.model_name] = []

        for step, scores in step_scores.items():
            for model_name, score in scores.items():
                if model_name in model_scores:
                    model_scores[model_name].append(score)

        for model_name, scores in model_scores.items():
            if scores:
                model_scores[model_name] = np.mean(scores)
            else:
                model_scores[model_name] = 0.0

        return model_scores

    def _extract_keywords(self, step_text: str) -> List[str]:
        actions = [
            'extract', 'combine', 'merge', 'transcribe', 'convert',
            'apply', 'add', 'remove', 'generate', 'create', 'modify',
            'simplify', 'split', 'process', 'transform', 'analyze'
        ]

        file_types = [
            'audio', 'video', 'image', 'text', 'file',
            'wav', 'mp3', 'mp4', 'jpg', 'png', 'pdf'
        ]

        effects = [
            'reverb', 'echo', 'noise', 'silence', 'fade',
            'speed', 'pitch', 'volume', 'quality'
        ]

        keywords = []
        step_lower = step_text.lower()

        for action in actions:
            if action in step_lower:
                keywords.append(action)

        for ft in file_types:
            if ft in step_lower:
                keywords.append(ft)

        for effect in effects:
            if effect in step_lower:
                keywords.append(effect)

        return keywords if keywords else ['general']

    def _normalize_dag(self, dag: Dict) -> Dict:
        return {
            'nodes': dag.get('task_nodes', []),
            'links': dag.get('task_links', []),
            'user_request': dag.get('user_request', '')
        }

    def _calculate_dag_similarity(self,
                                 gt_dag: Dict,
                                 model_dag: Dict,
                                 keywords: List[str]) -> float:

        gt_nodes = len(gt_dag.get('nodes', []))
        model_nodes = len(model_dag.get('nodes', []))

        if gt_nodes == 0 and model_nodes == 0:
            node_sim = 1.0
        elif gt_nodes == 0 or model_nodes == 0:
            node_sim = 0.0
        else:
            node_sim = 1.0 - abs(gt_nodes - model_nodes) / max(gt_nodes, model_nodes)

        gt_links = len(gt_dag.get('links', []))
        model_links = len(model_dag.get('links', []))

        if gt_links == 0 and model_links == 0:
            link_sim = 1.0
        elif gt_links == 0 or model_links == 0:
            link_sim = 0.0
        else:
            link_sim = 1.0 - abs(gt_links - model_links) / max(gt_links, model_links)

        gt_node_names = [node['task'].lower() for node in gt_dag.get('nodes', [])]
        model_node_names = [node['task'].lower() for node in model_dag.get('nodes', [])]

        keyword_matches = 0
        for keyword in keywords:
            if keyword in ' '.join(gt_node_names):
                keyword_matches += 1
            if keyword in ' '.join(model_node_names):
                keyword_matches += 1

        keyword_sim = keyword_matches / len(keywords) if keywords else 0

        similarity = (node_sim * 0.4 + link_sim * 0.4 + keyword_sim * 0.2)

        return similarity

    def batch_analyze(self,
                      tasks: List[Dict],
                      all_model_results: Dict[str, List[ModelSimulationResult]]) -> List[DiscrepancyReport]:

        reports = []

        for task in tasks:
            task_id = task['id']
            if task_id not in all_model_results:
                continue

            model_results = all_model_results[task_id]

            report = self.analyze_task(task, model_results)
            reports.append(report)

        return reports

    def get_summary_statistics(self, reports: List[DiscrepancyReport]) -> Dict[str, Any]:

        if not reports:
            return {}

        all_high_discrimination = []
        all_low_discrimination = []

        for report in reports:
            all_high_discrimination.extend(report.high_discrimination_steps)
            all_low_discrimination.extend(report.low_discrimination_steps)


        from collections import Counter
        high_freq = Counter(all_high_discrimination)
        low_freq = Counter(all_low_discrimination)

        return {
            'total_tasks': len(reports),
            'most_common_high_discrimination': high_freq.most_common(5),
            'most_common_low_discrimination': low_freq.most_common(5),
            'avg_high_discrimination_per_task': np.mean([r.summary['high_discrimination_count'] for r in reports]),
            'avg_discriminatory_power': np.mean([r.summary['avg_discriminatory_power'] for r in reports])
        }

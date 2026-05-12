"""
Evaluation Reporter
"""

from typing import List, Dict, Optional
from pathlib import Path
import json
from datetime import datetime

from src.evaluation.dag_evaluator import EvaluationResult, DimensionScore


class EvaluationReporter:


    def __init__(self, output_dir: str = "data/evaluations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_single_result(
        self,
        result: EvaluationResult,
        format: str = "both"  # 'json', 'markdown', or 'both'
    ) -> List[Path]:

        saved_paths = []

        if format in ['json', 'both']:

            json_path = self.output_dir / f"{result.task_id}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            saved_paths.append(json_path)

        if format in ['markdown', 'both']:
            md_path = self.output_dir / f"{result.task_id}.md"
            md_content = self._generate_markdown_single(result)
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            saved_paths.append(md_path)

        return saved_paths

    def save_batch_results(
        self,
        results: List[EvaluationResult],
        format: str = "both"
    ) -> Dict[str, List[Path]]:

        saved_paths = {'json': [], 'markdown': []}

        for result in results:
            paths = self.save_single_result(result, format)
            for path in paths:
                if path.suffix == '.json':
                    saved_paths['json'].append(path)
                elif path.suffix == '.md':
                    saved_paths['markdown'].append(path)

        return saved_paths

    def generate_summary_report(
        self,
        results: List[EvaluationResult],
        output_name: str = "summary_report"
    ) -> Path:

        summary = self._calculate_summary_statistics(results)

        json_path = self.output_dir / f"{output_name}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        md_path = self.output_dir / f"{output_name}.md"
        md_content = self._generate_markdown_summary(results, summary)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return md_path

    def generate_comparison_data(
        self,
        results: List[EvaluationResult],
        output_name: str = "comparison_data"
    ) -> Path:

        comparison_data = {
            'metadata': {
                'total_tasks': len(results),
                'generated_at': datetime.now().isoformat(),
                'description': 'Comparison data for experimental analysis'
            },
            'tasks': []
        }

        for result in results:
            task_data = {
                'task_id': result.task_id,
                'normalized_score': result.normalized_score,
                'total_weighted_score': result.total_weighted_score,
                'dimension_scores': {}
            }


            for ds in result.dimension_scores:
                task_data['dimension_scores'][ds.dimension_name] = {
                    'score': ds.score,
                    'weight': ds.weight,
                    'weighted_score': ds.weighted_score
                }

            comparison_data['tasks'].append(task_data)


        comparison_data['tasks'].sort(
            key=lambda x: x['normalized_score'],
            reverse=True
        )


        output_path = self.output_dir / f"{output_name}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(comparison_data, f, indent=2, ensure_ascii=False)

        return output_path

    def _calculate_summary_statistics(self, results: List[EvaluationResult]) -> Dict:


        if not results:
            return {'error': 'No results to summarize'}


        scores = [r.normalized_score for r in results]
        mean_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)

        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_dev = variance ** 0.5

        score_ranges = {
            '5.0-4.5 (excellent)': sum(1 for s in scores if s >= 4.5),
            '4.5-3.5 (good)': sum(1 for s in scores if 3.5 <= s < 4.5),
            '3.5-2.5 (medium)': sum(1 for s in scores if 2.5 <= s < 3.5),
            '2.5-1.5 (Poor)': sum(1 for s in scores if 1.5 <= s < 2.5),
            '1.5-1.0 (Very bad)': sum(1 for s in scores if s < 1.5)
        }

        all_dimensions = set()
        for result in results:
            for ds in result.dimension_scores:
                all_dimensions.add(ds.dimension_name)

        dimension_stats = {}
        for dim_name in all_dimensions:
            dim_scores = [
                ds.score
                for r in results
                for ds in r.dimension_scores
                if ds.dimension_name == dim_name
            ]
            dimension_stats[dim_name] = {
                'mean': sum(dim_scores) / len(dim_scores),
                'min': min(dim_scores),
                'max': max(dim_scores),
                'std': (sum((s - sum(dim_scores)/len(dim_scores))**2 for s in dim_scores) / len(dim_scores)) ** 0.5
            }

        sorted_results = sorted(results, key=lambda r: r.normalized_score, reverse=True)
        top_tasks = [
            {'task_id': r.task_id, 'score': r.normalized_score}
            for r in sorted_results[:5]
        ]
        bottom_tasks = [
            {'task_id': r.task_id, 'score': r.normalized_score}
            for r in sorted_results[-5:]
        ]

        return {
            'total_tasks': len(results),
            'score_statistics': {
                'mean': mean_score,
                'min': min_score,
                'max': max_score,
                'std': std_dev
            },
            'score_distribution': score_ranges,
            'dimension_statistics': dimension_stats,
            'top_tasks': top_tasks,
            'bottom_tasks': bottom_tasks
        }
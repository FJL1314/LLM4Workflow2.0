"""
Data Loade
"""

import json
from typing import List, Dict, Optional
from pathlib import Path
import random


class TaskLoader:

    def __init__(self, data_path: str = "data/raw/taskbench_multimedia_dag.json"):
        self.data_path = Path(data_path)
        self._data: Optional[List[Dict]] = None
        self._stats: Optional[Dict] = None

    def load(self) -> List[Dict]:
        if self._data is None:
            print(f"Loading data from {self.data_path}...")
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self._data = [json.loads(line) for line in f]
            print(f"Loaded {len(self._data)} tasks")
        return self._data

    def get_sample(self, n: Optional[int] = None, random_seed: Optional[int] = None) -> List[Dict]:
        data = self.load()

        if n is None or n >= len(data):
            return data

        if random_seed is not None:
            random.seed(random_seed)

        return random.sample(data, n)

    def get_dataset_stats(self) -> Dict:
        if self._stats is not None:
            return self._stats

        data = self.load()

        total_tasks = len(data)

        tool_counter = {}
        for task in data:
            for node in task.get('task_nodes', []):
                tool_name = node['task']
                tool_counter[tool_name] = tool_counter.get(tool_name, 0) + 1

        common_tools = sorted(tool_counter.items(), key=lambda x: x[1], reverse=True)

        n_tools_list = [task.get('n_tools', 0) for task in data]
        n_steps_list = [len(task.get('task_steps', [])) for task in data]
        n_nodes_list = [len(task.get('task_nodes', [])) for task in data]
        n_links_list = [len(task.get('task_links', [])) for task in data]

        task_types = set()
        for task in data:
            tools = [node['task'] for node in task.get('task_nodes', [])]
            if any('audio' in t.lower() for t in tools):
                task_types.add('audio')
            if any('video' in t.lower() for t in tools):
                task_types.add('video')
            if any('image' in t.lower() for t in tools):
                task_types.add('image')
            if any('text' in t.lower() for t in tools):
                task_types.add('text')

        self._stats = {
            'total_tasks': total_tasks,
            'task_types': list(task_types),
            'common_tools': [tool[0] for tool in common_tools[:20]],
            'tool_counts': dict(common_tools),
            'avg_n_tools': sum(n_tools_list) / len(n_tools_list) if n_tools_list else 0,
            'avg_n_steps': sum(n_steps_list) / len(n_steps_list) if n_steps_list else 0,
            'avg_n_nodes': sum(n_nodes_list) / len(n_nodes_list) if n_nodes_list else 0,
            'avg_n_links': sum(n_links_list) / len(n_links_list) if n_links_list else 0,
            'avg_complexity': (
                sum(n_nodes_list) * sum(n_links_list) / len(data) / len(data)
                if n_nodes_list and n_links_list else 0
            ),
            'tool_diversity': len(tool_counter),
            'num_dimensions': 6
        }

        return self._stats

    def print_stats(self):
        stats = self.get_dataset_stats()

        print("\n" + "="*60)
        print("DATASET STATISTICS")
        print("="*60)
        print(f"Total tasks: {stats['total_tasks']}")
        print(f"\nTask types: {', '.join(stats['task_types'])}")
        print(f"Tool diversity: {stats['tool_diversity']} different tools")
        print(f"\nCommon tools:")
        for tool, count in list(stats['tool_counts'].items())[:10]:
            print(f"  - {tool}: {count} tasks")
        print(f"\nAverage complexity:")
        print(f"  - Tools per task: {stats['avg_n_tools']:.2f}")
        print(f"  - Steps per task: {stats['avg_n_steps']:.2f}")
        print(f"  - Nodes per DAG: {stats['avg_n_nodes']:.2f}")
        print(f"  - Links per DAG: {stats['avg_n_links']:.2f}")
        print("="*60 + "\n")


class RubricLoader:

    @staticmethod
    def save_rubric(rubric, output_path: str):

        from ..rubric_generator.simple_rubric import Rubric

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        json_path = Path(str(output_path) + '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(rubric.to_dict(), f, indent=2, ensure_ascii=False)

        md_path = Path(str(output_path) + '.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(rubric.to_markdown())

        print(f"Saved rubric to {json_path} and {md_path}")

    @staticmethod
    def load_rubric(json_path: str):
        from ..rubric_generator.simple_rubric import Rubric, RubricDimension

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        dimensions = [
            RubricDimension(
                theme=dim['theme'],
                tips=dim['tips'],
                weight=dim.get('weight', 1.0),
                description=dim.get('description', '')
            )
            for dim in data['dimensions']
        ]

        return Rubric(
            task_id=data['task_id'],
            task_description=data['task_description'],
            dimensions=dimensions,
            min_score=data.get('min_score', 0),
            max_score=data.get('max_score', 5),
            metadata=data.get('metadata', {})
        )

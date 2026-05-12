"""
DAG Executor
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """result"""
    model_name: str
    dag: Dict
    success: bool
    execution_trace: List[str]
    intermediate_results: Dict[str, Any]
    errors: List[str]
    execution_time: float = 0.0


class DAGExecutor:

    def __init__(self, sampled_nodes: Optional[List[Dict]] = None):
        self.sampled_nodes = {}
        if sampled_nodes:
            self.sampled_nodes = {n['task']: n for n in sampled_nodes}

    def simulate_execution(self,
                          dag: Dict,
                          model_name: str = "unknown") -> ExecutionResult:

        import time

        start_time = time.time()
        execution_trace = []
        errors = []
        intermediate_results = {}

        try:
            topo_order = self._topological_sort(dag)
            if not topo_order:
                return ExecutionResult(
                    model_name=model_name,
                    dag=dag,
                    success=False,
                    execution_trace=["Failed: Cannot perform topological sort"],
                    intermediate_results={},
                    errors=["Cycle detected in DAG"],
                    execution_time=time.time() - start_time
                )

            execution_trace.append(f"Topological order: {' → '.join(topo_order)}")

            for node_name in topo_order:
                node = self._get_node_by_name(dag, node_name)
                if not node:
                    errors.append(f"Node not found: {node_name}")
                    continue
                result = self._execute_node(node, intermediate_results)
                intermediate_results[node_name] = result

                execution_trace.append(f"Executed {node_name}: {result}")

            success = len(errors) == 0
            execution_trace.append(f"Execution {'succeeded' if success else 'failed'}")

            return ExecutionResult(
                model_name=model_name,
                dag=dag,
                success=success,
                execution_trace=execution_trace,
                intermediate_results=intermediate_results,
                errors=errors,
                execution_time=time.time() - start_time
            )

        except Exception as e:
            return ExecutionResult(
                model_name=model_name,
                dag=dag,
                success=False,
                execution_trace=[f"Exception: {str(e)}"],
                intermediate_results=intermediate_results,
                errors=[str(e)],
                execution_time=time.time() - start_time
            )

    def _topological_sort(self, dag: Dict) -> Optional[List[str]]:
        from collections import defaultdict, deque

        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for link in dag.get('task_links', []):
            graph[link['source']].append(link['target'])
            in_degree[link['target']] += 1
            if link['source'] not in in_degree:
                in_degree[link['source']] = 0

        queue = deque([node for node in graph if in_degree[node] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(graph):
            return None

        return result

    def _get_node_by_name(self, dag: Dict, name: str) -> Optional[Dict]:
        for node in dag.get('task_nodes', []):
            if node['task'] == name:
                return node
        return None

    def _execute_node(self,
                     node: Dict,
                     intermediate_results: Dict) -> str:
        task_name = node['task']
        arguments = node.get('arguments', [])

        resolved_args = []
        for arg in arguments:
            if isinstance(arg, str) and arg.startswith('<node-') and arg.endswith('>'):
                resolved_args.append(f"[Output from {arg}]")
            else:
                resolved_args.append(arg)

        return f"Executed {task_name} with args: {resolved_args}"

    def validate_dag_structure(self, dag: Dict) -> Dict[str, Any]:
        result = {
            'has_cycles': False,
            'is_connected': False,
            'n_nodes': len(dag.get('task_nodes', [])),
            'n_edges': len(dag.get('task_links', [])),
            'sources': [],
            'sinks': [],
            'topological_order': None
        }

        topo_order = self._topological_sort(dag)
        if topo_order is None:
            result['has_cycles'] = True
        else:
            result['topological_order'] = topo_order

        from collections import defaultdict, deque
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)

        nodes = set(node['task'] for node in dag.get('task_nodes', []))
        for node in nodes:
            in_degree[node] = 0
            out_degree[node] = 0

        for link in dag.get('task_links', []):
            out_degree[link['source']] += 1
            in_degree[link['target']] += 1

        result['sources'] = [n for n in nodes if in_degree[n] == 0]
        result['sinks'] = [n for n in nodes if out_degree[n] == 0]
        result['is_connected'] = len(result['sources']) > 0 and len(result['sinks']) > 0

        return result

"""
DAG Validator
"""

from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    details: Dict

    def __str__(self) -> str:
        if self.is_valid:
            return f"✓ DAG is valid ({len(self.warnings)} warnings)"
        else:
            return f"✗ DAG is invalid ({len(self.errors)} errors, {len(self.warnings)} warnings)"


class DAGValidator:

    def __init__(self, sampled_nodes: Optional[List[Dict]] = None):
        self.sampled_nodes = {}
        if sampled_nodes:
            self.sampled_nodes = {n['task']: n for n in sampled_nodes}

    def validate(self, task: Dict, strict: bool = True) -> ValidationResult:

        errors = []
        warnings = []
        details = {}

        # 1. Topology check (acyclic)
        is_acyclic, cycle_info = self._check_acyclic(task)
        details['acyclic'] = is_acyclic
        if not is_acyclic:
            errors.append(f"DAG contains cycles: {cycle_info}")

        # 2.Type matching check
        type_errors, type_warnings = self._check_type_matching(task)
        errors.extend(type_errors)
        warnings.extend(type_warnings)
        details['type_errors'] = len(type_errors)
        details['type_warnings'] = len(type_warnings)

        # 3. Connectivity check
        is_connected, connectivity_info = self._check_connectivity(task)
        details['connected'] = is_connected
        if not is_connected:
            errors.append(f"DAG connectivity issue: {connectivity_info}")

        # 4. Parameter validity check
        param_errors = self._check_parameters(task)
        errors.extend(param_errors)
        details['param_errors'] = len(param_errors)

        # 5. Data Stream Integrity Check
        flow_errors, flow_warnings = self._check_data_flow(task)
        errors.extend(flow_errors)
        warnings.extend(flow_warnings)
        details['flow_errors'] = len(flow_errors)
        details['flow_warnings'] = len(flow_warnings)

        # 6. Sink node check (at least one sink node)
        sink_info = self._check_sinks(task)
        details['sinks'] = sink_info
        if not sink_info['has_sinks']:
            warnings.append("No explicit sink nodes found (nodes with no outgoing edges)")

        # 7. Source node check (at least one source node)
        source_info = self._check_sources(task)
        details['sources'] = source_info
        if not source_info['has_sources']:
            warnings.append("No explicit source nodes found (nodes with no incoming edges)")

        # Calculation validity
        is_valid = len(errors) == 0
        if strict:
            is_valid = is_valid and len(warnings) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            details=details
        )

    def _check_acyclic(self, task: Dict) -> Tuple[bool, str]:
        # Construct an adjacency list and an in-degree list
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for link in task.get('task_links', []):
            graph[link['source']].append(link['target'])
            in_degree[link['target']] += 1
            if link['source'] not in in_degree:
                in_degree[link['source']] = 0

        # Topological sorting
        queue = deque([node for node in graph if in_degree[node] == 0])
        visited = 0
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)
            visited += 1
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited != len(graph):
            cycle_nodes = set(graph.keys()) - set(order)
            return False, f"Cycle detected involving nodes: {cycle_nodes}"
        else:
            return True, f"Topological order: {' → '.join(order)}"

    def _check_type_matching(self, task: Dict) -> Tuple[List[str], List[str]]:
        errors = []
        warnings = []

        # If sampled_nodes are not present, skip type checking.
        if not self.sampled_nodes:
            warnings.append("No sampled_nodes provided, skipping type validation")
            return errors, warnings

        # Build node output type mapping
        node_outputs = {}
        for node in task.get('task_nodes', []):
            task_name = node['task']
            if task_name in self.sampled_nodes:
                node_outputs[task_name] = self.sampled_nodes[task_name]['output-type']
            else:
                warnings.append(f"Unknown node type: {task_name}")

        # Check the type compatibility of each edge
        for link in task.get('task_links', []):
            source = link['source']
            target = link['target']

            if source not in node_outputs:
                warnings.append(f"Skipping type check for unknown source: {source}")
                continue

            if target not in self.sampled_nodes:
                warnings.append(f"Skipping type check for unknown target: {target}")
                continue

            source_outputs = node_outputs[source]
            target_inputs = self.sampled_nodes[target]['input-type']

            is_compatible = any(
                self._types_compatible(out_type, target_inputs)
                for out_type in source_outputs
            )

            if not is_compatible:
                errors.append(
                    f"Type mismatch: {source} outputs {source_outputs} "
                    f"but {target} expects {target_inputs}"
                )

        return errors, warnings

    def _types_compatible(self, out_type: str, target_inputs: List[str]) -> bool:
        if out_type in target_inputs:
            return True

        # More complex type compatibility rules can be added.
        type_aliases = {
            'str': 'text',
            'string': 'text',
            'int': 'number',
            'float': 'number'
        }

        normalized_out = type_aliases.get(out_type, out_type)
        normalized_inputs = [type_aliases.get(t, t) for t in target_inputs]

        return normalized_out in normalized_inputs

    def _check_connectivity(self, task: Dict) -> Tuple[bool, str]:
        """
        Check connectivity

        Returns:
            (is_connected, info)
        """
        nodes = set(node['task'] for node in task.get('task_nodes', []))
        links = task.get('task_links', [])

        if not nodes:
            return True, "Empty DAG"

        # Build an adjacency list
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for link in links:
            graph[link['source']].append(link['target'])
            in_degree[link['target']] += 1
            if link['source'] not in in_degree:
                in_degree[link['source']] = 0

        # Find the source node (the node with no incoming edges).
        sources = [n for n in nodes if in_degree.get(n, 0) == 0]

        if not sources:
            return False, "No source nodes found (cycle or all nodes have incoming edges)"

        # BFS
        visited = set()
        queue = deque(sources)

        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)

            for link in links:
                if link['source'] == node:
                    queue.append(link['target'])

        unreachable = nodes - visited
        if unreachable:
            return False, f"Unreachable nodes: {unreachable}"

        return True, f"All {len(visited)} nodes are reachable from sources"

    def _check_parameters(self, task: Dict) -> List[str]:
        """
        Check parameter validity

        Returns:
            errors:
        """
        errors = []
        nodes = task.get('task_nodes', [])
        n_nodes = len(nodes)

        for node in nodes:
            task_name = node['task']
            args = node.get('arguments', [])

            for arg in args:
                if isinstance(arg, str) and arg.startswith('<node-') and arg.endswith('>'):
                    try:
                        idx = int(arg[6:-1])
                        if idx < 0 or idx >= n_nodes:
                            errors.append(
                                f"Invalid node reference in {task_name}: "
                                f"{arg} (index {idx} out of range [0, {n_nodes-1}])"
                            )
                    except ValueError:
                        errors.append(
                            f"Malformed node reference in {task_name}: {arg}"
                        )

        return errors

    def _check_data_flow(self, task: Dict) -> Tuple[List[str], List[str]]:
        """
        Check data stream integrity

        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []

        links = task.get('task_links', [])
        nodes = task.get('task_nodes', [])

        node_with_input = set()
        node_with_output = set()

        for link in links:
            node_with_input.add(link['target'])
            node_with_output.add(link['source'])

        all_nodes = set(node['task'] for node in nodes)
        isolated_nodes = all_nodes - node_with_input - node_with_output

        for isolated in isolated_nodes:
            warnings.append(f"Isolated node (no inputs or outputs): {isolated}")

        intermediate_nodes = node_with_input & node_with_output
        for node in intermediate_nodes:
            if self.sampled_nodes and node in self.sampled_nodes:
                node_info = self.sampled_nodes[node]
                pass

        return errors, warnings

    def _check_sources(self, task: Dict) -> Dict:
        """Check source node"""
        links = task.get('task_links', [])
        nodes = set(node['task'] for node in task.get('task_nodes', []))

        in_degree = defaultdict(int)
        for node in nodes:
            in_degree[node] = 0

        for link in links:
            in_degree[link['target']] += 1

        sources = [node for node in nodes if in_degree[node] == 0]

        return {
            'has_sources': len(sources) > 0,
            'count': len(sources),
            'nodes': sources
        }

    def _check_sinks(self, task: Dict) -> Dict:
        """Check the sink node"""
        links = task.get('task_links', [])
        nodes = set(node['task'] for node in task.get('task_nodes', []))

        out_degree = defaultdict(int)
        for node in nodes:
            out_degree[node] = 0

        for link in links:
            out_degree[link['source']] += 1

        sinks = [node for node in nodes if out_degree[node] == 0]

        return {
            'has_sinks': len(sinks) > 0,
            'count': len(sinks),
            'nodes': sinks
        }

    def get_dag_stats(self, task: Dict) -> Dict:
        """
        Obtain DAG statistics

        Returns:
            Statistical Information Dictionary
        """
        nodes = task.get('task_nodes', [])
        links = task.get('task_links', [])

        in_degree = defaultdict(int)
        out_degree = defaultdict(int)
        node_set = set(node['task'] for node in nodes)

        for node in node_set:
            in_degree[node] = 0
            out_degree[node] = 0

        for link in links:
            out_degree[link['source']] += 1
            in_degree[link['target']] += 1

        n_nodes = len(node_set)
        n_edges = len(links)
        max_edges = n_nodes * (n_nodes - 1) / 2 if n_nodes > 1 else 0
        density = n_edges / max_edges if max_edges > 0 else 0

        return {
            'n_nodes': n_nodes,
            'n_edges': n_edges,
            'density': density,
            'sources': [n for n in node_set if in_degree[n] == 0],
            'sinks': [n for n in node_set if out_degree[n] == 0],
            'avg_in_degree': sum(in_degree.values()) / n_nodes if n_nodes > 0 else 0,
            'avg_out_degree': sum(out_degree.values()) / n_nodes if n_nodes > 0 else 0,
            'max_in_degree': max(in_degree.values()) if in_degree else 0,
            'max_out_degree': max(out_degree.values()) if out_degree else 0
        }

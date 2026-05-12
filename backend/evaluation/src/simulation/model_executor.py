"""
Model Executor
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..llm_factory.factory import LLMFactory,Message
from .dag_executor import DAGExecutor, ExecutionResult
from ..utils import get_prompt_manager

@dataclass
class ModelSimulationResult:
    model_name: str
    provider: str
    execution_result: ExecutionResult
    generated_dag: Optional[Dict] = None
    generation_time: float = 0.0


class MultiModelExecutor:

    def __init__(self):
        self.executor = DAGExecutor()
        self.prompt_manager = get_prompt_manager()


    async def simulate_task(self,
                           task: Dict,
                           model_configs: Optional[List[Dict[str, str]]] = None) -> List[ModelSimulationResult]:

        if model_configs is None:
            model_configs = LLMFactory.get_simulation_configs()

        if not model_configs:
            config = LLMFactory.get_rubric_generator_config('generic')
            model_configs = [config]

        print(f"\n Simulating with {len(model_configs)} models...")

        tasks = []
        for i, config in enumerate(model_configs, 1):
            print(f"   {i}. {config['provider']} + {config['model']}")
            tasks.append(self._simulate_with_model(task, config))
        results = await asyncio.gather(*tasks, return_exceptions=True)

        model_results = []
        for i, (config, result) in enumerate(zip(model_configs, results)):
            if isinstance(result, Exception):
                print(f"   ❌ Model {i+1} failed: {result}")
                model_results.append(ModelSimulationResult(
                    model_name=config['model'],
                    provider=config['provider'],
                    execution_result=ExecutionResult(
                        model_name=config['model'],
                        dag=task,
                        success=False,
                        execution_trace=[f"Exception: {str(result)}"],
                        intermediate_results={},
                        errors=[str(result)]
                    ),
                    generation_time=0.0
                ))
            else:
                model_results.append(result)
                print(f"    Model {i+1} completed")

        return model_results

    def get_dag_generate_prompt(self, task: Dict) -> str:
        params = {
            "user_request": task.get('user_request', ''),
            "task_steps": task.get('task_steps', []),
            "available_tools": task.get('sampled_nodes', [])
        }
        return self.prompt_manager.get_dag_generate_prompt(**params)


    async def _simulate_with_model(self,
                                    task: Dict,
                                    model_config: Dict[str, str]) -> ModelSimulationResult:

        import time

        start_time = time.time()
        provider = model_config['provider']
        model = model_config['model']

        try:
            client = LLMFactory.get_client(provider, model)
            prompt = self.get_dag_generate_prompt(task)
            messages = [
                Message(role="user", content=prompt),
            ]
            generated_dag_LLMResponse = await client.acomplete(
                messages=messages,
                temperature=0.7,
                max_tokens=4000
            )
            import json
            generated_dag=generated_dag_LLMResponse.content.replace("```json", "").replace("```", "").strip()
            generated_dag = json.loads(generated_dag)
            generation_time = time.time() - start_time

            execution_result = self.executor.simulate_execution(
                generated_dag,
                model_name=model
            )

            return ModelSimulationResult(
                model_name=model,
                provider=provider,
                execution_result=execution_result,
                generated_dag=generated_dag,
                generation_time=generation_time
            )

        except Exception as e:
            print(e)
            return ModelSimulationResult(
                model_name=model,
                provider=provider,
                execution_result=ExecutionResult(
                    model_name=model,
                    dag=task,
                    success=False,
                    execution_trace=[f"Failed: {str(e)}"],
                    intermediate_results={},
                    errors=[str(e)]
                ),
                generation_time=time.time() - start_time
            )

    async def execute_with_ground_truth(self,
                                        tasks: List[Dict],
                                        model_configs: Optional[List[Dict[str, str]]] = None) -> Dict[str, List[ModelSimulationResult]]:
        results = {}

        for i, task in enumerate(tasks, 1):
            print(f"\n{'='*70}")
            print(f"Task {i}/{len(tasks)} (ID: {task['id']})")
            print(f"{'='*70}")

            task_results = await self.simulate_task(task, model_configs)

            results[task['id']] = task_results

        return results

    def get_execution_summary(self, results: List[ModelSimulationResult]) -> Dict[str, Any]:
        total = len(results)
        successful = sum(1 for r in results if r.execution_result.success)
        failed = total - successful

        summary = {
            'total_models': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0,
            'models': []
        }

        for result in results:
            summary['models'].append({
                'model': result.model_name,
                'provider': result.provider,
                'success': result.execution_result.success,
                'errors': len(result.execution_result.errors),
                'time': result.generation_time
            })

        return summary

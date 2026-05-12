from src.rubric_generator.simple_rubric import SimpleRubricGenerator,Rubric,RubricDimension
from src.simulation.model_executor import MultiModelExecutor
from src.simulation.discrepancy_analyzer import DiscrepancyAnalyzer,DiscrepancyReport
from src.simulation.rubric_refiner import RubricRefiner
generator = SimpleRubricGenerator(stage="draft")
executor = MultiModelExecutor()
analyzer = DiscrepancyAnalyzer()
refiner = RubricRefiner()
from src.evaluation import DAGEvaluator
from util import to_serializable, normalize_simulation_report
async def generate_draft_rubric(task):

    draft_rubric = await generator.generate_task_rubric(task)
    return draft_rubric


from typing import Dict, Any




async def generate_simulation_results(task: Dict[str, Any]) -> Dict[str, Any]:
    sim_results =await executor.simulate_task(task)
    print("sim_results",sim_results)
    report = analyzer.analyze_task(task, sim_results)
    sim_report = normalize_simulation_report(report)
    return sim_report

async def generate_final_task_specific_rubric(
    task,
    draft_rubric,
    sim_results,
):
    def normalize_dimension(item):
        if isinstance(item, RubricDimension):
            return item

        return RubricDimension(
            theme=item.get("theme", ""),
            tips=item.get("tips", []),
            description=item.get("description", ""),
            weight=item.get("weight", 1.0),
        )

    # draft_rubric -> Rubric
    if isinstance(draft_rubric, Rubric):
        draft_rubric_obj = draft_rubric

    elif isinstance(draft_rubric, dict):
        dims = draft_rubric.get("dimensions", [])
        draft_rubric_obj = Rubric(
            task_id=draft_rubric.get("task_id", str(task.get("id", ""))),
            task_description=draft_rubric.get("task_description", task.get("user_request", "")),
            dimensions=[normalize_dimension(item) for item in dims],
        )

    else:
        draft_rubric_obj = Rubric(
            task_id=str(task.get("id", "")),
            task_description=task.get("user_request", ""),
            dimensions=[normalize_dimension(item) for item in (draft_rubric or [])],
        )

    # sim_results -> DiscrepancyReport
    if isinstance(sim_results, DiscrepancyReport):
        discrepancy_report_obj = sim_results
    else:
        discrepancy_report_obj = DiscrepancyReport(**sim_results)

    final_rubric_obj = await refiner.refine_rubric(
        draft_rubric=draft_rubric_obj,
        discrepancy_report=discrepancy_report_obj,
        task=task,
    )

    final_rubric = to_serializable(final_rubric_obj)

    if isinstance(final_rubric, dict):
        return final_rubric.get("dimensions", [])

    if isinstance(final_rubric, list):
        return final_rubric

    return []


evaluator=DAGEvaluator()
from types import SimpleNamespace

class SimpleRubric:
    def __init__(
        self,
        dimensions,
        metadata=None,
        task_id="",
        task_description="",
        min_score=0,
        max_score=5,
    ):
        self.dimensions = dimensions
        self.metadata = metadata or {
            "type": "merged_selected",
            "source": "generic+draft",
        }
        self.task_id = task_id
        self.task_description = task_description
        self.min_score = min_score
        self.max_score = max_score


def dict_to_dimension_obj(item):
    return SimpleNamespace(
        theme=item.get("theme", ""),
        tips=item.get("tips", []),
        weight=item.get("weight", 1),
        description=item.get("description", ""),
    )


def normalize_rubric(rubric, task=None):
    if hasattr(rubric, "dimensions") and hasattr(rubric, "metadata"):
        return rubric

    task_id = ""
    task_description = ""
    if isinstance(task, dict):
        task_id = str(task.get("id", ""))
        task_description = task.get("user_request", "") or task.get("task_description", "")

    if isinstance(rubric, list):
        return SimpleRubric(
            dimensions=[
                dict_to_dimension_obj(item) if isinstance(item, dict) else item
                for item in rubric
            ],
            metadata={
                "type": "merged_selected",
                "source": "generic+draft",
                "total_dimensions": len(rubric),
            },
            task_id=task_id,
            task_description=task_description,
            min_score=0,
            max_score=5,
        )

    if isinstance(rubric, dict) and "dimensions" in rubric:
        dims = rubric.get("dimensions", [])
        return SimpleRubric(
            dimensions=[
                dict_to_dimension_obj(item) if isinstance(item, dict) else item
                for item in dims
            ],
            metadata=rubric.get("metadata", {
                "type": "merged_selected",
                "source": "generic+draft",
                "total_dimensions": len(dims),
            }),
            task_id=rubric.get("task_id", task_id),
            task_description=rubric.get("task_description", task_description),
            min_score=rubric.get("min_score", 0),
            max_score=rubric.get("max_score", 5),
        )

    return rubric


async def generate_dag_report(task, rubric):
    rubric = normalize_rubric(rubric, task=task)
    report = await evaluator.evaluate_dag(task, rubric)
    return report
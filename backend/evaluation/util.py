from typing import Any, List, Optional,Generic,TypeVar
def to_serializable(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # list / tuple / set
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(item) for item in obj]

    # dict
    if isinstance(obj, dict):
        return {key: to_serializable(value) for key, value in obj.items()}

    # Pydantic v2
    if hasattr(obj, "model_dump"):
        return to_serializable(obj.model_dump())

    # Pydantic v1
    if hasattr(obj, "dict"):
        return to_serializable(obj.dict())

    if hasattr(obj, "__dict__"):
        return {
            key: to_serializable(value)
            for key, value in obj.__dict__.items()
            if not key.startswith("_")
        }

    return str(obj)


def merge_rubrics(
    generic_rubric: Optional[List[dict]],
    final_rubric: Optional[List[dict]]
) -> List[dict]:
    merged = []
    seen = set()

    for rubric_list in [generic_rubric or [], final_rubric or []]:
        for item in rubric_list:
            theme = item.get("theme")
            if not theme:
                continue
            if theme not in seen:
                merged.append(item)
                seen.add(theme)

    return merged

def normalize_simulation_report(report_obj) -> dict:
    report_dict = to_serializable(report_obj)

    return {
        "task_id": report_dict.get("task_id"),
        "step_scores": report_dict.get("step_scores", {}),
        "discriminatory_power": report_dict.get("discriminatory_power", {}),
        "high_discrimination_steps": report_dict.get("high_discrimination_steps", []),
        "low_discrimination_steps": report_dict.get("low_discrimination_steps", []),
        "model_rankings": report_dict.get("model_rankings", {}),
        "summary": report_dict.get("summary", {}),
    }
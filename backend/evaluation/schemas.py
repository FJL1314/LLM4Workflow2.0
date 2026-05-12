from pydantic import BaseModel
from typing import Any, List, Optional,Dict


class genericRubricRequest(BaseModel):
    workflow_id: str
    task: Any


class DraftRubricRequest(BaseModel):
    workflow_id: str
    task: Any


class ReportRequest(BaseModel):
    workflow_id: str
    task: Any
    generic_rubric: Optional[List[Any]] = None
    draft_rubric: Optional[List[Any]] = None



class SimulationRequest(BaseModel):
    workflow_id: str
    task: Dict[str, Any]


class SimulationResponse(BaseModel):
    success: bool
    workflow_id: str
    sim_results: Dict[str, Any]


from pydantic import BaseModel
from typing import Any, List, Optional,Generic,TypeVar,Dict
from pydantic.generics import GenericModel
T = TypeVar('T')


class genericRubricRequest(BaseModel):
    workflow_id: str
    task: Any

class DraftRubricRequest(BaseModel):
    workflow_id: str
    task: Any


class RestfulModel(GenericModel, Generic[T]):
    code: int = 200
    msg: Optional[str] = "OK"
    data: Optional[T]= None


class SimulationRequest(BaseModel):
    workflow_id: str
    task: Dict[str, Any]


class SimulationResponse(BaseModel):
    success: bool
    workflow_id: str
    sim_results: Dict[str, Any]




class FinalRubricRequest(BaseModel):
    workflow_id: str
    task: Dict[str, Any]
    draft_rubric: List[Dict[str, Any]]
    sim_results: Dict[str, Any]


class FinalRubricResponse(BaseModel):
    code: int
    msg: str
    data: Dict[str, Any]

class ReportRequest(BaseModel):
    workflow_id: str
    task: Any
    generic_rubric: Optional[List[Any]] = None
    final_rubric: Optional[List[Any]] = None
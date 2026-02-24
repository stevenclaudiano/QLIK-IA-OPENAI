from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None

class ChartPayload(BaseModel):
    type: str  # "bar", "line", "pie"...
    title: str
    labels: List[str]
    datasets: List[Dict[str, Any]]  # compatível com Chart.js / flexível

class AskResponse(BaseModel):
    ok: bool
    answer: str
    chart: Optional[ChartPayload] = None
    meta: Optional[Dict[str, Any]] = None

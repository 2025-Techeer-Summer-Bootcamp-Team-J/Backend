from pydantic import BaseModel
from typing import Any, Optional

class ResultResponseModel(BaseModel):
    status_code: int
    message: str
    data: Optional[Any] = None
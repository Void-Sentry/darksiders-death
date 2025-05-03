from pydantic import BaseModel, Field

class SearchQueryParams(BaseModel):
    displayName: str = Field(..., min_length=4)

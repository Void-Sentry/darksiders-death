from pydantic import BaseModel, Field

class QueryParams(BaseModel):
    page: int = Field(default=1, gt=0)
    size: int = Field(default=10, gt=0, le=100)

# class FollowingQueryParams(QueryParams)
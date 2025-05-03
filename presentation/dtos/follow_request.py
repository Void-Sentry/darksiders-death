from pydantic import BaseModel, Field

class FollowPathParams(BaseModel):
    follower_id: str = Field(..., min_length=15, max_length=20, pattern=r'^\d+$')

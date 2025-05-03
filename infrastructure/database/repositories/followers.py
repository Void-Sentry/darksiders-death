from .generic import GenericRepository

class FollowersRepository(GenericRepository):
    def __init__(self):
        super().__init__("followers")

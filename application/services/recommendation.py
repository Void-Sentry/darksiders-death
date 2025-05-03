from infrastructure.database.repositories import follower_repository
from infrastructure.cache import cache_client
from infrastructure.bus import bus_client
from datetime import datetime
import uuid
import os

class RecommendationService:
    def __init__(self):
        self.follower_repo = follower_repository
        self.cache = cache_client
        self.bus = bus_client

    def _create_user_key(self, user_id):
        return f"users:recommendations:counting:{user_id}"

    def _create_group_key(self):
        return f"users:recommendations:groups:{uuid.uuid4().hex}_{int(datetime.now().timestamp())}"

    def _increment_user_follow_count(self, key):
        return self.cache.incr(key)
    
    def _reset_user_follow_count(self, key):
        self.cache.delete(key)
    
    def _add_user_to_group(self, group_id, user_id):
        ts = int(datetime.now().timestamp())
        self.cache.zadd(group_id, { user_id: ts })

    def _check_user_requirements(self, value):
        value == os.getenv('FOLLOWERS_PER_USER')

    def _get_last_group(self):
        pattern = "users:recommendations:groups:*"

        keys = self.cache.keys(pattern)
        
        if not keys:
            return None
        
        decoded_keys = [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]

        last_key = max(
            decoded_keys,
            key=lambda x: int(x.split('_')[-1])
        )

        return last_key

    def _check_group_requirements(self, value):
        self.cache.zcard(f"users:recommendations:groups:{value}")
        value == os.getenv('USERS_PER_GROUP')

    def get_recommendations(self, user_id):
        return self.cache.get(f"users:recommendations:results:{user_id}") or self._hottest(user_id)
    
    def _hottest(self, user_id):
        ids = self.bus.publish_event('war_queue', 'MOST_FOLLOWED', {})

        if not ids:
            return []

        profiles = self.bus.publish_event('war_queue', 'SEARCH_PROFILE', {
            'user_ids': [str(id) for id in ids]
        })

        for profile in profiles:
            data = self.follower_repo.find_by({ 'following_id': profile['userId'], 'follower_id': user_id })
            profile['isFollowing'] = bool(data)

        return profiles

    def run(self, user_id):
        user_key = self._create_user_key(user_id)
        total = self._increment_user_follow_count(user_key)
        
        if self._check_user_requirements(total):
            group_key = self._get_last_group()
            self._reset_user_follow_count(user_key)
            
            if self._check_group_requirements(group_key):
                new_group_key = self._create_group_key(user_id)
                self.bus.publish_event(os.getenv('BUS_QUEUE'), 'PROCESS_RECOMMENDATIONS', new_group_key)
                return self._add_user_to_group(new_group_key, user_id)
            
            self._add_user_to_group(group_key, user_id)

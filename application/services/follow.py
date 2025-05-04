from infrastructure.database.repositories import follower_repository
from infrastructure.bus import bus_client

class FollowService:
    def __init__(self):
        self.repo = follower_repository
        self.bus = bus_client

    def following(self, user_id, page=1, size=10):
        following = self.repo.find_by({
            'follower_id': user_id,
        }, page, size)

        if not following:
            return []

        data = self.bus.publish_event('war_queue', 'SEARCH_PROFILE', {
            'user_ids': [str(profile['following_id']) for profile in following]
        })

        if not data:
            return []
        
        for user in data:
            user['isFollowing'] = True

        return data
    
    def followers(self, user_id):
        return self.repo.find_by({
            'following_id': user_id
        })
    
    def search(self, display_name, user_id):
        profiles = self.bus.publish_event('war_queue', 'SEARCH_PROFILE', {
            'display_name': display_name
        })
        for profile in profiles:
            data = self.repo.find_by({ 'following_id': profile['userId'], 'follower_id': user_id })
            profile['isFollowing'] = bool(data)

        return profiles

    def follow(self, user_id, follower_id):
        if not follower_id:
            return f"Follower ID is missing"
        
        if user_id == follower_id:
            return "You cannot follow yourself"

        follower_info = self.bus.publish_event('war_queue', 'PROFILE_INFO', {
            'user_id': follower_id
        })

        if 'message' in follower_info:
            return follower_info['message']

        already_following = self.repo.find_by({
            'following_id': follower_id,
            'follower_id': user_id
        })

        if already_following:
            return "Already following"

        self.repo.insert({
            'follower_id': user_id,
            'following_id': follower_id,
        })

        payload = { 'operation': 'increment', 'user_id': user_id }

        self.bus.publish_event('war_queue', 'FOLLOW_COUNT', payload)
        self.bus.publish_event('fury_queue', 'UPDATE_FEED', { **payload, 'following_id': follower_id })

        return "Now following"

    def unfollow(self, user_id, follower_id):
        existing = self.repo.find_by({
            'following_id': follower_id,
            'follower_id': user_id
        })

        if not existing:
            return "Not following"

        self.repo.delete_by({
            'following_id': follower_id,
            'follower_id': user_id,
        })

        payload = { 'operation': 'decrement', 'user_id': user_id }

        self.bus.publish_event('war_queue', 'FOLLOW_COUNT', payload)
        self.bus.publish_event('fury_queue', 'UPDATE_FEED', { **payload, 'following_id': follower_id })

        return "Unfollowed"

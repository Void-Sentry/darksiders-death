from infrastructure.database.repositories import follower_repository
from application.services import follow_service
from infrastructure.bus import bus_client
import pytest

class TestFollowService:
    @pytest.fixture
    def service(self, monkeypatch):
        service = follow_service

        self.mock_repo = {
            'find_by': lambda *args, **kwargs: None,
            'insert': lambda *args, **kwargs: None,
            'delete_by': lambda *args, **kwargs: None
        }

        self.mock_bus = {
            'publish_event': lambda *args, **kwargs: None
        }

        monkeypatch.setattr(follower_repository, 'find_by', self.mock_repo['find_by'])
        monkeypatch.setattr(follower_repository, 'insert', self.mock_repo['insert'])
        monkeypatch.setattr(follower_repository, 'delete_by', self.mock_repo['delete_by'])
        monkeypatch.setattr(bus_client, 'publish_event', self.mock_bus['publish_event'])
        
        return service

    def test_following_empty(self, service):
        self.mock_repo['find_by'] = lambda *args, **kwargs: []
        
        result = service.following('user1', 1, 10)
        assert result == []

    def test_following_with_data(self, service):
        self.mock_repo['find_by'] = lambda *args, **kwargs: [
            {'follower_id': 'user1', 'following_id': 'user2'},
            {'follower_id': 'user1', 'following_id': 'user3'}
        ]
        
        self.mock_bus['publish_event'] = lambda *args, **kwargs: [
            {'userId': 'user2', 'name': 'User 2'},
            {'userId': 'user3', 'name': 'User 3'}
        ]
        
        result = service.following('user1', 1, 10)
        assert len(result) == 2
        assert all(user['isFollowing'] for user in result)

    def test_followers(self, service):
        expected = [{'follower_id': 'user1', 'following_id': 'user2'}]
        self.mock_repo['find_by'] = lambda *args, **kwargs: expected
        
        result = service.followers('user2')
        assert result == expected

    def test_search(self, service):
        self.mock_bus['publish_event'] = lambda *args, **kwargs: [
            {'userId': 'user2', 'displayName': 'User Two'},
            {'userId': 'user3', 'displayName': 'User Three'}
        ]
        
        self.mock_repo['find_by'] = lambda *args, **kwargs: [
            {'follower_id': 'user1', 'following_id': 'user2'}
        ]
        
        result = service.search('User', 'user1')
        assert len(result) == 2
        assert result[0]['isFollowing'] is True
        assert result[1]['isFollowing'] is False

    def test_follow_missing_follower_id(self, service):
        result = service.follow('user1', None)
        assert result == "Follower ID is missing"

    def test_follow_profile_not_found(self, service):
        self.mock_bus['publish_event'] = lambda *args, **kwargs: {
            'message': 'Profile not found'
        }
        
        result = service.follow('user1', 'user2')
        assert result == "Profile not found"

    def test_follow_already_following(self, service):
        self.mock_bus['publish_event'] = lambda *args, **kwargs: {}
        self.mock_repo['find_by'] = lambda *args, **kwargs: [
            {'follower_id': 'user1', 'following_id': 'user2'}
        ]
        
        result = service.follow('user1', 'user2')
        assert result == "Already following"

    def test_follow_success(self, service):
        self.mock_bus['publish_event'] = lambda *args, **kwargs: {}
        self.mock_repo['find_by'] = lambda *args, **kwargs: []
        
        result = service.follow('user1', 'user2')
        assert result == "Now following"

    def test_unfollow_not_following(self, service):
        self.mock_repo['find_by'] = lambda *args, **kwargs: []
        
        result = service.unfollow('user1', 'user2')
        assert result == "Not following"

    def test_unfollow_success(self, service):
        self.mock_repo['find_by'] = lambda *args, **kwargs: [
            {'follower_id': 'user1', 'following_id': 'user2'}
        ]
        
        result = service.unfollow('user1', 'user2')
        assert result == "Unfollowed"
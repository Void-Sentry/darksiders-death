import pytest
from infrastructure.database.repositories import follower_repository
from application.services import recommendation_service
from infrastructure.cache import cache_client
from infrastructure.bus import bus_client
from datetime import datetime
import uuid
import os

class TestRecommendationService:
    @pytest.fixture
    def service(self, monkeypatch):
        service = recommendation_service

        self.mock_repo = {
            'find_by': lambda *args, **kwargs: None
        }

        self.mock_cache = {
            'incr': lambda *args, **kwargs: 1,
            'delete': lambda *args, **kwargs: None,
            'zadd': lambda *args, **kwargs: None,
            'keys': lambda *args, **kwargs: [],
            'zcard': lambda *args, **kwargs: 0,
            'get': lambda *args, **kwargs: None
        }

        self.mock_bus = {
            'publish_event': lambda *args, **kwargs: None
        }

        self.mock_env = {
            'FOLLOWERS_PER_USER': '5',
            'USERS_PER_GROUP': '10',
            'BUS_QUEUE': 'recommendations_queue'
        }

        monkeypatch.setattr(follower_repository, 'find_by', self.mock_repo['find_by'])
        monkeypatch.setattr(cache_client, 'incr', self.mock_cache['incr'])
        monkeypatch.setattr(cache_client, 'delete', self.mock_cache['delete'])
        monkeypatch.setattr(cache_client, 'zadd', self.mock_cache['zadd'])
        monkeypatch.setattr(cache_client, 'keys', self.mock_cache['keys'])
        monkeypatch.setattr(cache_client, 'zcard', self.mock_cache['zcard'])
        monkeypatch.setattr(cache_client, 'get', self.mock_cache['get'])
        monkeypatch.setattr(bus_client, 'publish_event', self.mock_bus['publish_event'])
        monkeypatch.setattr(os, 'getenv', lambda key: self.mock_env.get(key))
        
        return service

    def test_create_user_key(self, service):
        user_id = "user123"
        result = service._create_user_key(user_id)
        assert result == f"users:recommendations:counting:{user_id}"

    def test_create_group_key(self, service):
        result = service._create_group_key()
        assert "users:recommendations:groups:" in result
        assert "_" in result

    def test_increment_user_follow_count(self, service):
        key = "test_key"
        self.mock_cache['incr'] = lambda *args, **kwargs: 2
        result = service._increment_user_follow_count(key)
        assert result == 2

    def test_reset_user_follow_count(self, service):
        key = "test_key"
        called = False
        def mock_delete(*args, **kwargs):
            nonlocal called
            called = True
            return None
        
        self.mock_cache['delete'] = mock_delete
        service._reset_user_follow_count(key)
        assert called is True

    def test_add_user_to_group(self, service):
        group_id = "group123"
        user_id = "user123"
        called = False
        
        def mock_zadd(*args, **kwargs):
            nonlocal called
            called = True
            return None
        
        self.mock_cache['zadd'] = mock_zadd
        service._add_user_to_group(group_id, user_id)
        assert called is True

    def test_check_user_requirements_true(self, service):
        self.mock_env['FOLLOWERS_PER_USER'] = '5'
        assert service._check_user_requirements(5) is True

    def test_check_user_requirements_false(self, service):
        self.mock_env['FOLLOWERS_PER_USER'] = '5'
        assert service._check_user_requirements(4) is False

    def test_get_last_group_no_groups(self, service):
        self.mock_cache['keys'] = lambda *args, **kwargs: []
        result = service._get_last_group()
        assert result is None

    def test_get_last_group_with_groups(self, service):
        test_keys = [
            "users:recommendations:groups:abc_1000",
            "users:recommendations:groups:def_2000",
            "users:recommendations:groups:ghi_1500"
        ]
        self.mock_cache['keys'] = lambda *args, **kwargs: test_keys
        result = service._get_last_group()
        assert result == "users:recommendations:groups:def_2000"

    def test_check_group_requirements_true(self, service):
        group_id = "group123"
        self.mock_cache['zcard'] = lambda *args, **kwargs: 10
        self.mock_env['USERS_PER_GROUP'] = '10'
        assert service._check_group_requirements(group_id) is True

    def test_check_group_requirements_false(self, service):
        group_id = "group123"
        self.mock_cache['zcard'] = lambda *args, **kwargs: 9
        self.mock_env['USERS_PER_GROUP'] = '10'
        assert service._check_group_requirements(group_id) is False

    def test_get_recommendations_from_cache(self, service):
        expected = [{'userId': '123', 'name': 'Test User'}]
        self.mock_cache['get'] = lambda *args, **kwargs: expected
        result = service.get_recommendations("user123")
        assert result == expected

    def test_get_recommendations_from_hottest(self, service):
        test_ids = ["user1", "user2"]
        test_profiles = [
            {'userId': 'user1', 'name': 'User 1'},
            {'userId': 'user2', 'name': 'User 2'}
        ]
        
        self.mock_bus['publish_event'] = lambda *args, **kwargs: (
            test_ids if args[1] == 'MOST_FOLLOWED' else test_profiles
        )
        
        self.mock_repo['find_by'] = lambda *args, **kwargs: [
            {'follower_id': 'current_user', 'following_id': 'user1'}
        ]
        
        result = service.get_recommendations("current_user")
        assert len(result) == 2
        assert result[0]['isFollowing'] is True
        assert result[1]['isFollowing'] is False

    def test_run_first_increment(self, service):
        user_id = "user123"
        self.mock_cache['incr'] = lambda *args, **kwargs: 1
        self.mock_env['FOLLOWERS_PER_USER'] = '5'

        result = service.run(user_id)
        assert result is None

    def test_run_reaches_user_limit_but_not_group(self, service):
        user_id = "user123"
        group_key = "existing_group_1000"
        
        self.mock_cache['incr'] = lambda *args, **kwargs: 5
        self.mock_cache['keys'] = lambda *args, **kwargs: [group_key]
        self.mock_cache['zcard'] = lambda *args, **kwargs: 8
        self.mock_env['FOLLOWERS_PER_USER'] = '5'
        self.mock_env['USERS_PER_GROUP'] = '10'
        
        zadd_called = False
        def mock_zadd(*args, **kwargs):
            nonlocal zadd_called
            zadd_called = True
            return None
        
        self.mock_cache['zadd'] = mock_zadd
        
        result = service.run(user_id)
        assert zadd_called is True
        assert result is None

    def test_run_creates_new_group(self, service):
        user_id = "user123"
        
        self.mock_cache['incr'] = lambda *args, **kwargs: 5
        self.mock_cache['keys'] = lambda *args, **kwargs: ["existing_group_1000"]
        self.mock_cache['zcard'] = lambda *args, **kwargs: 10
        self.mock_env['FOLLOWERS_PER_USER'] = '5'
        self.mock_env['USERS_PER_GROUP'] = '10'
        
        bus_called = False
        def mock_publish(*args, **kwargs):
            nonlocal bus_called
            bus_called = True
            return None
        
        self.mock_bus['publish_event'] = mock_publish
        
        zadd_called = False
        def mock_zadd(*args, **kwargs):
            nonlocal zadd_called
            zadd_called = True
            return None
        
        self.mock_cache['zadd'] = mock_zadd
        
        result = service.run(user_id)
        assert bus_called is True
        assert zadd_called is True
        assert result is None
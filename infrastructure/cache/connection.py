import threading
import redis
import os

class RedisSingleton:
    _instance = None
    _client = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(RedisSingleton, cls).__new__(cls)
                    cls._client = redis.Redis(
                        host=os.getenv('CACHE_HOST', 'localhost'),
                        port=int(os.getenv('CACHE_PORT', 6379)),
                        db=int(os.getenv('CACHE_DB', 0)),
                        decode_responses=True
                    )
                    try:
                        cls._client.ping()
                        print("Redis connection established successfully")
                    except redis.ConnectionError as e:
                        print(f"Failed to connect to Redis: {e}")
                        raise
        return cls._instance

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls()
        return cls._client

    @classmethod
    def close_connection(cls):
        with cls._lock:
            if cls._client:
                cls._client.close()
                cls._client = None
            cls._instance = None

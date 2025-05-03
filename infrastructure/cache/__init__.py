from .connection import RedisSingleton

cache_client = RedisSingleton.get_client()

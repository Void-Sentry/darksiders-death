from infrastructure.bus import bus_client as bus
from application.services import follow_service

@bus.register_handler("FOLLOWERS")
def followers(payload, ch):
    return follow_service.followers(payload['user_id'])

@bus.register_handler("FOLLOWING")
def following(payload, ch):
    return follow_service.following(payload['user_id'])

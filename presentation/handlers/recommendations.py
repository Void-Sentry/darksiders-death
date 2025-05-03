from infrastructure.cache import cache_client as cache
from infrastructure.bus import bus_client as bus
from application.services import follow_service

@bus.register_handler("PROCESS_RECOMMENDATIONS")
def recommendation_handler(payload, ch):
    users = [member.decode('utf-8') for member in cache.zrange(payload, 0, -1, withscores=False)]

    for user_id in users:
        acc = {}

        direct_friends = follow_service.following(user_id)
        direct_friend_ids = {f['following_id'] for f in direct_friends}

        for friend in direct_friend_ids:
            friends_of_friend = follow_service.following(friend)
            for fof in friends_of_friend:
                fof_id = fof['following_id']

                if fof_id == user_id or fof_id in direct_friend_ids:
                    continue

                acc[fof_id] = acc.get(fof_id, 0) + 1

        sorted_recommendations = sorted(acc.items(), key=lambda x: x[1], reverse=True)
        recommended_user_ids = [user_id for user_id, _ in sorted_recommendations]

        cache.set(f"users:recommendations:results:{user_id}", recommended_user_ids)

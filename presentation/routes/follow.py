from application.services import follow_service, recommendation_service
from ..dtos import FollowPathParams, SearchQueryParams, QueryParams
from ..guards import cookie_required
from flask_pydantic import validate
from flask import jsonify, request
from .content import bp

@bp.route('/search', methods=['GET'])
@cookie_required
@validate()
def search(query: SearchQueryParams):
    user_id = request.user['sub']
    res = follow_service.search(query.displayName, user_id)

    return jsonify({"message": "followers list", "data": res}), 201

@bp.route('/following', methods=['GET'])
@cookie_required
@validate()
def following(query: QueryParams):
    user_id = request.user['sub']
    
    res = follow_service.following(
        user_id,
        query.page,
        query.size,
    )

    return jsonify({"message": "followers list", "data": res}), 201

@bp.route('/<string:follower_id>', methods=['POST'])
@cookie_required
@validate()
def follow(follower_id: str):
    validation = FollowPathParams(follower_id=follower_id)
    user_id = request.user['sub']
    
    message = follow_service.follow(
        user_id,
        validation.follower_id,
    )

    recommendation_service.run(user_id)

    return jsonify({ "message": message }), 201

@bp.route('/<string:follower_id>', methods=['DELETE'])
@cookie_required
@validate()
def unfollow(follower_id: str):
    validation = FollowPathParams(follower_id=follower_id)
    user_id = request.user['sub']
    
    message = follow_service.unfollow(
        user_id,
        validation.follower_id,
    )

    return jsonify({"message": message}), 201

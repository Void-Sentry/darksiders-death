from application.services import recommendation_service
from ..guards import cookie_required
from flask import request, jsonify
from .content import bp

@bp.route('/recommendations', methods=['GET'])
@cookie_required
def recommendation_list():
    user_id = request.user['sub']
    data = recommendation_service.get_recommendations(user_id)

    return jsonify({ "message": "Recommended Followers", "data": data }), 201

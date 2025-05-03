from flask import Blueprint

bp = Blueprint('content', __name__, url_prefix='/follow')

def initialize_routes(app):
    from . import follow, recommendation
    app.register_blueprint(bp)
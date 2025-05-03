from .json_bigint import convert_bigints

def initialize_middlewares(app):
    convert_bigints(app)

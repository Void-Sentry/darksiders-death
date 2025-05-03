from flask import Response
import json

def stringify_bigints(obj):
    if isinstance(obj, dict):
        return {k: stringify_bigints(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [stringify_bigints(v) for v in obj]
    elif isinstance(obj, int):
        if abs(obj) > 9007199254740991:
            return str(obj)
        else:
            return obj
    else:
        return obj

def convert_bigints(app):
    @app.after_request
    def _convert(response: Response):
        if response.content_type == 'application/json' and response.data:
            try:
                data = json.loads(response.get_data())
                transformed = stringify_bigints(data)
                response.set_data(json.dumps(transformed))
            except Exception as e:
                app.logger.warning(f"[BigInt Middleware] Erro ao converter BigInt: {e}")
        return response

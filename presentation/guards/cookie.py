from infrastructure.cache import cache_client
from flask import request, jsonify
from functools import wraps
from jwt import algorithms
import requests
import jwt
import os

def fetch_jwks_with_headers():
    response = requests.get(
        os.getenv('JWKS_URI'),
        headers={ "Host": os.getenv('EXTERNAL_DOMAIN') }
    )
    response.raise_for_status()
    return response.json()

def get_signing_key_from_kid(kid: str):
    jwks = fetch_jwks_with_headers()
    for key in jwks["keys"]:
        if key["kid"] == kid:
            return algorithms.RSAAlgorithm.from_jwk(key)
    raise Exception("Matching JWK not found")

def cookie_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.cookies.get('sessionId')
        if not session_id:
            return jsonify({"message": "Session cookie missing"}), 401

        try:
            redis_key = f"users:sessions:{session_id}"

            if not cache_client.exists(redis_key):
                return jsonify({"message": "Invalid or expired session"}), 401

            token = cache_client.get(redis_key)
            if not token:
                return jsonify({"message": "Authentication token missing in session"}), 401

            unverified_header = jwt.get_unverified_header(token)
            signing_key = get_signing_key_from_kid(unverified_header["kid"])

            decoded = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=os.getenv('AUDIENCE'),
                issuer=os.getenv('ISSUER'),
            )

            request.user = decoded
            request.session_id = session_id

            return f(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            cache_client.delete(redis_key)
            return jsonify({"message": "Session expired"}), 401

        except jwt.InvalidTokenError as e:
            return jsonify({"message": f"Invalid token: {str(e)}"}), 401

        except Exception as e:
            print(f"Internal error: {str(e)}")
            return jsonify({"message": "Authentication error"}), 500

    return decorated
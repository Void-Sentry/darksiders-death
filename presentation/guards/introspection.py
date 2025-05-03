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


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"message": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ")[1]

        try:
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
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"message": f"Invalid token: {str(e)}"}), 401
        except Exception as e:
            return jsonify({"message": f"Key resolution error: {str(e)}"}), 500

    return decorated

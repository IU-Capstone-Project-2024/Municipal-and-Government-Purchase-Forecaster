from flask import Blueprint, request, jsonify, render_template
from functools import wraps
from jwt import decode
from keycloak import KeycloakOpenID
from bidict import bidict
from time import time
from .config import Config

auth_bp = Blueprint('auth', __name__)
keycloak_openid = KeycloakOpenID(server_url=Config.KEYCLOAK_URL,
                                 client_id=Config.CLIENT_ID,
                                 realm_name=Config.REALM_NAME,
                                 client_secret_key=Config.CLIENT_SECRET_KEY)

tokens = {}
sessions = bidict({})

def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"message": "Token is missing!"}), 401
        if token != Config.AUTHORIZATION_TOKEN:
            return jsonify({"message": "Token is invalid!"}), 401
        return f(*args, **kwargs)
    return decorator

@auth_bp.route('/authenticate')
def authenticate():
    if "code" in request.args:
        code = request.args.get('code')
        current_state = request.args.get('state')
        access_token = keycloak_openid.token(
            grant_type='authorization_code',
            code=code,
            redirect_uri="http://127.0.0.1:9111/authenticate")
        user_id = sessions.inverse[current_state]
        tokens[user_id] = access_token
        del sessions.inverse[current_state]
        return render_template('success_page.html')
    return render_template('fail_page.html')

@auth_bp.route('/token/<int:user_id>',  methods=['GET'])
@token_required
def get_token(user_id):
    if user_id in tokens:
        return jsonify(tokens[user_id]), 200
    return jsonify({"message": "Token not found"}), 404

@auth_bp.route('/token/<int:user_id>', methods=['DELETE'])
@token_required
def delete_token(user_id):
    if user_id in tokens:
        del tokens[user_id]
        return '', 204
    return jsonify({"message": "Token not found"}), 404

@auth_bp.route('/token/<int:user_id>/expired', methods=['GET'])
@token_required
def check_token_expired(user_id):
    if user_id in tokens:
        access_token = tokens[user_id]['access_token']
        decoded_access_tkn = decode(access_token, options={"verify_signature": False})
        if decoded_access_tkn["exp"] - time() < 0:
            return jsonify({'expired': True}), 200
        else:
            return jsonify({'expired': False}), 200
    return jsonify({"message": "Token not found"}), 404

@auth_bp.route('/token/<int:user_id>/refresh-token-expired', methods=['GET'])
@token_required
def check_refresh_token_expired(user_id):
    if user_id in tokens:
        refresh_token = tokens[user_id]['refresh_token']
        decoded_refresh_tkn = decode(refresh_token, options={"verify_signature": False})
        if decoded_refresh_tkn["exp"] - time() < 0:
            return jsonify({'expired': True}), 200
        else:
            return jsonify({'expired': False}), 200
    return jsonify({"message": "Token not found"}), 404

@auth_bp.route('/token/<int:user_id>/refresh', methods=['POST'])
@token_required
def refresh_token(user_id):
    if user_id in tokens:
        tokens[user_id] = keycloak_openid.refresh_token(tokens[user_id]['refresh_token'])
        return '', 204
    return jsonify({"message": "Token not found"}), 404


@auth_bp.route('/store-session', methods=['POST'])
@token_required
def store_session():
    try:
        data = request.get_json()
        sessions[data['user_id']] = str(data["state"])
        return '', 204
    except Exception as e:
        return jsonify({"message": str(e)}), 400


@auth_bp.route('/get-userids', methods=['GET'])
@token_required
def get_user_ids():
    return jsonify({"id_list": list(tokens.keys())}), 200


@auth_bp.route('/token/<int:user_id>/roles', methods=['GET'])
@token_required
def get_token_roles(user_id):
    if user_id in tokens:
        access_token = tokens[user_id]['access_token']
        decoded_access_tkn = decode(access_token, options={"verify_signature": False})
        return jsonify({'roles': decoded_access_tkn["realm_access"]["roles"]}), 200
    return jsonify({"message": "Token not found"}), 404

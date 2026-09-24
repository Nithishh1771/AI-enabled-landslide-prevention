from flask import Blueprint, jsonify, session
map_bp = Blueprint("map_routes", __name__, url_prefix="/map-api")

@map_bp.get("/health")
def health():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "Authentication required."}), 401
    return jsonify({"success": True, "data": {"map_service": "ready"}})

from flask import Blueprint
from flask import Response, jsonify, request
import json
from utils import Config

# 引入数据库表定义
from user_manager.medols import User

user_route = Blueprint(name="user_manager", import_name=__name__, url_prefix="/user")


@user_route.route("health", methods=["GET"])
def user_():
    return Response(
        status=200,
        response=json.dumps({
                "message": "User Manager"
            }),
        mimetype="application/json"
    )


@user_route.route("", methods=["GET"])
def get_users():
    users = User.query.all()

    data = []
    for u in users:
        data.append(
            {
                "id": u.id,
                "username": u.username,
                "email": u.email
            }
        )

    return jsonify(data)


@user_route.route("", methods=["POST"])
def add_user():
    user_data = request.get_json()
    user = User(username=user_data["username"], email=user_data["email"])
    Config.database.session.add(user)
    Config.database.session.commit()
    return jsonify(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    )


@user_route.route("", methods=["PUT"])
def update_user():
    user_data = request.get_json()

    # 获取用户
    user = User.query.get(user_data["id"])
    if "username" in user_data:
        user.username = user_data["username"]
    if "email" in user_data:
        user.email = user_data["email"]

    Config.database.session.commit()
    return jsonify(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    )


@user_route.route("/<int:userId>", methods=["DELETE"])
def delete_user(userId):
    """
    删除用户
    :param userId: 用户ID
    :return:
    """
    user = User.query.get(userId)
    if user is None:
        return jsonify(
            {
                "message": "User not found"
            }
        ), 404

    Config.database.session.delete(user)
    Config.database.session.commit()
    return jsonify(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    ), 200

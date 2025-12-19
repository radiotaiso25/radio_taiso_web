# =============================================================
# login_routes.py
#
# 役割：
#   - /login : ログイン
#   - /guest : ゲスト利用
#   - /logout : ログアウト
#
# ほかの処理は server.py と result_routes.py が担当
# =============================================================

from flask import Blueprint, render_template, request, redirect, url_for, session

auth_bp = Blueprint("auth", __name__)

# -------------------------------------------------------------
# /login
# -------------------------------------------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        if not user_id:
            return render_template("login.html", error="ユーザー名を入力してください。")

        session.clear()
        session["user_id"] = user_id
        return redirect(url_for("chat.chat_page"))

    return render_template("login.html")

# -------------------------------------------------------------
# /guest
# -------------------------------------------------------------
@auth_bp.route("/guest", methods=["POST"])
def guest_login():
    session.clear()
    session["guest"] = True
    print("🚪 ゲストログイン")
    return redirect(url_for("chat.chat_page"))

# -------------------------------------------------------------
# /logout
# -------------------------------------------------------------
@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

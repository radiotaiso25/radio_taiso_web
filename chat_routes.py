from flask import Blueprint, render_template

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat")
def chat_page():
    # web/chat.html を表示
    return render_template("web/chat.html")

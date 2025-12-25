# chat_routes.py
# GPTチャットページのルーティングとAPI処理を担当

from flask import Blueprint, render_template, request, session, jsonify
import os
import openai

chat_bp = Blueprint("chat", __name__)

# Render → Environment Variables に OPENAI_API_KEY を入れている前提
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------------------------------------
# /chat 画面表示
# -------------------------------------------------------------
@chat_bp.route("/chat")
def chat_page():
    # 未ログインならログインへ
    if "user_id" not in session and "guest" not in session:
        return render_template("login.html", error="ログインしてください")

    return render_template("chat.html")


# -------------------------------------------------------------
# /chat_api  GPTへ問い合わせるAPI
# -------------------------------------------------------------
@chat_bp.route("/chat_api", methods=["POST"])
def chat_api():
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"error": "メッセージが空です"}), 400

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは優しい体操コーチAIです。"},
                {"role": "user", "content": user_message}
            ]
        )

        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
        print("チャットAPI エラー:", e)
        return jsonify({"error": str(e)}), 500


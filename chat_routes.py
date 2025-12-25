# chat_routes.py
# GPTチャットページのルーティングとAPI処理を担当

from openai import OpenAI
import os
import tempfile
from flask import Blueprint, render_template, request, session, jsonify

chat_bp = Blueprint("chat", __name__)

# OpenAI クライアント（新SDK）
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------------------------
# /chat 画面表示
# -------------------------------------------------------------
@chat_bp.route("/chat")
def chat_page():
    if "user_id" not in session and "guest" not in session:
        return render_template("login.html", error="ログインしてください")
    return render_template("chat.html")

# -------------------------------------------------------------
# /chat_api  テキスト → GPT
# -------------------------------------------------------------
@chat_bp.route("/chat_api", methods=["POST"])
def chat_api():
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"error": "メッセージが空です"}), 400

        response = client.chat.completions.create(
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

# -------------------------------------------------------------
# /voice_api  音声 → テキスト（Whisper）
# -------------------------------------------------------------
@chat_bp.route("/voice_api", methods=["POST"])
def voice_api():
    try:
        if "audio" not in request.files:
            return jsonify({"error": "audio file not found"}), 400

        audio_file = request.files["audio"]

        # Render対策：一時ファイルに保存
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            audio_file.save(tmp.name)

            transcript = client.audio.transcriptions.create(
                file=open(tmp.name, "rb"),
                model="whisper-1"
            )

        return jsonify({"text": transcript.text})

    except Exception as e:
        print("音声認識エラー:", e)
        return jsonify({"error": str(e)}), 500

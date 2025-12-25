# chat_routes.py
# GPTチャットページのルーティングとAPI処理を担当

import tempfile
from openai import OpenAI

client = OpenAI()

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
                model="gpt-4o-mini-transcribe"
            )

        return jsonify({
            "text": transcript.text
        })

    except Exception as e:
        print("音声認識エラー:", e)
        return jsonify({"error": str(e)}), 500

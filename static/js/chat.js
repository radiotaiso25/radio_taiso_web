// static/js/chat.js
// WebSocket完全撤去版 / HTTP + Whisper API 対応

var errorTextArea = document.getElementById("errorTextArea");
var answerTextArea = document.getElementById("answerTextArea");
var messageTextArea = document.getElementById("messageTextArea");

// ================================
// Vue（録音ボタンまわり）
// ================================
new Vue({
    el: '#app',
    data: {
        status: 'init',
        recorder: null,
        audioData: []
    },
    methods: {
        startRecording() {
            this.status = 'recording';
            this.audioData = [];
            this.recorder.start();
        },
        stopRecording() {
            this.recorder.stop();
            this.status = 'ready';
        }
    },
    mounted() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                this.recorder = new MediaRecorder(stream);

                this.recorder.addEventListener('dataavailable', e => {
                    this.audioData.push(e.data);
                });

                this.recorder.addEventListener('stop', async () => {
                    const audioBlob = new Blob(this.audioData, { type: "audio/wav" });

                    try {
                        // ① Whisper API に音声送信
                        const text = await sendAudioBlob(audioBlob);

                        // ② 認識結果を入力欄に反映
                        document.getElementById("input").value = text;

                        // ③ そのままチャット送信
                        await sendMessage();

                    } catch (e) {
                        console.error(e);
                        answerTextArea.value = "音声認識に失敗しました";
                    }
                });

                this.status = 'ready';
            })
            .catch(err => {
                console.error(err);
                errorTextArea.value = "マイクの使用が許可されていません";
            });
    }
});

// ================================
// 音声 → Whisper API
// ================================
async function sendAudioBlob(audioBlob) {
    const formData = new FormData();
    formData.append("audio", audioBlob, "voice.wav");

    const res = await fetch("/voice_api", {
        method: "POST",
        body: formData
    });

    if (!res.ok) {
        throw new Error("voice api error");
    }

    const data = await res.json();
    return data.text;
}

// ================================
// テキストチャット（HTTP）
// ================================
async function sendMessage() {
    const messageInput = document.getElementById("input");
    const text = messageInput.value.trim();
    if (!text) return;

    // ユーザー発言表示
    messageTextArea.value += text + "\n";
    messageInput.value = "";

    // ★ 体操開始トリガー判定（既存仕様そのまま）
    const triggerWords = [
        "体操したい", "対象したい", "体操する", "対象する",
        "ラジオ体操したい", "ラジオ対象したい",
        "ラジオ体操する", "ラジオ対象する",
        "やってみる", "やってみたい"
    ];
    const hit = triggerWords.some(w => text.includes(w));

    if (hit) {
        const now = new Date().toISOString();
        localStorage.setItem("taiso_trigger_text", text);
        localStorage.setItem("taiso_trigger_time", now);
        setTimeout(() => {
            window.location.href = "/record";
        }, 800);
        return;
    }

    try {
        const res = await fetch("/chat_api", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                user_id: CURRENT_USER_ID
            })
        });

        if (!res.ok) {
            throw new Error("chat api error");
        }

        const data = await res.json();
        answerTextArea.value = data.reply;

    } catch (e) {
        console.error(e);
        answerTextArea.value = "エラーが発生しました";
    }
}

// ================================
// リンクトリガー（既存）
// ================================
function onTaisoLinkClick(event) {
    const now = new Date().toISOString();
    localStorage.setItem("taiso_trigger_text", "link_click");
    localStorage.setItem("taiso_trigger_time", now);
}

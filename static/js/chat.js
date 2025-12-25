// static/js/chat.js

// グローバル変数（HTML 側で CURRENT_USER_ID は定義されている前提）
var webSocket; //ウェブソケット

var errorTextArea = document.getElementById("errorTextArea");
var answerTextArea = document.getElementById("answerTextArea");
var messageTextArea = document.getElementById("messageTextArea");

// ===== Vue（録音ボタンまわり） =====
new Vue({
    el: '#app',
    data: {
        status: 'init',
        recorder: null,
        audioData: [],
        audioExtension: ''
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
        },
        getExtension(audioType) {
            let extension = 'wav';
            const matches = audioType.match(/audio\/([^;]+)/);
            if (matches) {
                extension = matches[1];
            }
            return '.' + extension;
        }
    },
    mounted() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                this.recorder = new MediaRecorder(stream);
                this.recorder.addEventListener('dataavailable', e => {
                    this.audioData.push(e.data);
                    this.audioExtension = this.getExtension(e.data.type);
                });
                this.recorder.addEventListener('stop', () => {
                    const audioBlob = new Blob(this.audioData);
                    // 音声を Whisper サーバに使ってもらうトリガー
                    sendAudio();

                    const url = URL.createObjectURL(audioBlob);
                    let a = document.createElement('a');
                    a.href = url;
                    a.download = "sample" + this.audioExtension;
                    document.body.appendChild(a);
                    a.click();
                });
                this.status = 'ready';
            });
    }
});

// ===== WebSocket 関連 =====

function connect() {
    webSocket = new WebSocket("ws://localhost:8001"); // インスタンスを作り、サーバと接続

    webSocket.onopen = function (message) {
        errorTextArea.value += "接続中\n";
        // 最初に「この接続は誰のものか」を Whisper に教える
        webSocket.send("__USERID__:" + CURRENT_USER_ID);
    };

    webSocket.onclose = function (message) {
        errorTextArea.value += "接続停止\n";
    };

    webSocket.onerror = function (message) {
        errorTextArea.value += "error...\n";
    };

    webSocket.onmessage = function (message) {
        // ★ Whisper から「体操に行って」と合図が来たとき
        if (message.data === "__GO_RECORD__") {
            const now = new Date().toISOString();
            localStorage.setItem("taiso_trigger_text", "voice");
            localStorage.setItem("taiso_trigger_time", now);
            window.location.href = "/record";
            return;
        }

        if (message.data.includes('.mp4') && message.data.includes('file:')) {
            const urls = message.data.split(' ');
            localStorage.setItem('url_1', urls[0]);
            localStorage.setItem('url_2', urls[1]);
            localStorage.setItem('url_3', urls[2]);
        }
        else if (message.data.includes('.mp4')) {
            const names = message.data.split(' ');
            localStorage.setItem('name_1', names[0]);
            localStorage.setItem('name_2', names[1]);
            localStorage.setItem('name_3', names[2]);
        }
        else {
            if (message.data.substring(0, 1) == "0") {
                // ０はユーザで、１はAIです。
                messageTextArea.value = message.data.substring(1);
            }
            else if (message.data.substring(0, 1) == "1") {
                let messag = message.data.replaceAll('。', '。\n');
                let messa = messag.replaceAll('？', '？\n');
                answerTextArea.value = messa.substring(1);
                console.log(messa);
            }
        }
    };
}

function sendAudio() {
    // 「onsei」という合図を送る
    const Hello = "onsei";
    webSocket.send(Hello);
    console.log("send audio trigger");
}

async function sendMessage() {
    const messageInput = document.getElementById("input");
    const text = messageInput.value.trim();
    if (!text) return;

    // 自分の吹き出し表示
    messageTextArea.value += text + "\n";
    messageInput.value = "";

    // ★ 体操開始トリガー判定（これはそのまま）
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

    // ===== HTTPでサーバへ送信 =====
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
            throw new Error("Server error");
        }

        const data = await res.json();
        answerTextArea.value = data.reply;

    } catch (e) {
        console.error(e);
        answerTextArea.value = "エラーが発生しました";
    }
}


function onTaisoLinkClick(event) {
    const now = new Date().toISOString();
    localStorage.setItem("taiso_trigger_text", "link_click");
    localStorage.setItem("taiso_trigger_time", now);
}

function disconnect() {
    if (webSocket) {
        webSocket.close();
    }
}

// ページ読み込み時に自動で接続
window.addEventListener('load', connect);

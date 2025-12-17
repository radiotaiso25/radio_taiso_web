const WIDTH = 640;
const HEIGHT = 480;
const gameCanvas = document.getElementById('gameCanvas');
const ctx = gameCanvas.getContext('2d'); // 2D描画コンテキスト
const countdownOverlay = document.getElementById('countdown');
const gameOverScreen = document.getElementById('gameOverScreen');
const finalScoreDisplay = document.getElementById('finalScore');
const retryButton = document.getElementById('retryButton');
const quitButton = document.getElementById('quitButton');

// Canvasのサイズを設定
gameCanvas.width = WIDTH;
gameCanvas.height = HEIGHT;

let video = document.createElement('video'); // カメラ映像用のvideo要素
video.autoplay = true;
video.playsInline = true; // iOSでの自動再生のために必要

let hands; // MediaPipe Handsインスタンス
let results; // MediaPipeの検出結果

let fallingObjects = [];
let score = 0;
let lastFrameTime = 0;
let gameDuration = 30; // ゲーム時間（秒）
let gameStartTime = 0;
let gameRunning = false;

// アセットの読み込み
const itemImage = new Image();
itemImage.src = 'item.png'; // 落下物の画像
const catchSound = new Audio('catch.mp3'); // キャッチ音

// ===== スクリプトの読み込み確認用ログ =====
console.log("Script loaded successfully.");
// ===========================================

itemImage.onload = () => {
    // 画像が読み込まれたら準備完了
    console.log("item.png loaded");
    initGame(); // ゲームの初期化を開始
};
// エラーハンドリング
itemImage.onerror = () => {
    console.error("Failed to load item.png. Make sure the file exists in the same directory.");
};
catchSound.onerror = () => {
    console.error("Failed to load catch.mp3. Make sure the file exists in the same directory.");
};

// ===========================================
// MediaPipe Handsの初期化
// ===========================================
function initMediaPipe() {
    console.log("initMediaPipe called.");
    hands = new Hands({locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
    }});

    hands.setOptions({
        maxNumHands: 2,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.5
    });

    hands.onResults(onResults); // 結果が利用可能になったときに呼び出されるコールバック

    hands.initialize().then(() => {
        console.log("MediaPipe Hands initialized successfully.");
    }).catch(error => {
        console.error("Failed to initialize MediaPipe Hands:", error);
        alert("手の検出機能を初期化できませんでした。ブラウザコンソールを確認してください。");
    });
}

// ===========================================
// カメラの初期化とMediaPipeへのフィード
// ===========================================
async function setupCamera() {
    console.log("setupCamera called.");
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        await video.play(); // ここはそのまま

        console.log("Camera started successfully. Waiting for video to be ready...");

        // ========== ここから変更 ==========
        // loadedmetadata イベントリスナーを削除し、ポーリングループで readyState を確認
        let checkVideoReady = setInterval(() => {
            // readyState が HAVE_ENOUGH_DATA (4) になったらビデオが再生可能
            if (video.readyState >= 2) { // HAVE_CURRENT_DATA (2) またはそれ以上
                clearInterval(checkVideoReady);
                console.log("Video is ready! Dimensions:", video.videoWidth, video.videoHeight);
                if (!video.videoWidth || !video.videoHeight) {
                    console.warn("Video dimensions still 0 after readyState. This might be an issue.");
                }

                console.log("Starting MediaPipe processing loop...");
                sendVideoToMediaPipeLoop(); // await は不要。ループは非同期で継続するため
                console.log("MediaPipe processing loop started.");

                showCountdown(); // カウントダウンを開始
            } else {
                console.log("Video not ready yet. readyState:", video.readyState);
            }
        }, 100); // 100ミリ秒ごとにチェック
        // ========== ここまで変更 ==========

    } catch (error) {
        console.error('カメラのアクセスに失敗しました:', error);
        alert('カメラのアクセスを許可してください。');
    }
}
// ===========================================
// MediaPipeへのビデオフィードの送信を継続するループ
// ===========================================
async function sendVideoToMediaPipeLoop() {
    console.log("sendVideoToMediaPipeLoop called.");
    console.log("Video dimensions:", video.videoWidth, video.videoHeight);

    if (!video.videoWidth || !video.videoHeight) {
        console.log("Video dimensions not ready yet. Retrying sendVideoToMediaPipeLoop...");
        requestAnimationFrame(sendVideoToMediaPipeLoop);
        return;
    }

    try {
        await hands.send({image: video});
        console.log("hands.send() successful.");
    } catch (error) {
        console.error("Error sending image to MediaPipe:", error);
        // ここでエラーが出ている可能性が高いので、要確認
    }

    // ゲームが実行中、またはカウントダウン中（hiddenクラスがない）、
    // またはゲームオーバー画面が表示されていない（hiddenクラスがある）場合は継続
    // 論理を少し修正して、ゲーム終了画面が出たら確実に停止するようにしました
    if (gameRunning || !countdownOverlay.classList.contains('hidden') || gameOverScreen.classList.contains('hidden') === false) {
        requestAnimationFrame(sendVideoToMediaPipeLoop);
    } else {
        console.log("Stopping MediaPipe processing loop.");
        return;
    }
}


// ===========================================
// MediaPipeからの結果処理
// ===========================================
function onResults(results_mp) {
    // console.log("onResults called. Results received."); // 大量のログになるので注意
    results = results_mp; // グローバル変数に結果を保存
}

// ===========================================
// ゲームオブジェクトクラス
// ===========================================
class FallingObject {
    constructor() {
        this.x = Math.random() * (WIDTH - 40) + 20; // 画面幅内でランダムなX座標
        this.y = 0;
        this.speed = Math.random() * (5 - 2) + 2; // 2から5の間のランダムな速度
        this.radius = 25; // キャッチ判定用
        this.caught = false; // キャッチされたかどうかのフラグ
    }

    fall() {
        this.y += this.speed;
    }

    draw(ctx) {
        // 画像を描画（中心に来るように位置を調整）
        ctx.drawImage(itemImage, this.x - this.radius, this.y - this.radius, this.radius * 2, this.radius * 2);
    }
}

// ===========================================
// キャッチ判定
// ===========================================
function isCatch(obj_x, obj_y, hand_x, hand_y, threshold = 50) {
    const dist = Math.sqrt(Math.pow(obj_x - hand_x, 2) + Math.pow(obj_y - hand_y, 2));
    return dist < threshold;
}

// ===========================================
// ゲームの描画と更新ループ
// ===========================================
function gameLoop(timestamp) {
    if (!gameRunning) {
        console.log("Game loop stopped."); // ゲームが終了したことを示すログ
        return;
    }
    console.log("gameLoop called."); // ゲームループが実行されていることを確認

    const deltaTime = timestamp - lastFrameTime; // 前回のフレームからの経過時間
    lastFrameTime = timestamp;

    // カメラ映像の描画 (左右反転)
    ctx.clearRect(0, 0, WIDTH, HEIGHT); // Canvasをクリア
    ctx.save(); // 現在の状態を保存
    ctx.scale(-1, 1); // X軸で反転 (左右反転)
    ctx.drawImage(video, -WIDTH, 0, WIDTH, HEIGHT); // 反転した状態で描画
    ctx.restore(); // 状態を元に戻す

    // MediaPipeの結果に基づいて手のランドマークを描画
    if (results && results.multiHandLandmarks) {
        // console.log("Hand landmarks detected!"); // 手が検出されたことを確認するログ
        for (const landmarks of results.multiHandLandmarks) {
            const wrist = landmarks[0];
            const indexBase = landmarks[5];
            const pinkyBase = landmarks[17];

            const handX = WIDTH - ((wrist.x + indexBase.x + pinkyBase.x) / 3) * WIDTH;
            const handY = ((wrist.y + indexBase.y + pinkyBase.y) / 3) * HEIGHT;

            // 手の位置に円を描画
            ctx.beginPath();
            ctx.arc(handX, handY, 20, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(0, 0, 255, 0.7)'; // 青色で半透明
            ctx.fill();

            // 落下物とのキャッチ判定
            fallingObjects.forEach(obj => {
                if (!obj.caught && isCatch(obj.x, obj.y, handX, handY)) {
                    score++;
                    catchSound.play();
                    obj.caught = true; // キャッチ済みとしてマーク
                    // キャッチエフェクト
                    ctx.beginPath();
                    ctx.arc(obj.x, obj.y, 30, 0, Math.PI * 2);
                    ctx.fillStyle = 'rgba(255, 255, 0, 0.5)'; // 黄色で半透明
                    ctx.fill();
                }
            });
        }
    }

    // 落下物生成
    if (Math.random() < 0.03) { // フレームごとに確率で生成 (調整可能)
        fallingObjects.push(new FallingObject());
    }

    // 落下物更新と描画
    fallingObjects.forEach(obj => {
        obj.fall();
        obj.draw(ctx);
    });

    // 画面外に出たオブジェクトやキャッチされたオブジェクトを削除
    fallingObjects = fallingObjects.filter(obj => !obj.caught && obj.y < HEIGHT + obj.radius);

    // スコア表示
    ctx.fillStyle = 'black';
    ctx.font = '50px sans-serif';
    ctx.fillText(`Score: ${score}`, 10, 50);

    // 残り時間表示
    const elapsedTime = (timestamp - gameStartTime) / 1000; // 秒に変換
    const remainingTime = Math.max(0, gameDuration - Math.floor(elapsedTime));
    ctx.fillText(`Time: ${remainingTime}`, WIDTH - 180, 50);

    // ゲーム終了判定
    if (remainingTime <= 0) {
        gameRunning = false;
        showEndScreen(score);
        return; // ループを終了
    }

    requestAnimationFrame(gameLoop); // 次のフレームを要求
}

// ===========================================
// カウントダウン表示
// ===========================================
function showCountdown() {
    console.log("showCountdown called. Displaying countdown.");
    countdownOverlay.classList.remove('hidden');
    let count = 3;
    countdownOverlay.textContent = count;

    const timer = setInterval(() => {
        count--;
        if (count > 0) {
            countdownOverlay.textContent = count;
        } else if (count === 0) {
            countdownOverlay.textContent = 'START!';
        } else {
            clearInterval(timer);
            countdownOverlay.classList.add('hidden');
            startGame();
        }
    }, 1000);
}

// ===========================================
// ゲーム開始
// ===========================================
function startGame() {
    console.log("startGame called. Initializing game state.");
    score = 0;
    fallingObjects = [];
    gameStartTime = performance.now(); // ゲーム開始時間を記録
    gameRunning = true;
    lastFrameTime = performance.now(); // 最初のフレーム時間を設定
    // sendVideoToMediaPipeLoop() の呼び出しは setupCamera() の loadeddata イベントリスナーで既に開始されているため、
    // ここで再度呼び出す必要はありません。
    requestAnimationFrame(gameLoop); // ゲームループを開始
}

// ===========================================
// 終了画面表示
// ===========================================
function showEndScreen(finalScore) {
    console.log("showEndScreen called. Final Score:", finalScore);
    gameOverScreen.classList.remove('hidden');
    finalScoreDisplay.textContent = `TOKUTEN: ${finalScore}`;

    retryButton.onclick = () => {
        gameOverScreen.classList.add('hidden');
        showCountdown();
    };

    quitButton.onclick = () => {
        alert('ゲームを終了します。');
        if (video.srcObject) {
            video.srcObject.getTracks().forEach(track => track.stop());
        }
    };
}

// ===========================================
// ゲーム初期化（アセット読み込み後に呼び出される）
// ===========================================
function initGame() {
    console.log("initGame called.");
    initMediaPipe(); // MediaPipeを初期化
    setupCamera();   // カメラを設定
    // カウントダウンの開始は setupCamera の loadeddata イベントリスナー内で実行されるように変更
}
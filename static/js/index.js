// radio_taiso.js

const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const scoreEl = document.getElementById("score");
const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");
const countdownEl = document.getElementById("countdown");

let camera, mediaRecorder;
let recordedChunks = [];
let running = false;
let countingDown = false;
let insideTimer = 0;
let insideBox = false;
let showBox = true; // 枠の表示制御フラグ
const INSIDE_FRAMES = 30;

// 必要に応じて内部解像度も合わせる
canvas.width = 720;
canvas.height = 540;

const steps = [
  { name: "両腕を前から上に上げて背伸びの運動",              duration: 7770  }, // E01
  { name: "腕を振って脚を曲げ伸ばす運動",                      duration: 15540 }, // E02
  { name: "腕を回す運動",                                       duration: 15310 }, // E03
  { name: "胸を反らす運動",                                     duration: 16690 }, // E04
  { name: "体を横にまげる運動",                                 duration: 15850 }, // E05
  { name: "体を前後にまげる運動",                               duration: 15460 }, // E06
  { name: "体をねじる運動",                                     duration: 15000 }, // E07
  { name: "腕を上下にのばす運動",                               duration: 14690 }, // E08
  { name: "体を斜め下にまげ胸をそらす運動",                     duration: 16770 }, // E09
  { name: "体を回す運動",                                       duration: 16540 }, // E10
  { name: "両脚でとぶ運動",                                     duration: 10310 }, // E11
  { name: "腕を振って脚をまげのばす運動（2回目）",             duration: 16380 }, // E12
  { name: "深呼吸の運動",                                       duration: 17310 }, // E13
];

// const steps = [
//   { name: "両腕を前から上に上げて背伸びの運動",              duration: 1000  }, // E01
//   { name: "腕を振って脚を曲げ伸ばす運動",                      duration: 1000 }, // E02
//   { name: "腕を回す運動",                                       duration: 1000 }, // E03
//   { name: "胸を反らす運動",                                     duration: 1000 }, // E04
//   { name: "体を横にまげる運動",                                 duration: 1000 }, // E05
//   { name: "体を前後にまげる運動",                               duration: 1000 }, // E06
//   { name: "体をねじる運動",                                     duration: 1000 }, // E07
//   { name: "腕を上下にのばす運動",                               duration: 1000 }, // E08
//   { name: "体を斜め下にまげ胸をそらす運動",                     duration: 1000 }, // E09
//   { name: "体を回す運動",                                       duration: 1000 }, // E10
//   { name: "両脚でとぶ運動",                                     duration: 1000 }, // E11
//   { name: "腕を振って脚をまげのばす運動（2回目）",             duration: 1000 }, // E12
//   { name: "深呼吸の運動",                                       duration: 1000 }, // E13
// ];

// ===== Pose設定 =====
const pose = new Pose({ locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}` });
pose.setOptions({
  modelComplexity: 0,
  smoothLandmarks: true,
  enableSegmentation: false,
  minDetectionConfidence: 0.5,
  minTrackingConfidence: 0.5,
});

pose.onResults((results) => {
  ctx.save();
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);

  // === 枠の判定＆描画 ===
  if (showBox) {
    const boxX = canvas.width * 0.1;
    const boxY = canvas.height * 0.05;
    const boxW = canvas.width * 0.8;
    const boxH = canvas.height * 0.9;

    if (results.poseLandmarks) {
      const keypoints = [0, 11, 12, 23, 24, 27, 28];
      insideBox = keypoints.every(i => {
        const p = results.poseLandmarks[i];
        return (
          p.visibility > 0.6 &&
          p.x > boxX / canvas.width &&
          p.x < (boxX + boxW) / canvas.width &&
          p.y > boxY / canvas.height &&
          p.y < (boxY + boxH) / canvas.height
        );
      });
    } else {
      insideBox = false;
    }

    // 枠の色を変更
    ctx.strokeStyle = insideBox ? "rgba(0,255,0,0.9)" : "rgba(255,0,0,0.9)";
    ctx.lineWidth = 5;
    ctx.strokeRect(boxX, boxY, boxW, boxH);

    // 枠内で安定 → カウント開始
    if (insideBox && !running && !countingDown) {
      insideTimer++;
      if (insideTimer > INSIDE_FRAMES) {
        insideTimer = 0;
        startCountdown();
      }
    } else {
      insideTimer = 0;
    }
  }
  ctx.restore();
});

// ===== カメラ起動 =====
async function initCamera() {
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  video.srcObject = stream;
  await video.play();
  camera = new Camera(video, {
    onFrame: async () => { await pose.send({ image: video }); },
    width: 720,
    height: 540,
  });
  camera.start();
}

// ===== カウントダウン =====
function startCountdown() {
  if (countingDown || running) return;
  countingDown = true;
  let count = 3;
  countdownEl.textContent = count;

  const timer = setInterval(() => {
    // 💥 カウント中に枠外に出たら中断
    if (!insideBox) {
      clearInterval(timer);
      countingDown = false;
      countdownEl.textContent = ""; // 表示を消す
      insideTimer = 0; // タイマーもリセット
      return; // 最初から
    }

    count--;
    if (count > 0) {
      countdownEl.textContent = count;
    } else if (count === 0) {
      countdownEl.textContent = "スタート！";
    } else {
      clearInterval(timer);
      countdownEl.textContent = "";
      countingDown = false;
      showBox = false; // ← 枠と判定をOFF！
      startRecording();
    }
  }, 1000);
}

function showStep(index) {
  const step = steps[index];
  scoreEl.textContent = step ? `現在: ${step.name}` : "完了！採点中...";
}

// ===== 録画開始 =====
async function startRecording() {
  running = true;
  recordedChunks = [];
  const stream = video.srcObject;
  mediaRecorder = new MediaRecorder(stream, { mimeType: "video/webm" });
  mediaRecorder.ondataavailable = e => {
    if (e.data.size > 0) recordedChunks.push(e.data);
  };
  mediaRecorder.onstop = uploadVideo;
  mediaRecorder.start();

  startBtn.disabled = true;
  stopBtn.disabled = false;
  showStep(0);

  let stepIndex = 0;
  function nextStep() {
    if (!running) return;
    stepIndex++;
    if (stepIndex < steps.length) {
      showStep(stepIndex);
      setTimeout(nextStep, steps[stepIndex].duration);
    } else {
      stopRecording();
    }
  }
  setTimeout(nextStep, steps[0].duration);
}

function stopRecording() {
  running = false;
  stopBtn.disabled = true;
  startBtn.disabled = false;
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
  showStep(-1);
}

async function uploadVideo() {
  const blob = new Blob(recordedChunks, { type: "video/webm" });
  const formData = new FormData();
  formData.append("video", blob, "student_recording.webm");
  scoreEl.textContent = "アップロード中...";

  const res = await fetch("/upload", { method: "POST", body: formData });

  // ✅ FlaskがHTMLを返す場合は、画面遷移にする！
  if (res.redirected) {
    window.location.href = res.url;
    return;
  }

  // エラーハンドリング
  try {
    const result = await res.json();
    scoreEl.innerHTML = `<h3>採点結果</h3><pre>${JSON.stringify(result, null, 2)}</pre>`;
  } catch {
    scoreEl.textContent = "採点結果ページに移動できませんでした。";
  }
}

// ページ読み込み時にカメラ起動
window.onload = initCamera;

// ボタン押下でも録画開始（自動スタートも併用OK）
startBtn.onclick = () => {
  if (!running && !countingDown) {
    insideTimer = 0;          // リセット
    // showBox は true のまま：枠は表示し続ける
    countdownEl.textContent = "";
    startRecording();         // 即スタート
  }
};

// 停止ボタン
stopBtn.onclick = stopRecording;

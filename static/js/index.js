// ===== DOM =====
const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const scoreEl = document.getElementById("score");
const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");
const countdownEl = document.getElementById("countdown");

// ===== 状態 =====
let camera = null;
let running = false;
let countingDown = false;
let insideTimer = 0;
let insideBox = false;
let showBox = true;
let cameraStarted = false;

// ★ landmarks を溜める
let allFrames = [];

const INSIDE_FRAMES = 30;

// 描画サイズ
canvas.width = 720;
canvas.height = 540;

// ===== ステップ =====
const steps = [
  { name: "両腕を前から上に上げて背伸びの運動", duration: 7770 },
  { name: "腕を振って脚を曲げ伸ばす運動", duration: 15540 },
  { name: "腕を回す運動", duration: 15310 },
  { name: "胸を反らす運動", duration: 16690 },
  { name: "体を横にまげる運動", duration: 15850 },
  { name: "体を前後にまげる運動", duration: 15460 },
  { name: "体をねじる運動", duration: 15000 },
  { name: "腕を上下にのばす運動", duration: 14690 },
  { name: "体を斜め下にまげ胸をそらす運動", duration: 16770 },
  { name: "体を回す運動", duration: 16540 },
  { name: "両脚でとぶ運動", duration: 10310 },
  { name: "腕を振って脚をまげのばす運動（2回目）", duration: 16380 },
  { name: "深呼吸の運動", duration: 17310 },
];

// ===== Pose =====
const pose = new Pose({
  locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}`
});

pose.setOptions({
  modelComplexity: 0,
  smoothLandmarks: true,
  minDetectionConfidence: 0.5,
  minTrackingConfidence: 0.5,
});

// ===== Pose結果 =====
pose.onResults(results => {
  ctx.save();
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(results.image, 0, 0, canvas.width, canvas.height);

  if (results.poseLandmarks) {
    // ★ landmarks を保存
    const frame = results.poseLandmarks.map(p => [
      p.x, p.y, p.z, p.visibility
    ]);
    if (running) {
      allFrames.push(frame);
    }

    if (showBox) {
      const boxX = canvas.width * 0.1;
      const boxY = canvas.height * 0.05;
      const boxW = canvas.width * 0.8;
      const boxH = canvas.height * 0.9;

      const ids = [0, 11, 12, 23, 24, 27, 28];
      insideBox = ids.every(i => {
        const p = results.poseLandmarks[i];
        return p.visibility > 0.6 &&
          p.x > boxX / canvas.width &&
          p.x < (boxX + boxW) / canvas.width &&
          p.y > boxY / canvas.height &&
          p.y < (boxY + boxH) / canvas.height;
      });

      ctx.strokeStyle = insideBox ? "lime" : "red";
      ctx.lineWidth = 5;
      ctx.strokeRect(boxX, boxY, boxW, boxH);

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
  }

  ctx.restore();
});

// ===== カメラ準備 =====
function prepareCamera() {
  if (camera) return;
  camera = new Camera(video, {
    onFrame: async () => {
      await pose.send({ image: video });
    }
  });
}

// ===== カメラ起動 =====
async function startCameraOnce() {
  if (cameraStarted) return;
  prepareCamera();
  await camera.start();
  cameraStarted = true;
}

// ===== カウントダウン =====
function startCountdown() {
  if (countingDown || running) return;
  countingDown = true;
  let c = 3;
  countdownEl.textContent = c;

  const timer = setInterval(() => {
    if (!insideBox) {
      clearInterval(timer);
      countingDown = false;
      countdownEl.textContent = "";
      return;
    }
    c--;
    if (c > 0) countdownEl.textContent = c;
    else if (c === 0) countdownEl.textContent = "スタート！";
    else {
      clearInterval(timer);
      countdownEl.textContent = "";
      countingDown = false;
      showBox = false;
      startExercise();
    }
  }, 1000);
}

// ===== 表示 =====
function showStep(i) {
  scoreEl.textContent = steps[i]
    ? `現在: ${steps[i].name}`
    : "完了！採点中...";
}

// ===== 体操開始 =====
async function startExercise() {
  running = true;
  allFrames = [];
  startBtn.disabled = true;
  stopBtn.disabled = false;
  showStep(0);

  let i = 0;
  function next() {
    if (!running) return;
    i++;
    if (i < steps.length) {
      showStep(i);
      setTimeout(next, steps[i].duration);
    } else {
      stopExercise();
    }
  }
  setTimeout(next, steps[0].duration);
}

// ===== 体操終了 → 採点送信 =====
async function stopExercise() {
  running = false;
  stopBtn.disabled = true;
  startBtn.disabled = false;
  showStep(-1);
  scoreEl.textContent = "採点中...";

  const res = await fetch("/score_landmarks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ frames: allFrames })
  });

  if (res.redirected) {
    location.href = res.url;
  }
}

// ===== ボタン =====
startBtn.onclick = async () => {
  await startCameraOnce();
};

stopBtn.onclick = stopExercise;

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Render 完全対応版
------------------------------------------------------------
特徴:
  ● index.html（録画なし版）から送られる landmarks を直接採点
  ● 動画保存なし
  ● 説明した「方式A（今のscore_student_windows.py）」をそのまま利用
  ● login_routes / result_routes もそのまま使える
  ● data/teacher_timing_model.* 不要
------------------------------------------------------------
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import os, uuid, csv, json, subprocess
import pandas as pd

# === Blueprint ===
from login_routes import auth_bp
from result_routes import result_bp

# ============================================================
# Flaskアプリ
# ============================================================
app = Flask(__name__, template_folder="web")
app.secret_key = "radio-taiso-secret-key-2025"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")

RESULTS_DIR = os.path.join(DATA_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ============================================================
# サブプロセス実行（共通関数）
# ============================================================
def run_script(cmd):
    print("▶ 実行:", " ".join(cmd))
    try:
        subprocess.run(cmd, cwd=BASE_DIR, check=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, str(e)

# ============================================================
# Blueprint 登録
# ============================================================
app.register_blueprint(auth_bp)
app.register_blueprint(result_bp)

# ============================================================
# ページ遷移
# ============================================================
@app.route("/")
def index():
    return redirect(url_for("auth.login"))

@app.route("/record")
def record_page():
    return render_template("index.html")


# ============================================================
# ★ landmarks → CSV に変換して採点（録画なし版の本体）
# ============================================================
@app.route("/score_landmarks", methods=["POST"])
def score_landmarks():
    """
    index.html が送る JSON:
      {
        "frames": [
           [[x,y,z,v], ×33 ],
           ...
        ]
      }
    """
    data = request.get_json()
    if not data or "frames" not in data:
        return jsonify({"error": "frames がありません"}), 400

    frames = data["frames"]
    if len(frames) == 0:
        return jsonify({"error": "フレーム数が 0"}), 400

    # 生徒フォルダ作成
    uid = uuid.uuid4().hex[:6]
    student_dir = os.path.join(RESULTS_DIR, f"student_{uid}")
    lm_dir = os.path.join(student_dir, "landmarks")
    os.makedirs(lm_dir, exist_ok=True)

    # ========================================================  
    # 1. JSON → landmarks.csv へ変換
    # ========================================================
    lm_csv = os.path.join(lm_dir, f"student_{uid}_landmarks.csv")

    with open(lm_csv, "w", newline="") as f:
        writer = csv.writer(f)

        header = ["time_sec"]
        for i in range(33):
            for ax in ["x", "y", "z", "v"]:
                header.append(f"{ax}_{i}")
        writer.writerow(header)

        t = 0.0
        for frame in frames:
            row = [t]
            for p in frame:
                row += [p[0], p[1], p[2], p[3]]
            writer.writerow(row)
            t += 1.0 / 30.0   # 30fps 固定

    print(f"📄 JSON→CSV 保存: {lm_csv}")

    # ========================================================  
    # 2. ウィンドウ特徴量生成
    # ========================================================
    wf_dir = os.path.join(student_dir, "student_window_features")
    os.makedirs(wf_dir, exist_ok=True)

    ok, err = run_script([
        "python3", "make_student_window_features.py",
        "--indir", lm_dir,
        "--outdir", wf_dir
    ])
    if not ok:
        return jsonify({"error": f"特徴量生成エラー: {err}"}), 500

    # ========================================================  
    # 3. 採点
    # ========================================================
    ok, err = run_script([
        "python3", "score_student_windows.py",
        "--indir", wf_dir,
        "--outdir", student_dir
    ])
    if not ok:
        return jsonify({"error": f"採点エラー: {err}"}), 500

    summary_csv = os.path.join(student_dir, "results_score/student_score_summary.csv")

    # ========================================================  
    # 4. ログインユーザーは履歴に保存
    # ========================================================
    user_id = session.get("user_id")
    if user_id:
        history_dir = os.path.join(DATA_DIR, "history")
        os.makedirs(history_dir, exist_ok=True)
        history_path = os.path.join(history_dir, f"{user_id}_history.csv")

        df_curr = pd.read_csv(summary_csv)
        from datetime import datetime
        df_curr["session_id"] = uid
        df_curr["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if os.path.exists(history_path):
            df_old = pd.read_csv(history_path)
            df_all = pd.concat([df_old, df_curr], ignore_index=True)
        else:
            df_all = df_curr
        df_all.to_csv(history_path, index=False)

    # ========================================================  
    # 5. 結果ページへリダイレクト
    # ========================================================
    return redirect(url_for("result.show_result", student_id=uid))


# ============================================================
# 起動
# ============================================================
if __name__ == "__main__":
    print("====================================")
    print(" RadioTaiso Auto-Scoring Server（Render対応版）")
    print(" http://127.0.0.1:5000/")
    print("====================================")
    app.run(host="0.0.0.0", port=5000, debug=True)

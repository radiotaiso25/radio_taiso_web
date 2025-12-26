#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_student_window_features.py（教師と完全一致版）
============================================================
・前奏(E00)の自動検出
・E01開始を t=0 に正規化
・E01〜E13 を教師モデルの秒数で自動分割
・各Eについて 20角度 → 83次元特徴量を生成し保存

出力:
  data/student_window_features/E01/student_xxx_E01.csv
  data/student_window_features/E02/student_xxx_E02.csv
  ...
============================================================
"""

import os
import numpy as np
import pandas as pd
import argparse 
import json
from glob import glob
from tqdm import tqdm

from compute_20_angles import compute_20_angles   # ← DataFrame版を使用
from motion_features import extract_features      # 83次元を返す


# ====== 定数 ======
WIN = 30
HOP = 15


# ====== 教師の時間モデル読み込み ======
MODEL_JSON = "data/teacher_timing_model.json"
with open(MODEL_JSON, "r") as f:
    E_TIMES_LIST = json.load(f)

# list → dict（"E01": {start, end}）
E_TIMES = {
    d["exercise_id"]: {
        "start": float(d["mean_start_sec"]),
        "end":   float(d["mean_end_sec"])
    }
    for d in E_TIMES_LIST
}


# ====== 前奏検出 ======
def detect_start_t0(angles8, fps=15):
    d = np.abs(np.diff(angles8, axis=0))
    speed = d.mean(axis=1)
    smooth = np.convolve(speed, np.ones(5)/5, mode="same")
    th = smooth.mean() + 2 * smooth.std()
    idx = np.where(smooth > th)[0]
    return idx[0] / fps if len(idx) > 0 else 0.0


# ====== ウィンドウ作成 ======
def create_windows(X, win=30, hop=15):
    T = X.shape[0]
    return [X[s:s+win] for s in range(0, T-win+1, hop)]


# ====== メイン処理 ======
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    IN_DIR = args.indir
    OUT_DIR = args.outdir
    os.makedirs(OUT_DIR, exist_ok=True)

    files = sorted(glob(os.path.join(IN_DIR, "*_landmarks.npz")))
    print(f"🔍 生徒ランドマーク: {len(files)} 件")

    for path in tqdm(files):
        name = os.path.splitext(os.path.basename(path))[0].replace("_landmarks", "")
        print(f"\n▶ {name} 処理中...")

        d = np.load(path)
        P = d["norm"]      # (T,33,3)
        angles8 = d["angles"]
        ts = d["ts"]

        # -------- E01 の最初の動き detect --------
        t0 = detect_start_t0(angles8)
        t_norm = ts - t0
        print(f"   🔍 E01開始検出: {t0:.3f} sec")

        # -------- ここが超重要！！教師と同じ DataFrame 20角度 --------
        angle20_df = compute_20_angles(P)  # DataFrame (T,20)

        # -------- E01〜E13 ループ --------
        for eid, se in E_TIMES.items():
            s, e = se["start"], se["end"]

            mask = (t_norm >= s) & (t_norm < e)
            idx = np.where(mask)[0]

            if len(idx) < WIN:
                print(f"   ⚠ {eid}: フレーム不足 → スキップ")
                continue

            # ★ DataFrame → 行抽出 → NumPy化（教師と完全一致）
            A = angle20_df.iloc[idx].to_numpy()   # (T',20)
            L = P[idx]                            # (T',33,3)

            wins_A = create_windows(A, WIN, HOP)
            wins_L = create_windows(L, WIN, HOP)

            rows = []
            for wA, wL in zip(wins_A, wins_L):
                rows.append(extract_features(wL, wA))

            df = pd.DataFrame(rows)

            out_e_dir = os.path.join(OUT_DIR, eid)
            os.makedirs(out_e_dir, exist_ok=True)

            out_path = os.path.join(out_e_dir, f"{name}_{eid}.csv")
            df.to_csv(out_path, index=False)

            print(f"   ✔ {eid}: {len(df)} windows → {out_path}")

    print("\n🎉 生徒ウィンドウ特徴量生成 完了！")


# ====== 実行 ======
if __name__ == "__main__":
    main()

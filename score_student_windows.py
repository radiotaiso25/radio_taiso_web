#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
score_student_windows.py（方式A＋誤差100点方式）
============================================================
教師プロファイルと生徒ウィンドウを比較し、
教師の最小距離で正規化したうえで、
一定以下の距離は「誤差」として 100 点扱いにする。

server.py から呼び出すときは:

python3 score_student_windows.py --indir <student_window_features_dir> \
                                 --outdir <student_result_dir>

出力:
  <outdir>/results_score/student_score_summary.csv
  <outdir>/results_score/student_score_detail.csv
  <outdir>/results_score/student_part_error.csv
============================================================
"""

import os
import argparse
import numpy as np
import pandas as pd
from glob import glob

PROFILE_PATH = "../data/teacher_profile/teacher_profile_window_median.npz"

ANGLE_PART = {
    0:"肩",1:"肩",2:"肘",3:"肘",4:"股関節",5:"股関節",
    6:"膝",7:"膝",8:"肘",9:"肘",10:"膝",11:"膝",
    12:"腕と脚の協調",13:"腕と脚の協調",14:"腕と脚の協調",15:"腕と脚の協調",
    16:"体幹〜四肢の連動",17:"体幹〜四肢の連動",
    18:"脚の連動",19:"脚の連動"
}

def build_feature_part_map(columns):
    mapping = {}
    for idx, col in enumerate(columns):
        if col.startswith("f") and "_" in col:
            try:
                angle_idx = int(col[1:3])
                part = ANGLE_PART.get(angle_idx)
                if part:
                    mapping[idx] = part
            except ValueError:
                pass
        elif col in ("trunk_range", "trunk_vel"):
            mapping[idx] = "体幹"
        elif col == "symmetry":
            mapping[idx] = "左右バランンス"
    return mapping

# ============================================================
# ⭐ 方式A＋誤差100点方式のスコア関数
# ============================================================
def score_window(student_vec, teacher_vec, min_teacher_dist):
    true_dist = np.linalg.norm(student_vec - teacher_vec)
    dist_norm = max(0.0, true_dist - min_teacher_dist)

    # ★ 誤差として許容する距離（これ以下は100点）
    TOL = 3000

    if dist_norm <= TOL:
        return 100.0

    # ★ 優しさ（ALPHAを大きくすると点数が上がりやすくなる）
    ALPHA = 7000

    score = 100 * np.exp(-(dist_norm - TOL) / ALPHA)
    return max(0.0, min(score, 100.0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    IN_DIR = args.indir
    OUT_BASE = args.outdir

    OUT_DIR = os.path.join(OUT_BASE, "results_score")
    os.makedirs(OUT_DIR, exist_ok=True)

    print("📘 Loading teacher profile...")
    prof = np.load(PROFILE_PATH)

    for eid in sorted(prof.files):
        print(f"  {eid}: {prof[eid].shape}")

    student_folders = sorted(glob(os.path.join(IN_DIR, "E*")))
    print(f"\n🎯 生徒 Eフォルダ検出: {len(student_folders)} 個")

    results = []
    feature_part_map = None
    part_error = {}
    part_count = {}

    for e_folder in student_folders:
        eid = os.path.basename(e_folder)
        teacher_mat = prof.get(eid, None)

        if teacher_mat is None:
            print(f"⚠ {eid}: 教師データなし → スキップ")
            continue

        csv_list = sorted(glob(os.path.join(e_folder, "*.csv")))
        if len(csv_list) == 0:
            print(f"⚠ {eid}: 生徒データなし → スキップ")
            continue

        student_df = pd.read_csv(csv_list[0])
        student_mat = student_df.values

        if feature_part_map is None:
            feature_part_map = build_feature_part_map(list(student_df.columns))
            print("🧩 feature→部位 マップ:", feature_part_map)

        # ===== 教師の最小距離（dist-min）を計算 =====
        teacher_min_dist = np.inf
        for i in range(len(teacher_mat) - 1):
            d = np.linalg.norm(teacher_mat[i] - teacher_mat[i+1])
            teacher_min_dist = min(teacher_min_dist, d)

        print(f"\n➡ {eid}: teacher_min_dist = {teacher_min_dist:.2f}")

        # ===== 生徒スコア算出 =====
        W = min(teacher_mat.shape[0], student_mat.shape[0])

        for i in range(W):
            s_vec = student_mat[i]
            t_vec = teacher_mat[i]

            score = score_window(s_vec, t_vec, teacher_min_dist)

            results.append({
                "exercise": eid,
                "window_index": i,
                "score": score
            })

            # 部位誤差集計
            diff = np.abs(s_vec - t_vec)
            pe = part_error.setdefault(eid, {})
            pc = part_count.setdefault(eid, {})

            for fi, part in feature_part_map.items():
                pe[part] = pe.get(part, 0.0) + float(diff[fi])
                pc[part] = pc.get(part, 0) + 1

    df = pd.DataFrame(results)

    detail_path = os.path.join(OUT_DIR, "student_score_detail.csv")
    summary_path = os.path.join(OUT_DIR, "student_score_summary.csv")

    df.to_csv(detail_path, index=False)
    df.groupby("exercise")["score"].mean().reset_index() \
        .rename(columns={"score": "mean_score"}) \
        .to_csv(summary_path, index=False)

    print("\n🎉 採点完了!!!!")
    print(f"  🔍 詳細: {detail_path}")
    print(f"  📊 平均: {summary_path}")

    # 部位誤差
    part_rows = []
    for eid, per_part in part_error.items():
        for part, total_err in per_part.items():
            cnt = part_count[eid].get(part, 1)
            part_rows.append({
                "exercise": eid,
                "part": part,
                "mean_abs_error": total_err / cnt
            })

    if part_rows:
        df_part = pd.DataFrame(part_rows)
        part_path = os.path.join(OUT_DIR, "student_part_error.csv")
        df_part.to_csv(part_path, index=False)
        print(f"  🧠 部位別誤差: {part_path}")


if __name__ == "__main__":
    main()

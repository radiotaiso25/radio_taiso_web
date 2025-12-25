# =============================================================
# result_routes.py
#
# 💡 このファイルは「採点結果ページと前回との比較」を担当します。
#
#  /result/<student_id>
#   - スコア表の表示
#   - 部位毎の誤差からアドバイス生成
#   - 平均スコアが低い体操(下位3つ)の抽出
#   - ログインユーザーのみ「前回との比較」表示
#   - ゲスト時は比較なし
#
# server.py から Blueprint として読み込んで使用します。
# =============================================================

from flask import Blueprint, render_template, session
from recommend_game import recommend_game
import os, csv, random
import pandas as pd

# === Blueprint ===
result_bp = Blueprint("result", __name__)

# === パス設定（server.py と同階層を想定） ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

# === 定義（server.py と共有したい） ===
EXERCISE_LABEL = {
    "E01": "両腕を前から上に上げて背伸びの運動",
    "E02": "腕を振って脚を曲げ伸ばす運動",
    "E03": "腕を回す運動",
    "E04": "胸を反らす運動",
    "E05": "体を横にまげる運動",
    "E06": "体を前後にまげる運動",
    "E07": "体をねじる運動",
    "E08": "腕を上下にのばす運動",
    "E09": "体を斜め下にまげ胸をそらす運動",
    "E10": "体を回す運動",
    "E11": "両脚でとぶ運動",
    "E12": "腕を振って脚をまげのばす運動（２回目）",
    "E13": "深呼吸の運動",
}

ADVICE_TAILS = [
    "少し大きく動かすと改善します。",
    "ゆっくり大きめに動かすと良くなります。",
    "意識して動かすだけでも改善が期待できます。",
    "無理のない範囲で可動域を広げてみましょう。",
    "一つ一つの動きを丁寧に行うと安定します。",
]

# =============================================================
# /result/<student_id>
# =============================================================
@result_bp.route("/result/<student_id>")
def show_result(student_id):
    # ===== パス類 =====
    student_dir = os.path.join(RESULTS_DIR, f"student_{student_id}")
    summary_path = os.path.join(student_dir, "results_score", "student_score_summary.csv")
    part_path    = os.path.join(student_dir, "results_score", "student_part_error.csv")

    # 結果が無ければ 404 返して終了
    # 結果が無ければ採点待ち画面を表示
    if not os.path.exists(summary_path):
        return f"結果ファイルが見つかりません: {summary_path}", 404


    # ===== 今回のスコア（DataFrame） =====
    df_curr = pd.read_csv(summary_path)
    if "exercise" not in df_curr.columns and "exercise_id" in df_curr.columns:
        df_curr = df_curr.rename(columns={"exercise_id": "exercise"})
    if "mean_score" not in df_curr.columns and "score" in df_curr.columns:
        df_curr = df_curr.rename(columns={"score": "mean_score"})

    # ===== テーブル & グラフ用データ =====
    table_data = []
    exercises = []
    scores = []

    with open(summary_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ex = (
                row.get("exercise")
                or row.get("exercise_id")
                or row.get("label")
                or ""
            )
            val = row.get("mean_score", "") or row.get("score", "") or "0"
            try:
                ms = float(val)
            except ValueError:
                ms = 0.0

            table_data.append({"exercise_id": ex, "mean_score": ms})
            exercises.append(ex)
            scores.append(ms)

    # ★ 下位3つ体操（E番号 & 日本語ラベル）
    sorted_by_score = sorted(table_data, key=lambda r: r["mean_score"])
    low3 = sorted_by_score[:3]
    low_eids   = [r["exercise_id"] for r in low3]
    low_labels = [f"{EXERCISE_LABEL.get(e, e)} ({e})" for e in low_eids]

    # ===== 部位別誤差・総合コメント =====
    part_feedback   = {}   # 各Eの「悪かった部位」リスト
    global_feedback = []   # 全体で悪かった部位TOP3

    if os.path.exists(part_path):
        dfp = pd.read_csv(part_path)

        # --- 体操ごと（下位3つだけ） ---
        for eid in low_eids:
            sub = dfp[dfp["exercise"] == eid]
            if sub.empty:
                continue

            # 誤差の大きい順に並べて上位3つの部位だけ
            sub = sub.sort_values("mean_abs_error", ascending=False)
            tops = sub.head(3)

            parts = [row["part"] for _, row in tops.iterrows()]
            part_feedback[eid] = parts

        # --- 総合コメント（全Eまとめて部位TOP3） ---
        df_global = dfp.groupby("part")["mean_abs_error"].mean().reset_index()
        df_global = df_global.sort_values("mean_abs_error", ascending=False)
        global_feedback = [row["part"] for _, row in df_global.head(3).iterrows()]

    # ===== 前回との比較 ＋ 自己ベスト =====
    compare_rows = []                 # 比較結果（ログインしてない or 履歴無しなら空のまま）
    user_id = session.get("user_id")  # None ならゲスト

    if user_id is not None:
        history_dir = os.path.join(DATA_DIR, "history")
        history_path = os.path.join(history_dir, f"{user_id}_history.csv")

        if os.path.exists(history_path):
            df_hist = pd.read_csv(history_path)

            # カラム名をそろえる
            if "exercise" not in df_hist.columns and "exercise_id" in df_hist.columns:
                df_hist = df_hist.rename(columns={"exercise_id": "exercise"})
            if "mean_score" not in df_hist.columns and "score" in df_hist.columns:
                df_hist = df_hist.rename(columns={"score": "mean_score"})

            curr_sid = student_id  # URL の <student_id> をセッションIDとして使う

            # このユーザーのセッション一覧（古い順）
            sids = df_hist["session_id"].dropna().unique().tolist()

            if curr_sid in sids:
                idx = sids.index(curr_sid)

                # ① 前回セッションとの比較（1つ前があれば）
                if idx > 0:
                    prev_sid = sids[idx - 1]
                    df_prev = df_hist[df_hist["session_id"] == prev_sid]

                    df_merged = df_curr.merge(
                        df_prev[["exercise", "mean_score"]],
                        on="exercise",
                        how="left",
                        suffixes=("_curr", "_prev")
                    )

                    # ② 自己ベスト（全履歴の max）
                    df_best = (
                        df_hist
                        .groupby("exercise")["mean_score"]
                        .max()
                        .reset_index()
                        .rename(columns={"mean_score": "best_score"})
                    )

                    df_merged = df_merged.merge(df_best, on="exercise", how="left")

                    df_merged["diff_prev"] = df_merged["mean_score_curr"] - df_merged["mean_score_prev"]
                    df_merged["diff_best"] = df_merged["mean_score_curr"] - df_merged["best_score"]

                    for _, r in df_merged.iterrows():
                        compare_rows.append({
                            "exercise": r["exercise"],
                            "label": EXERCISE_LABEL.get(r["exercise"], r["exercise"]),
                            "curr": round(r["mean_score_curr"], 2),
                            "prev": round(r["mean_score_prev"], 2) if not pd.isna(r["mean_score_prev"]) else None,
                            "diff_prev": round(r["diff_prev"], 2) if not pd.isna(r["diff_prev"]) else None,
                            "best": round(r["best_score"], 2) if not pd.isna(r["best_score"]) else None,
                            "diff_best": round(r["diff_best"], 2) if not pd.isna(r["diff_best"]) else None,
                        })

    # ===== 体操ごとの一文アドバイス（下位3つだけ） =====
    exercise_advice = {}
    for eid, parts in part_feedback.items():
        if not parts:
            exercise_advice[eid] = "特に大きな問題はありませんでした。"
        else:
            # 「肩・股関節・体幹」みたいに並べる
            unique_parts = list(dict.fromkeys(parts))  # 重複削除
            joined = "・".join(unique_parts)
            tail = random.choice(ADVICE_TAILS)
            exercise_advice[eid] = f"{joined}の動きが小さめです。{tail}"


    # ===== ★ 総合スコア（全体平均） =====
    all_scores = [r["mean_score"] for r in table_data if r["mean_score"] is not None]
    if len(all_scores) > 0:
        overall_score = sum(all_scores) / len(all_scores)
    else:
        overall_score = 0.0

    # ===== ★ メッセージ判定 =====
    def score_message(score):
        if score >= 90:
            return "🌟 すごい！！完璧です！"
        elif score >= 70:
            return "👍 あとちょっと！かなり良いです！"
        elif score >= 40:
            return "🙂 少しずつ改善していきましょう！"
        else:
            return "🔥 一緒に頑張ろう！伸びしろがあります！"

    # ===== ★ 色判定 =====
    def score_color(score):
        if score >= 90:
            return "#d4edda"  # 緑
        elif score >= 70:
            return "#fff3cd"  # 黄
        elif score >= 40:
            return "#ffeeba"  # 濃い黄
        else:
            return "#f8d7da"  # 赤

    overall_message = score_message(overall_score)
    overall_color = score_color(overall_score)
    
    # ===== ★ おすすめゲーム判定用のデータ =====
    # 体操ごとのスコアを dict にする（例：{"E01": 80.5, "E02": 65.0, ...}）
    exercise_scores = {
        row["exercise_id"]: row["mean_score"]
        for row in table_data
        if row.get("exercise_id") is not None
    }

    # チャットのタグ（/api/chat で session["chat_tags"] に入れておく）
    chat_tags = session.get("chat_tags", [])

    # バランス型ロジックでおすすめゲームを決定
    recommended_game = recommend_game(chat_tags, exercise_scores, global_feedback)



    # ===== ここで必ずテンプレートを返す（どの条件でも） =====
    return render_template(
        "result.html",
        result_path=summary_path,
        table_data=table_data,
        exercises=exercises,
        scores=scores,
        part_feedback=part_feedback,
        low_eids=low_eids,
        low_labels=low_labels,
        global_feedback=global_feedback,
        EXERCISE_LABEL=EXERCISE_LABEL,
        exercise_advice=exercise_advice,
        compare_rows=compare_rows,
        overall_score=overall_score,
        overall_message=overall_message,
        overall_color=overall_color,
        recommended_game=recommended_game,
        chat_tags=chat_tags,
    )

# radio_taiso/src/recommend_game.py
from statistics import mean

def _part_key_from_text(text: str):
    """部位名っぽい文字列から共通キーを返す"""
    s = str(text).lower()
    if ("首" in s) or ("neck" in s):
        return "neck"
    if ("肩" in s) or ("shoulder" in s) or ("腕" in s) or ("arm" in s):
        return "shoulder"
    if ("腰" in s) or ("背" in s) or ("back" in s) or ("体幹" in s):
        return "trunk"   # 体幹・腰・背中まわり
    if ("全身" in s) or ("whole" in s) or ("body" in s):
        return "whole_body"
    return None


def _game_from_key(key: str, mode: str = "normal"):
    """部位キー → おすすめゲーム情報"""
    if key == "neck":
        reason = (
            "首まわりの動きに少し課題が見られたため、首を中心にやさしく動かせるゲームをおすすめします。"
            if mode == "focus" else
            "首はよく動いていましたので、今日は他の部位を休めつつ、首まわりもやさしく動かせるゲームをおすすめします。"
        )
        return {
            "id": "neck_target",
            "label": "首まわりネックターゲット",
            "reason": reason,
        }

    if key == "shoulder":
        reason = (
            "肩や腕まわりの動きが少し控えめだったため、無理なく大きく動かせるゲームをおすすめします。"
        )
        return {
            "id": "balloon_catch",
            "label": "座ってできる風船つかみゲーム",
            "reason": reason,
        }

    # trunk / whole_body は全身かたぬきに寄せる
    reason = (
        "体全体の動きに少しバラつきが見られたため、全身をバランスよく動かせるゲームをおすすめします。"
    )
    return {
        "id": "body_katanuki",
        "label": "体全体のかたぬきゲーム",
        "reason": reason,
    }


def recommend_game(chat_tags, exercise_scores, global_feedback=None):
    """
    chat_tags: チャットから抜き出したタグ（["neck", "肩", "whole_body", ...]）
    exercise_scores: {"E01": 78.5, ...}
    global_feedback: 「動きが小さかった部位」リスト（例: ["首", "肩", "腰"]）
    """
    if chat_tags is None:
        chat_tags = []
    if global_feedback is None:
        global_feedback = []

    # 1) タグ側の部位キー（ユーザが気にしている場所）
    tag_keys = set()
    for t in chat_tags:
        k = _part_key_from_text(t)
        if k:
            tag_keys.add(k)

    # 2) 誤差が大きかった部位側のキー（実際に弱かった場所）
    gf_keys = [_part_key_from_text(p) for p in global_feedback]
    gf_keys = [k for k in gf_keys if k is not None]

    # 3) 「タグにも出ていて、誤差側にも出ている部位」を優先
    #    = ユーザが気にしていて、かつ本当に弱かった場所
    for key in ["neck", "shoulder", "trunk", "whole_body"]:
        if (key in tag_keys) and (key in gf_keys):
            return _game_from_key(key, mode="focus")

    # 4) タグにはあるけど誤差側には出てこない
    #    = 気にしていたけど実際にはそこまで悪くなかった → 一番悪い部位を優先
    if gf_keys:
        return _game_from_key(gf_keys[0], mode="normal")

    # 5) 誤差情報も無いとき：全体スコアだけでざっくり判定
    all_scores = list(exercise_scores.values()) if exercise_scores else []
    avg = mean(all_scores) if all_scores else 100.0
    if avg < 70:
        return _game_from_key("whole_body", mode="normal")

    # デフォルト：座ってできる風船つかみ
    return {
        "id": "balloon_catch",
        "label": "座ってできる風船つかみゲーム",
        "reason": "無理のない範囲で楽しく続けられるよう、座ったままできるゲームをおすすめします。",
    }

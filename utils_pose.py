# src/utils_pose.py

import numpy as np
import math

# MediaPipe Pose のランドマーク index（BlazePose Full / 33点）
# 主要点のみ: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
IDX = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}

LEFT_IDX = [11, 13, 15, 23, 25, 27]
RIGHT_IDX = [12, 14, 16, 24, 26, 28]


def _angle(a, b, c):
    """
    3点 A-B-C の ∠ABC（度）
    a, b, c: (..., 3)
    """
    v1 = a - b
    v2 = c - b

    # 正規化
    v1 = v1 / (np.linalg.norm(v1, axis=-1, keepdims=True) + 1e-9)
    v2 = v2 / (np.linalg.norm(v2, axis=-1, keepdims=True) + 1e-9)

    # 角度
    cos = np.clip(np.sum(v1 * v2, axis=-1), -1.0, 1.0)
    return np.degrees(np.arccos(cos))


def compute_basic_angles(P):
    """
    P: (T, 33, 3) 正規化済み座標
    返り値: angles(T, 8)
      [肩屈曲L, 肩屈曲R,
       肘L, 肘R,
       股関節L, 股関節R,
       膝L, 膝R]
    """
    Ls, Rs = IDX["left_shoulder"], IDX["right_shoulder"]
    Le, Re = IDX["left_elbow"], IDX["right_elbow"]
    Lw, Rw = IDX["left_wrist"], IDX["right_wrist"]
    Lh, Rh = IDX["left_hip"], IDX["right_hip"]
    Lk, Rk = IDX["left_knee"], IDX["right_knee"]
    La, Ra = IDX["left_ankle"], IDX["right_ankle"]

    shoulder_flex_L = _angle(P[:, Le], P[:, Ls], P[:, Lh])
    shoulder_flex_R = _angle(P[:, Re], P[:, Rs], P[:, Rh])

    elbow_L = _angle(P[:, Ls], P[:, Le], P[:, Lw])
    elbow_R = _angle(P[:, Rs], P[:, Re], P[:, Rw])

    hip_L = _angle(P[:, Lk], P[:, Lh], P[:, Ls])
    hip_R = _angle(P[:, Rk], P[:, Rh], P[:, Rs])

    knee_L = _angle(P[:, Lh], P[:, Lk], P[:, La])
    knee_R = _angle(P[:, Rh], P[:, Rk], P[:, Ra])

    angles = np.stack([
        shoulder_flex_L, shoulder_flex_R,
        elbow_L, elbow_R,
        hip_L, hip_R,
        knee_L, knee_R
    ], axis=-1)

    return angles


def diff_pad(x):
    """
    時間微分（フレーム差分）
    shape: (T, D) → (T, D)
    先頭は0で埋める
    """
    d = np.diff(x, axis=0, prepend=x[:1])
    return d


def pelvis_center(P33):
    """
    左右Hipの中点 (T,3)
    """
    Lh, Rh = IDX["left_hip"], IDX["right_hip"]
    return (P33[:, Lh, :3] + P33[:, Rh, :3]) / 2.0


def shoulder_width(P33):
    """
    左右Shoulderの距離 (T,)
    """
    Ls, Rs = IDX["left_shoulder"], IDX["right_shoulder"]
    return np.linalg.norm(P33[:, Ls, :3] - P33[:, Rs, :3], axis=-1) + 1e-9


def normalize_pose(raw_xyz):
    """
    raw_xyz: (T,33,3)
    手順:
      1) 骨盤中心を原点に平行移動
      2) 肩幅でスケール正規化
      3) 肩ラインが水平になるように回転（Z軸回り）
    """
    P = raw_xyz.copy()

    # 1) 平行移動
    pc = pelvis_center(P)
    P = P - pc[:, None, :]

    # 2) スケール正規化
    sw = shoulder_width(P)
    P = P / sw[:, None, None]

    # 3) 回転（Z軸まわりに2D回転）
    Ls, Rs = IDX["left_shoulder"], IDX["right_shoulder"]
    v = P[:, Rs, :2] - P[:, Ls, :2]  # (T, 2)
    theta = np.arctan2(v[:, 1], v[:, 0])

    cos, sin = np.cos(-theta), np.sin(-theta)
    R = np.stack([
        np.stack([cos, -sin], axis=-1),
        np.stack([sin,  cos], axis=-1)
    ], axis=-2)

    Pxy = P[..., :2]
    P[..., :2] = np.einsum("tij,tkj->tki", R, Pxy)

    return P


def visibility_mask(raw):
    """
    簡易マスク:
      visibility の平均が 0.5 以上のフレームを True
    """
    vis = raw[..., 3]  # (T,33)
    m = (np.nanmean(vis, axis=-1) >= 0.5).astype(np.uint8)
    return m

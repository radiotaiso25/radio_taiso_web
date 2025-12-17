# ================================================================
# motion_features.py（（20角度モデル対応版））
# ランドマーク（正規化済み33点＋角度8本）から
# 20角度×4統計＝83次元モデルの最終特徴量を作るためのファイル
# ================================================================

import numpy as np
from scipy.signal import find_peaks

# ---------------------------------------------------------------
# 基本統計
# ---------------------------------------------------------------
def calc_mean(x):
    return float(np.nanmean(x))

def calc_range(x):
    return float(np.nanmax(x) - np.nanmin(x))

def calc_var(x):
    return float(np.nanvar(x))

def calc_periodicity(x):
    if len(x) < 4:
        return 0.0
    x = np.nan_to_num(x)
    fft_vals = np.abs(np.fft.rfft(x))
    total = np.sum(fft_vals[1:])
    if total == 0:
        return 0.0
    main_peak = np.max(fft_vals[1:])
    return float(main_peak / total)

# ================================================================
# 20角度モデル
# ================================================================
def angle_between(v1, v2):
    v1 = v1 / (np.linalg.norm(v1) + 1e-6)
    v2 = v2 / (np.linalg.norm(v2) + 1e-6)
    dot = np.clip(np.dot(v1, v2), -1.0, 1.0)
    return np.degrees(np.arccos(dot))

def compute_20_angles(coords):
    """
    coords: (T, 33, 3)
    return: (T,20) の角度行列
    """

    T = coords.shape[0]
    vals = []

    gravity = np.array([0, -1, 0], dtype=float)
    right_axis = np.array([1, 0, 0])
    forward_axis = np.array([0, 1, 0])

    for t in range(T):
        P = coords[t]

        # 関節位置
        L_SHO, R_SHO = P[11], P[12]
        L_ELB, R_ELB = P[13], P[14]
        L_WRI, R_WRI = P[15], P[16]
        L_HIP, R_HIP = P[23], P[24]
        L_KNE, R_KNE = P[25], P[26]
        L_ANK, R_ANK = P[27], P[28]

        MID_SHO = (L_SHO + R_SHO) / 2
        MID_HIP = (L_HIP + R_HIP) / 2

        # ベクトル
        TORSO = MID_SHO - MID_HIP

        L_UP  = L_ELB - L_SHO
        R_UP  = R_ELB - R_SHO
        L_LOW = L_WRI - L_ELB
        R_LOW = R_WRI - R_ELB

        L_THI = L_KNE - L_HIP
        R_THI = R_KNE - R_HIP
        L_CALF = L_ANK - L_KNE
        R_CALF = R_ANK - R_KNE

        # 20角度
        angles = [

            # 腕 6本
            angle_between(L_UP, -TORSO),   # shoulder_L
            angle_between(R_UP, -TORSO),   # shoulder_R
            angle_between(L_UP, L_LOW),    # elbow_L
            angle_between(R_UP, R_LOW),    # elbow_R
            angle_between(L_LOW, gravity), # wrist_L
            angle_between(R_LOW, gravity), # wrist_R

            # 脚 6本
            angle_between(L_THI, TORSO),   # hip_L
            angle_between(R_THI, TORSO),   # hip_R
            angle_between(L_THI, L_CALF),  # knee_L
            angle_between(R_THI, R_CALF),  # knee_R
            angle_between(L_CALF, gravity),# ankle_L
            angle_between(R_CALF, gravity),# ankle_R

            # 体幹 4本
            angle_between(TORSO, forward_axis), # torso_forward
            angle_between(TORSO, right_axis),   # torso_side

            angle_between(R_SHO - L_SHO, R_HIP - L_HIP), # twist_shoulder
            angle_between(R_HIP - L_HIP, R_SHO - L_SHO), # twist_hip

            # 開き 4本
            angle_between(L_UP,  right_axis),  # arm_open_L
            angle_between(R_UP, -right_axis),  # arm_open_R
            angle_between(L_THI, right_axis),  # leg_open_L
            angle_between(R_THI, -right_axis), # leg_open_R
        ]

        vals.append(angles)

    return np.array(vals)  # (T,20)

# ================================================================
# 体幹3指標
# ================================================================
def pelvis_motion_features(norm_landmarks):
    LEFT_HIP = 23
    RIGHT_HIP = 24
    pelvis = (norm_landmarks[:, LEFT_HIP, :] + norm_landmarks[:, RIGHT_HIP, :]) / 2
    y = pelvis[:, 1]
    z = pelvis[:, 2]
    range_y = calc_range(y)
    vel = np.abs(np.diff(pelvis, axis=0))
    vel_mean = float(np.nanmean(vel))
    return range_y, vel_mean


# ================================================================
# extract_features（20角度対応版）
# ================================================================
def extract_features(norm_landmarks, angles):
    """
    angles: (T,20)
    20角度 × 4統計 = 80次元
    + 体幹3つ = 83次元
    """

    feats = {}

    # ① 20角度 × 4統計（80次元）
    for i in range(20):
        x = angles[:, i]
        feats[f"f{i:02d}_mean"]        = calc_mean(x)
        feats[f"f{i:02d}_range"]       = calc_range(x)
        feats[f"f{i:02d}_var"]         = calc_var(x)
        feats[f"f{i:02d}_periodicity"] = calc_periodicity(x)

    # ② 体幹3つ（3次元）
    range_y, vel_mean = pelvis_motion_features(norm_landmarks)
    feats["trunk_range"] = range_y
    feats["trunk_vel"]   = vel_mean

    # 左右股関節の角度差
    feats["symmetry"] = float(np.nanmean(np.abs(angles[:, 6] - angles[:, 7])))

    return feats

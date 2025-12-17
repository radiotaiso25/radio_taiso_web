#!/usr/bin/env python3
import numpy as np
import pandas as pd

def angle_between(v1, v2):
    v1 = v1 / (np.linalg.norm(v1) + 1e-6)
    v2 = v2 / (np.linalg.norm(v2) + 1e-6)
    dot = np.clip(np.dot(v1, v2), -1.0, 1.0)
    return float(np.degrees(np.arccos(dot)))

def compute_20_angles(coords):
    """
    coords : (T,33,3)
    return : DataFrame (T,20)
    """

    # indices
    L_SH = 11; R_SH = 12
    L_EL = 13; R_EL = 14
    L_WR = 15; R_WR = 16
    L_HP = 23; R_HP = 24
    L_KN = 25; R_KN = 26
    L_AN = 27; R_AN = 28

    T = coords.shape[0]
    rows = []

    for t in range(T):
        P = coords[t]

        # main segments
        L_UP   = P[L_SH] - P[L_EL]
        R_UP   = P[R_SH] - P[R_EL]
        L_LOW  = P[L_EL] - P[L_WR]
        R_LOW  = P[R_EL] - P[R_WR]

        L_THI  = P[L_HP] - P[L_KN]
        R_THI  = P[R_HP] - P[R_KN]
        L_CALF = P[L_KN] - P[L_AN]
        R_CALF = P[R_KN] - P[R_AN]

        TORSO  = P[L_SH] - P[L_HP]

        vals = [
            angle_between(L_UP,   TORSO),
            angle_between(R_UP,   TORSO),
            angle_between(L_LOW,  TORSO),
            angle_between(R_LOW,  TORSO),
            angle_between(L_THI,  TORSO),
            angle_between(R_THI,  TORSO),
            angle_between(L_CALF, TORSO),
            angle_between(R_CALF, TORSO),

            angle_between(L_UP,   L_LOW),
            angle_between(R_UP,   R_LOW),
            angle_between(L_THI,  L_CALF),
            angle_between(R_THI,  R_CALF),

            angle_between(L_UP,   L_THI),
            angle_between(R_UP,   R_THI),
            angle_between(L_LOW,  L_CALF),
            angle_between(R_LOW,  R_CALF),

            angle_between(P[L_SH] - P[L_HP],  P[L_EL] - P[L_KN]),
            angle_between(P[R_SH] - P[R_HP],  P[R_EL] - P[R_KN]),
            angle_between(P[L_HP] - P[L_KN],  P[L_KN] - P[L_AN]),
            angle_between(P[R_HP] - P[R_KN],  P[R_KN] - P[R_AN]),
        ]

        rows.append(vals)

    cols = [f"angle20_{i:02d}" for i in range(20)]
    return pd.DataFrame(rows, columns=cols)

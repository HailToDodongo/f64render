from dataclasses import dataclass

import numpy as np
import bpy

CC_C = {
    "COMBINED": 0,
    "TEXEL0": 1,
    "TEXEL1": 2,
    "PRIMITIVE": 3,
    "SHADE": 4,
    "ENVIRONMENT": 5,
    "CENTER": 6,
    "SCALE": 6,
    "COMBINED_ALPHA": 7,
    "TEXEL0_ALPHA": 8,
    "TEXEL1_ALPHA": 9,
    "PRIMITIVE_ALPHA": 10,
    "SHADE_ALPHA": 11,
    "ENV_ALPHA": 12,
    "LOD_FRACTION": 13,
    "PRIM_LOD_FRAC": 14,
    "NOISE": 7,
    "K4": 7,
    "K5": 15,
    "1": 6,
    "0": 31,
}

CC_A = {
    "COMBINED": 0,
    "TEXEL0": 1,
    "TEXEL1": 2,
    "PRIMITIVE": 3,
    "SHADE": 4,
    "ENVIRONMENT": 5,
    "LOD_FRACTION": 0,
    "PRIM_LOD_FRAC": 6,
    "1": 6,
    "0": 7,
}

# Color combiner values (integer) for a materials
@dataclass
class CCSettings:
  cc0_color: np.ndarray
  cc0_alpha: np.ndarray
  cc1_color: np.ndarray
  cc1_alpha: np.ndarray

# Fetches CC settings from a given fast64-material
def get_cc_settings(f3d_mat) -> CCSettings:
  c0 = f3d_mat.combiner1
  c1 = f3d_mat.combiner2

  return CCSettings(
    cc0_color = np.array([CC_C[c0.A      ], CC_C[c0.B      ], CC_C[c0.C      ], CC_C[c0.D      ]], dtype=np.int32),
    cc0_alpha = np.array([CC_A[c0.A_alpha], CC_A[c0.B_alpha], CC_A[c0.C_alpha], CC_A[c0.D_alpha]], dtype=np.int32),
    cc1_color = np.array([CC_C[c1.A      ], CC_C[c1.B      ], CC_C[c1.C      ], CC_C[c1.D      ]], dtype=np.int32),
    cc1_alpha = np.array([CC_A[c1.A_alpha], CC_A[c1.B_alpha], CC_A[c1.C_alpha], CC_A[c1.D_alpha]], dtype=np.int32)
  )
from dataclasses import dataclass

import numpy as np

BL_INP = {
  "G_BL_0"      : 0,
  "G_BL_1"      : 1,
  "G_BL_CLR_IN" : 2,
  "G_BL_CLR_MEM": 3,
  "G_BL_CLR_BL" : 4,
  "G_BL_CLR_FOG": 5,
  "G_BL_A_IN"   : 6,
  "G_BL_A_FOG"  : 7,
  "G_BL_A_SHADE": 8,
  "G_BL_1MA"    : 9,
  "G_BL_A_MEM"  : 10,
}

def get_blender_settings(f3d_mat) -> tuple:
  rdp = f3d_mat.rdp_settings
  cycle0 = (rdp.blend_p1, rdp.blend_a1, rdp.blend_m1, rdp.blend_b1)
  cycle1 = (rdp.blend_p2, rdp.blend_a2, rdp.blend_m2, rdp.blend_b2)

  if f3d_mat.rdp_settings.g_mdsft_cycletype == 'G_CYC_1CYCLE':
    cycle1 = cycle0

  return (
    BL_INP[cycle0[0]], BL_INP[cycle0[1]], BL_INP[cycle0[2]], BL_INP[cycle0[3]],
    BL_INP[cycle1[0]], BL_INP[cycle1[1]], BL_INP[cycle1[2]], BL_INP[cycle1[3]],
  )
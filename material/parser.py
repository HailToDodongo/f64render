from dataclasses import dataclass
import bpy
import numpy as np
import gpu
import time
from .cc import CCSettings, get_cc_settings

@dataclass
class F64Material:
    color_prim: np.ndarray
    color_env: np.ndarray
    cc: CCSettings = None
    cull: str = 'NONE'
    tex0Buff: gpu.types.GPUTexture = None
    tex1Buff: gpu.types.GPUTexture = None

def create_f64_material():
  return F64Material(
     np.array([1, 1, 1, 1], dtype=np.float32),
     np.array([1, 1, 1, 1], dtype=np.float32),
  )

# parses a non-f3d material for the fallback renderer
def node_material_parse(mat: bpy.types.Material) -> F64Material:
  color = np.array([1, 1, 1, 1], dtype=np.float32)
  if mat.use_nodes:
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
      base_color = bsdf.inputs['Base Color'].default_value
      color = np.array([base_color[0], base_color[1], base_color[2], 1], dtype=np.float32)

  return F64Material(color, color)

def f64_material_parse(f3d_mat: any, prev_f64mat: F64Material) -> F64Material:
  f64mat = F64Material(
     color_prim = f3d_mat.prim_color,
     color_env = f3d_mat.env_color,
     cc = get_cc_settings(f3d_mat)
  )

  if f3d_mat.rdp_settings.g_cull_back: f64mat.cull = "BACK"
  if f3d_mat.rdp_settings.g_cull_front: f64mat.cull = "FRONT"

  # Note: doing 'gpu.texture.from_image' seems to cost nothing, caching is not needed
  if f3d_mat.tex0.tex:
      # f3d_mat.tex0.S.low
      # f3d_mat.tex0.T.low
      f64mat.tex0Buff = gpu.texture.from_image(f3d_mat.tex0.tex)

  if f3d_mat.tex1.tex:
    f64mat.tex1Buff = gpu.texture.from_image(f3d_mat.tex1.tex)

  return f64mat
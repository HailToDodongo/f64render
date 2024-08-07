from dataclasses import dataclass
import bpy
import numpy as np
import gpu
import time

from .tile import get_tile_conf
from .cc import get_cc_settings

DRAW_FLAG_FLATSHADE    = (1 << 0)
DRAW_FLAG_FILTER_TRI   = (1 << 1)
DRAW_FLAG_UVGEN_SPHERE = (1 << 2)
DRAW_FLAG_TEX0_MONO    = (1 << 3)
DRAW_FLAG_TEX1_MONO    = (1 << 4)
DRAW_FLAG_DECAL        = (1 << 5)

@dataclass
class F64Material:
    color_prim: np.ndarray
    color_env: np.ndarray
    cc: np.ndarray = None
    tile_conf: np.ndarray = None
    cull: str = 'NONE'
    blend: str = 'NONE'
    depth_test: str = 'LESS_EQUAL'
    depth_write: bool = True
    flags: int = 0
    alphaClip: float = -1.0
    queue: int = 0
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

# @TODO: re-use fast64 logic
def f64_parse_blend_mode(f3d_mat: any, f64mat: F64Material) -> str:
  f64mat.alphaClip = -1
  f64mat.blend = "NONE"
  is_one_cycle = f3d_mat.rdp_settings.g_mdsft_cycletype == "G_CYC_1CYCLE"

  if f3d_mat.rdp_settings.set_rendermode:
    if f3d_mat.rdp_settings.cvg_x_alpha:
        f64mat.alphaClip = 0.75
    elif (
        is_one_cycle
        and f3d_mat.rdp_settings.force_bl
        and f3d_mat.rdp_settings.blend_p1 == "G_BL_CLR_IN"
        and f3d_mat.rdp_settings.blend_a1 == "G_BL_A_IN"
        and f3d_mat.rdp_settings.blend_m1 == "G_BL_CLR_MEM"
        and f3d_mat.rdp_settings.blend_b1 == "G_BL_1MA"
    ):
        f64mat.blend = "ALPHA"
    elif (
        not is_one_cycle
        and f3d_mat.rdp_settings.force_bl
        and f3d_mat.rdp_settings.blend_p2 == "G_BL_CLR_IN"
        and f3d_mat.rdp_settings.blend_a2 == "G_BL_A_IN"
        and f3d_mat.rdp_settings.blend_m2 == "G_BL_CLR_MEM"
        and f3d_mat.rdp_settings.blend_b2 == "G_BL_1MA"
    ):
        f64mat.blend = "ALPHA"

def f64_material_parse(f3d_mat: any, prev_f64mat: F64Material) -> F64Material:
  f64mat = F64Material(
     color_prim = f3d_mat.prim_color,
     color_env = f3d_mat.env_color,
     cc = get_cc_settings(f3d_mat)
  )

  if f3d_mat.rdp_settings.g_cull_back: f64mat.cull = "BACK"
  if f3d_mat.rdp_settings.g_cull_front: f64mat.cull = "FRONT"
  
  f64_parse_blend_mode(f3d_mat, f64mat)

  f64mat.flags = 0 if f3d_mat.rdp_settings.g_shade_smooth else DRAW_FLAG_FLATSHADE
  f64mat.flags |= DRAW_FLAG_FILTER_TRI if (f3d_mat.rdp_settings.g_mdsft_text_filt == 'G_TF_BILERP') else 0
  f64mat.flags |= DRAW_FLAG_UVGEN_SPHERE if f3d_mat.rdp_settings.g_tex_gen else 0
  
  if f3d_mat.draw_layer.oot == 'Transparent':
    f64mat.queue = 1

  if f3d_mat.rdp_settings.zmode == 'ZMODE_DEC':
    f64mat.flags |= DRAW_FLAG_DECAL

  if not f3d_mat.rdp_settings.z_cmp:
    f64mat.depth_test = 'NONE'

  f64mat.depth_write = f3d_mat.rdp_settings.z_upd

  # Note: doing 'gpu.texture.from_image' seems to cost nothing, caching is not needed
  if f3d_mat.tex0.tex:
    f64mat.tex0Buff = gpu.texture.from_image(f3d_mat.tex0.tex)
    if f3d_mat.tex0.tex_format == 'I4' or f3d_mat.tex0.tex_format == 'I8':
      f64mat.flags |= DRAW_FLAG_TEX0_MONO

  if f3d_mat.tex1.tex:
    f64mat.tex1Buff = gpu.texture.from_image(f3d_mat.tex1.tex)
    if f3d_mat.tex1.tex_format == 'I4' or f3d_mat.tex1.tex_format == 'I8':
      f64mat.flags |= DRAW_FLAG_TEX1_MONO

  if f3d_mat.tex0.tex or f3d_mat.tex1.tex:
    f64mat.tile_conf = get_tile_conf(f3d_mat)

  return f64mat
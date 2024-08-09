from dataclasses import dataclass, field
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
DRAW_FLAG_ALPHA_BLEND  = (1 << 6)

@dataclass
class F64Material:
    color_prim: tuple = field(default_factory=lambda: (1, 1, 1, 1))
    lod_prim: tuple = field(default_factory=lambda: (0, 0))
    color_env: tuple = field(default_factory=lambda: (0.5, 0.5, 0.5, 0.5))
    ck: tuple = field(default_factory=lambda: (0, 0, 0, 0, 0, 0, 0, 0))
    convert: tuple = field(default_factory=lambda: (0, 0, 0, 0, 0, 0))
    color_ambient: tuple = None
    color_light: tuple= None
    
    set_prim: bool = False
    set_env: bool = False
    set_ck: bool = False
    set_convert: bool = False
    set_ambient: bool = False
    set_light: bool = False

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
        f64mat.flags |= DRAW_FLAG_ALPHA_BLEND
    elif (
        not is_one_cycle
        and f3d_mat.rdp_settings.force_bl
        and f3d_mat.rdp_settings.blend_p2 == "G_BL_CLR_IN"
        and f3d_mat.rdp_settings.blend_a2 == "G_BL_A_IN"
        and f3d_mat.rdp_settings.blend_m2 == "G_BL_CLR_MEM"
        and f3d_mat.rdp_settings.blend_b2 == "G_BL_1MA"
    ):
        f64mat.blend = "ALPHA"
        f64mat.flags |= DRAW_FLAG_ALPHA_BLEND
  else:
    if f3d_mat.draw_layer.sm64 == '4':
        f64mat.alphaClip = 0.125
    elif f3d_mat.draw_layer.sm64 in ['5', '6','7']:
        f64mat.blend = "ALPHA"
        f64mat.flags |= DRAW_FLAG_ALPHA_BLEND

def f64_material_parse(f3d_mat: any, prev_f64mat: F64Material) -> F64Material:
  f64mat = F64Material(
     color_prim = list(f3d_mat.prim_color),
     lod_prim   = [f3d_mat.prim_lod_min, f3d_mat.prim_lod_frac],
     set_prim   = f3d_mat.set_prim,
     color_env  = list(f3d_mat.env_color),
     set_env    = f3d_mat.set_env,
     ck = list(f3d_mat.key_center) + list(f3d_mat.key_scale) + [0.0], # alpha goes unused, but fixes alignement
     set_ck = f3d_mat.set_key,
     convert=[getattr(f3d_mat, f"k{i}") for i in range(0, 6)],
     set_convert=f3d_mat.set_k0_5,
     color_ambient = list(f3d_mat.ambient_light_color),
     color_light = list(f3d_mat.default_light_color),
     set_ambient = f3d_mat.set_lights,
     set_light   = f3d_mat.set_lights, # shared flag

     flags = 0,
     cc = get_cc_settings(f3d_mat)
  )

  if f3d_mat.rdp_settings.g_cull_back: f64mat.cull = "BACK"
  if f3d_mat.rdp_settings.g_cull_front: f64mat.cull = "FRONT"
  
  f64_parse_blend_mode(f3d_mat, f64mat)

  f64mat.flags |= 0 if f3d_mat.rdp_settings.g_shade_smooth else DRAW_FLAG_FLATSHADE
  f64mat.flags |= DRAW_FLAG_FILTER_TRI if (f3d_mat.rdp_settings.g_mdsft_text_filt == 'G_TF_BILERP') else 0
  f64mat.flags |= DRAW_FLAG_UVGEN_SPHERE if f3d_mat.rdp_settings.g_tex_gen else 0
  
  if f3d_mat.draw_layer.oot == 'Transparent' or f3d_mat.draw_layer.sm64 in ['5', '6','7']:
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
import math
import struct
import bpy
import mathutils
import gpu
from .utils.addon import addon_set_fast64_path
from .mesh.gpu_batch import batch_for_shader
from .material.parser import F64Material, f64_material_parse, node_material_parse
import pathlib
import time
import numpy as np

from .mesh.mesh import MeshBuffers, mesh_to_buffers

f64render_materials_dirty = True
f64render_instance = None
f64render_meshCache: dict[MeshBuffers] = {}
current_ucode = None

# N64 is y-up, blender is z-up
yup_to_zup = mathutils.Quaternion((1, 0, 0), math.radians(90.0)).to_matrix().to_4x4()

UNIFORM_BUFFER_STRUCT = struct.Struct(f"4f 4f 3f i 3f i 4f 4f 4f 8f 2f 6f 2f i i i f")

def cache_del_by_mesh(mesh_name):
  global f64render_meshCache
  for key in list(f64render_meshCache.keys()):
    if f64render_meshCache[key].mesh_name == mesh_name:
      del f64render_meshCache[key]

def obj_has_f3d_materials(obj):
  for slot in obj.material_slots:
    if slot.material.is_f3d and slot.material.f3d_mat:
      return True
  return False

class Fast64RenderEngine(bpy.types.RenderEngine):
  bl_idname = "FAST64_RENDER_ENGINE"
  bl_label = "Fast64 Renderer"
  bl_use_preview = False

  def __init__(self):
    super().__init__()
    addon_set_fast64_path()

    self.shader = None
    self.shader_fallback = None
    self.draw_handler = None
    self.last_ucode = None
        
    self.depth_texture: gpu.types.GPUTexture = None
    self.update_render_size(128, 128)
    bpy.app.handlers.depsgraph_update_post.append(Fast64RenderEngine.mesh_change_listener)
    
  def __del__(self):
    if Fast64RenderEngine.mesh_change_listener in bpy.app.handlers.depsgraph_update_post:
      bpy.app.handlers.depsgraph_update_post.remove(Fast64RenderEngine.mesh_change_listener)
    pass
  
  def update_render_size(self, size_x, size_y):
    if not self.depth_texture or size_x != self.depth_texture.width or size_y != self.depth_texture.height:
      self.depth_texture = gpu.types.GPUTexture((size_x, size_y), format='R32I')

  def init_shader(self):
    if not self.shader:
      print("Compiling shader")

      shaderPath = (pathlib.Path(__file__).parent / "shader").resolve()
      shaderVert = ""
      shaderFrag = ""

      with open(shaderPath / "utils.glsl", "r", encoding="utf-8") as f:
        shaderUtils = f.read()
        shaderVert += shaderUtils
        shaderFrag += shaderUtils

      with open(shaderPath / "defines.glsl", "r", encoding="utf-8") as f:
        shaderDef = f.read()
        shaderVert += shaderDef
        shaderFrag += shaderDef

      with open(shaderPath / "main3d.vert.glsl", "r", encoding="utf-8") as f:
        shaderVert += f.read()

      with open(shaderPath / "main3d.frag.glsl", "r", encoding="utf-8") as f:
        shaderFrag += f.read()

      shader_info = gpu.types.GPUShaderCreateInfo()
      
      with open(shaderPath / "structs.glsl", "r", encoding="utf-8") as f:
        shader_info.typedef_source(f.read())
      
      # vertex -> fragment
      vert_out = gpu.types.GPUStageInterfaceInfo("vert_interface")
      vert_out.no_perspective("VEC4", "cc_shade")
      vert_out.flat("VEC4", "cc_shade_flat")
      vert_out.smooth("VEC4", "cc_env")
      vert_out.smooth("VEC4", "cc_prim_color")
      vert_out.smooth("FLOAT", "cc_prim_lod_frac")
      vert_out.smooth("VEC3", "cc_ck_center")
      vert_out.smooth("VEC3", "cc_ck_scale")
      vert_out.smooth("FLOAT", "cc_k4")
      vert_out.smooth("FLOAT", "cc_k5")
      vert_out.smooth("VEC2", "primDepth")
      vert_out.smooth("VEC4", "uv")
      vert_out.no_perspective("VEC2", "posScreen")
      vert_out.flat("VEC4", "tileSize")
      vert_out.flat("INT", "flags")

      shader_info.push_constant("MAT4", "matMVP")
      shader_info.push_constant("MAT3", "matNorm")
      # TODO: move properties into one big uniform buffer
      shader_info.push_constant("INT", "inFlags")

      shader_info.uniform_buf(0, "UBO_CCData", "ccData")
      shader_info.uniform_buf(1, "UBO_CCConf", "ccConf")
      shader_info.uniform_buf(2, "UBO_TileConf", "tileConf")
      
      shader_info.vertex_in(0, "VEC3", "pos") # keep blenders name keep for better compat.
      shader_info.vertex_in(1, "VEC3", "inNormal")
      shader_info.vertex_in(2, "VEC4", "inColor")
      shader_info.vertex_in(3, "VEC2", "inUV")
      shader_info.vertex_out(vert_out)
      
      shader_info.sampler(0, "FLOAT_2D", "tex0")
      shader_info.sampler(1, "FLOAT_2D", "tex1")
      shader_info.image(3, 'R32I', "INT_2D_ATOMIC", "depth_texture", qualifiers={"READ", "WRITE"})
      shader_info.fragment_out(0, "VEC4", "FragColor")

      shader_info.vertex_source(shaderVert)
      shader_info.fragment_source(shaderFrag)
      
      self.shader = gpu.shader.create_from_info(shader_info)      
      self.shader_fallback = gpu.shader.from_builtin('UNIFORM_COLOR')

  def mesh_change_listener(scene, depsgraph):
    global f64render_meshCache
    global f64render_materials_dirty
    global current_ucode
    # print("################ MESH CHANGE LISTENER ################")  

    if depsgraph.id_type_updated('SCENE'):
      if current_ucode != depsgraph.scene.f3d_type:
        f64render_materials_dirty = True
        current_ucode = depsgraph.scene.f3d_type

    if depsgraph.id_type_updated('MATERIAL'):
      for update in depsgraph.updates:
        # this seems to trigger for all materials if only one changed (@TODO: check if i can get proper updates)
        f64render_materials_dirty = True
      return

    if not depsgraph.id_type_updated('MESH'):
       return

    # This causes the actual object mesh to update after leaving edit-mode
    for update in depsgraph.updates:
      if isinstance(update.id, bpy.types.Mesh):
        cache_del_by_mesh(update.id.name)

  def view_update(self, context, depsgraph):
    if self.draw_handler is None:
      self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_scene, (context, depsgraph), 'WINDOW', 'POST_VIEW')

    # this causes the mesh to update during edit-mode
    for obj in depsgraph.objects:
      if obj.type == 'MESH' and obj.mode == 'EDIT':
        meshID = obj.name + "#" + obj.data.name
        if meshID in f64render_meshCache:
          del f64render_meshCache[meshID]

  def view_draw(self, context, depsgraph):
    self.draw_scene(context, depsgraph)

  def draw_scene(self, context, depsgraph):
    global f64render_meshCache
    global f64render_materials_dirty
    
    # TODO: fixme, after reloading this script during dev, something calls this function
    #       with an invalid reference (viewport?)
    if repr(self).endswith("invalid>"):
        return

    t = time.process_time()

    self.update_render_size(context.region.width, context.region.height)
    self.depth_texture.clear(format='UINT', value=[0])

    self.init_shader()
    self.shader.bind()

    # Enable depth test
    gpu.state.depth_test_set('LESS')
    gpu.state.depth_mask_set(True)

    # global params
    f64_render = depsgraph.scene.fast64.renderSettings
    lightDir0, lightDir1 = f64_render.light0Direction, f64_render.light1Direction
    if not f64_render.useWorldSpaceLighting:
      view_rotation = (mathutils.Quaternion((1, 0, 0), math.radians(90.0)) @ context.region_data.view_matrix.to_quaternion()).to_matrix()
      lightDir0, lightDir1 = lightDir0 @ view_rotation, lightDir1 @ view_rotation
    lightDir0, lightDir1 = lightDir0 @ yup_to_zup, lightDir1 @ yup_to_zup
    lightColor0 = f64_render.light0Color
    lightColor1 = f64_render.light1Color
    ambientColor = f64_render.ambientColor

    lastPrimColor = np.array([1, 1, 1, 1], dtype=np.float32)
    last_prim_lod = np.array([0, 0], dtype=np.float32)
    lastEnvColor = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    last_ck = np.array([0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
    last_convert = np.array([0, 0, 0, 0, 0, 0], dtype=np.float32)

    fallback_objs = []
    for obj in depsgraph.objects:
      if obj.type == 'MESH':

        meshID = obj.name + "#" + obj.data.name

        # check for objects that transitioned from non-f3d to f3d materials
        if meshID in f64render_meshCache:
          renderObj = f64render_meshCache[meshID]
          if len(renderObj.cc_conf) == 0 and obj_has_f3d_materials(obj):
            del f64render_meshCache[meshID]
            
        # Mesh not cached: parse & convert mesh data, then prepare a GPU batch
        if meshID not in f64render_meshCache:
          # print("    -> Update object", meshID)
          mesh = obj.evaluated_get(depsgraph).to_mesh()
          renderObj = f64render_meshCache[meshID] = mesh_to_buffers(mesh)
          renderObj.mesh_name = obj.data.name

          mat_count = len(obj.material_slots)
          renderObj.batch = batch_for_shader(self.shader,
            renderObj.vert,
            renderObj.norm,
            renderObj.color,
            renderObj.uv,
            renderObj.indices
          )

          renderObj.cc_data = [bytes(52 * 4)] * mat_count
          renderObj.cc_conf = [np.zeros(4*4, dtype=np.int32)] * mat_count

          renderObj.ubo_cc_data = [None] * mat_count
          renderObj.ubo_cc_conf = [None] * mat_count
          renderObj.ubo_tile_conf = [None] * mat_count
          renderObj.materials = [None] * mat_count

          for i in range(mat_count):
            renderObj.ubo_cc_data[i] = gpu.types.GPUUniformBuf(renderObj.cc_data[i])
            renderObj.ubo_cc_conf[i] = gpu.types.GPUUniformBuf(renderObj.cc_conf[i])
            renderObj.ubo_tile_conf[i] = gpu.types.GPUUniformBuf(np.empty(4*4, dtype=np.float32))

          obj.to_mesh_clear()
        
        if not obj_has_f3d_materials(obj):
          fallback_objs.append(obj)
          continue
        
    self.shader.image('depth_texture', self.depth_texture)
    
    # Draw opaque objects first, then transparent ones
    #for obj in object_queue[0] + object_queue[1]:
    for layer in range(2):
      for obj in depsgraph.objects:
        if obj.type != 'MESH': continue

        # print("  -> Draw object", meshID)
        meshID = obj.name + "#" + obj.data.name
        renderObj: MeshBuffers = f64render_meshCache[meshID]

        modelview_matrix = obj.matrix_world
        projection_matrix = context.region_data.perspective_matrix
        mvp_matrix = projection_matrix @ modelview_matrix
        normal_matrix = (obj.matrix_world @ context.region_data.view_matrix).to_3x3().inverted().transposed()
        self.shader.uniform_float("matMVP", mvp_matrix)
        self.shader.uniform_float("matNorm", normal_matrix)

        mat_idx = 0        
        for slot in obj.material_slots:
          indices_count = renderObj.index_offsets[mat_idx+1] - renderObj.index_offsets[mat_idx]
          if indices_count == 0: # ignore unused materials
            mat_idx += 1
            continue
          
          f3d_mat = slot.material.f3d_mat                    
          if f64render_materials_dirty or renderObj.materials[mat_idx] is None:
            renderObj.materials[mat_idx] = f64_material_parse(f3d_mat, renderObj.materials[mat_idx])

          f64mat = renderObj.materials[mat_idx]
          if f64mat.queue != layer: # skip if not in current layer
            mat_idx += 1
            continue

          gpu.state.face_culling_set(f64mat.cull)
          gpu.state.blend_set(f64mat.blend)
          gpu.state.depth_test_set(f64mat.depth_test)
          gpu.state.depth_mask_set(f64mat.depth_write)
          
          if f64mat.tex0Buff: self.shader.uniform_sampler("tex0", f64mat.tex0Buff)
          if f64mat.tex1Buff: self.shader.uniform_sampler("tex1", f64mat.tex1Buff)
          self.shader.uniform_int("inFlags", f64mat.flags)

          renderObj.cc_data[mat_idx] = UNIFORM_BUFFER_STRUCT.pack(
            *(f64mat.color_light if f64mat.set_light      else lightColor0),
            *lightColor1,
            *lightDir0,
            0,
            *lightDir1,
            0,
            *(f64mat.color_prim    if f64mat.set_prim     else lastPrimColor),
            *(f64mat.color_env     if f64mat.set_env      else lastEnvColor),
            *(f64mat.color_ambient if f64mat.set_ambient  else ambientColor),
            *(f64mat.ck            if f64mat.set_ck       else last_ck),
            *(f64mat.lod_prim      if f64mat.set_prim     else last_prim_lod),
            *(f64mat.convert       if f64mat.set_convert  else last_convert),
            *f64mat.prim_depth,
            f64mat.geo_mode,
            f64mat.othermode_l,
            f64mat.othermode_h,
            f64mat.alphaClip
          )

          if f64mat.set_prim: lastPrimColor, last_prim_lod = f64mat.color_prim, f64mat.lod_prim
          if f64mat.set_env: lastEnvColor = f64mat.color_env
          if f64mat.set_ck: last_ck = f64mat.ck
          if f64mat.set_convert: last_convert = f64mat.convert
          
          renderObj.ubo_cc_data[mat_idx].update(renderObj.cc_data[mat_idx])                        
          self.shader.uniform_block("ccData", renderObj.ubo_cc_data[mat_idx])
          
          # renderObj.cc_conf[mat_idx][0:16] = f64mat.cc
          renderObj.ubo_cc_conf[mat_idx].update(f64mat.cc)
          self.shader.uniform_block("ccConf", renderObj.ubo_cc_conf[mat_idx])

          if f64mat.tile_conf is not None:
            renderObj.ubo_tile_conf[mat_idx].update(f64mat.tile_conf)
            self.shader.uniform_block("tileConf", renderObj.ubo_tile_conf[mat_idx])

          # @TODO: is frustum-culling necessary, or done by blender?
          
          renderObj.batch.draw_range(self.shader, elem_start=renderObj.index_offsets[mat_idx], elem_count=indices_count)
          mat_idx += 1  

    f64render_materials_dirty = False
    print("Time F3D (ms)", (time.process_time() - t) * 1000)
          
    if len(fallback_objs) > 0:
      t = time.process_time()
      self.shader_fallback.bind()

      for obj in fallback_objs:
        meshID = obj.name + "#" + obj.data.name
        renderObj = f64render_meshCache[meshID]

        # get material (we don't expect any changes here, so caching is fine)
        if renderObj.materials is None or len(renderObj.materials) == 0:
          renderObj.materials = [F64Material()]
          if obj.material_slots:
            mat = obj.material_slots[0].materials[0]
            renderObj.materials[0] = node_material_parse(mat)

        self.shader_fallback.uniform_float("color", renderObj.materials[0].color_prim)

        modelview_matrix = obj.matrix_world
        projection_matrix = context.region_data.perspective_matrix
        mvp_matrix = projection_matrix @ modelview_matrix
        self.shader_fallback.uniform_float("ModelViewProjectionMatrix", mvp_matrix)

        renderObj.batch.draw(self.shader_fallback)
        obj.to_mesh_clear()

      print("Time fallback (ms)", (time.process_time() - t) * 1000)

# By default blender will hide quite a few panels like materials or vertex attributes
# Add this method to override the check blender does by render engine
def get_panels():
    exclude_panels = {
      'VIEWLAYER_PT_filter',
        'VIEWLAYER_PT_layer_passes',
    }
    
    include_panels = {
      'EEVEE_MATERIAL_PT_context_material',
      'MATERIAL_PT_preview'
    }

    panels = []
    for panel in bpy.types.Panel.__subclasses__():
      if hasattr(panel, 'COMPAT_ENGINES'):
        if (('BLENDER_RENDER' in panel.COMPAT_ENGINES and panel.__name__ not in exclude_panels)
          or panel.__name__ in include_panels):
          panels.append(panel)

    return panels

def register():
  global f64render_meshCache
  f64render_meshCache = {}
  # bpy.utils.register_class(Fast64RenderEngine)

  bpy.types.RenderEngine.f64_render_engine = bpy.props.PointerProperty(type=Fast64RenderEngine)
  for panel in get_panels():
    panel.COMPAT_ENGINES.add('FAST64_RENDER_ENGINE')

def unregister():
  global f64render_meshCache
  f64render_meshCache = {}

  # bpy.utils.unregister_class(Fast64RenderEngine)
  del bpy.types.RenderEngine.f64_render_engine

  for panel in get_panels():
    if 'FAST64_RENDER_ENGINE' in panel.COMPAT_ENGINES:
      panel.COMPAT_ENGINES.remove('FAST64_RENDER_ENGINE')


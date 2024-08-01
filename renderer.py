import bpy
import gpu
from .mesh.gpu_batch import batch_for_shader
from .material.parser import create_f64_material, f64_material_parse, node_material_parse
import pathlib
import time
import numpy as np

from .mesh.mesh import MeshBuffers, mesh_to_buffers

f64render_instance = None
f64render_meshCache: dict[MeshBuffers] = {}

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
    self.shader = None
    self.shader_fallback = None
    self.draw_handler = None
    bpy.app.handlers.depsgraph_update_post.append(Fast64RenderEngine.mesh_change_listener)
    
  def __del__(self):
    if Fast64RenderEngine.mesh_change_listener in bpy.app.handlers.depsgraph_update_post:
      bpy.app.handlers.depsgraph_update_post.remove(Fast64RenderEngine.mesh_change_listener)
    pass

  def init_shader(self):
    if not self.shader:
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
      vert_out.smooth("VEC4", "cc_prim")
      vert_out.smooth("VEC4", "uv")
      vert_out.smooth("VEC2", "posScreen")
      vert_out.flat("VEC4", "tileSize")
      vert_out.flat("INT", "flags")

      shader_info.push_constant("VEC4", "ambientColor")
      shader_info.push_constant("MAT4", "matMVP")
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
      shader_info.fragment_out(0, "VEC4", "FragColor")

      shader_info.vertex_source(shaderVert)
      shader_info.fragment_source(shaderFrag)
      
      self.shader = gpu.shader.create_from_info(shader_info)      
      self.shader_fallback = gpu.shader.from_builtin('UNIFORM_COLOR')

  def mesh_change_listener(scene, depsgraph):
    global f64render_meshCache
    # print("################ MESH CHANGE LISTENER ################")  

    if depsgraph.id_type_updated('MATERIAL'):
      for update in depsgraph.updates:
        # print("MATERIAL update", update.id.name)
        # TODO: update materials here and cache
        pass
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
    
    # TODO: fixme, after reloading this script during dev, something calls this function
    #       with an invalid reference (viewport?)
    if repr(self).endswith("invalid>"):
        return

    t = time.process_time()

    self.init_shader()
    self.shader.bind()

    # Enable depth test
    gpu.state.depth_test_set('LESS')
    gpu.state.depth_mask_set(True)

    # global params
    f64_render = depsgraph.scene.fast64.renderSettings
    lightDir0 = f64_render.light0Direction
    lightDir1 = f64_render.light1Direction
    lightColor0 = f64_render.light0Color
    lightColor1 = f64_render.light1Color
    ambientColor = f64_render.ambientColor

    self.shader.uniform_float("ambientColor", ambientColor)

    # @TODO: according to the docs you can re-use 'batch.draw' later in the code (?)
    #        in any case, only re-assign material settings if they changed

    fallback_objs = []
    for obj in depsgraph.objects:
      if obj.type == 'MESH':                

        meshID = obj.name + "#" + obj.data.name

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

          renderObj.cc_data = [np.zeros(4*6, dtype=np.float32)] * mat_count
          renderObj.cc_conf = [np.zeros(4*4, dtype=np.int32)] * mat_count
          
          renderObj.ubo_cc_data = [None] * mat_count
          renderObj.ubo_cc_conf = [None] * mat_count
          renderObj.ubo_tile_conf = [None] * mat_count

          for i in range(mat_count):
            renderObj.ubo_cc_data[i] = gpu.types.GPUUniformBuf(renderObj.cc_data[i])
            renderObj.ubo_cc_conf[i] = gpu.types.GPUUniformBuf(renderObj.cc_conf[i])
            renderObj.ubo_tile_conf[i] = gpu.types.GPUUniformBuf(np.empty(4*4, dtype=np.float32))

          obj.to_mesh_clear()
        
        if not obj_has_f3d_materials(obj):
          fallback_objs.append(obj)
          continue
          
        # print("  -> Draw object", meshID)
        renderObj: MeshBuffers = f64render_meshCache[meshID]

        modelview_matrix = obj.matrix_world
        projection_matrix = context.region_data.perspective_matrix
        mvp_matrix = projection_matrix @ modelview_matrix
        self.shader.uniform_float("matMVP", mvp_matrix)

        mat_idx = 0        
        for slot in obj.material_slots:
          f3d_mat = slot.material.f3d_mat                    
          renderObj.material = f64_material_parse(f3d_mat, renderObj.material)

          # gpu.state.blend_set('ALPHA') # @TODO: Alpha blend

          f64mat = renderObj.material
          gpu.state.face_culling_set(f64mat.cull)
          
          if f64mat.tex0Buff: self.shader.uniform_sampler("tex0", f64mat.tex0Buff)
          if f64mat.tex1Buff: self.shader.uniform_sampler("tex1", f64mat.tex1Buff)
          self.shader.uniform_int("inFlags", f64mat.flags)

          renderObj.cc_data[mat_idx][0:4] = lightColor0
          renderObj.cc_data[mat_idx][4:8] = lightColor1
          renderObj.cc_data[mat_idx][8:11] = lightDir0
          renderObj.cc_data[mat_idx][12:15] = lightDir1
          
          renderObj.cc_data[mat_idx][16:20] = f64mat.color_prim
          renderObj.cc_data[mat_idx][20:24] = f64mat.color_env
          
          renderObj.ubo_cc_data[mat_idx].update(renderObj.cc_data[mat_idx])                        
          self.shader.uniform_block("ccData", renderObj.ubo_cc_data[mat_idx])
          
          # renderObj.cc_conf[mat_idx][0:16] = f64mat.cc
          renderObj.ubo_cc_conf[mat_idx].update(f64mat.cc)
          self.shader.uniform_block("ccConf", renderObj.ubo_cc_conf[mat_idx])

          if f64mat.tile_conf is not None:
            renderObj.ubo_tile_conf[mat_idx].update(f64mat.tile_conf)
            self.shader.uniform_block("tileConf", renderObj.ubo_tile_conf[mat_idx])

          # @TODO: is frustum-culling necessary, or done by blender?
          
          indices_count = renderObj.index_offsets[mat_idx+1] - renderObj.index_offsets[mat_idx]
          renderObj.batch.draw_range(self.shader, elem_start=renderObj.index_offsets[mat_idx], elem_count=indices_count)
          mat_idx += 1

    print("Time F3D (ms)", (time.process_time() - t) * 1000)
    t = time.process_time()

    if len(fallback_objs) > 0:
      self.shader_fallback.bind()

      for obj in fallback_objs:
        meshID = obj.name + "#" + obj.data.name
        renderObj = f64render_meshCache[meshID]

        # get material (we don't expect any changes here, so caching is fine)
        if renderObj.material is None:
          renderObj.material = create_f64_material()
          if obj.material_slots:
            mat = obj.material_slots[0].material
            renderObj.material = node_material_parse(mat)

        self.shader_fallback.uniform_float("color", renderObj.material.color_prim)

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


import bpy
from bpy.app.handlers import persistent
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix
import pathlib
import time
import numpy as np

from .mesh.mesh import mesh_to_buffers

f64render_instance = None
f64render_meshCache = {}

class Fast64RenderEngine(bpy.types.RenderEngine):
  bl_idname = "FAST64_RENDER_ENGINE"
  bl_label = "Fast64 Renderer"
  bl_use_preview = False

  def __init__(self):
    super().__init__()
    self.shader = None
    self.draw_handler = None
    
  def __del__(self):
    pass

  def init_shader(self):
    if not self.shader:
      shaderPath = (pathlib.Path(__file__).parent / "shader").resolve()
      shaderVert = ""
      shaderFrag = ""

      with open(shaderPath / "main3d.vert.glsl", "r", encoding="utf-8") as f:
        shaderVert = f.read()

      with open(shaderPath / "main3d.frag.glsl", "r", encoding="utf-8") as f:
        shaderFrag = f.read()

      self.shader = gpu.types.GPUShader(shaderVert, shaderFrag)

  def view_update(self, context, depsgraph):
    if self.draw_handler is None:
      self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_scene, (context, depsgraph), 'WINDOW', 'POST_VIEW')

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
    lightDir = depsgraph.scene.fast64.renderSettings.lightDirection
    lightColor = depsgraph.scene.fast64.renderSettings.lightColor
    ambientColor = depsgraph.scene.fast64.renderSettings.ambientColor

    self.shader.uniform_float("lightDir", lightDir)
    self.shader.uniform_float("lightColor", lightColor)
    self.shader.uniform_float("ambientColor", ambientColor)

    for obj in depsgraph.objects:
      if obj.type == 'MESH':                
              
        meshName = obj.data.name        

        if not meshName in f64render_meshCache:
          mesh = obj.evaluated_get(depsgraph).to_mesh()
          f64render_meshCache[meshName] = mesh_to_buffers(mesh)
        
        meshBuffers = f64render_meshCache[meshName]

        # Shader uniforms
        material = None
        
        f3d_mat = None
        if obj.material_slots:
          f3d_mat = obj.material_slots[0].material.f3d_mat                    
              
        if f3d_mat.tex0.tex:
          gpuTex0 = gpu.texture.from_image(f3d_mat.tex0.tex)
          self.shader.uniform_sampler("tex0", gpuTex0)

        if f3d_mat.tex1.tex:
          gpuTex1 = gpu.texture.from_image(f3d_mat.tex1.tex)
          self.shader.uniform_sampler("tex1", gpuTex1)

        self.shader.uniform_float("colorPrim", f3d_mat.prim_color)
        self.shader.uniform_float("colorEnv", f3d_mat.env_color)
        
        # Draw object
        batch = batch_for_shader(self.shader, 'TRIS', {
          "inPos": meshBuffers.vert,
          "inNormal": meshBuffers.norm,
          "inColor": meshBuffers.color,
          "inUV": meshBuffers.uv
        })

        modelview_matrix = obj.matrix_world
        projection_matrix = context.region_data.perspective_matrix
        mvp_matrix = projection_matrix @ modelview_matrix
        self.shader.uniform_float("matMVP", mvp_matrix)

        batch.draw(self.shader)
        obj.to_mesh_clear()

    print("Time (ms)", (time.process_time() - t) * 1000)
#        if self.shader:
#            self.shader.unbind()

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

@persistent
def mesh_change_listener(scene, depsgraph):
    global f64render_meshCache
  
    # check if we need to iterate through updates at all
    if not depsgraph.id_type_updated('MESH'):
       return

    # @TODO: when in edit mode, all objects are rendered as usual, except the currently edited one
    #        in the actual draw there seems to be a new object called "Mesh" which doesn't appear in the scene
    #        this seems to be incompatible with the cache / rendering (?), at least nothing is shown in that case (or a "ghost" if reloaded in dev mode)
    for update in depsgraph.updates:
      if isinstance(update.id, bpy.types.Mesh):
        print('Mesh \"{}\" updated.'.format(update.id.name))
        print(f64render_meshCache.keys())

        if update.id.name in f64render_meshCache:
          del f64render_meshCache[update.id.name]

def register():
  global f64render_meshCache
  f64render_meshCache = {}
  # bpy.utils.register_class(Fast64RenderEngine)
  if not mesh_change_listener in bpy.app.handlers.depsgraph_update_post:
    bpy.app.handlers.depsgraph_update_post.append(mesh_change_listener)

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


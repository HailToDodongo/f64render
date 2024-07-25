import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix
import pathlib
import time
import numpy as np

f64render_instance = None

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
        # TODO: fixme, after reload this script during dev. something calls this function
        #       with an invalid reference
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
                mesh = obj.evaluated_get(depsgraph).to_mesh()
                
                # extract vertex data, @TODO: this is relatively slow, try to cache it
                # direct draw seems not possible due to different domains (vertex, face, face-corner)
                mesh.calc_loop_triangles()

                # color_layer = mesh.vertex_colors.active.data if mesh.vertex_colors else None
                color_layer = mesh.color_attributes.get("Col")
                alpha_layer = mesh.color_attributes.get("Alpha")
                uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None

                tDes = time.process_time()

                num_faces = len(mesh.loop_triangles)
                num_corners = num_faces * 3

                face_corners_positions = np.zeros((num_corners, 3), dtype=np.float32)
                face_corners_normals = np.zeros((num_corners, 3), dtype=np.float32)
                face_corners_indices = np.zeros((num_corners, ), dtype=np.int32)

                # map vertices to face-corner
                vertex_positions = np.zeros((len(mesh.vertices), 3), dtype=np.float32)
                mesh.vertices.foreach_get('co', vertex_positions.ravel())

                # map normals to face-corner
                vertex_normals = np.zeros((len(mesh.vertices), 3), dtype=np.float32)
                mesh.vertices.foreach_get('normal', vertex_normals.ravel())

                # Populate the array with vertex positions for each face-corner
                face_corners_start = 0
                for face in mesh.loop_triangles:
                    face_corners_indices[face_corners_start:face_corners_start + 3] = face.vertices
                    face_corners_start += 3

                face_corners_normals = vertex_normals[face_corners_indices]
                face_corners_positions = vertex_positions[face_corners_indices]

                num_loops = len(mesh.loops)
                col = np.zeros((num_loops * 4,), dtype=np.float32)  # RGBA
                color_layer.data.foreach_get('color', col)
                col.shape = (-1, 4)

                uvs = np.zeros((num_loops * 2,), dtype=np.float32)  # UV
                uv_layer.foreach_get('uv', uvs)
                uvs.shape = (-1, 2)

                print(" - Des", (time.process_time() - tDes) * 1000)

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
                  "inPos": face_corners_positions,
                  "inNormal": face_corners_normals,
                  "inColor": col,
                  "inUV": uvs
                })

                modelview_matrix = obj.matrix_world
                projection_matrix = context.region_data.perspective_matrix
                mvp_matrix = projection_matrix @ modelview_matrix
                self.shader.uniform_float("matMVP", mvp_matrix)

                batch.draw(self.shader)
                obj.to_mesh_clear()

        elapsed_time = time.process_time() - t
        print("Time", elapsed_time)
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


def register():
    # bpy.utils.register_class(Fast64RenderEngine)
    bpy.types.RenderEngine.f64_render_engine = bpy.props.PointerProperty(type=Fast64RenderEngine)
    for panel in get_panels():
        panel.COMPAT_ENGINES.add('FAST64_RENDER_ENGINE')

def unregister():
    # bpy.utils.unregister_class(Fast64RenderEngine)
    del bpy.types.RenderEngine.f64_render_engine

    for panel in get_panels():
        if 'FAST64_RENDER_ENGINE' in panel.COMPAT_ENGINES:
          panel.COMPAT_ENGINES.remove('FAST64_RENDER_ENGINE')


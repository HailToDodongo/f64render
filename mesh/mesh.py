from dataclasses import dataclass

import numpy as np
import bpy
import bmesh
import time
import gpu
from ..material.parser import F64Material

# Container for all vertex attributes
@dataclass
class MeshBuffers:
  # input buffers:
    vert: np.ndarray
    color: np.ndarray
    uv: np.ndarray
    norm: np.ndarray
  # render data:
    batch: gpu.types.GPUBatch
    material: F64Material = None
    mesh_name: str = "" # multiple obj. can share the same mesh, store to allow deletion by name

# Converts a blender mesh into buffers to be used by the GPU renderer
# Note that this can be a slow process, so it should be cached externally
# This will only handle mesh data itself, materials are not read out here
def mesh_to_buffers(mesh: bpy.types.Mesh) -> MeshBuffers:
  tDes = time.process_time()
  mesh.calc_loop_triangles()

  # Here we want to transform all attributes into un-indexed arrays of per-vertex data
  # Position + normals are stored per vertex (indexed), colors and uvs are stored per face-corner
  # All need to be normalized to the same length
  
  color_layer = mesh.color_attributes.get("Col")
  alpha_layer = mesh.color_attributes.get("Alpha")
  uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None

  num_corners = len(mesh.loop_triangles) * 3
  # print("Faces: ", num_corners, color_layer)

  positions = np.empty((num_corners, 3), dtype=np.float32)
  normals   = np.empty((num_corners, 3), dtype=np.float32)
  colors    = np.empty((num_corners, 4), dtype=np.float32)
  uvs       = np.empty((num_corners, 2), dtype=np.float32)

  indices   = np.empty((num_corners   ), dtype=np.int32)
  mesh.loop_triangles.foreach_get('vertices', indices)

  # map vertices to unique face-corner
  tmp_vec3 = np.empty((len(mesh.vertices), 3), dtype=np.float32)
  mesh.vertices.foreach_get('co', tmp_vec3.ravel())
  positions = tmp_vec3[indices]

  # map normals to unique face-corner
  mesh.vertices.foreach_get('normal', tmp_vec3.ravel())
  normals = tmp_vec3[indices]

  mesh.loop_triangles.foreach_get('loops', indices)
  
  if uv_layer: 
    uv_layer.foreach_get('uv', uvs.ravel())
    uvs = uvs[indices]
  else:
    uvs.fill(0.0)

  if color_layer:
    colors_tmp = np.empty((len(color_layer.data), 4), dtype=np.float32)
    color_layer.data.foreach_get('color_srgb', colors_tmp.ravel())
    colors = colors_tmp[indices]

    if alpha_layer:
      alpha_layer.data.foreach_get('color', colors_tmp.ravel())
      colors[:, 3] = colors_tmp[indices, 0]

  else:
    colors.fill(1.0)

  print(" - Mesh", (time.process_time() - tDes) * 1000)

  return MeshBuffers(positions, colors, uvs, normals, None)
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
    indices: np.ndarray # global index array, sorted by material
    index_offsets: np.ndarray # offsets for each material in the index array
  # render data:
    batch: gpu.types.GPUBatch
    mat_data: list[np.ndarray]
    ubo_mat_data: list[gpu.types.GPUUniformBuf]
    materials: list[F64Material] = None
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

  # read normals (these contain pre-calculated normals handling  flat, smooth, custom split normals)
  corner_norm = np.empty((len(mesh.corner_normals), 3), dtype=np.float32)
  mesh.corner_normals.foreach_get('vector', corner_norm.ravel())

  mesh.loop_triangles.foreach_get('loops', indices)
  normals = corner_norm[indices]
  
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

  # create map of hidden polygons (we need to map that to triangles)
  poly_hidden = np.empty(len(mesh.polygons), dtype=np.int32)
  mesh.polygons.foreach_get('hide', poly_hidden)

  tri_hidden = np.empty(len(mesh.loop_triangles), dtype=np.int32)
  mesh.loop_triangles.foreach_get('polygon_index', tri_hidden)
  tri_hidden = poly_hidden[tri_hidden]

  # create index buffers for the mesh by material, the data behind it is unindexed
  # this is done to do a cheap split by material
  mat_count = len(mesh.materials)

  mat_indices = np.empty(len(mesh.loop_triangles), dtype=np.int8)
  mesh.loop_triangles.foreach_get('material_index', mat_indices) # materials, e.g.: [0, 1, 0, 1, 2, 1, ...]
  index_array = np.arange(num_corners, dtype=np.int32) # -> [0, 1, 2, 3, 4, 5, ...]
  index_array = index_array.reshape((-1, 3))           # -> [[0, 1, 2], [3, 4, 5], ...]

  # remove faces based on 'tri_hidden' (0=visible, 1=hidden)
  index_array = index_array[tri_hidden == 0]
  mat_indices = mat_indices[tri_hidden == 0]
  
  index_array = index_array[np.argsort(mat_indices)] # sort index_array by value in use_flat (aka material-index)
  index_offsets = np.bincount(mat_indices, minlength=mat_count)    # now get counts of each material, e.g.: [1, 2] where index is material-index
  index_offsets = np.insert(index_offsets, 0, 0)  # prepend 0 to turn counts into offsets
  index_offsets = np.cumsum(index_offsets) * 3    # converted into accumulated offset / mul. by 3 for triangles

  print(" - Mesh", (time.process_time() - tDes) * 1000)

  return MeshBuffers(positions, colors, uvs, normals, index_array, index_offsets, None, None, None, None, None)
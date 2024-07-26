from dataclasses import dataclass

import numpy as np
import bpy
import bmesh
import time

# Container for all vertex attributes
@dataclass
class MeshBuffers:
  vert: np.ndarray
  color: np.ndarray
  uv: np.ndarray
  norm: np.ndarray

# Converts a blender mesh into buffers to be used by the GPU renderer
# Note that this can be a slow process, so it should be cached externally
# This will only handle mesh data itself, materials are not read out here
def mesh_to_buffers(mesh: bpy.types.Mesh) -> MeshBuffers:
  mesh.calc_loop_triangles()

  # Here we want to transform all attributes into "face-corner"-space
  # colors and UVs are already in that, vertices and normals need to be converted
  tDes = time.process_time()
  
  color_layer = mesh.color_attributes.get("Col")
  alpha_layer = mesh.color_attributes.get("Alpha")
  uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None

  num_faces = len(mesh.loop_triangles)
  num_corners = num_faces * 3
  print("Faces: ", num_corners, color_layer)

  positions = np.zeros((num_corners, 3), dtype=np.float32)
  normals   = np.zeros((num_corners, 3), dtype=np.float32)
  colors    = np.zeros((num_corners, 4), dtype=np.float32)
  uvs       = np.zeros((num_corners, 2), dtype=np.float32)
  indices   = np.zeros((num_corners   ), dtype=np.int32  )

  # map vertices to face-corner
  vertex_positions = np.zeros((len(mesh.vertices), 3), dtype=np.float32)
  mesh.vertices.foreach_get('co', vertex_positions.ravel())

  # map normals to face-corner
  vertex_normals = np.zeros((len(mesh.vertices), 3), dtype=np.float32)
  mesh.vertices.foreach_get('normal', vertex_normals.ravel())

  face_corners_start = 0
  for face in mesh.loop_triangles:
    indices[face_corners_start:face_corners_start + 3] = face.vertices
    face_corners_start += 3

  normals = vertex_normals[indices]
  positions = vertex_positions[indices]

  # Now remap vertex color and UVs from the "face-corner" domain into a per-vertex domain
  if color_layer: color_loop = color_layer.data
  if alpha_layer: alpha_loop = alpha_layer.data

  target_idx = 0
  for face in mesh.loop_triangles:
    for j in range(3): # 3 vertices per face
      loop_index = face.loops[j]
      
      if color_loop: colors[target_idx] = color_loop[loop_index].color
      if alpha_loop: colors[target_idx][3] = alpha_loop[loop_index].color[0]
      uvs[target_idx] = uv_layer[loop_index].uv

      target_idx += 1

  print(" - Mesh", (time.process_time() - tDes) * 1000)

  return MeshBuffers(positions, colors, uvs, normals)
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
  alpha_layer = mesh.color_attributes.get("Alpha") # TODO: merge into color
  uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None

  num_faces = len(mesh.loop_triangles)
  num_corners = num_faces * 3
  print("Faces: ", num_corners, color_layer)

  positions = np.zeros((num_corners, 3), dtype=np.float32)
  normals = np.zeros((num_corners, 3), dtype=np.float32)
  indices = np.zeros((num_corners, ), dtype=np.int32)

  # map vertices to face-cornerg
  vertex_positions = np.zeros((len(mesh.vertices), 3), dtype=np.float32)
  mesh.vertices.foreach_get('co', vertex_positions.ravel())

  # map normals to face-corner
  vertex_normals = np.zeros((len(mesh.vertices), 3), dtype=np.float32)
  mesh.vertices.foreach_get('normal', vertex_normals.ravel())

  # Populate the array with vertex positions for each face-corner
  face_corners_start = 0
  for face in mesh.loop_triangles:
    indices[face_corners_star>t:face_corners_start + 3] = face.vertices
    face_corners_start += 3

  normals = vertex_normals[indices]
  positions = vertex_positions[indices]

  colors = np.zeros((num_corners * 4,), dtype=np.float32)  # RGBA
  color_layer.data.foreach_get('color', colors)
  colors.shape = (-1, 4)

  uvs = np.zeros((num_corners * 2,), dtype=np.float32)  # UV
  uv_layer.foreach_get('uv', uvs)
  uvs.shape = (-1, 2)

  print(" - Mesh", (time.process_time() - tDes) * 1000)

  return MeshBuffers(positions, colors, uvs, normals)
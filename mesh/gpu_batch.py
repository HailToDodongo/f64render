import numpy as np
import gpu

# Version of blenders own batch function specific to our vertex layout
# and with the ability to re-use the save vertex data for multiple index-buffers
def multi_batch_for_shader(shader, 
    buff_vert: np.ndarray, buff_norm: np.ndarray, buff_color: np.ndarray, buff_uv: np.ndarray, 
    indices_arr: list[np.ndarray]
) -> list[gpu.types.GPUBatch]:
    type = "TRIS"
    vbo_format = shader.format_calc()
    vbo = gpu.types.GPUVertBuf(vbo_format, len(buff_vert))

    vbo.attr_fill("inPos",    buff_vert)
    vbo.attr_fill("inNormal", buff_norm)
    vbo.attr_fill("inColor",  buff_color)
    vbo.attr_fill("inUV",     buff_uv)

    batches = []
    for indices in indices_arr:
        ibo = gpu.types.GPUIndexBuf(type=type, seq=indices)
        batches.append(gpu.types.GPUBatch(type=type, buf=vbo, elem=ibo))
    return batches

import numpy as np
import gpu

# Stripped down version of blender own batch function, specific to our layout
def batch_for_shader(shader, 
    buff_vert: np.ndarray, buff_norm: np.ndarray, buff_color: np.ndarray, buff_uv: np.ndarray, 
    indices: np.ndarray
) -> list[gpu.types.GPUBatch]:
    type = "TRIS"
    vbo_format = shader.format_calc()
    vbo = gpu.types.GPUVertBuf(vbo_format, len(buff_vert))

    vbo.attr_fill("pos",    buff_vert)
    vbo.attr_fill("inNormal", buff_norm)
    vbo.attr_fill("inColor",  buff_color)
    vbo.attr_fill("inUV",     buff_uv)
    
    ibo = gpu.types.GPUIndexBuf(type=type, seq=indices)
    return gpu.types.GPUBatch(type=type, buf=vbo, elem=ibo)

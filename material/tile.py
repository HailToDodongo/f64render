import numpy as np

def get_tile_conf(f3d_mat) -> np.ndarray:
  t0 = f3d_mat.tex0
  t1 = f3d_mat.tex1

  conf = np.array([
  #    X            Y           Z           W
    t0.S.mask,   t0.T.mask,  t1.S.mask,   t1.T.mask,
    t0.S.shift,  t0.T.shift, t1.S.shift,  t1.T.shift,
    t0.S.low,   -t0.T.low,   t1.S.low,   -t1.T.low,
    t0.S.high,   t0.T.high,  t1.S.high,   t1.T.high,
  ], dtype=np.float32)

  conf[0:8] = 2 ** conf[0:8] # mask/shift are exponents, calc. 2^x
  conf[4:8] = 1 / conf[4:8] # shift is inverted
  
  # quantize the low/high values into 0.25 pixel increments
  conf[8:] = np.round(conf[8:] * 4) / 4

  # if clamp is on, negate the mask value
  if t0.S.clamp: conf[0] = -conf[0]
  if t0.T.clamp: conf[1] = -conf[1]
  if t1.S.clamp: conf[2] = -conf[2]
  if t1.T.clamp: conf[3] = -conf[3]

  # if mirror is on, negate the high value
  if t0.S.mirror: conf[12] = -conf[12]
  if t0.T.mirror: conf[13] = -conf[13]
  if t1.S.mirror: conf[14] = -conf[14]
  if t1.T.mirror: conf[15] = -conf[15]
  
  return conf
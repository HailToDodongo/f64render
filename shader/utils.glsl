#define GAMMA_FACTOR 2.2

vec3 gammaToLinear(in vec3 color)
{
  return pow(color, vec3(GAMMA_FACTOR));
}

vec3 linearToGamma(in vec3 color)
{
  return pow(color, vec3(1.0 / GAMMA_FACTOR));
}

#define mixSelect(amount, a, b) (mix(a, b, float(amount)))
#define flagSelect(flag_mask, a, b) (mixSelect((DRAW_FLAGS & flag_mask) != 0, a, b))
#define geoModeSelect(flag_mask, a, b) (mixSelect((GEO_MODE & flag_mask) != 0, a, b))
#define othermodeHSelect(flag_mask, a, b) mixSelect((material.othermodeH & flag_mask) != 0, a, b)

#define zSource() (OTHER_MODE_L & (1 << G_MDSFT_ZSRCSEL))
#define texFilter() (OTHER_MODE_H & (2 << G_MDSFT_TEXTFILT))

#define boolSelect(cond, a, b) (bool(mix(a, b, cond)))

float noise(in vec2 uv)
{
  return fract(sin(dot(uv, vec2(12.9898, 78.233)))* 43758.5453);
}

vec4 mirrorUV(vec4 uvEnd, vec4 uvIn)
{
  vec4 uvMod2 = mod(uvIn, uvEnd * 2.0 + 1.0);
  return mix(uvMod2, (uvEnd * 2.0) - uvMod2, step(uvEnd, uvMod2));
}

ivec4 wrappedMirror(ivec4 texSize, ivec4 uv)
{
  vec4 mask = abs(material.mask);

  // fetch settings
  vec4 isClamp      = step(material.mask, vec4(1.0));
  vec4 isMirror     = step(material.high, vec4(0.0));
  vec4 isForceClamp = step(mask, vec4(1.0)); // mask == 0 forces clamping
  mask = mix(mask, vec4(256), isForceClamp); // if mask == 0, we also have to ignore it

  // @TODO: do this in vertex shader once initially
  uv.yw = texSize.yw - uv.yw; // invert Y to have 0,0 in the top-left corner
  
  // first apply clamping if enabled (clamp S/T, low S/T -> high S/T)
  vec4 uvClamp = clamp(uv, vec4(0.0), tileSize);
  uv = ivec4(mix(uv, uvClamp, isClamp));

  // then mirror the result if needed (mirror S/T)
  vec4 uvMirror = mirrorUV(mask - vec4(0.5), vec4(uv));
  uv = ivec4(mix(vec4(uv),  uvMirror, isMirror));
  
  // clamp again (mask S/T), this is also done to avoid OOB texture access
  uv = ivec4(mod(uv, min(texSize+1, mask)));
  uv.yw = texSize.yw - uv.yw; // invert Y back
  return uv;
}
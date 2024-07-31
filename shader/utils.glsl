#define GAMMA_FACTOR 2.2

vec3 gammaToLinear(in vec3 color)
{
  return pow(color, vec3(GAMMA_FACTOR));
}

vec3 linearToGamma(in vec3 color)
{
  return pow(color, vec3(1.0 / GAMMA_FACTOR));
}

#define flagSelect(flag_mask, a, b) (mix(a, b, float( (flags & flag_mask) != 0 )))

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
  vec4 mask = abs(tileConf.mask);

  vec4 isClamp      = step(tileConf.mask, vec4(1.0));
  vec4 isMirror     = step(tileConf.high, vec4(0.0));
  vec4 isForceClamp = step(mask, vec4(1.0)); // mask == 0 forces clamping

  mask = mix(mask, vec4(256), isForceClamp); // if mask == 0, we also have to ignore it

  uv.yw = texSize.yw - uv.yw;
  
  vec4 uvMirror = mirrorUV(tileSize + vec4(0.5), vec4(uv));
  uvMirror = mix( vec4(uv),  uvMirror, isMirror);   

  vec4 uvMod = ivec4(mod(uvMirror, mask));
  vec4 uvClamp = mod(clamp(uv, vec4(0.0), tileSize), mask);
  uv = ivec4(mix(uvMod, uvClamp, isClamp));

  uv.yw = texSize.yw - uv.yw;
  return uv;
}
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

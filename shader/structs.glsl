// NOTE: this file is included by blender via 'shader_info.typedef_source(...)'

struct UBO_CCData 
{
  vec4 lightColor[2];
  vec4 lightDir[2];
  vec4 prim_color;
  vec4 env;
  vec4 ambientColor;
  vec4 ck_center;
  vec4 ck_scale;
  float prim_lod_min, prim_lod_frac;
  float k0, k1, k2, k3, k4, k5;
  vec2 primDepth;
  int geoMode, othermodeL, othermodeH;
  float alphaClip;
};

struct UBO_TileConf
{
  // xy = TEX0, zw = TEX1
  vec4 mask; // clamped if < 0, mask = abs(mask)
  vec4 shift;
  vec4 low;
  vec4 high; // if negative, mirrored, high = abs(high)
};

struct UBO_CCConf
{
  ivec4 cc0Color;
  ivec4 cc0Alpha;
  ivec4 cc1Color;
  ivec4 cc1Alpha;
};

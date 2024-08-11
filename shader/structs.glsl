// NOTE: this file is included by blender via 'shader_info.typedef_source(...)'

struct UBO_CCData
{
  ivec4 blender[2];
  ivec4 modes; // geo, other-low, other-high, flags
  vec4 lightColor[2];
  vec4 lightDir[2]; // [0].w is alpha clip
  vec4 prim_color;
  vec4 env;
  vec4 ambientColor;
  vec4 ck_center;
  vec4 ck_scale;
  vec4 primLodDepth;
  vec4 k_0123;
  vec2 k_45;  
};

#define GEO_MODE     ccData.modes.x
#define OTHER_MODE_L ccData.modes.y
#define OTHER_MODE_H ccData.modes.z
#define ALPHA_CLIP   ccData.lightDir[0].w

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

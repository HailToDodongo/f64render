// NOTE: this file is included by blender via 'shader_info.typedef_source(...)'

struct UBO_CCData 
{
  vec4 lightColor;
  vec4 lightDir;
  vec4 prim;
  vec4 env;
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

struct UBO_CCData 
{
  vec4 lightColor;
  vec4 lightDir;
  vec4 prim;
  vec4 env;
};

struct UBO_CCConf 
{
  ivec4 cc0Color;
  ivec4 cc0Alpha;
  ivec4 cc1Color;
  ivec4 cc1Alpha;
};

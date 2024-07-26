in vec4 cc_shade;
in vec4 cc_env;
in vec4 cc_prim;

in vec2 uv;

in flat ivec4 cc0Color;
in flat ivec4 cc0Alpha;
in flat ivec4 cc1Color;
in flat ivec4 cc1Alpha;

uniform sampler2D tex0;
uniform sampler2D tex1;

out vec4 FragColor;

vec3 cc_fetchColor(in int val, in vec4 comb)
{
       if(val == CC_C_COMB       ) return comb.rgb;
  else if(val == CC_C_TEX0       ) return texture_3point(tex0, uv).rgb;
  else if(val == CC_C_TEX1       ) return texture_3point(tex1, uv).rgb;
  else if(val == CC_C_PRIM       ) return cc_prim.rgb;
  else if(val == CC_C_SHADE      ) return cc_shade.rgb;
  else if(val == CC_C_ENV        ) return cc_env.rgb;
  // else if(val == CC_C_CENTER     ) return vec3(0.0); // @TODO
  // else if(val == CC_C_SCALE      ) return vec3(0.0); // @TODO
  else if(val == CC_C_COMB_ALPHA ) return comb.aaa;
  else if(val == CC_C_TEX0_ALPHA ) return texture_3point(tex0, uv).aaa;
  else if(val == CC_C_TEX1_ALPHA ) return texture_3point(tex1, uv).aaa;
  else if(val == CC_C_PRIM_ALPHA ) return cc_prim.aaa;
  else if(val == CC_C_SHADE_ALPHA) return cc_shade.aaa;
  else if(val == CC_C_ENV_ALPHA  ) return cc_env.aaa;
  // else if(val == CC_C_LOD_FRAC   ) return vec3(0.0); // @TODO
  // else if(val == CC_C_PRIM_LOD_FRAC) return vec3(0.0); // @TODO
  // else if(val == CC_C_NOISE      ) return vec3(0.0); // @TODO
  // else if(val == CC_C_K4         ) return vec3(0.0); // @TODO
  // else if(val == CC_C_K5         ) return vec3(0.0); // @TODO
  else if(val == CC_C_1          ) return vec3(1.0);
  return vec3(0.0); // default: CC_C_0
}

float cc_fetchAlpha(in int val, in vec4 comb)
{
       if(val == CC_A_COMB ) return comb.a;
  else if(val == CC_A_TEX0 ) return texture_3point(tex0, uv).a;
  else if(val == CC_A_TEX1 ) return texture_3point(tex1, uv).a;
  else if(val == CC_A_PRIM ) return cc_prim.a;
  else if(val == CC_A_SHADE) return cc_shade.a;
  else if(val == CC_A_ENV  ) return cc_env.a;
  // else if(val == CC_A_LOD_FRAC) return 0.0; // @TODO
  // else if(val == CC_A_PRIM_LOD_FRAC) return 0.0; // @TODO
  else if(val == CC_A_1    ) return 1.0;
  return 0.0; // default: CC_A_0
}

void main() 
{
  vec4 cc0[4];
  vec4 cc1[4];

  vec4 colorOut = vec4(1.0, 1.0, 1.0, 1.0);

  cc0[0].rgb = cc_fetchColor(cc0Color.x, vec4(1.0));
  cc0[1].rgb = cc_fetchColor(cc0Color.y, vec4(1.0));
  cc0[2].rgb = cc_fetchColor(cc0Color.z, vec4(1.0));
  cc0[3].rgb = cc_fetchColor(cc0Color.w, vec4(1.0));

  cc0[0].a = cc_fetchAlpha(cc0Alpha.x, vec4(1.0));
  cc0[1].a = cc_fetchAlpha(cc0Alpha.y, vec4(1.0));
  cc0[2].a = cc_fetchAlpha(cc0Alpha.z, vec4(1.0));
  cc0[3].a = cc_fetchAlpha(cc0Alpha.w, vec4(1.0));

  vec4 cycle0 = (cc0[0] - cc0[1]) * cc0[2] + cc0[3];

  cc1[0].rgb = cc_fetchColor(cc1Color.x, cycle0);
  cc1[1].rgb = cc_fetchColor(cc1Color.y, cycle0);
  cc1[2].rgb = cc_fetchColor(cc1Color.z, cycle0);
  cc1[3].rgb = cc_fetchColor(cc1Color.w, cycle0);

  cc1[0].a = cc_fetchAlpha(cc1Alpha.x, cycle0);
  cc1[1].a = cc_fetchAlpha(cc1Alpha.y, cycle0);
  cc1[2].a = cc_fetchAlpha(cc1Alpha.z, cycle0);
  cc1[3].a = cc_fetchAlpha(cc1Alpha.w, cycle0);

  vec4 ccFinal = (cc1[0] - cc1[1]) * cc1[2] + cc1[3];
  // if(ccFinal.a < alphaThreshold) discard; // @TODO: alpha threshold
  FragColor = ccFinal;
}
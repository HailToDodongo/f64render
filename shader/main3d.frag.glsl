
vec3 cc_fetchColor(in int val, in vec4 shade, in vec4 comb)
{
       if(val == CC_C_COMB       ) return comb.rgb;
  else if(val == CC_C_TEX0       ) return linearToGamma(texture_3point(tex0, uv).rgb);
  else if(val == CC_C_TEX1       ) return linearToGamma(texture_3point(tex1, uv).rgb);
  else if(val == CC_C_PRIM       ) return cc_prim.rgb;
  else if(val == CC_C_SHADE      ) return shade.rgb;
  else if(val == CC_C_ENV        ) return cc_env.rgb;
  // else if(val == CC_C_CENTER     ) return vec3(0.0); // @TODO
  // else if(val == CC_C_SCALE      ) return vec3(0.0); // @TODO
  else if(val == CC_C_COMB_ALPHA ) return comb.aaa;
  else if(val == CC_C_TEX0_ALPHA ) return texture_3point(tex0, uv).aaa;
  else if(val == CC_C_TEX1_ALPHA ) return texture_3point(tex1, uv).aaa;
  else if(val == CC_C_PRIM_ALPHA ) return cc_prim.aaa;
  else if(val == CC_C_SHADE_ALPHA) return shade.aaa;
  else if(val == CC_C_ENV_ALPHA  ) return cc_env.aaa;
  // else if(val == CC_C_LOD_FRAC   ) return vec3(0.0); // @TODO
  // else if(val == CC_C_PRIM_LOD_FRAC) return vec3(0.0); // @TODO
  else if(val == CC_C_NOISE      ) return vec3(noise(posScreen*0.25)); // @TODO
  // else if(val == CC_C_K4         ) return vec3(0.0); // @TODO
  // else if(val == CC_C_K5         ) return vec3(0.0); // @TODO
  else if(val == CC_C_1          ) return vec3(1.0);
  return vec3(0.0); // default: CC_C_0
}

float cc_fetchAlpha(in int val, vec4 shade, in vec4 comb)
{
       if(val == CC_A_COMB ) return comb.a;
  else if(val == CC_A_TEX0 ) return texture_3point(tex0, uv).a;
  else if(val == CC_A_TEX1 ) return texture_3point(tex1, uv).a;
  else if(val == CC_A_PRIM ) return cc_prim.a;
  else if(val == CC_A_SHADE) return shade.a;
  else if(val == CC_A_ENV  ) return cc_env.a;
  // else if(val == CC_A_LOD_FRAC) return 0.0; // @TODO
  // else if(val == CC_A_PRIM_LOD_FRAC) return 0.0; // @TODO
  else if(val == CC_A_1    ) return 1.0;
  return 0.0; // default: CC_A_0
}

/**
 * handles both CC clamping and overflow:
 *        x ≤ -0.5: wrap around
 * -0.5 ≥ x ≤  1.5: clamp to 0-1
 *  1.5 < x       : wrap around
 */
vec4 cc_clampValue(in vec4 value)
{
  vec4 cycle = mod(value + 0.5, 2.0) - 0.5;
  return clamp(cycle, 0.0, 1.0);
}

void main()
{
  vec4 cc0[4]; // inputs for 1. cycle
  vec4 cc1[4]; // inputs for 2. cycle
  vec4 ccValue = vec4(0.0); // result after 1/2 cycle

  vec4 ccShade = flagSelect(DRAW_FLAG_FLATSHADE, cc_shade, cc_shade_flat);

  cc0[0].rgb = cc_fetchColor(ccConf.cc0Color.x, ccShade, ccValue);
  cc0[1].rgb = cc_fetchColor(ccConf.cc0Color.y, ccShade, ccValue);
  cc0[2].rgb = cc_fetchColor(ccConf.cc0Color.z, ccShade, ccValue);
  cc0[3].rgb = cc_fetchColor(ccConf.cc0Color.w, ccShade, ccValue);

  cc0[0].a = cc_fetchAlpha(ccConf.cc0Alpha.x, ccShade, ccValue);
  cc0[1].a = cc_fetchAlpha(ccConf.cc0Alpha.y, ccShade, ccValue);
  cc0[2].a = cc_fetchAlpha(ccConf.cc0Alpha.z, ccShade, ccValue);
  cc0[3].a = cc_fetchAlpha(ccConf.cc0Alpha.w, ccShade, ccValue);

  ccValue = (cc0[0] - cc0[1]) * cc0[2] + cc0[3];

  cc1[0].rgb = cc_fetchColor(ccConf.cc1Color.x, ccShade, ccValue);
  cc1[1].rgb = cc_fetchColor(ccConf.cc1Color.y, ccShade, ccValue);
  cc1[2].rgb = cc_fetchColor(ccConf.cc1Color.z, ccShade, ccValue);
  cc1[3].rgb = cc_fetchColor(ccConf.cc1Color.w, ccShade, ccValue);

  cc1[0].a = cc_fetchAlpha(ccConf.cc1Alpha.x, ccShade, ccValue);
  cc1[1].a = cc_fetchAlpha(ccConf.cc1Alpha.y, ccShade, ccValue);
  cc1[2].a = cc_fetchAlpha(ccConf.cc1Alpha.z, ccShade, ccValue);
  cc1[3].a = cc_fetchAlpha(ccConf.cc1Alpha.w, ccShade, ccValue);

  ccValue = (cc1[0] - cc1[1]) * cc1[2] + cc1[3];
  ccValue = cc_clampValue(ccValue);

  ccValue.rgb = gammaToLinear(ccValue.rgb);
  FragColor = ccValue;
}
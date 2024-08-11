
// allows for a per-pixel atomic access to the depth texture (needed for decals)
#extension GL_ARB_fragment_shader_interlock : enable
layout(pixel_interlock_ordered) in;

#define DECAL_DEPTH_DELTA 100

vec4 quantize3Bit(in vec4 color) {
  return vec4(round(color.rgb * 8.0) / 8.0, step(color.a, 0.5));
}

vec4 quantize4Bit(in vec4 color) {
  return round(color * 16.0) / 16.0; // (16 seems more accurate than 15)
}

vec4 quantizeTexture0(vec4 color) {
  vec4 colorQuant = flagSelect(DRAW_FLAG_TEX0_4BIT, color, quantize4Bit(color));
  return flagSelect(DRAW_FLAG_TEX0_3BIT, colorQuant, quantize3Bit(colorQuant));
}

vec4 quantizeTexture1(vec4 color) {
  vec4 colorQuant = flagSelect(DRAW_FLAG_TEX1_4BIT, color, quantize4Bit(color));
  return flagSelect(DRAW_FLAG_TEX1_3BIT, colorQuant, quantize3Bit(colorQuant));
}

void fetchTex01Filtered(in ivec4 texSize, out vec4 texData0, out vec4 texData1)
{
  // Original 3-point code taken from: https://www.shadertoy.com/view/Ws2fWV (By: cyrb)
  ivec4 uv0 = ivec4(floor(uv));
  vec4 ratio = uv - vec4(uv0);

  ivec2 lower_flag = ivec2(step(0.0, ratio.xz - ratio.yw));
  ivec4 corner = ivec4(
    lower_flag.x, 1 - lower_flag.x,
    lower_flag.y, 1 - lower_flag.y
  );

  ivec4 uv1 = uv0 + corner;
  ivec4 uv2 = uv0 + 1;

  uv0 = wrappedMirror(texSize, uv0);
  uv1 = wrappedMirror(texSize, uv1);
  uv2 = wrappedMirror(texSize, uv2);

  vec4 v0 = vec4(0 - corner);
  vec4 v1 = vec4(1 - corner);
  vec4 v2 = ratio - vec4(corner);

  vec2 den = v0.xw * v1.yz - v1.xw * v0.yz;

  vec2 lambda1 = abs((v2.xz * v1.yw - v1.xz * v2.yw) / den);
  vec2 lambda2 = abs((v0.xz * v2.yw - v2.xz * v0.yw) / den);
  vec2 lambda0 = 1.0 - lambda1 - lambda2;

  texData0 =  quantizeTexture0(texelFetch(tex0, uv1.xy, 0)) * lambda0.x
            + quantizeTexture0(texelFetch(tex0, uv0.xy, 0)) * lambda1.x
            + quantizeTexture0(texelFetch(tex0, uv2.xy, 0)) * lambda2.x;
  
  texData1 =  quantizeTexture1(texelFetch(tex1, uv1.zw, 0)) * lambda0.y
            + quantizeTexture1(texelFetch(tex1, uv0.zw, 0)) * lambda1.y
            + quantizeTexture1(texelFetch(tex1, uv2.zw, 0)) * lambda2.y;
}

vec3 cc_fetchColor(in int val, in vec4 shade, in vec4 comb, in vec4 texData0, in vec4 texData1)
{
       if(val == CC_C_COMB       ) return comb.rgb;
  else if(val == CC_C_TEX0       ) return texData0.rgb;
  else if(val == CC_C_TEX1       ) return texData1.rgb;
  else if(val == CC_C_PRIM       ) return ccData.prim_color.rgb;
  else if(val == CC_C_SHADE      ) return shade.rgb;
  else if(val == CC_C_ENV        ) return ccData.env.rgb;
  else if(val == CC_C_CENTER     ) return ccData.ck_center.rgb;
  else if(val == CC_C_SCALE      ) return ccData.ck_scale.rgb;
  else if(val == CC_C_COMB_ALPHA ) return comb.aaa;
  else if(val == CC_C_TEX0_ALPHA ) return texData0.aaa;
  else if(val == CC_C_TEX1_ALPHA ) return texData1.aaa;
  else if(val == CC_C_PRIM_ALPHA ) return ccData.prim_color.aaa;
  else if(val == CC_C_SHADE_ALPHA) return shade.aaa;
  else if(val == CC_C_ENV_ALPHA  ) return ccData.env.aaa;
  // else if(val == CC_C_LOD_FRAC   ) return vec3(0.0); // @TODO
  else if(val == CC_C_PRIM_LOD_FRAC) return vec3(ccData.primLodDepth[1]);
  else if(val == CC_C_NOISE      ) return vec3(noise(posScreen*0.25));
  else if(val == CC_C_K4         ) return vec3(ccData.k_45[0]);
  else if(val == CC_C_K5         ) return vec3(ccData.k_45[1]);
  else if(val == CC_C_1          ) return vec3(1.0);
  return vec3(0.0); // default: CC_C_0
}

float cc_fetchAlpha(in int val, vec4 shade, in vec4 comb, in vec4 texData0, in vec4 texData1)
{
       if(val == CC_A_COMB ) return comb.a;
  else if(val == CC_A_TEX0 ) return texData0.a;
  else if(val == CC_A_TEX1 ) return texData1.a;
  else if(val == CC_A_PRIM ) return ccData.prim_color.a;
  else if(val == CC_A_SHADE) return shade.a;
  else if(val == CC_A_ENV  ) return ccData.env.a;
  // else if(val == CC_A_LOD_FRAC) return 0.0; // @TODO
  else if(val == CC_A_PRIM_LOD_FRAC) return ccData.primLodDepth[1];
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


vec4 blendColor(vec4 oldColor, vec4 newColor)
{
  // @TODO
  return mix(oldColor, newColor, newColor.a);
}

void main()
{
  vec4 cc0[4]; // inputs for 1. cycle
  vec4 cc1[4]; // inputs for 2. cycle
  vec4 ccValue = vec4(0.0); // result after 1/2 cycle

  vec4 uvTex = uv;

  vec4 ccShade = geoModeSelect(G_SHADE_SMOOTH, cc_shade_flat, cc_shade);

  // pre-calc UVs for both textures + get two extra points for 3-point sampling
  // then sample both textures even if none are used. This is done to vectorize both
  // the UV and clamp/mirror calculations, as well as minimize the number of texture fetches
  vec4 texData0, texData1;
  ivec4 texSize = ivec4(textureSize(tex0, 0), textureSize(tex1, 0)) - 1;

  if(texFilter() == G_TF_BILERP)
  {
    fetchTex01Filtered(texSize, texData0, texData1);
  } else {
    ivec4 uv0 = ivec4(floor(uv + 0.5));
    uv0 = wrappedMirror(texSize, uv0);

    texData0 = quantizeTexture0(texelFetch(tex0, uv0.xy, 0));
    texData1 = quantizeTexture0(texelFetch(tex1, uv0.zw, 0));
  }

  // handle I4/I8
  texData0.rgb = linearToGamma(texData0.rgb);
  texData1.rgb = linearToGamma(texData1.rgb);
  texData0.rgba = flagSelect(DRAW_FLAG_TEX0_MONO, texData0.rgba, texData0.rrrr);
  texData1.rgba = flagSelect(DRAW_FLAG_TEX1_MONO, texData1.rgba, texData1.rrrr);

  // @TODO: emulate other formats, e.g. quantization?

  cc0[0].rgb = cc_fetchColor(ccConf.cc0Color.x, ccShade, ccValue, texData0, texData1);
  cc0[1].rgb = cc_fetchColor(ccConf.cc0Color.y, ccShade, ccValue, texData0, texData1);
  cc0[2].rgb = cc_fetchColor(ccConf.cc0Color.z, ccShade, ccValue, texData0, texData1);
  cc0[3].rgb = cc_fetchColor(ccConf.cc0Color.w, ccShade, ccValue, texData0, texData1);

  cc0[0].a = cc_fetchAlpha(ccConf.cc0Alpha.x, ccShade, ccValue, texData0, texData1);
  cc0[1].a = cc_fetchAlpha(ccConf.cc0Alpha.y, ccShade, ccValue, texData0, texData1);
  cc0[2].a = cc_fetchAlpha(ccConf.cc0Alpha.z, ccShade, ccValue, texData0, texData1);
  cc0[3].a = cc_fetchAlpha(ccConf.cc0Alpha.w, ccShade, ccValue, texData0, texData1);

  ccValue = (cc0[0] - cc0[1]) * cc0[2] + cc0[3];

  cc1[0].rgb = cc_fetchColor(ccConf.cc1Color.x, ccShade, ccValue, texData0, texData1);
  cc1[1].rgb = cc_fetchColor(ccConf.cc1Color.y, ccShade, ccValue, texData0, texData1);
  cc1[2].rgb = cc_fetchColor(ccConf.cc1Color.z, ccShade, ccValue, texData0, texData1);
  cc1[3].rgb = cc_fetchColor(ccConf.cc1Color.w, ccShade, ccValue, texData0, texData1);
  
  cc1[0].a = cc_fetchAlpha(ccConf.cc1Alpha.x, ccShade, ccValue, texData0, texData1);
  cc1[1].a = cc_fetchAlpha(ccConf.cc1Alpha.y, ccShade, ccValue, texData0, texData1);
  cc1[2].a = cc_fetchAlpha(ccConf.cc1Alpha.z, ccShade, ccValue, texData0, texData1);
  cc1[3].a = cc_fetchAlpha(ccConf.cc1Alpha.w, ccShade, ccValue, texData0, texData1);

  ccValue = (cc1[0] - cc1[1]) * cc1[2] + cc1[3];
  ccValue = cc_clampValue(ccValue);

  ccValue.rgb = gammaToLinear(ccValue.rgb);

  if(ccValue.a < ALPHA_CLIP)discard;

  ccValue.a = flagSelect(DRAW_FLAG_ALPHA_BLEND, 1.0, ccValue.a);

  // Depth / Decal handling:
  // We manually write & check depth values in an image in addition to the actual depth buffer.
  // This allows us to do manual compares (e.g. decals) and discard fragments based on that.
  // In order to guarantee proper ordering, we both use atomic image access as well as an invocation interlock per pixel.
  // If those where not used, a race-condition will occur where after a depth read happens, the depth value might have changed,
  // leading to culled faces writing their color values even though a new triangles has a closer depth value already written.
  ivec2 screenPosPixel = ivec2(gl_FragCoord.xy);

  int currDepth = int(mixSelect(zSource() == G_ZS_PRIM, gl_FragCoord.w * 0xFFFFF, ccData.primLodDepth.z));
  int writeDepth = int(flagSelect(DRAW_FLAG_DECAL, currDepth, -0xFFFFFF));

  beginInvocationInterlockARB();
  {
    int oldDepth = imageAtomicMax(depth_texture, screenPosPixel, writeDepth);
    int depthDiff = int(mixSelect(zSource() == G_ZS_PRIM, abs(oldDepth - currDepth), ccData.primLodDepth.w));

    bool depthTest = writeDepth >= oldDepth;
    if((flags & DRAW_FLAG_DECAL) != 0) {
      depthTest = depthDiff <= DECAL_DEPTH_DELTA;
    }
    
    uint oldColorInt = imageLoad(color_texture, screenPosPixel).r;
    vec4 oldColor = unpackUnorm4x8(oldColorInt);
    
    ccValue = blendColor(oldColor, ccValue);
    ccValue.a = 1.0;  
    uint writeColor = packUnorm4x8(ccValue);

    if(depthTest) {
      // Note: a basic 'imageStore' cause coherence issues (@TODO: why?)
      imageAtomicExchange(color_texture, screenPosPixel, writeColor.r);
    }
  }
  
  endInvocationInterlockARB();

  // Since we only need our own depth/color textures, there is no need to actually write out fragments.
  // It may seem like we could use the calc. color from out texture and set it here,
  // but it will result in incoherent results (e.g. blocky artifacts due to depth related race-conditions)
  // This is most prominent on decals.
  discard;
}

void main() 
{
  // Directional light
  vec3 norm = inNormal;
  vec3 normScreen = normalize(matNorm * norm);

  cc_shade = inColor;
  flags = inFlags;

  vec4 lightTotal = vec4(ccData.ambientColor.rgb, 0.0);
  for(int i=0; i<2; ++i) {
    float lightStren = max(dot(norm, ccData.lightDir[i].xyz), 0.0);
    lightTotal += ccData.lightColor[i] * (lightStren * 2);
  }

  lightTotal.rgb = linearToGamma(clamp(lightTotal.rgb, 0.0, 1.0));

  vec3 shadeWithLight = geoModeSelect(G_PACKED_NORMALS, lightTotal.rgb, cc_shade.rgb * lightTotal.rgb);
  cc_shade.rgb = geoModeSelect(G_LIGHTING, cc_shade.rgb, shadeWithLight);
  cc_shade = clamp(cc_shade, 0.0, 1.0);
  cc_shade.a = 1.0;
  cc_shade_flat = cc_shade;

  cc_env.rgb = linearToGamma(ccData.env.rgb);
  cc_prim_color.rgb = linearToGamma(ccData.prim_color.rgb);
  cc_env.a = ccData.env.a;
  cc_prim_color.a = ccData.prim_color.a;
  cc_prim_lod_frac = ccData.prim_lod_frac;
  cc_ck_center = linearToGamma(ccData.ck_center.rgb);
  cc_ck_scale = ccData.ck_scale.rgb;
  cc_k4 = ccData.k4;
  cc_k5 = ccData.k5;
  primDepth = ccData.primDepth;

  vec2 uvGen = geoModeSelect(G_TEX_GEN, inUV, normScreen.xy * 0.5 + 0.5);

  // turn UVs ionto pixel-space, apply first tile settings
  ivec4 texSize = ivec4(textureSize(tex0, 0), textureSize(tex1, 0));
  // we simulate UVs in pixel-space, since there is only one UV set, we scale by the first texture size
  uv = uvGen.xyxy * texSize.xyxy;
  // apply tileConf.shift from top left of texture:
  uv.yw = texSize.yw - uv.yw - 1;
  uv *= tileConf.shift;
  uv.yw = texSize.yw - uv.yw - 1;

  uv = uv - (tileConf.shift * 0.5) - tileConf.low;

  tileSize = abs(tileConf.high) - abs(tileConf.low);

  // @TODO: uvgen (f3d + t3d)
  // forward CC (@TODO: do part of this here? e.g. prim/env/shade etc.)

  vec3 posQuant = pos;
  //posQuant = round(posQuant * 10) * 0.1;
  
  gl_Position = matMVP * vec4(posQuant, 1.0);
  posScreen = gl_Position.xy / gl_Position.w;
  
  // quantize depth to what the RDP has (16bit)
  gl_Position.z = ceil(gl_Position.z * 0x7FFF) / 0x7FFF;
  // move the depth ever so slightly to avoid z-fighting with blenders own overlays
  // e.g. transparent faces in face-edit mode, lines & points
  float depthOffset = flagSelect(DRAW_FLAG_DECAL, 0.00006, 0.0); // don't offset decals to make manual depth checks work later
  gl_Position.z += depthOffset;
}
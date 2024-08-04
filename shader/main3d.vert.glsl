
void main() 
{
  // Directional light
  vec3 norm = normalize(matNorm * inNormal);

  vec4 lightTotal = vec4(ccData.ambientColor.rgb, 0.0);
  for(int i=0; i<2; ++i) {
    float lightStren = max(dot(norm, ccData.lightDir[i].xyz), 0.0);
    lightTotal += ccData.lightColor[i] * lightStren*lightStren;
  }

  lightTotal = clamp(lightTotal, 0.0, 1.0);
  
  // Ambient light
  cc_shade.rgb = linearToGamma(lightTotal.rgb);
  cc_shade.a = 1.0;
  cc_shade *= inColor;
  cc_shade_flat = cc_shade;

  cc_env.rgb = linearToGamma(ccData.env.rgb);
  cc_prim.rgb = linearToGamma(ccData.prim.rgb);
  cc_env.a = ccData.env.a;
  cc_prim.a = ccData.prim.a;

  flags = inFlags;
  vec2 uvGen = flagSelect(DRAW_FLAG_UVGEN_SPHERE, inUV, norm.xy * 0.5 + 0.5);

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
  
  // move the depth ever so slightly to avoid z-fighting with blenders own overlays
  // e.g. transparent faces in face-edit mode, lines & points
  gl_Position.z += 0.00001;
}

void main() 
{
  // Directional light
  vec3 norm = normalize(inNormal);
  float lightStren = max(dot(norm, ccData.lightDir.xyz), 0.0);
  vec4 lightTotal = ccData.lightColor * lightStren;

  lightTotal += vec4(ambientColor.rgb, 0.0);
  lightTotal = clamp(lightTotal, 0.0, 1.0);  
  
  // Ambient light
  cc_shade.rgb = linearToGamma(lightTotal.rgb);
  cc_shade.a = 1.0;
  cc_shade *= inColor;
  cc_shade_flat = cc_shade;

  cc_env.rgb = linearToGamma(ccData.env.rgb);
  cc_prim.rgb = linearToGamma(ccData.prim.rgb);

  // turn UVs ionto pixel-space, apply first tile settings
  ivec4 texSize = ivec4(textureSize(tex0, 0), textureSize(tex1, 0));
  uv = vec4(inUV, inUV) * texSize;
  // apply tileConf.shift from top left of texture:
  uv.yw = texSize.yw - uv.yw - 1;
  uv *= tileConf.shift;
  uv.yw = texSize.yw - uv.yw - 1;

  uv = uv - (tileConf.shift * 0.5) - tileConf.low;

  tileSize = abs(tileConf.high) - abs(tileConf.low);

  flags = inFlags;

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
uniform mat4 matMVP;

uniform vec4 colorPrim;
uniform vec4 colorEnv;

uniform vec4 lightColor;
uniform vec3 lightDir;
uniform vec4 ambientColor;

in vec3 inPos;
in vec3 inNormal;
in vec4 inColor;
in vec2 inUV;

out vec4 colorShade;
out vec2 uv;

void main() 
{
  // Directional light
  vec3 norm = normalize(inNormal);
  float lightStren = max(dot(norm, lightDir), 0.0);
  vec4 lightTotal = lightColor * lightStren;

  lightTotal += vec4(ambientColor.rgb, 0.0);
  
  // Ambient light
  colorShade = colorPrim * lightTotal;
  colorShade.a = 1.0;

  if(colorEnv.a == 0.5) { // bs to keep env color
    colorShade *= colorEnv;
  }

  colorShade *= inColor;
  uv = inUV;

  gl_Position = matMVP * vec4(inPos, 1.0);
}
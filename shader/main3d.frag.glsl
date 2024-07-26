in vec4 colorShade;
in vec2 uv;

uniform sampler2D tex0;

out vec4 FragColor;

void main() 
{
  vec4 colorOut = colorShade * vec4(1.0, 1.0, 1.0, 1.0);

  vec4 tex0Color = texture(tex0, uv);
  
  colorOut.a = 1.0;
  tex0Color.a = 1.0;
  FragColor = colorOut * tex0Color;
}
// Taken from: https://www.shadertoy.com/view/Ws2fWV
// By: cyrb

// to use on shadertoy.com
// DKO's 3point GLSL shader

#if 0
float find_mipmap_level(in vec2 texture_coordinate) // in texel units
{
    vec2  dx_vtc        = dFdx(texture_coordinate);
    vec2  dy_vtc        = dFdy(texture_coordinate);
    float delta_max_sqr = max(dot(dx_vtc, dx_vtc), dot(dy_vtc, dy_vtc));
    float mml = 0.5 * log2(delta_max_sqr);
    return max( 0, mml ); // Thanks @Nims
}
#endif

/*
 * Unlike Nintendo's documentation, the N64 does not use
 * the 3 closest texels.
 * The texel grid is triangulated:
 *
 *     0 .. 1        0 .. 1
 *   0 +----+      0 +----+
 *     |   /|        |\   |
 *   . |  / |        | \  |
 *   . | /  |        |  \ |
 *     |/   |        |   \|
 *   1 +----+      1 +----+
 *
 * If the sampled point falls above the diagonal,
 * The top triangle is used; otherwise, it's the bottom.
 */

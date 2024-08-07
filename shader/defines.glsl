// CC Color inputs
#define CC_C_0             0
#define CC_C_1             1
#define CC_C_COMB          2
#define CC_C_TEX0          3
#define CC_C_TEX1          4
#define CC_C_PRIM          5
#define CC_C_SHADE         6
#define CC_C_ENV           7
#define CC_C_CENTER        8
#define CC_C_SCALE         9
#define CC_C_COMB_ALPHA    10
#define CC_C_TEX0_ALPHA    11
#define CC_C_TEX1_ALPHA    12
#define CC_C_PRIM_ALPHA    13
#define CC_C_SHADE_ALPHA   14
#define CC_C_ENV_ALPHA     15
#define CC_C_LOD_FRAC      16
#define CC_C_PRIM_LOD_FRAC 17
#define CC_C_NOISE         18
#define CC_C_K4            19
#define CC_C_K5            20

// CC Alpha inputs
#define CC_A_0             0
#define CC_A_1             1
#define CC_A_COMB          2
#define CC_A_TEX0          3
#define CC_A_TEX1          4
#define CC_A_PRIM          5
#define CC_A_SHADE         6
#define CC_A_ENV           7
#define CC_A_LOD_FRAC      8
#define CC_A_PRIM_LOD_FRAC 9

// Draw flags (custom for the shader)
#define DRAW_FLAG_FLATSHADE    (1 << 0)
#define DRAW_FLAG_FILTER_TRI   (1 << 1)
#define DRAW_FLAG_UVGEN_SPHERE (1 << 2)
#define DRAW_FLAG_TEX0_MONO    (1 << 3)
#define DRAW_FLAG_TEX1_MONO    (1 << 4)
#define DRAW_FLAG_DECAL        (1 << 5)

struct TileConf {
  vec2 mask;
  vec2 shift;
  vec2 low;
  vec2 high;
};
// CC Color inputs
#define CC_C_COMB          0
#define CC_C_TEX0          1
#define CC_C_TEX1          2
#define CC_C_PRIM          3
#define CC_C_SHADE         4
#define CC_C_ENV           5
#define CC_C_CENTER        6
#define CC_C_SCALE         6
#define CC_C_COMB_ALPHA    7
#define CC_C_TEX0_ALPHA    8
#define CC_C_TEX1_ALPHA    9
#define CC_C_PRIM_ALPHA    10
#define CC_C_SHADE_ALPHA   11
#define CC_C_ENV_ALPHA     12
#define CC_C_LOD_FRAC      13
#define CC_C_PRIM_LOD_FRAC 14
#define CC_C_NOISE         7
#define CC_C_K4            7
#define CC_C_K5            15
#define CC_C_1             6
#define CC_C_0             31

// CC Alpha inputs
#define CC_A_COMB          0
#define CC_A_TEX0          1
#define CC_A_TEX1          2
#define CC_A_PRIM          3
#define CC_A_SHADE         4
#define CC_A_ENV           5
#define CC_A_LOD_FRAC      0
#define CC_A_PRIM_LOD_FRAC 6
#define CC_A_1             6
#define CC_A_0             7

// Draw flags (custom for the shader)
#define DRAW_FLAG_FLATSHADE (1 << 0)
precision mediump float;

uniform    mat4   u_pvmMatrix;
uniform    float  u_aspectRatio;
uniform    float  u_alpha;
uniform    float  u_fovy;
uniform    float  u_minWidth;
uniform    int    u_darkenNarrowLine;
attribute  vec3   a_p;
attribute  vec3   a_a;
attribute  vec3   a_b;
attribute  float  a_y;
attribute  float  a_width;
attribute  vec4   a_color;
varying    vec4   v_color;
varying    float  v_y;
varying    float  v_w;


void main(void) {
    vec4 p4 = u_pvmMatrix * vec4(a_p, 1.);

    vec4 a4 = u_pvmMatrix * vec4(a_a, 1.),
         b4 = u_pvmMatrix * vec4(a_b, 1.);

    vec2 a2 = (p4.w * a4.xy - a4.w * p4.xy) / (p4.w * p4.w),
         b2 = (p4.w * b4.xy - b4.w * p4.xy) / (p4.w * p4.w);

    a2.x *= u_aspectRatio;
    b2.x *= u_aspectRatio;
    a2 = normalize(a2);
    b2 = normalize(b2);

    vec2 t2 = normalize(b2 - a2),
         v2 = vec2(-t2.y, t2.x);

	v_color = a_color;
    v_color.a *= u_alpha;

    float cosecPhi = clamp(1. / (a2.y*v2.x - a2.x*v2.y), -2., 2.),
          width = a_width / u_fovy,
          minWidth = u_minWidth * p4.w;

    if (width < minWidth) {
        if (u_darkenNarrowLine == 1) {
            v_color.a *= width / minWidth;
        }
        width = minWidth;
    }

    vec2 d2 = width * a_y * v2 * cosecPhi;
    d2.x /= u_aspectRatio;
    p4.xy += d2;
    gl_Position = p4;

    v_y = a_y;
    v_w = gl_Position.w;
}
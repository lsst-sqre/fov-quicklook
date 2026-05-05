uniform    mat4   u_pvMatrix, u_mMatrix;
uniform    float  u_width, u_height;
attribute  vec3   a_vCoord;
attribute  vec2   a_size, a_tCoord;
attribute  vec4   a_color;
varying    vec2   v_tCoord;
varying    vec4   v_color;

void main(void) {
    gl_Position = u_pvMatrix * vec4(a_vCoord, 1.);
    gl_Position.x += a_size.x / u_width * gl_Position.w;
    gl_Position.y += a_size.y / u_height * gl_Position.w;
    v_tCoord = a_tCoord;
    v_color = a_color;
}
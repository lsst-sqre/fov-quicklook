precision mediump float;

uniform    mat4          u_pvMatrix;
uniform    float         u_radius;
attribute  vec3          a_position;
varying    vec3          v_position;

void main(void) {
    gl_Position = u_pvMatrix * vec4(u_radius * a_position, 1.);
    v_position = u_radius * a_position;
}
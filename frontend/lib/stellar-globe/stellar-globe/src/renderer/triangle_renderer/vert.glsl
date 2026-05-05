precision mediump float;

uniform mat4 u_pvmMatrix;
attribute vec3 a_position;
attribute vec4 a_color;
varying vec4 v_color;

void main(void) {
    gl_Position = u_pvmMatrix * vec4(a_position, 1.);
    v_color = a_color;
}

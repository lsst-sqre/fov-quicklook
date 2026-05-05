uniform    mat4   u_pvMatrix;
uniform    float  u_minSize;
uniform    float  u_alpha;
uniform    float  u_fovy;
uniform    float  u_bufferHeight;
uniform    int    u_darkenSmallPoint;
attribute  vec3   a_position;
attribute  float  a_size;
attribute  vec4   a_color;
varying    vec4   v_color;
varying    float  v_w;



void main(void) {
    gl_Position = u_pvMatrix * vec4(a_position, 1.);
    float pointSize = u_bufferHeight * a_size / (gl_Position.w * u_fovy);
    float screenSize = max(pointSize, u_minSize);
    float r = pointSize / screenSize;
    v_color = a_color;
    v_color.a *= u_darkenSmallPoint != 0 ? u_alpha * r * r : u_alpha;
    gl_PointSize = screenSize;
    v_w = gl_Position.w;
}
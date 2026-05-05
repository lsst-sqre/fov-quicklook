vec3 simple_rgb(in vec3 raw, in float beta, in float a, in float bias, in float b0) {
    raw += b0;
    vec3 color = asinh(beta * raw) / asinh(vec3(beta));
    color = a * color + vec3(bias);
    return color;
}

const vec3 colorTable[16] = vec3[](vec3(0.0, 0.1262, 0.3015), vec3(0.0, 0.1743, 0.4172), vec3(0.0576, 0.2187, 0.4301), vec3(0.1923, 0.2667, 0.4214), vec3(0.2728, 0.3144, 0.4206), vec3(0.3398, 0.3622, 0.427), vec3(0.401, 0.4104, 0.44), vec3(0.4589, 0.4593, 0.4604), vec3(0.5196, 0.5095, 0.4737), vec3(0.5852, 0.5615, 0.4709), vec3(0.6529, 0.6153, 0.46), vec3(0.7225, 0.671, 0.4409), vec3(0.7942, 0.7288, 0.4129), vec3(0.8681, 0.7889, 0.3739), vec3(0.9444, 0.8518, 0.3195), vec3(1.0, 0.9131, 0.268));

vec3 colormap(float value) {
    value = clamp(value, 0.0, 1.0);
    int n = colorTable.length() - 1;
    float scaledValue = value * float(n);
    int index = int(floor(scaledValue));
    float fraction = scaledValue - float(index);
    index = clamp(index, 0, n);
    return mix(colorTable[index], colorTable[index + 1], fraction);
}

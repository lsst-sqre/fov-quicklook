
const vec3 colorTable[16] = vec3[](vec3(0.18995, 0.07176, 0.23217), vec3(0.25369, 0.26327, 0.65406), vec3(0.27691, 0.44145, 0.91328), vec3(0.24427, 0.60937, 0.99697), vec3(0.13278, 0.77165, 0.8858), vec3(0.10342, 0.896, 0.715), vec3(0.27597, 0.97092, 0.51653), vec3(0.53255, 0.99919, 0.30581), vec3(0.72596, 0.9647, 0.2064), vec3(0.88331, 0.86553, 0.21719), vec3(0.98, 0.73, 0.22161), vec3(0.99297, 0.55214, 0.15417), vec3(0.94084, 0.35566, 0.07031), vec3(0.83926, 0.20654, 0.02305), vec3(0.68602, 0.09536, 0.00481), vec3(0.49321, 0.01963, 0.00955));

vec3 colormap(float value) {
    value = clamp(value, 0.0, 1.0);
    int n = colorTable.length() - 1;
    float scaledValue = value * float(n);
    int index = int(floor(scaledValue));
    float fraction = scaledValue - float(index);
    index = clamp(index, 0, n - 1);
    return mix(colorTable[index], colorTable[index + 1], fraction);
}

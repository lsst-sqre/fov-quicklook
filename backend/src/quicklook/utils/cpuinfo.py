def is_x86_v2() -> bool:
    """
    Function to check if the CPU is x86_v2 (supports AVX)

    Returns:
        bool: True if x86_v2 (supports AVX), False otherwise
    """
    # Open /proc/cpuinfo and read its content
    with open("/proc/cpuinfo", "r") as cpuinfo_file:
        cpuinfo = cpuinfo_file.read()

    # Extract the flags line
    flags_line = next((line for line in cpuinfo.splitlines() if line.startswith("flags")), None)
    if not flags_line:  # pragma: no cover
        return False

    # Extract flags as a list
    flags = flags_line.split(":")[1].strip().split()

    # Check for the presence of AVX
    if "avx" in flags:
        return True
    else:
        return False

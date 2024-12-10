import pytest
from unittest.mock import mock_open, patch
from quicklook.utils.cpuinfo import is_x86_v2

def test_is_x86_v2_with_avx():
    mock_cpuinfo = "flags\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx lm constant_tsc rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 cx16 xtpr pdcm sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault epb invpcid_single pti ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid mpx rdseed adx smap clflushopt clwb intel_pt xsaveopt xsavec xgetbv1 xsaves dtherm ida arat pln pts hwp hwp_notify hwp_act_window hwp_epp md_clear flush_l1d"
    with patch("builtins.open", mock_open(read_data=mock_cpuinfo)):
        assert is_x86_v2() is True

def test_is_x86_v2_without_avx():
    mock_cpuinfo = "flags\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx lm constant_tsc rep_good nopl xtopology nonstop_tsc cpuid aperfmperf pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 cx16 xtpr pdcm sse4_1 sse4_2 movbe popcnt tsc_deadline_timer aes xsave f16c rdrand lahf_lm abm 3dnowprefetch cpuid_fault epb invpcid_single pti ssbd ibrs ibpb stibp tpr_shadow vnmi flexpriority ept vpid fsgsbase tsc_adjust bmi1 avx2 smep bmi2 erms invpcid mpx rdseed adx smap clflushopt clwb intel_pt xsaveopt xsavec xgetbv1 xsaves dtherm ida arat pln pts hwp hwp_notify hwp_act_window hwp_epp md_clear flush_l1d"
    with patch("builtins.open", mock_open(read_data=mock_cpuinfo)):
        assert is_x86_v2() is False

def test_is_x86_v2_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        with pytest.raises(Exception):
            is_x86_v2()

def test_is_x86_v2_general_exception():
    with patch("builtins.open", side_effect=Exception):
        with pytest.raises(Exception):
            assert is_x86_v2() is False

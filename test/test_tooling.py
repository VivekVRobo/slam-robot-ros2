from pathlib import Path
from tools import config_lint, urdf_lint, map_metrics, odom_metrics, release_gate

ROOT = Path(__file__).resolve().parents[1]

def test_config_lint():
    assert config_lint.lint(ROOT) == []

def test_urdf_lint():
    assert urdf_lint.lint(ROOT / "urdf/robot.urdf.xacro") == []

def test_map_metrics_ratios_sum_to_one():
    m = map_metrics.summarize(ROOT / "examples/sample_map.pgm")
    assert abs(m["occupied_ratio"] + m["free_ratio"] + m["unknown_ratio"] - 1.0) < 1e-9

def test_binary_pgm_support(tmp_path):
    p = tmp_path / "map.pgm"
    p.write_bytes(b"P5\n2 2\n255\n" + bytes([0, 255, 128, 255]))
    m = map_metrics.summarize(p)
    assert m["cells"] == 4
    assert m["occupied_ratio"] == 0.25
    assert m["free_ratio"] == 0.5

def test_odom_metrics():
    m = odom_metrics.summarize(ROOT / "examples/sample_odom.csv")
    assert m["samples"] == 5
    assert 19.9 < m["mean_rate_hz"] < 20.1
    assert m["max_translation_step_m"] < 0.01

def test_reference_gate_passes():
    ok, missing = release_gate.evaluate("reference", ROOT)
    assert ok and missing == []

def test_hardware_gate_is_blocked_without_evidence():
    ok, missing = release_gate.evaluate("hardware-mapping-validated", ROOT)
    assert not ok
    assert "hardware_mapping_passed" in missing

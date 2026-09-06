from pathlib import Path
import importlib.util
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_hardware_profile_template_is_valid_but_not_measured():
    mod = load_tool("hardware_profile_lint")
    data = yaml.safe_load((ROOT / "config/hardware_profile.yaml").read_text())
    assert mod.lint(data, False) == []
    assert mod.lint(data, True)


def test_wheel_calibration_math():
    mod = load_tool("wheel_calibration")
    assert abs(mod.radius_scale(2.0, 1.9) - (2.0 / 1.9)) < 1e-12
    assert abs(mod.separation_scale(6.283185307, 6.5) - (6.5 / 6.283185307)) < 1e-12


def test_example_manifest_is_structurally_hardware_only():
    mod = load_tool("evidence_manifest")
    path = ROOT / "evidence/manifest.example.yaml"
    data = yaml.safe_load(path.read_text())
    assert mod.lint(data, path.parent, False) == []

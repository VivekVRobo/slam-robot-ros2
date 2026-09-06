import subprocess,sys

def test_simulation_lint():
    subprocess.check_call([sys.executable,'tools/simulation_lint.py'])

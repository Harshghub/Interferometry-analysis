import subprocess

ans = subprocess.call([r"/home/tiqi/src/Interferometry-analysis/.venv/bin/python",r"/home/tiqi/src/Interferometry-analysis/measurement/measurement_with_log.py","--config","config2.json"])
if ans == 0:
    print("measurement with config2.json Command executed.")
else:
    print("measurement with config2.json Command failed.")

ans = subprocess.call([r"/home/tiqi/src/Interferometry-analysis/.venv/bin/python",r"/home/tiqi/src/Interferometry-analysis/measurement/measurement_with_alternating_modulation.py","--config","config.json"])
if ans == 0:
    print("alternating modulation measurement with config.json Command executed.")
else:
    print("alternating modulation measurement with config.json Command failed.")
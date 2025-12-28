import subprocess
ans = subprocess.call([r"C:\Users\hupad\Desktop\Interferometry-analysis\.venv\Scripts\python.exe",r"C:\Users\hupad\Desktop\Interferometry-analysis\measurement\modulation_modulator.py","--modulation","off"])
if ans == 0:
    print("Command executed.")
else:
    print("Command failed.")
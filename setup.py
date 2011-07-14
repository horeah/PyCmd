from cx_Freeze import setup, Executable

setup(
    name = "PyCmd",
    version = "0.8",
    description = "Smart windows shell",
    executables = [Executable("PyCmd.py")],
    options = {"build_exe": {"icon": "PyCmd.ico"}})



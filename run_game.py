import sys
import os
import platform


def main():
    py_exec = sys.executable
    game_path = os.path.join(os.path.dirname(__file__), "main.py")
    if platform.system() == "Windows":
        # Use startfile for double-click, fallback to os.system
        try:
            import subprocess

            subprocess.Popen([py_exec, game_path], shell=True)
        except Exception:
            os.system(f'"{py_exec}" "{game_path}"')
    elif platform.system() == "Darwin":
        # Mac: open Terminal and run
        try:
            # Use osascript to open Terminal and run the script
            script = f'tell application "Terminal" to do script "{py_exec} {game_path}"'
            os.system(f'osascript -e "{script}"')
        except Exception:
            os.system(f'"{py_exec}" "{game_path}"')
    else:
        os.system(f'"{py_exec}" "{game_path}"')


if __name__ == "__main__":
    main()

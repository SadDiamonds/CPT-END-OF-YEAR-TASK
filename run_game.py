import sys
import os
import platform


def main():
    py_exec = sys.executable
    game_path = os.path.join(os.path.dirname(__file__), "main.py")
    if platform.system() == "Windows":
        os.system(f'"{py_exec}" "{game_path}"')
    else:
        os.system(f'"{py_exec}" "{game_path}"')


if __name__ == "__main__":
    main()

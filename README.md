# CPT END OF YEAR TASK

## How to Run (Windows & Mac)

### Option 1: Run with Python

Make sure you have Python 3 installed. Then run:

```sh
python3 run_game.py
```

Or, if you want to run directly:

```sh
python3 main.py
```

### Option 2: Create a Standalone Executable

You can use [PyInstaller](https://pyinstaller.org/) to create a single executable for Windows or Mac:

#### Install PyInstaller
```sh
pip install pyinstaller
```

#### Build Executable
```sh
pyinstaller --onefile run_game.py
```

The executable will be in the `dist/` folder. Double-click or run from terminal:

- Windows: `dist/run_game.exe`
- Mac: `dist/run_game`

### Notes
- The game saves progress in `data/save.json`.
- If you see color issues, make sure your terminal supports ANSI colors.
- If you get a missing package error, run:
	```sh
	pip install colorama
	```

## Troubleshooting
- If you see errors about missing modules, install them with `pip install <modulename>`.
- For best results, use a terminal window with at least 80x24 size.
# CPT END OF YEAR TASK
 INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL INCREMENTAL 

# ascii_art.py — Unique terminal descent inspired art

try:
    from colorama import Fore
except ImportError:
    class _ColorCodes:
        BLACK = RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = ""
        LIGHTBLACK_EX = LIGHTRED_EX = LIGHTGREEN_EX = LIGHTYELLOW_EX = ""
        LIGHTBLUE_EX = LIGHTMAGENTA_EX = LIGHTCYAN_EX = ""

    Fore = _ColorCodes()

LAYER_0_DESK = [
        "╔═══════════════════════╗",
        "║     Just your desk    ║",
        "╠═══════════════════════╣",
        "║                       ║",
        "║                       ║",
        "║                       ║",
        "║                       ║",
        "║                       ║",
        "║                       ║",
        "║                       ║",
        "║                       ║",
        "║                       ║",
        "╚═══════════════════════╝"
]

UPGRADE_ART = {
    "keyboard": [
        "       ┌───────┐       ",
        "       │ ▓ ▓ ▓ │       ",
        "       └───────┘       ",
    ],
    "monitor": [
        "      ┌─────────┐      ",
        "      │         │      ",
        "      └─────────┘      ",
    ],
    "coffee": [
        " ( )                  ",
        " ===                  ",
        " |_|                  ",
    ],
    "dual_monitors": [
        "  ┌───────┐ ┌───────┐  ",
        "  │       │ │       │  ",
        "  └───────┘ └───────┘  ",
    ],
    "mech_keyboard": [
        "   ┌────────────────┐  ",
        "   │ ▓▓ ▓▓ ▓▓ ▓▓ ▓▓ │  ",
        "   └────────────────┘  ",
    ],
}

EVENT_ANIMATIONS = {
    "campfire": {
        "frames": [
            ["   (   )   ", "    ) (    ", "   (___)   "],
            ["    ) (    ", "   (   )   ", "    ) (    "],
        ],
        "color": Fore.LIGHTYELLOW_EX,
        "delay": 0.4,
    },
    "relic": {
        "frames": [
            ["  ◇     ◇  ", "    ◇◇    ", "  ◇     ◇  "],
            ["    ◇◇    ", "  ◇    ◇  ", "    ◇◇    "],
        ],
        "color": Fore.CYAN,
        "delay": 0.45,
    },
    "secret": {
        "frames": [
            ["┌──────┐", "│ ░░░░ │", "│ ░◇░░ │", "│ ░░░░ │", "└──────┘"],
            ["┌──────┐", "│ ░░░░ │", "│ ░░◇░ │", "│ ░░░░ │", "└──────┘"],
            ["┌──────┐", "│ ░░░░ │", "│ ░░░◇ │", "│ ░░░░ │", "└──────┘"],
        ],
        "color": Fore.BLUE,
        "delay": 0.25,
    },
}

RPG_DEFAULT_ICON_ART = [
    "┌────┐",
    "│ ?? │",
    "│ ?? │",
    "└────┘",
]

RPG_ICON_ART = {
    "game": [
        "┌──────────┐",
        "│ █▓██▓██  │",
        "│  GAME.EXE│",
        "│  ENTER→  │",
        "└──────────┘",
    ],
    "safari": [
        "┌──────────┐",
        "│  ╲ ╱  ☼  │",
        "│   ⌖  /   │",
        "│  ╱ ╲     │",
        "└──────────┘",
    ],
    "trash": [
        "┌──────────┐",
        "│  ______  │",
        "│ | ____ | │",
        "│ |______| │",
        "└──────────┘",
    ],
}

RPG_ICON_HEIGHT = max(len(art) for art in list(RPG_ICON_ART.values()) + [RPG_DEFAULT_ICON_ART])
RPG_ICON_WIDTH = max(
    max(len(line) for line in art)
    for art in list(RPG_ICON_ART.values()) + [RPG_DEFAULT_ICON_ART]
)

ENEMY_ASCII_FRAMES = [
    [
        "  /\\  ",
        " ( oo )",
        "  \\__/ ",
    ],
    [
        "  /\\  ",
        " ( -- )",
        "  /__\\",
    ],
]

BREACH_DOOR_CLOSED_ART = [
    "          ________________          ",
    "         /______________/|         ",
    "        /______________/ |         ",
    "       /______________/| |         ",
    "      | |   ______   | | |        ",
    "      | |  |  __  |  | | |        ",
    "      | |  | |  | |  | | |        ",
    "      | |  | |__| |  | | |        ",
    "      | |  |______|  | | |        ",
    "      | |     ||     | | |        ",
    "      | |     ||  o  | | |        ",
    "      |_|_____|\\_____|_|_|        ",
]

BREACH_DOOR_OPEN_ART = [
    "          ______________________________        ",
    "         /_____________________________/|       ",
    "        /_____________________________/ |       ",
    "        |   ________      ________    | |       ",
    "        |  |  ____  |    |  ____  |   | |       ",
    "        |  | |    | |    | |    | |   | |       ",
    "        |  | |____| |    | |____| |   | |       ",
    "        |  |________|    |________|   | |       ",
    "        |       ___    ___    ___     | |       ",
    "        |      |___|  |___|  |___|    | |       ",
    "        |   ___[___]__keyboard___    | |       ",
    "        |  /_____________________/|  | |       ",
    "        | /_____________________/ |  | |       ",
    "        |/_____________________/  |__| |       ",
    "        /______________________/_____/        ",
    "        \\____________________/_____/         ",
]

BREACH_KEY_ART = [
    "      ____                           ",
    " ____/ __ \\_____>>>                 ",
    "|____| |  | |_____|                 ",
    "      | |__| |                      ",
    "      |  __  |                      ",
    "      | |  | |                      ",
    "      | |  | |                      ",
    "      | |__| |                      ",
    "      |______|                      ",
    "         ||                         ",
    "         <>                         ",
    "                                    ",
]


def _shift_art_block(art, spaces):
    pad = " " * max(0, spaces)
    return [pad + line for line in art]


def _combine_art_blocks(left, right):
    height = max(len(left), len(right))
    left_lines = left + ["" for _ in range(height - len(left))]
    right_lines = right + ["" for _ in range(height - len(right))]
    return [left_lines[i] + right_lines[i] for i in range(height)]


def _build_breach_unlock_frames():
    frames = []
    for offset in (0, 4, 8):
        key = _shift_art_block(BREACH_KEY_ART, offset)
        frames.append(_combine_art_blocks(key, BREACH_DOOR_CLOSED_ART))
    frames.append(BREACH_DOOR_OPEN_ART)
    return frames


BREACH_DOOR_UNLOCK_FRAMES = _build_breach_unlock_frames()
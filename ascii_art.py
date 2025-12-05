# ascii_art.py — Unique terminal descent inspired art

# -----------------------------
# Layer 0 — Workstation / Desk
# -----------------------------
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

RPG_DEFAULT_ICON_ART = [
    "┌────┐",
    "│ ?? │",
    "│ ?? │",
    "└────┘",
]

RPG_ICON_ART = {
    "game": [
        "┌──────────┐",
        "│ █▓██▓██ │",
        "│  GAME.EXE│",
        "│  ENTER→  │",
        "└──────────┘",
    ],
    "safari": [
        "┌──────────┐",
        "│  ╲ ╱  ☼ │",
        "│   ⌖  /  │",
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
    "               _______________________               ",
    "              / _____________________ \\              ",
    "             / /#####################\\ \\             ",
    "            / /#######################\\ \\            ",
    "           | |#########################| |           ",
    "           | |##########|###|##########| |           ",
    "           | |##########|###|##########| |           ",
    "           | |##########|###|##########| |           ",
    "           | |##########|###|##########| |           ",
    "           | |#########################| |           ",
    "           | |#########################| |           ",
    "           |_|_________________________|_|           ",
]

BREACH_DOOR_OPEN_ART = [
    "               __________     __________               ",
    "              / ________\\   //________ \\              ",
    "             / /######/ /   \\ \\######\\ \\             ",
    "            / /######/ /     \\ \\######\\ \\            ",
    "           | |######/ /       \\ \\######| |           ",
    "           | |#####/ /         \\ \\#####| |           ",
    "           | |####/ /           \\ \\####| |           ",
    "           | |###/ /             \\ \\###| |           ",
    "           | |##/ /               \\ \\##| |           ",
    "           | |#/ /                 \\ \\#| |           ",
    "           | |  /                   \\  | |           ",
    "           |_|_/                     \\_|_|           ",
]

BREACH_KEY_ART = [
    "        ________                                       ",
    "=======/ ______ \\===========>                        ",
    "      /_/ ____ \\\\                                  ",
    "         | || |                                      ",
    "         | || |                                      ",
    "         | || |                                      ",
    "         | || |                                      ",
    "         | || |                                      ",
    "         | || |                                      ",
    "         |_|\\_/                                      ",
    "                                                      ",
    "                                                      ",
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
# config.py

# Base resource values
BASE_MONEY_GAIN = 1.0  # money gained per work cycle before modifiers
BASE_WORK_DELAY = 5.0  # seconds per work cycle (base)
BASE_MONEY_MULT = 1.0  # base multiplier (other multipliers multiply this)

# Focus (temporary boost) config
FOCUS_UNLOCK_COST_INSP = 0  # if you want inspiration cost for unlocking (unused)
FOCUS_BOOST_FACTOR = (
    0.5  # while focus active, work delay is multiplied by this (faster)
)
FOCUS_DURATION = 12  # how many seconds focus lasts
FOCUS_CHARGE_PER_EARN = (
    12  # how many 'focus points' earned per completed work (max 100)
)
FOCUS_MAX = 100

# Inspiration reset rates
INSPIRATION_CONVERT_DIV = 50  # money // DIV gives inspiration when resetting

# Motivation system
MOTIVATION_MAX = 100
MOTIVATION_DRAIN_PER_WORK = 1
MAX_MOTIVATION_MULT = 3.0


# COFFEEEEEE
STEAM_SPEED = 0.1  # fraction of a line per tick (slower for Minecraft effect)
STEAM_CHANCE = 0.2  # chance to emit a new puff per render
STEAM_SPREAD = 3  # max horizontal offset from center
STEAM_LIFETIME = 8  # number of lines before disappearing
STEAM_CHARS = ["~", "^", "."]

# UI / layout
MIN_BOX_WIDTH = 50  # don't make the box narrower than this
BOX_MARGIN = 4  # left/right margin in terminal columns

# TEMPLATE {"id": "", "name":"", "cost": ,"type": "", "value": , "unlocked": False},

UPGRADES = [
    {
        "id": "keyboard",
        "name": "New Keyboard",
        "cost": 20,
        "type": "mult",
        "value": 1.5,
        "unlocked": True,
    },
    {
        "id": "Dev_upg",
        "name": "Dev_upg",
        "cost": 1,
        "type": "mult",
        "value": 10000000,
        "unlocked": False,
    },
    {
        "id": "coffee",
        "name": "Coffee!!!!!",
        "cost": 200,
        "type": "reduce_delay",
        "value": 0.75,
        "unlocked": False,
    },
    # coffee here divides delay (we'll treat 'value' as a factor to multiply work_delay by)
    {
        "id": "monitor",
        "name": "New Monitor",
        "cost": 1000,
        "type": "add",
        "value": 3.0,
        "unlocked": False,
    },
    {
        "id": "focus_meter",
        "name": "Ability to lock in",
        "cost": 5000,
        "type": "unlock_focus",
        "value": 0,
        "unlocked": False,
    },
]

INSPIRE_UPGRADES = [
    {
        "id": "inspire_motiv",
        "name": "Motivation",
        "cost": 1,
        "type": "unlock_motivation",
        "value": 1,
        "max_level": 1,
        "desc": "A buff that decays over work",
    },
    {
        "id": "inspire_2",
        "name": "Efficient Worker",
        "base_cost": 1,
        "type": "money_mult",
        "level": 0,
        "max_level": 10,
        "cost_mult": 1.45,
        "base_value": 3,
        "value_mult": 1.25,
        "desc": "base $x3, $x1.25 compounding per lvl",
    },
    {
        "id": "inspire_auto_work",
        "name": "Auto-generation",
        "cost": 250,
        "type": "auto_work",
        "value": 1,
        "max_level": 1,
        "desc": "Generates $ at a reduced rate",
    },
    {
        "id": "inspire_3",
        "name": "Efficient Worker",
        "cost": 100,
        "type": "money_mult",
        "value": 10000,
        "max_level": 1,
        "desc": "$xPLACEHOLDER",
    },
    {
        "id": "inspire_4",
        "name": "Master Mind",
        "cost": 200,
        "type": "focus_max",
        "value": 200,
        "max_level": 1,
        "desc": "xPLACEHOLDER focus cap",
    },
]

BORDERS = {
    0: {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"},
    1: {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║"},
    2: {"tl": "▓", "tr": "▓", "bl": "▓", "br": "▓", "h": "█", "v": "█"},
    3: {"tl": "◆", "tr": "◆", "bl": "◆", "br": "◆", "h": "─", "v": "│"},
    4: {"tl": "▛", "tr": "▜", "bl": "▙", "br": "▟", "h": "▀", "v": "▌"},
}


# FORMATTING NUMBERS CUZ FUNNY
def format_number(n):
    neg = n < 0
    n = abs(n)

    # Named tiers up to 1e33
    suffixes = [
        (1e33, "De"),  # Decillion
        (1e30, "No"),  # Nonillion
        (1e27, "Oc"),  # Octillion
        (1e24, "Sp"),  # Septillion
        (1e21, "Sx"),  # Sextillion
        (1e18, "Qn"),  # Quintillion
        (1e15, "Qd"),  # Quadrillion
        (1e12, "T"),  # Trillion
        (1e9, "B"),  # Billion
        (1e6, "M"),  # Million
        (1e3, "K"),  # Thousand
    ]

    for value, symbol in suffixes:
        if n >= value:
            s = f"{n / value:.2f}".rstrip("0").rstrip(".")
            return f"-{s}{symbol}" if neg else f"{s}{symbol}"

    # Once it goes past 1e33, show exponent form (like 1.23e45)
    if n >= 1e33:
        s = f"{n:.2e}"  # scientific notation
        return f"-{s}" if neg else s

    # Small numbers
    s = f"{n:.2f}".rstrip("0").rstrip(".")
    return f"-{s}" if neg else s

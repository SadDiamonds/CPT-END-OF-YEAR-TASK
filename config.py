# config.py

# Base resource values
BASE_MONEY_GAIN = 1.0  # money gained per work cycle before modifiers
BASE_WORK_DELAY = 10.0  # seconds per work cycle (base)
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
CAFFEINE_POINT_RATE = 1  # caffeine points gained per second when coffee is owned

# UI / layout
MIN_BOX_WIDTH = 50  # don't make the box narrower than this
BOX_MARGIN = 4  # left/right margin in terminal columns

# TEMPLATE {"id": "", "name":"", "cost": ,"type": "", "value": , "unlocked": False},

UPGRADE_REPLACEMENT = {
    "mech_keyboard": "keyboard",
    "dual_monitors": "monitor",
}

DESK_ORDER = [
    "ergonomic_chair",
    "keyboard",
    "mech_keyboard",  
    "coffee",
    "monitor",
    "dual_monitors",  
]

UPGRADES = [
    {
        "id": "keyboard",
        "name": "New Keyboard",
        "cost": 20,
        "type": "mult",
        "base_value": 2,
        "unlocked": True,
    },
    {
        "id": "coffee",
        "name": "Coffee!!!!!",
        "cost": 100,
        "type": "reduce_delay",
        "base_value": 0.5,
        "unlocked": False,
    },
    # coffee here divides delay (we'll treat 'value' as a factor to multiply work_delay by)
    {
        "id": "monitor",
        "name": "New Monitor",
        "cost": 500,
        "type": "add",
        "base_value": 1000000000.0,
        "unlocked": False,
    },
    {
        "id": "ergonomic_chair",
        "name": "Ergonomic Chair",
        "cost": 1500,
        "type": "mult",
        "base_value": 3,
        "unlocked": False,
    },
    {
        "id": "dual_monitors",
        "name": "Dual Monitors",
        "cost": 3000,
        "type": "add",
        "base_value": 20.0,
        "unlocked": False,
    },
    {
        "id": "mech_keyboard",
        "name": "Mechanical Keyboard",
        "cost": 5000,
        "type": "mult",
        "base_value": 5.0,
        "unlocked": False,
    }
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
        "cost_mult": 1.75,
        "base_value": 1.5,
        "value_mult": 1.25,
        "desc": "base $x1.5, $x1.25 compounding per lvl",
    },
    {
        "id": "inspire_auto_work",
        "name": "Auto-generation",
        "cost": 1,
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

INSPIRATION_MILESTONES = [
    {
        "inspirations_required": 1,
        "reward_type": "xmult",
        "reward_value": 3.0
    },
    {
        "inspirations_required": 2,
        "reward_type": "+mult",
        "reward_value": 50.0
    },
    {
        "inspirations_required": 5,
        "reward_type": "-cd",
        "reward_value": 0.75
    },
    # add more milestones as needed
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

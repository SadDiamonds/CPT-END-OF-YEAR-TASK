BASE_MONEY_GAIN = 1.0
BASE_WORK_DELAY = 10.0
BASE_MONEY_MULT = 10.0

FOCUS_BOOST_FACTOR = 0.5
FOCUS_DURATION = 12
FOCUS_CHARGE_PER_EARN = 12
FOCUS_MAX = 100

INSPIRATION_UNLOCK_MONEY = 100_000
CONCEPTS_UNLOCK_MONEY = 100_000_000

MOTIVATION_MAX = 100
MAX_MOTIVATION_MULT = 3.0

STEAM_SPEED = 0.1
STEAM_CHANCE = 0.2
STEAM_SPREAD = 3
STEAM_LIFETIME = 8
STEAM_CHARS = ["~", "^", "."]
CAFFEINE_POINT_RATE = 1

MIN_BOX_WIDTH = 50
BOX_MARGIN = 4

UPGRADES = [
    {
        "id": "keyboard",
        "name": "Basic Keyboard",
        "cost": 100,
        "type": "mult",
        "base_value": 1.25,
        "value_mult": 1.17,
        "max_level": 5,
        "cost_mult": 2.0,
        "desc": "Your first upgrade!. $1.25x, +17% per level",
        "unlocked": True,
    },
    {
        "id": "coffee",
        "name": "Coffee",
        "cost": 500,
        "type": "reduce_delay",
        "base_value": 0.97,
        "value_mult": 0.95,
        "max_level": 3,
        "cost_mult": 2.5,
        "desc": "Caffeine 4ever. Reduces autowork by 3%, -5% per level",
        "unlocked": False,
    },
    {
        "id": "cup_holder",
        "name": "Cup Holder",
        "cost": 400,
        "type": "add",
        "base_value": 1.0,
        "max_level": 1,
        "desc": "A lonely holder, that feels like its a part of something bigger...",
        "unlocked": False,
    },
    {
        "id": "monitor",
        "name": "Dusty Monitor",
        "cost": 2000,
        "type": "add",
        "base_value": 5.0,
        "value_mult": 1.5,
        "max_level": 4,
        "cost_mult": 2.5,
        "desc": "An old ahh monitor. +$5, +50% per level",
        "unlocked": False,
    },
    {
        "id": "ergonomic_chair",
        "name": "Ergonomic Chair",
        "cost": 5000,
        "type": "mult",
        "base_value": 1.5,
        "value_mult": 1.25,
        "max_level": 3,
        "cost_mult": 2.5,
        "desc": "Pro gamer chair. $1.5x base, +25% per level",
        "unlocked": False,
    },
    {
        "id": "dual_monitors",
        "name": "Dual Monitors",
        "cost": 12000,
        "type": "add",
        "base_value": 10.0,
        "value_mult": 1.5,
        "max_level": 3,
        "cost_mult": 2.5,
        "desc": "2x the monitors, +$10, +50% per level",
        "unlocked": False,
    },
    {
        "id": "mech_keyboard",
        "name": "Mechanical Keyboard",
        "cost": 25000,
        "type": "mult",
        "base_value": 1.8,
        "value_mult": 1.3,
        "max_level": 5,
        "cost_mult": 2.8,
        "desc": "Clackety clack. $1.8x base, +30% per level",
        "unlocked": False,
    },
    {
        "id": "lamp",
        "name": "Desk Lamp",
        "cost": 40000,
        "type": "reduce_delay",
        "base_value": 0.95,
        "value_mult": 0.95,
        "max_level": 4,
        "cost_mult": 3.0,
        "unlocked": False,
    },
    {
        "id": "whiteboard",
        "name": "Whiteboard",
        "cost": 100000,
        "type": "add",
        "base_value": 25.0,
        "value_mult": 1.5,
        "max_level": 5,
        "cost_mult": 3.5,
        "unlocked": False,
    },
]

UPGRADE_DEPENDENCIES = {
    "coffee": ["keyboard"],
    "cup_holder": ["coffee"],
    "monitor": ["keyboard"],
    "ergonomic_chair": ["cup_holder"],
    "dual_monitors": ["monitor"],
    "mech_keyboard": ["keyboard"],
    "lamp": ["monitor"],
    "whiteboard": ["lamp"],
}

INSPIRE_UPGRADES = [
    {
        "id": "inspire_motiv",
        "name": "Motivation",
        "cost": 1,
        "type": "unlock_motivation",
        "value": 1,
        "max_level": 1,
        "desc": "Unlocks Motivation (buff that decays over work)",
    },
    {
        "id": "inspire_efficiency",
        "name": "Efficient Worker",
        "base_cost": 2,
        "type": "money_mult",
        "max_level": 10,
        "cost_mult": 1.75,
        "base_value": 1.25,
        "value_mult": 1.15,
        "desc": "×1.25 base, +15% per level",
    },
    {
        "id": "inspire_focus_cap",
        "name": "Mindspace",
        "base_cost": 5,
        "type": "focus_max",
        "max_level": 3,
        "cost_mult": 2.0,
        "value": 100,
        "desc": "+100 Focus cap per level",
    },
    {
        "id": "inspire_scaling",
        "name": "Creative Momentum",
        "base_cost": 10,
        "type": "money_mult",
        "max_level": 8,
        "cost_mult": 1.9,
        "base_value": 1.2,
        "value_mult": 1.12,
        "desc": "Stacking income boost",
    },
    {
        "id": "ip_rate",
        "name": "Insight Flow",
        "base_cost": 15,
        "type": "inspire_rate",
        "max_level": 6,
        "cost_mult": 2.2,
        "base_value": 1.5,
        "value_mult": 1.12,
        "desc": "×1.5 Inspiration gain, +12% per level",
    },
]

CONCEPT_UPGRADES = [
    {
        "id": "concept_autowork",
        "name": "Auto‑Work",
        "cost": 1,
        "type": "unlock_autowork",
        "value": 1,
        "max_level": 1,
        "desc": "Unlocks automatic work cycles",
    },
    {
        "id": "concept_autospeed",
        "name": "Automation Speed",
        "base_cost": 5,
        "type": "work_mult",
        "max_level": 10,
        "cost_mult": 2.0,
        "base_value": 0.95,
        "value_mult": 0.95,
        "desc": "Reduces auto‑work delay",
    },
    {
        "id": "concept_autoeff",
        "name": "Automation Efficiency",
        "base_cost": 10,
        "type": "money_mult",
        "max_level": 10,
        "cost_mult": 2.0,
        "base_value": 1.2,
        "value_mult": 1.1,
        "desc": "Boosts auto‑work money gain",
    },
    {
        "id": "concept_rate",
        "name": "Conceptual Drift",
        "base_cost": 20,
        "type": "concept_rate",
        "max_level": 6,
        "cost_mult": 2.2,
        "base_value": 1.5,
        "value_mult": 1.12,
        "desc": "×1.5 Concepts gain, +12% per level",
    },
    {
        "id": "concept_mastery",
        "name": "System Mastery",
        "base_cost": 25,
        "type": "money_mult",
        "max_level": 8,
        "cost_mult": 2.3,
        "base_value": 1.3,
        "value_mult": 1.15,
        "desc": "Global income boost from systems understanding",
    },
]

CHARGE_THRESHOLDS = [
    {"amount": 0, "reward_type": "x$", "reward_value": 1.1},
    {"amount": 500, "reward_type": "x$", "reward_value": 1.2},
]

BATTERY_TIERS = {
    1: {"cap": 1000, "rows": 5},
    2: {"cap": 100000, "rows": 10},
    3: {"cap": 10000000, "rows": 15},
}

BORDERS = {
    0: {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"},
    1: {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║"},
    2: {"tl": "▓", "tr": "▓", "bl": "▓", "br": "▓", "h": "█", "v": "█"},
    3: {"tl": "◆", "tr": "◆", "bl": "◆", "br": "◆", "h": "─", "v": "│"},
    4: {"tl": "▛", "tr": "▜", "bl": "▙", "br": "▟", "h": "▀", "v": "▌"},
}


def format_number(n):
    neg = n < 0
    n = abs(n)
    suffixes = [
        (1e33, "De"),
        (1e30, "No"),
        (1e27, "Oc"),
        (1e24, "Sp"),
        (1e21, "Sx"),
        (1e18, "Qn"),
        (1e15, "Qd"),
        (1e12, "T"),
        (1e9, "B"),
        (1e6, "M"),
        (1e3, "K"),
    ]
    for value, symbol in suffixes:
        if n >= value:
            s = f"{n / value:.2f}".rstrip("0").rstrip(".")
            return f"-{s}{symbol}" if neg else f"{s}{symbol}"
    if n >= 1e33:
        s = f"{n:.2e}"
        return f"-{s}" if neg else s
    s = f"{n:.2f}".rstrip("0").rstrip(".")
    return f"-{s}" if neg else s

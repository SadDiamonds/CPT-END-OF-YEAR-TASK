BASE_MONEY_GAIN = 1.0
BASE_WORK_DELAY = 6.7
BASE_MONEY_MULT = 1.0

CURRENCY_SYMBOL = "¤"
STABILITY_CURRENCY_NAME = "Stability Sparks"
STABILITY_REWARD_MULT = 0.5
STABILITY_REWARD_EXP = 0.55

WAKE_TIMER_START = 120
WAKE_TIMER_UPGRADES = [
    {
        "id": "Unlock_upgrade",
        "name": "Newgame+",
        "cost": 5,
        "upgrades_unlocked": True,
           "desc": "Unlocks the upgrade menu.",
    },
    {
        "id": "wake_breath",
        "desc": "-7% delay base, -6% per level",
        "cost": 15,
        "time_bonus": 60,
           "desc": "Adds 60 seconds to the timer.",
    },
    {
        "id": "wake_anchor",
        "name": "Anchor Points",
        "cost": 250,
        "time_bonus": 180,
           "desc": "Adds 180 seconds to the timer.",
    },
    {
        "id": "wake_lock",
        "name": "Phase Lock",
        "cost": 1000,
        "time_bonus": 0,
        "grant_infinite": True,
           "desc": "Stops the wake timer permanently.",
    },
]

LAYER_FLOW = [
    {
        "id": 0,
        "key": "wake",
        "name": "Desk",
        "currency_name": "Money",
        "currency_suffix": "Cl",
        "storage_key": "money",
        "unlock_money": 0,
        "border_id": 0,
           "desc": "Primary money layer.",
    },
    {
        "id": 1,
        "key": "corridor",
        "name": "Hall",
        "currency_name": "Marks",
        "currency_suffix": "Mk",
        "storage_key": "inspiration",
        "unlock_money": 100_000,
        "border_id": 1,
           "desc": "Generates and spends Inspiration currency.",
    },
    {
        "id": 2,
        "key": "archive",
        "name": "The Echo",
        "currency_name": "Echoes",
        "currency_suffix": "Ec",
        "storage_key": "concepts",
        "unlock_money": 100_000_000,
        "border_id": 2,
           "desc": "Generates and spends Concept currency.",
    },
    {
        "id": 3,
        "key": "dreamwalk",
        "name": "Dreamtrail",
        "currency_name": "Pulse",
        "currency_suffix": "Pu",
        "storage_key": "pulses",
        "unlock_money": 5_000_000_000_000,
        "border_id": 3,
           "desc": "Future prestige layer.",
    },
    {
        "id": 4,
        "key": "persona",
        "name": "Maskroom",
        "currency_name": "Veil",
        "currency_suffix": "Ve",
        "storage_key": "veils",
        "unlock_money": 10**18,
        "border_id": 4,
           "desc": "Future meta-progression layer.",
    },
    {
        "id": 5,
        "key": "threshold",
        "name": "Gate",
        "currency_name": "Seal",
        "currency_suffix": "Se",
        "storage_key": "sigils",
        "unlock_money": 10**24,
        "border_id": 4,
           "desc": "Future endgame layer.",
    },
]

LAYER_BY_KEY = {entry["key"]: entry for entry in LAYER_FLOW}
LAYER_BY_ID = {entry["id"]: entry for entry in LAYER_FLOW}

FOCUS_BOOST_FACTOR = 0.5
FOCUS_DURATION = 12
FOCUS_CHARGE_PER_EARN = 12
FOCUS_MAX = 100

INSPIRATION_UNLOCK_MONEY = LAYER_BY_KEY["corridor"]["unlock_money"]
CONCEPTS_UNLOCK_MONEY = LAYER_BY_KEY["archive"]["unlock_money"]

MOTIVATION_MAX = 100
MAX_MOTIVATION_MULT = 3.0

STEAM_SPEED = 2.45 
STEAM_CHANCE = 0.8 
STEAM_SPREAD = 3
STEAM_LIFETIME = 0.5 
STEAM_CHARS = ["~", "^", "."]
CAFFEINE_POINT_RATE = 1

MIN_BOX_WIDTH = 50
BOX_MARGIN = 4
SAVE_SLOT_COUNT = 4
MAIN_LOOP_MIN_DT = 0.02
ENEMY_ANIM_DELAY = 0.35

UPGRADES = [
    {
        "id": "keyboard",
        "name": "Basic Keyboard",
        "cost": 45,
        "type": "mult",
        "base_value": 1.35,
        "value_mult": 1.18,
        "max_level": 5,
        "cost_mult": 1.85,
        "desc": "Calibrate your fingers. 1.35x base, +18% per level",
        "unlocked": True,
    },
    {
        "id": "coffee",
        "name": "Coffee",
        "cost": 160,
        "type": "reduce_delay",
        "base_value": 0.965,
        "value_mult": 0.95,
        "max_level": 3,
        "cost_mult": 2.2,
        "desc": "-3.5% auto delay, -5% per level",
        "unlocked": False,
    },
    {
        "id": "cup_holder",
        "name": "Cup Holder",
        "cost": 260,
        "type": "add",
        "base_value": 4.0,
        "max_level": 1,
        "cost_mult": 3.0,
        "desc": "+4 income",
        "unlocked": False,
    },
    {
        "id": "monitor",
        "name": "Dusty Monitor",
        "cost": 520,
        "type": "add",
        "base_value": 6,
        "value_mult": 1.4,
        "max_level": 4,
        "cost_mult": 2.2,
        "desc": "+6 income, +40% per level",
        "unlocked": False,
    },
    {
        "id": "ergonomic_chair",
        "name": "Ergonomic Chair",
        "cost": 950,
        "type": "mult",
        "base_value": 1.28,
        "value_mult": 1.22,
        "max_level": 3,
        "cost_mult": 2.3,
        "desc": "x1.28 base income, +22% per level",
        "unlocked": False,
    },
    {
        "id": "dual_monitors",
        "name": "Dual Monitors",
        "cost": 1800,
        "type": "add",
        "base_value": 14.0,
        "value_mult": 1.45,
        "max_level": 3,
        "cost_mult": 2.35,
        "desc": "+14 income, +45% per level",
        "unlocked": False,
    },
    {
        "id": "mech_keyboard",
        "name": "Mechanical Keyboard",
        "cost": 3600,
        "type": "mult",
        "base_value": 1.6,
        "value_mult": 1.24,
        "max_level": 4,
        "cost_mult": 2.6,
        "desc": "x1.6 base income, +24% per level",
        "unlocked": False,
    },
    {
        "id": "lamp",
        "name": "Desk Lamp",
        "cost": 5400,
        "type": "reduce_delay",
        "base_value": 0.93,
        "value_mult": 0.94,
        "max_level": 4,
        "cost_mult": 2.6,
        "unlocked": False,
    },
    {
        "id": "whiteboard",
        "name": "Whiteboard",
        "cost": 8200,
        "type": "add",
        "base_value": 32.0,
        "value_mult": 1.4,
        "max_level": 5,
        "cost_mult": 3.0,
        "desc": "+32 income, +40% per level",
        "unlocked": False,
    },
    {
        "id": "chrono_lattice",
        "name": "Chrono Lattice",
        "cost": 15000,
        "type": "time_velocity_mult",
        "base_value": 1.18,
        "value_mult": 1.12,
        "max_level": 4,
        "cost_mult": 2.7,
        "desc": "+18% time velocity base, +12% per level",
        "unlocked": False,
    },
]

UPGRADE_DEPENDENCIES = {
    "coffee": ["keyboard"],
    "cup_holder": ["keyboard"],
    "monitor": ["keyboard"],
    "ergonomic_chair": ["cup_holder"],
    "dual_monitors": ["monitor"],
    "mech_keyboard": ["keyboard"],
    "lamp": ["monitor"],
    "whiteboard": ["lamp"],
    "chrono_lattice": ["whiteboard"],
}

INSPIRE_UPGRADES = [
    {
        "id": "inspire_motiv",
        "name": "Motivation",
        "cost": 1,
        "type": "unlock_motivation",
        "value": 1,
        "max_level": 1,
        "cost_mult": 1.3,
        "desc": "Unlocks the Motivation buff.",
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
        "desc": "x1.25 income, +15% per level",
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
        "desc": "x1.2 income base, +12% per level",
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
        "desc": "x1.5 Inspiration gain, +12% per level",
    },
    {
        "id": "inspire_timeloom",
        "name": "Time Loom",
        "base_cost": 22,
        "type": "time_velocity_mult",
        "max_level": 5,
        "cost_mult": 2.3,
        "base_value": 1.12,
        "value_mult": 1.08,
        "desc": "+12% time velocity base, +8% per level",
    },
]

CONCEPT_UPGRADES = [
    {
        "id": "concept_autowork",
        "name": "Signal Tuner",
        "cost": 1,
        "type": "unlock_autowork",
        "value": 1,
        "max_level": 1,
        "cost_mult": 1.3,
        "desc": "Unlocks automatic work cycles.",
    },
    {
        "id": "concept_autospeed",
        "name": "Waveform Compression",
        "base_cost": 5,
        "type": "work_mult",
        "max_level": 10,
        "cost_mult": 2.0,
        "base_value": 0.95,
        "value_mult": 0.95,
        "desc": "Reduces auto-work delay.",
    },
    {
        "id": "concept_autoeff",
        "name": "Amplitude Boost",
        "base_cost": 10,
        "type": "auto_money_mult",
        "max_level": 10,
        "cost_mult": 2.0,
        "base_value": 1.2,
        "value_mult": 1.1,
        "desc": "Boosts auto-work income.",
    },
    {
        "id": "concept_rate",
        "name": "Echo Chamber",
        "base_cost": 20,
        "type": "concept_rate",
        "max_level": 6,
        "cost_mult": 2.2,
        "base_value": 1.5,
        "value_mult": 1.12,
        "desc": "x1.5 Concept gain, +12% per level.",
    },
    {
        "id": "concept_mastery",
        "name": "Harmonic Convergence",
        "base_cost": 25,
        "type": "money_mult",
        "max_level": 8,
        "cost_mult": 2.3,
        "base_value": 1.3,
        "value_mult": 1.15,
        "desc": "x1.3 income, +15% per level.",
    },
    {
        "id": "concept_stabilizer",
        "name": "Phase Lock",
        "base_cost": 50,
        "type": "resonance_stability",
        "max_level": 5,
        "cost_mult": 2.5,
        "base_value": 0.9,
        "value_mult": 0.9,
        "desc": "Improves resonance stability.",
    },
    {
        "id": "concept_timebond",
        "name": "Temporal Bond",
        "base_cost": 120,
        "type": "timeflow_bonus",
        "max_level": 4,
        "cost_mult": 2.4,
        "base_value": 1.0,
        "value_mult": 1.0,
        "desc": "Converts timeflow reward into money bonus.",
    },
    {
        "id": "concept_timecore",
        "name": "Chronal Archive",
        "base_cost": 170,
        "type": "time_velocity_mult",
        "max_level": 4,
        "cost_mult": 2.5,
        "base_value": 1.2,
        "value_mult": 1.08,
        "desc": "+20% time velocity base, +8% per level",
    },
    {
        "id": "concept_breach",
        "name": "A key",
        "base_cost": 100,
        "type": "unlock_rpg",
        "value": 1,
        "max_level": 1,
        "cost_mult": 1.0,
        "desc": "Unlocks the RPG mode.",
    },
]

RESONANCE_MAX = 100
RESONANCE_START = 50
RESONANCE_TARGET_WIDTH = 15
RESONANCE_DRIFT_RATE = 2.0
RESONANCE_TUNE_POWER = 4.0
RESONANCE_BASE_INSTABILITY = 1.3
RESONANCE_MIN_INSTABILITY = 0.35
RESONANCE_JUMP_CHANCE = 0.45
RESONANCE_JUMP_POWER = 10.0

RPG_PLAYER_START_HP = 100
RPG_PLAYER_START_ATK = 4
RPG_NG_HP_BONUS = 15
RPG_NG_ATK_BONUS = 1
RPG_NG_GOLD_STEP = 250
RPG_FLOOR_CAP = 15
RPG_GOLD_REWARD_SCALE = 0.5
RPG_ENEMIES = [
    {"name": "Glitch Mite", "hp": 22, "atk": 2, "xp": 10, "gold": 4, "min_floor": 1, "max_floor": 3},
    {"name": "Static Shade", "hp": 55, "atk": 5, "xp": 28, "gold": 10, "min_floor": 2, "max_floor": 5},
    {"name": "Frayed Crawler", "hp": 80, "atk": 7, "xp": 40, "gold": 14, "min_floor": 3, "max_floor": 6},
    {"name": "Null Walker", "hp": 135, "atk": 13, "xp": 85, "gold": 24, "min_floor": 4, "max_floor": 8},
    {"name": "Pulse Warden", "hp": 200, "atk": 16, "xp": 120, "gold": 32, "min_floor": 5, "max_floor": 9},
    {"name": "Code Eater", "hp": 320, "atk": 24, "xp": 210, "gold": 48, "min_floor": 7, "max_floor": 12},
    {"name": "Amber Golem", "hp": 420, "atk": 28, "xp": 260, "gold": 60, "min_floor": 8, "max_floor": 13},
    {"name": "Signal Ravager", "hp": 520, "atk": 34, "xp": 320, "gold": 72, "min_floor": 10, "max_floor": 15},
    {"name": "Fractal Beast", "hp": 650, "atk": 40, "xp": 380, "gold": 90, "min_floor": 12, "max_floor": 15},
]
RPG_BOSSES = {
    5: {
        "id": "warden_core",
        "name": "Warden Core",
        "hp": 650,
        "atk": 28,
        "xp": 320,
        "gold": 140,
        "reward": {"max_hp": 40, "potions": 1, "desc": "+40 Max HP, +1 potion"},
    },
    10: {
        "id": "echo_overseer",
        "name": "Echo Overseer",
        "hp": 1100,
        "atk": 38,
        "xp": 520,
        "gold": 220,
        "reward": {"atk": 6, "def": 2, "desc": "+6 ATK, +2 DEF"},
    },
    15: {
        "id": "archivist_prime",
        "name": "Archivist Prime",
        "hp": 1650,
        "atk": 48,
        "xp": 800,
        "gold": 320,
        "reward": {"max_hp": 60, "atk": 8, "desc": "+60 Max HP, +8 ATK"},
    },
}
RPG_FLOOR_MODIFIERS = [
    {
        "id": "overclocked",
        "name": "Overclocked Hostiles",
        "desc": "+20% enemy HP/ATK, +15% XP",
        "enemy_hp_mult": 1.2,
        "enemy_atk_mult": 1.2,
        "enemy_xp_mult": 1.15,
        "weight": 1.0,
    },
    {
        "id": "hazard_bloom",
        "name": "Hazard Bloom",
        "desc": "Traps deal +40% damage, combat gold +10%",
        "trap_damage_mult": 1.4,
        "enemy_gold_mult": 1.1,
        "weight": 0.8,
    },
    {
        "id": "supply_drought",
        "name": "Supply Drought",
        "desc": "Potion finds -40%, treasure gold +25%",
        "potion_drop_mult": 0.6,
        "treasure_gold_bonus": 1.25,
        "weight": 0.9,
    },
    {
        "id": "rich_veins",
        "name": "Rich Veins",
        "desc": "Enemy gold +25%, traps -20% damage",
        "enemy_gold_mult": 1.25,
        "trap_damage_mult": 0.8,
        "weight": 0.7,
    },
    {
        "id": "thick_fog",
        "name": "Thick Fog",
        "desc": "Enemies hit -10% harder but gain +15% HP",
        "enemy_hp_mult": 1.15,
        "enemy_atk_mult": 0.9,
        "weight": 0.6,
    },
]
RPG_DESKTOP_APPS = [
    {
        "id": "game",
        "name": "GAME.EXE",
        "icon": "[#]",
        "tooltip": "Launch the RPG client",
    },
    {
        "id": "safari",
        "name": "Safari",
        "icon": "( )",
        "tooltip": "Browser disabled in this build",
    },
    {
        "id": "trash",
        "name": "Trash Bin",
        "icon": "[X]",
        "tooltip": "Recycle bin is empty",
    },
]
RPG_DESKTOP_COLS = 2
RPG_MAP_WIDTH = 6
RPG_MAP_HEIGHT = 6
RPG_MAZE_VARIANTS = [
    {"id": "square", "label": "6x6 Balanced", "width": 6, "height": 6, "weight": 0.45, "min_floor": 1, "color": "CYAN"},
    {"id": "wide", "label": "8x5 Wide", "width": 8, "height": 5, "weight": 0.3, "min_floor": 2, "color": "MAGENTA"},
    {"id": "deep", "label": "5x8 Deep", "width": 5, "height": 8, "weight": 0.25, "min_floor": 3, "color": "BLUE"},
]
RPG_ROOM_TYPES = [
    ("enemy", 0.42),
    ("elite", 0.12),
    ("treasure", 0.13),
    ("healer", 0.05),
    ("trap", 0.13),
    ("empty", 0.15),
]
RPG_ROOM_DESCRIPTIONS = {
    "start": "floor starting node",
    "enemy": "standard battle room",
    "elite": "high-threat battle room",
    "treasure": "loot cache",
    "healer": "restore HP and potions",
    "trap": "hazard tile",
    "empty": "no encounter",
    "boss": "boss arena",
    "exit": "progress to next floor",
    "stairs": "progress to next floor",
    "secret": "optional bonus room",
}
RPG_POTION_HEAL_RATIO = 0.45
RPG_LOG_MAX = 10
RPG_RELICS = [
    {"id": "heart_shard", "name": "Fractured Heart", "desc": "+25 Max HP", "effect": "max_hp", "value": 25},
    {"id": "blade_loop", "name": "Blade Loop", "desc": "+3 ATK", "effect": "atk", "value": 3},
    {"id": "obsidian_plate", "name": "Obsidian Plate", "desc": "+2 DEF", "effect": "def", "value": 2},
    {"id": "gilded_eye", "name": "Gilded Eye", "desc": "+15% GOLD", "effect": "gold_bonus", "value": 0.15},
]
RPG_RELIC_LOOKUP = {entry["id"]: entry for entry in RPG_RELICS}
RPG_SECRET_ROOM_TYPES = ["vault", "sentinel", "echo"]
RPG_MIN_SECRET_FLOOR = 2
RPG_SECRET_BASE_COUNT = 1
RPG_SECRET_SCALE = 3
RPG_SECRET_BOSS_TEMPLATE = {
    "name": "Archivist Sentinel",
    "hp": 220,
    "atk": 22,
    "xp": 180,
    "gold": 220,
}
RPG_SHOP_STOCK = [
    {
        "id": "iron_edge",
        "name": "Iron Edge",
        "slot": "weapon",
        "cost": 90,
        "atk_bonus": 4,
        "floor_req": 1,
        "aura_hint": "crimson",
        "desc": "Reliable +4 ATK, slight crimson tint",
    },
    {
        "id": "signal_saber",
        "name": "Signal Saber",
        "slot": "weapon",
        "cost": 180,
        "atk_bonus": 9,
        "floor_req": 3,
        "aura_hint": "amber",
        "desc": "+9 ATK, crit bias from amber traces",
    },
    {
        "id": "ion_halberd",
        "name": "Ion Halberd",
        "slot": "weapon",
        "cost": 260,
        "atk_bonus": 14,
        "floor_req": 5,
        "aura_hint": "crimson",
        "desc": "+14 ATK, pulses twice each strike",
    },
    {
        "id": "chrono_lash",
        "name": "Chrono Lash",
        "slot": "weapon",
        "cost": 420,
        "atk_bonus": 20,
        "floor_req": 8,
        "aura_hint": "amber",
        "desc": "+20 ATK, quickens crit window",
    },
    {
        "id": "patchwork_plate",
        "name": "Patchwork Plate",
        "slot": "armor",
        "cost": 85,
        "def_bonus": 2,
        "floor_req": 1,
        "desc": "+2 DEF, cobbled from spare brackets",
    },
    {
        "id": "mirror_cowl",
        "name": "Mirror Cowl",
        "slot": "armor",
        "cost": 160,
        "def_bonus": 4,
        "floor_req": 3,
        "desc": "+4 DEF, reflects minor chip damage",
    },
    {
        "id": "resonant_mail",
        "name": "Resonant Mail",
        "slot": "armor",
        "cost": 320,
        "def_bonus": 6,
        "floor_req": 6,
        "desc": "+6 DEF, dampens charging attacks",
    },
    {
        "id": "amber_core",
        "name": "Amber Core",
        "slot": "aura",
        "cost": 120,
        "aura": "amber",
        "floor_req": 2,
        "desc": "Switch aura to Amber Critical",
    },
    {
        "id": "cobalt_core",
        "name": "Cobalt Core",
        "slot": "aura",
        "cost": 120,
        "aura": "cobalt",
        "floor_req": 2,
        "desc": "Switch aura to Cobalt Guard",
    },
    {
        "id": "verdant_core",
        "name": "Verdant Core",
        "slot": "aura",
        "cost": 120,
        "aura": "verdant",
        "floor_req": 2,
        "desc": "Switch aura to Verdant Regen",
    },
    {
        "id": "crimson_core",
        "name": "Crimson Core",
        "slot": "aura",
        "cost": 210,
        "aura": "crimson",
        "floor_req": 5,
        "desc": "Switch aura to Crimson Critical",
    },
]
RPG_AURAS = {
    "amber": {"label": "Amber Critical", "color": "LIGHTYELLOW_EX", "crit_bonus": 0.1},
    "cobalt": {"label": "Cobalt Guard", "color": "LIGHTBLUE_EX", "damage_reduction": 2},
    "verdant": {"label": "Verdant Regen", "color": "GREEN", "floor_heal": 0.08},
    "crimson": {"label": "Crimson Critical", "color": "LIGHTRED_EX", "crit_bonus": 0.15},
}
RPG_DEFAULT_AURA = "amber"
RPG_BASE_CRIT = 0.15

CHARGE_THRESHOLDS = [
    {"amount": 0, "reward_type": "x¤", "reward_value": 1.1},
    {"amount": 500, "reward_type": "x¤", "reward_value": 1.2},
]

BATTERY_TIERS = {
    1: {"cap": 1000, "rows": 5},
    2: {"cap": 100000, "rows": 10},
    3: {"cap": 10000000, "rows": 15},
}

TIME_STRATA = [
    {"label": "Seconds", "scale": 1.0, "reward_mult": 1.0},
    {"label": "Minutes", "scale": 60.0, "reward_mult": 1.15},
    {"label": "Hours", "scale": 3600.0, "reward_mult": 1.4},
    {"label": "Days", "scale": 86400.0, "reward_mult": 2.0},
    {"label": "Weeks", "scale": 604800.0, "reward_mult": 3.0},
    {"label": "Months", "scale": 2_630_000.0, "reward_mult": 4.5},
    {"label": "Years", "scale": 31_536_000.0, "reward_mult": 6.5},
    {"label": "Decades", "scale": 315_360_000.0, "reward_mult": 10.0},
    {"label": "Centuries", "scale": 3_153_600_000.0, "reward_mult": 16.0},
    {"label": "Millennia", "scale": 31_536_000_000.0, "reward_mult": 24.0},
    {"label": "Eons", "scale": 31_536_000_000_000.0, "reward_mult": 40.0},
]

BORDERS = {
    0: {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"},
    1: {"tl": "╭", "tr": "╮", "bl": "╰", "br": "╯", "h": "─", "v": "│"},
    2: {"tl": "╔", "tr": "╗", "bl": "╚", "br": "╝", "h": "═", "v": "║"},
    3: {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "│"},
    4: {"tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "h": "─", "v": "║"},
}

LAYER2_PARTICLE_CHARS = ["·", "*", ".", "'"]
LAYER2_PARTICLE_COUNT = 3
LAYER2_PARTICLE_AMPLITUDE = 12
LAYER2_PARTICLE_FREQ = 3


def format_number(n):
    neg = n < 0
    n = abs(n)

    suffixes = [
        (10**303, "e303"),
        (10**300, "e300"),
        (10**297, "e297"),
        (10**294, "e294"),
        (10**291, "e291"),
        (10**288, "e288"),
        (10**285, "e285"),
        (10**282, "e282"),
        (10**279, "e279"),
        (10**276, "e276"),
        (10**273, "e273"),
        (10**270, "e270"),
        (10**267, "e267"),
        (10**264, "e264"),
        (10**261, "e261"),
        (10**258, "e258"),
        (10**255, "e255"),
        (10**252, "e252"),
        (10**249, "e249"),
        (10**246, "e246"),
        (10**243, "e243"),
        (10**240, "e240"),
        (10**237, "e237"),
        (10**234, "e234"),
        (10**231, "e231"),
        (10**228, "e228"),
        (10**225, "e225"),
        (10**222, "e222"),
        (10**219, "e219"),
        (10**216, "e216"),
        (10**213, "e213"),
        (10**210, "e210"),
        (10**207, "e207"),
        (10**204, "e204"),
        (10**201, "e201"),
        (10**198, "e198"),
        (10**195, "e195"),
        (10**192, "e192"),
        (10**189, "e189"),
        (10**186, "e186"),
        (10**183, "e183"),
        (10**180, "e180"),
        (10**177, "e177"),
        (10**174, "e174"),
        (10**171, "e171"),
        (10**168, "e168"),
        (10**165, "e165"),
        (10**162, "e162"),
        (10**159, "e159"),
        (10**156, "e156"),
        (10**153, "e153"),
        (10**150, "e150"),
        (10**147, "e147"),
        (10**144, "e144"),
        (10**141, "e141"),
        (10**138, "e138"),
        (10**135, "e135"),
        (10**132, "e132"),
        (10**129, "e129"),
        (10**126, "e126"),
        (10**123, "e123"),
        (10**120, "e120"),
        (10**117, "e117"),
        (10**114, "e114"),
        (10**111, "e111"),
        (10**108, "e108"),
        (10**105, "e105"),
        (10**102, "e102"),
        (10**99, "e99"),
        (10**96, "e96"),
        (10**93, "e93"),
        (10**90, "e90"),
        (10**87, "e87"),
        (10**84, "e84"),
        (10**81, "e81"),
        (10**78, "e78"),
        (10**75, "e75"),
        (10**72, "e72"),
        (10**69, "e69"),
        (10**66, "e66"),
        (10**63, "e63"),
        (10**60, "e60"),
        (10**57, "e57"),
        (10**54, "e54"),
        (10**51, "e51"),
        (10**48, "e48"),
        (10**45, "e45"),
        (10**42, "e42"),
        (10**39, "e39"),
        (10**36, "e36"),
        (10**33, "De"),
        (10**30, "No"),
        (10**27, "Oc"),
        (10**24, "Sp"),
        (10**21, "Sx"),
        (10**18, "Qn"),
        (10**15, "Qd"),
        (10**12, "T"),
        (10**9, "B"),
        (10**6, "M"),
        (10**3, "K"),
    ]

    for value, symbol in suffixes:
        if n >= value:
            s = f"{n / value:.2f}".rstrip("0").rstrip(".")
            return f"-{s}{symbol}" if neg else f"{s}{symbol}"

    s = f"{n:.2f}".rstrip("0").rstrip(".")
    return f"-{s}" if neg else s


AUTO_BALANCE_UPGRADES = True
BALANCE_DELTA = 0.3
BALANCE_MIN_MULT = 1.07
BALANCE_MAX_MULT = 5.0
PRINT_BALANCE_CHANGES = False

BALANCE_ADJUSTMENTS = []


def _normalize_upgrade_costs():
    if not AUTO_BALANCE_UPGRADES:
        return

    def effect_strength_for(u):
        try:
            vm = u.get("value_mult")
            if vm is not None:
                f = float(vm)
                return f if f >= 1.0 else (1.0 / f if f > 0 else 1.0)
        except Exception:
            pass

        for key in ("base_value", "value"):
            if key in u:
                try:
                    f = float(u[key])
                    if u.get("type") in ("add", "value"):
                        denom = max(1.0, BASE_MONEY_GAIN)
                        return max(1.0, 1.0 + (f / denom))
                    if u.get("type") in ("work_mult", "reduce_delay"):
                        return f if f >= 1.0 else (1.0 / f if f > 0 else 1.0)
                    return f if f >= 1.0 else 1.0
                except Exception:
                    pass
        return 1.0

    def ensure_list(lst, table_name):
        adjustments = []
        for u in lst:
            try:
                strength = effect_strength_for(u)
                desired = round(
                    max(
                        BALANCE_MIN_MULT,
                        min(BALANCE_MAX_MULT, strength + BALANCE_DELTA),
                    ),
                    2,
                )
                cur = float(u.get("cost_mult", desired))
                if cur < desired:
                    u["cost_mult"] = desired
                    adjustments.append((u.get("id"), cur, desired))
            except Exception:
                continue
        if adjustments:
            BALANCE_ADJUSTMENTS.extend(
                [(table_name, aid, old, new) for (aid, old, new) in adjustments]
            )
        if PRINT_BALANCE_CHANGES and adjustments:
            print(f"[BALANCE] Adjusted cost_mult in {table_name}:")
            for aid, old, new in adjustments:
                print(f"  {aid}: {old} -> {new}")

    ensure_list(UPGRADES, "UPGRADES")
    ensure_list(INSPIRE_UPGRADES, "INSPIRE_UPGRADES")
    ensure_list(CONCEPT_UPGRADES, "CONCEPT_UPGRADES")


_normalize_upgrade_costs()

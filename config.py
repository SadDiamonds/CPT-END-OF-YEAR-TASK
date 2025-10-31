# config.py

# Base resource values
BASE_MONEY_GAIN = 1.0          # money gained per work cycle before modifiers
BASE_WORK_DELAY = 5.0          # seconds per work cycle (base)
BASE_MONEY_MULT = 1.0          # base multiplier (other multipliers multiply this)

# Focus (temporary boost) config
FOCUS_UNLOCK_COST_INSP = 0     # if you want inspiration cost for unlocking (unused)
FOCUS_BOOST_FACTOR = 0.5       # while focus active, work delay is multiplied by this (faster)
FOCUS_DURATION = 12            # how many seconds focus lasts
FOCUS_CHARGE_PER_EARN = 12     # how many 'focus points' earned per completed work (max 100)
FOCUS_MAX = 100

# Inspiration reset rates
INSPIRATION_CONVERT_DIV = 50   # money // DIV gives inspiration when resetting

# UI / layout
MIN_BOX_WIDTH = 50             # don't make the box narrower than this
BOX_MARGIN = 4                 # left/right margin in terminal columns

UPGRADES = [
    {"id": "better_desk", "name": "Better Desk", "cost": 20, "type": "mult", "value": 1.5, "unlocked": True},
    {"id": "coffee",      "name": "Coffee",      "cost": 200, "type": "mult", "value": 0.75, "unlocked": False},
    # coffee here divides delay (we'll treat 'value' as a factor to multiply work_delay by)
    {"id": "overtime",    "name": "Overtime",    "cost": 1000, "type": "add",  "value": 3.0, "unlocked": False},
    {"id": "focus_meter", "name": "Focus Meter", "cost": 5000, "type": "unlock_focus", "value": 0, "unlocked": False},
]

INSPIRE_UPGRADES = [
    {"id":"inspire_1", "name":"Quick Learner", "cost":50, "type":"work_mult", "value":0.9}, 
    {"id":"inspire_2", "name":"Efficient Worker", "cost":100, "type":"money_mult", "value":100}, 
    {"id":"inspire_3", "name":"Master Mind", "cost":200, "type":"focus_max", "value":20}, 
]
"""
Configuration constants for Pokemon Battle Arena
"""
import pygame

# ==================== DISPLAY CONFIGURATION ====================
pygame.init()
display_info = pygame.display.Info()
BASE_WIDTH, BASE_HEIGHT = display_info.current_w - 100, display_info.current_h - 100
WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT
FPS = 60
FONTNAME = "arial"

# ==================== GRID CONFIGURATION ====================
TILE = 50
GRIDW, GRIDH = 24, 11

# ==================== PHASE TIMINGS ====================
INTRO_TIME = 7.0
PHASE1_TIME = 30.0
PHASE2_TIME = 3.0
PHASE3_TIME = 130.0

# ==================== MOVEMENT AND ANIMATION ====================
MOVESPEEDPX = 4.0
IDLEANIMSPEED = 0.5
IDLEANIMBOB = 5
ATTACKEFFECTDURATION = 0.7
HPBARANIMSPEED = 3.0

# ==================== POKEMON TYPE SYSTEM ====================
TYPES = {"Fire", "Electric", "Water"}
TYPECOLOR = {
    "Fire": (255, 100, 60), 
    "Electric": (255, 230, 80), 
    "Water": (80, 180, 255)
}
TYPEADV = {
    ("Fire", "Electric"): 1.3,
    ("Electric", "Water"): 1.3,
    ("Water", "Fire"): 1.3
}
FIELDBOOST = 1.2

# ==================== TEAM ROSTERS ====================
ASHTEAMSPECIES = [("Pikachu", "Electric"), ("Charmander", "Fire"), ("Squirtle", "Water")]
ROCKETTEAMSPECIES = [("Meowth", "Electric"), ("Weezing", "Fire"), ("Wobbuffet", "Water")]

# ==================== IMAGE ASSETS ====================
IMAGEASSETS = {
    "Pikachu": "images/pickachu.png", 
    "Charmander": "images/charmander.png", 
    "Squirtle": "images/squirtle.png",
    "Meowth": "images/meowth.png", 
    "Weezing": "images/weezing.png", 
    "Wobbuffet": "images/wobbuffet.png",
    "Ash": "images/ash.png", 
    "Team Rocket": "images/team_rocket.png",
    "fireright": "images/fire_right.png", 
    "fireleft": "images/fire_left.png",
    "waterright": "images/water_right.png", 
    "waterleft": "images/water_left.png",
    "electricleft": "images/electric_left.png", 
    "electricright": "images/electric_right.png",
}

BACKGROUNDS = {
    "intro": "images/pokemon_intro.webp",
    "forest": "images/forest.jpg",
    "elixir": "images/elixir.png",
    "battle": "images/battleground.png"
}

# ==================== VOICE FILES ====================
VOICE_FILES = {
    "intro": "sound/game_intro_voice.mp3",
    "phase1": "sound/phase_1.mp3",
    "phase2": "sound/phase_2.mp3",
    "phase3": "sound/phase_3.mp3",
    "ash_wins": "sound/game_result_ash_wins.mp3",
    "rocket_wins": "sound/game_result_team_rocket_wins.mp3",
    "draw": "sound/game_result_match_tied.mp3"
}

# ==================== SPRITE SIZES ====================
BASE_BATTLESPRITESIZE = (160, 160)
BASE_TOKENSPRITESIZE = (60, 60)
BASE_TRAINERSPRITESIZE = (80, 80)
BASE_ATTACKICONSIZE = (200, 200)
BASE_ELIXIRSIZE = (50, 50)

# ==================== ECONOMY ====================
FUELPERCATCH = 15
STARTFUEL = 45
COINSPERAGENT = 100
ELIXIRS = {"Small": (25, 15), "Medium": (50, 30), "Large": (80, 50)}

# ==================== PATHFINDING ====================
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


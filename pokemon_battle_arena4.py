"""
Pokemon Battle Arena 4.0 - Audio-Synced & Enhanced UI
Features: A* Pathfinding, Minimax with Alpha-Beta Pruning, Fuzzy Logic
Enhanced with: Audio-synced phase timing, Larger attack icons, Improved layout
Game Phases: Intro -> Phase 1 (Catching) -> Phase 2 (Elixirs) -> Phase 3 (Battle) -> Result
"""

import math
import random
import time
import sys
import os
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Union
import pygame
import numpy as np

# ==================== CONFIGURATION ====================
# Get display info for fullscreen-like experience
pygame.init()
display_info = pygame.display.Info()
BASE_WIDTH, BASE_HEIGHT = display_info.current_w - 100, display_info.current_h - 100
WIDTH, HEIGHT = BASE_WIDTH, BASE_HEIGHT  # These will be updated when window is resized
FPS = 60
TILE = 50
GRIDW, GRIDH = 24, 11
FONTNAME = "arial"

# Phase timings (in seconds)
INTRO_TIME = 7.0
PHASE1_TIME = 30.0
PHASE2_TIME = 3.0  # Changed from 15 to 5
PHASE3_TIME = 130.0  # Changed from 120 to 130

# Movement and animation
MOVESPEEDPX = 4.0  # Grid cells per second
IDLEANIMSPEED = 0.5
IDLEANIMBOB = 5
ATTACKEFFECTDURATION = 0.7
HPBARANIMSPEED = 3.0

# Pokemon type system
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

# Team rosters
ASHTEAMSPECIES = [("Pikachu", "Electric"), ("Charmander", "Fire"), ("Squirtle", "Water")]
ROCKETTEAMSPECIES = [("Meowth", "Electric"), ("Weezing", "Fire"), ("Wobbuffet", "Water")]

# Image assets
IMAGEASSETS = {
    "Pikachu": "pickachu.png", "Charmander": "charmander.png", "Squirtle": "squirtle.png",
    "Meowth": "meowth.png", "Weezing": "weezing.png", "Wobbuffet": "wobbuffet.png",
    "Ash": "ash.png", "Team Rocket": "team_rocket.png",
    "fireright": "fire_right.png", "fireleft": "fire_left.png",
    "waterright": "water_right.png", "waterleft": "water_left.png",
    "electricleft": "electric_left.png", "electricright": "electric_right.png",
}

BACKGROUNDS = {
    "intro": "pokemon_intro.webp",
    "forest": "forest.jpg",
    "elixir": "elixir.png",
    "battle": "battleground.png"
}

# Voice files
VOICE_FILES = {
    "intro": "game_intro_voice.mp3",
    "phase1": "phase_1.mp3",
    "phase2": "phase_2.mp3",
    "phase3": "phase_3.mp3",
    "ash_wins": "game_result_ash_wins.mp3",
    "rocket_wins": "game_result_team_rocket_wins.mp3",
    "draw": "game_result_match_tied.mp3"
}

# Sprite sizes (base sizes, will scale with window)
BASE_BATTLESPRITESIZE = (160, 160)
BASE_TOKENSPRITESIZE = (60, 60)
BASE_TRAINERSPRITESIZE = (80, 80)
BASE_ATTACKICONSIZE = (200, 200)  # Increased for stunning visuals
BASE_ELIXIRSIZE = (50, 50)

# Economy
FUELPERCATCH = 15
STARTFUEL = 45
COINSPERAGENT = 100
ELIXIRS = {"Small": (25, 15), "Medium": (50, 30), "Large": (80, 50)}

# ==================== FUZZY LOGIC SYSTEM ====================
class FuzzyLogic:
    """Fuzzy Logic Controller for Pokemon battle decisions"""
    
    @staticmethod
    def membership_low(value, min_val, max_val):
        if value <= min_val:
            return 1.0
        elif value >= max_val:
            return 0.0
        else:
            return (max_val - value) / (max_val - min_val)
    
    @staticmethod
    def membership_medium(value, low, mid, high):
        if value <= low or value >= high:
            return 0.0
        elif value == mid:
            return 1.0
        elif value < mid:
            return (value - low) / (mid - low)
        else:
            return (high - value) / (high - mid)
    
    @staticmethod
    def membership_high(value, min_val, max_val):
        if value >= max_val:
            return 1.0
        elif value <= min_val:
            return 0.0
        else:
            return (value - min_val) / (max_val - min_val)
    
    @staticmethod
    def should_heal(pokemon_hp_percent, has_elixir, enemy_hp_percent):
        if not has_elixir:
            return 0.0
        
        hp_low = FuzzyLogic.membership_low(pokemon_hp_percent, 20, 50)
        hp_medium = FuzzyLogic.membership_medium(pokemon_hp_percent, 30, 50, 70)
        hp_high = FuzzyLogic.membership_high(pokemon_hp_percent, 60, 80)
        
        enemy_low = FuzzyLogic.membership_low(enemy_hp_percent, 20, 50)
        enemy_high = FuzzyLogic.membership_high(enemy_hp_percent, 50, 80)
        
        rule1 = min(hp_low, 1.0 - enemy_low) * 0.9
        rule2 = min(hp_medium, enemy_high) * 0.6
        rule3 = hp_high * 0.0
        rule4 = min(hp_low, enemy_low) * 0.4
        
        heal_strength = max(rule1, rule2, rule3, rule4)
        return heal_strength
    
    @staticmethod
    def should_swap(active_type, enemy_type, bench_has_advantage, active_hp_percent):
        if not bench_has_advantage:
            return 0.0
        
        has_disadvantage = 1.0 if (enemy_type, active_type) in TYPEADV else 0.0
        
        hp_critical = FuzzyLogic.membership_low(active_hp_percent, 10, 30)
        hp_low = FuzzyLogic.membership_low(active_hp_percent, 20, 50)
        hp_high = FuzzyLogic.membership_high(active_hp_percent, 50, 80)
        
        rule1 = min(hp_critical, has_disadvantage) * 0.95
        rule2 = min(hp_low, has_disadvantage) * 0.75
        rule3 = has_disadvantage * 0.5
        rule4 = min(hp_high, 1.0 - has_disadvantage) * 0.0
        
        swap_strength = max(rule1, rule2, rule3, rule4)
        return swap_strength

# ==================== CORE DATA STRUCTURES ====================
@dataclass
class Pokemon:
    name: str
    ptype: str
    maxhp: int = 100
    hp: int = 100
    atk: int = 22
    dfn: int = 10
    alive: bool = True
    displayhp: float = 100.0
    boboffset: float = 0.0
    
    def takedamage(self, dmg: int):
        if not self.alive:
            return
        self.hp = max(0, self.hp - dmg)
        if self.hp == 0:
            self.alive = False
    
    def heal(self, amt: int):
        if not self.alive:
            return
        self.hp = min(self.maxhp, self.hp + amt)
    
    def update(self, dt: float):
        if abs(self.hp - self.displayhp) > 0.5:
            diff = self.hp - self.displayhp
            self.displayhp += diff * min(1.0, dt * HPBARANIMSPEED)
        else:
            self.displayhp = float(self.hp)
        self.boboffset = math.sin(time.time() * 2 * math.pi / IDLEANIMSPEED) * IDLEANIMBOB

@dataclass
class Agent:
    name: str
    team: List[Pokemon]
    coins: int = COINSPERAGENT
    fuel: int = STARTFUEL
    elixirs: Dict[str, int] = field(default_factory=dict)
    position: Tuple[float, float] = (0, 0)
    targetpos: Tuple[float, float] = (0, 0)
    current_path: List[Tuple[int, int]] = field(default_factory=list)
    path_index: int = 0

# ==================== A* PATHFINDING ====================
Grid = List[List[int]]
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

def inbounds(x, y):
    return 0 <= x < GRIDW and 0 <= y < GRIDH

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(grid: Grid, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
    """A* pathfinding algorithm"""
    if start == goal:
        return [start]
    
    openset = {start}
    came: Dict[Tuple[int, int], Tuple[int, int]] = {}
    g: Dict[Tuple[int, int], float] = {start: 0}
    f: Dict[Tuple[int, int], float] = {start: manhattan(start, goal)}
    
    while openset:
        current = min(openset, key=lambda n: f.get(n, 1e9))
        if current == goal:
            path = [current]
            while current in came:
                current = came[current]
                path.append(current)
            path.reverse()
            return path
        
        openset.remove(current)
        cx, cy = current
        
        for dx, dy in DIRS:
            nx, ny = cx + dx, cy + dy
            if not inbounds(nx, ny) or grid[ny][nx] == 1:
                continue
            
            tentative = g.get(current, 1e9) + 1
            if tentative < g.get((nx, ny), 1e9):
                came[(nx, ny)] = current
                g[(nx, ny)] = tentative
                f[(nx, ny)] = tentative + manhattan((nx, ny), goal)
                openset.add((nx, ny))
    
    return []

# ==================== BATTLE LOGIC ====================
@dataclass
class BattleState:
    fieldtype: str
    ashactive: int = 0
    rocketactive: int = 0

class BActEnum(Enum):
    ATTACK = auto()
    DEFEND = auto()
    SWAP = auto()
    HEAL = auto()

@dataclass
class BattleAction:
    kind: BActEnum
    arg: Optional[Union[int, str]] = None

def computedamage(attacker: Pokemon, defender: Pokemon, fieldtype: str) -> int:
    """Calculate battle damage with type advantages"""
    base = max(5, attacker.atk - defender.dfn // 2)
    mult = 1.0
    
    if (attacker.ptype, defender.ptype) in TYPEADV:
        mult *= TYPEADV[(attacker.ptype, defender.ptype)]
    
    if attacker.ptype == fieldtype:
        mult *= FIELDBOOST
    
    # More randomness for unpredictability
    mult *= random.uniform(0.8, 1.2)
    
    return int(round(base * mult))

def evalstate(ash: Agent, rocket: Agent, bs: BattleState) -> int:
    """Evaluate battle state - PERFECTLY EQUAL for both agents"""
    ashhp = sum(p.hp for p in ash.team)
    rockethp = sum(p.hp for p in rocket.team)
    
    ashalive = sum(1 for p in ash.team if p.alive)
    rocketalive = sum(1 for p in rocket.team if p.alive)
    
    return (ashhp - rockethp) + (ashalive - rocketalive) * 30

def legalactions(agent: Agent, activeidx: int, opppokemon: Pokemon) -> List[BattleAction]:
    """Get legal actions using fuzzy logic"""
    acts = [BattleAction(BActEnum.ATTACK), BattleAction(BActEnum.DEFEND)]
    
    activepoke = agent.team[activeidx]
    
    bench_has_advantage = False
    best_swap_idx = None
    for i, p in enumerate(agent.team):
        if i != activeidx and p.alive:
            if (p.ptype, opppokemon.ptype) in TYPEADV:
                bench_has_advantage = True
                best_swap_idx = i
                break
    
    if bench_has_advantage:
        hp_percent = (activepoke.hp / activepoke.maxhp) * 100
        swap_strength = FuzzyLogic.should_swap(
            activepoke.ptype,
            opppokemon.ptype,
            True,
            hp_percent
        )
        if swap_strength > 0.5:
            acts.append(BattleAction(BActEnum.SWAP, arg=best_swap_idx))
    
    has_elixir = any(v > 0 for v in agent.elixirs.values())
    if has_elixir and activepoke.hp < activepoke.maxhp:
        hp_percent = (activepoke.hp / activepoke.maxhp) * 100
        enemy_hp_percent = (opppokemon.hp / opppokemon.maxhp) * 100
        
        heal_strength = FuzzyLogic.should_heal(hp_percent, True, enemy_hp_percent)
        if heal_strength > 0.4:
            avail = [k for k, v in agent.elixirs.items() if v > 0]
            if avail:
                best_elixir = max(avail, key=lambda n: ELIXIRS[n][0])
                acts.append(BattleAction(BActEnum.HEAL, arg=best_elixir))
    
    return acts

def cloneagents(a: Agent) -> Agent:
    """Deep clone agent for minimax simulation"""
    return Agent(
        name=a.name,
        team=[Pokemon(p.name, p.ptype, p.maxhp, p.hp, p.atk, p.dfn, p.alive) for p in a.team],
        coins=a.coins,
        fuel=a.fuel,
        elixirs=dict(a.elixirs),
        position=a.position,
        targetpos=a.targetpos
    )

def stepbattle(ash: Agent, rocket: Agent, bs: BattleState, ashact: BattleAction, rocketact: BattleAction, game: 'Game'):
    """Execute one battle turn"""
    def apply(agent, act, activeidxref):
        if act.kind == BActEnum.SWAP and isinstance(act.arg, int):
            if 0 <= act.arg < len(agent.team) and agent.team[act.arg].alive:
                activeidxref[0] = act.arg
                if game:
                    game.sfx['swap'].play()
                    game.last_action[agent.name] = "SWAP"
        elif act.kind == BActEnum.HEAL and isinstance(act.arg, str) and agent.elixirs.get(act.arg, 0) > 0:
            healamt, _ = ELIXIRS[act.arg]
            agent.team[activeidxref[0]].heal(healamt)
            agent.elixirs[act.arg] -= 1
            if game:
                game.sfx['heal'].play()
                pos = game.getpokemonscreenpos("ash" if agent.name == "Ash" else "rocket")
                game.addparticleeffect(pos, (100, 255, 100), 25)
                game.last_action[agent.name] = "HEAL"
    
    ashidx, rocidx = [bs.ashactive], [bs.rocketactive]
    apply(ash, ashact, ashidx)
    apply(rocket, rocketact, rocidx)
    
    if game:
        if ashact.kind == BActEnum.DEFEND:
            game.last_action["Ash"] = "DEFEND"
        if rocketact.kind == BActEnum.DEFEND:
            game.last_action["Team Rocket"] = "DEFEND"
    
    ashdef, rocdef = (ashact.kind == BActEnum.DEFEND), (rocketact.kind == BActEnum.DEFEND)
    
    if ashact.kind == BActEnum.ATTACK and ash.team[ashidx[0]].alive and rocket.team[rocidx[0]].alive:
        dmg = computedamage(ash.team[ashidx[0]], rocket.team[rocidx[0]], bs.fieldtype)
        if rocdef:
            dmg = int(dmg * 0.5)
        rocket.team[rocidx[0]].takedamage(dmg)
        if game:
            game.sfx['attack'].play()
            game.addattackeffect(ash, ash.team[ashidx[0]])
            game.adddamagepopup(dmg, "rocket")
            game.triggerscreenshake(6)
            game.last_action["Ash"] = "ATTACK"
    
    if rocketact.kind == BActEnum.ATTACK and rocket.team[rocidx[0]].alive and ash.team[ashidx[0]].alive:
        dmg = computedamage(rocket.team[rocidx[0]], ash.team[ashidx[0]], bs.fieldtype)
        if ashdef:
            dmg = int(dmg * 0.5)
        ash.team[ashidx[0]].takedamage(dmg)
        if game:
            game.sfx['attack'].play()
            game.addattackeffect(rocket, rocket.team[rocidx[0]])
            game.adddamagepopup(dmg, "ash")
            game.triggerscreenshake(6)
            game.last_action["Team Rocket"] = "ATTACK"
    
    if not ash.team[ashidx[0]].alive:
        for i, p in enumerate(ash.team):
            if p.alive:
                ashidx[0] = i
                break
    if not rocket.team[rocidx[0]].alive:
        for i, p in enumerate(rocket.team):
            if p.alive:
                rocidx[0] = i
                break
    
    bs.ashactive, bs.rocketactive = ashidx[0], rocidx[0]

# ==================== MINIMAX WITH ALPHA-BETA PRUNING ====================
def minimaxalpha(me: Agent, opp: Agent, bs: BattleState, meisash: bool, depth: int, game: 'Game') -> BattleAction:
    """Minimax algorithm - PERFECTLY EQUAL for both agents"""
    
    def recurse(a: Agent, b: Agent, s: BattleState, ply: int, maximizing: bool, alpha: float, beta: float) -> Tuple[int, Optional[BattleAction]]:
        if ply == 0 or all(not p.alive for p in a.team) or all(not p.alive for p in b.team):
            score = evalstate(a if meisash else b, b if meisash else a, s)
            return (score if meisash else -score), None
        
        bestval = -1e9 if maximizing else 1e9
        bestact = None
        
        currentactiveidx = s.ashactive if maximizing else s.rocketactive
        oppactiveidx = s.rocketactive if maximizing else s.ashactive
        agentforactions = a if maximizing else b
        oppforactions = b if maximizing else a
        
        actions = legalactions(agentforactions, currentactiveidx, oppforactions.team[oppactiveidx])
        
        # Shuffle for maximum randomness
        random.shuffle(actions)
        
        for act in actions:
            aclone, bclone = cloneagents(a), cloneagents(b)
            sclone = BattleState(s.fieldtype, s.ashactive, s.rocketactive)
            
            myact = act
            oppact = BattleAction(BActEnum.ATTACK)
            ashact = myact if maximizing else oppact
            rocketact = oppact if maximizing else myact
            
            stepbattle(aclone, bclone, sclone, ashact, rocketact, None)
            val, _ = recurse(aclone, bclone, sclone, ply - 1, not maximizing, alpha, beta)
            
            if maximizing:
                if val > bestval:
                    bestval, bestact = val, act
                alpha = max(alpha, bestval)
            else:
                if val < bestval:
                    bestval, bestact = val, act
                beta = min(beta, bestval)
            
            if beta <= alpha:
                break
        
        return bestval, bestact
    
    _, action = recurse(
        me if meisash else opp,
        opp if meisash else me,
        bs,
        depth,
        meisash,
        -1e9,
        1e9
    )
    return action or BattleAction(BActEnum.ATTACK)

# ==================== GAME ENTITIES ====================
@dataclass
class DamagePopup:
    text: str
    pos: Tuple[float, float]
    starttime: float
    duration: float = 1.2
    color: Tuple[int, int, int] = (255, 220, 0)

@dataclass
class Particle:
    pos: List[float]
    vel: List[float]
    lifespan: float
    startlife: float
    color: Tuple[int, int, int]

# ==================== GAME STATES ====================
class GStateEnum(Enum):
    INTRO = auto()
    CATCH = auto()
    ELIXIR = auto()
    BATTLE = auto()
    PAUSED = auto()
    GAMEOVER = auto()

class BattleLog:
    """Log system for tracking game events"""
    def __init__(self, cap=10):
        self.lines: List[str] = []
        self.cap = cap
    
    def add(self, s: str):
        self.lines.append(s)
        if len(self.lines) > self.cap:
            self.lines = self.lines[-self.cap:]
    
    def clear(self):
        self.lines = []

# ==================== SOUND GENERATION ====================
def maketone(hz, duration_ms, samplerate=44100):
    """Generate simple tone for sound effects"""
    nsamples = int(samplerate * duration_ms / 1000.0)
    buf = np.zeros((nsamples, 2), dtype=np.int16)
    max_sample = 2**15 - 1
    t = np.arange(nsamples) / samplerate
    waveform = np.sin(2 * np.pi * hz * t) * max_sample * 0.3
    fade_len = max(1, nsamples // 10)
    waveform[nsamples - fade_len:] *= np.linspace(1, 0, fade_len)
    buf[:, 0] = waveform.astype(np.int16)
    buf[:, 1] = waveform.astype(np.int16)
    return pygame.sndarray.make_sound(buf)

def makeblastsound(duration_ms=300, samplerate=44100):
    """Generate blast sound effect"""
    nsamples = int(samplerate * duration_ms / 1000.0)
    t = np.linspace(0.0, duration_ms / 1000.0, nsamples)
    bass_freq = 80
    bass_wave = np.sin(2.0 * np.pi * bass_freq * t)
    noise = np.random.uniform(-1, 1, nsamples)
    envelope = np.exp(-t * 12.0)
    waveform = (bass_wave * 0.6 + noise * 0.4) * envelope * 0.6
    waveform = waveform / np.max(np.abs(waveform) + 1e-8) * (2**15 - 1.0)
    waveform = waveform.astype(np.int16)
    buf = np.zeros((nsamples, 2), dtype=np.int16)
    buf[:, 0] = waveform
    buf[:, 1] = waveform
    return pygame.sndarray.make_sound(buf)

# ==================== MAIN GAME CLASS ====================
class Game:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GStateEnum.INTRO
        self.paused_from_state = None
        
        # Window size tracking for scaling
        self.current_width = WIDTH
        self.current_height = HEIGHT
        
        # Initialize fonts (will be recreated on resize)
        self.create_fonts()
        
        # Initialize sounds
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(16)
        self.sfx = {
            'attack': makeblastsound(300),
            'heal': maketone(880, 300),
            'swap': maketone(550, 200),
            'catch': maketone(1200, 350),
            'gameover': maketone(200, 1500),
            'transition': maketone(660, 400),
        }
        
        for sound in self.sfx.values():
            sound.set_volume(0.8)
        
        # Load MP3 voices
        self.voices = self.load_voices()
        
        # Load sprites and backgrounds
        self.sprites = self.loadsprites()
        self.backgrounds = self.loadbackgrounds()
        
        # Voice playback tracking
        self.voice_played = {"intro": False, "phase1": False, "phase2": False, "phase3": False, "result": False}
        self.voice_start_time = {}
        self.voice_finished = {"intro": False, "phase1": False, "phase2": False, "phase3": False, "result": False}
        self.waiting_for_audio = False
        
        # Game timing
        self.phase_start_time = 0
        self.intro_start_time = time.time()
        
        # Battle log
        self.log = BattleLog(cap=12)
        
        # Last action tracker
        self.last_action = {"Ash": "WAITING", "Team Rocket": "WAITING"}
        
        # Initialize game data
        self.initgame()
    
    def create_fonts(self):
        """Create fonts based on current window size"""
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        pygame.font.init()
        self.font_small = pygame.font.SysFont(FONTNAME, max(12, int(16 * scale)), bold=True)
        self.font = pygame.font.SysFont(FONTNAME, max(14, int(20 * scale)), bold=True)
        self.font_big = pygame.font.SysFont(FONTNAME, max(20, int(36 * scale)), bold=True)
        self.font_huge = pygame.font.SysFont(FONTNAME, max(36, int(72 * scale)), bold=True)
        self.font_title = pygame.font.SysFont(FONTNAME, max(42, int(84 * scale)), bold=True)
    
    def get_scaled_size(self, base_size):
        """Get scaled size based on current window dimensions"""
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        return (int(base_size[0] * scale), int(base_size[1] * scale))
    
    def load_voices(self) -> Dict[str, pygame.mixer.Sound]:
        """Load MP3 voice files"""
        voices = {}
        for key, filename in VOICE_FILES.items():
            try:
                sound = pygame.mixer.Sound(filename)
                sound.set_volume(1.0)  # Maximum volume
                voices[key] = sound
                print(f"Loaded voice: {filename}")
            except pygame.error as e:
                print(f"Warning: Could not load voice {filename}: {e}")
                voices[key] = None
        return voices
    
    def play_voice(self, key: str):
        """Play voice for specific phase"""
        phase_key = key
        if not self.voice_played.get(phase_key, False):
            voice = self.voices.get(key)
            if voice:
                voice.play()
                self.voice_start_time[key] = time.time()
                self.waiting_for_audio = True
                print(f"Playing voice: {key}")
            else:
                # If voice file missing, mark as finished immediately
                self.voice_finished[phase_key] = True
            self.voice_played[phase_key] = True
    
    def is_voice_finished(self, key: str) -> bool:
        """Check if voice has finished playing"""
        if self.voice_finished.get(key, False):
            return True
        
        voice = self.voices.get(key)
        if voice is None:
            return True
        
        if key in self.voice_start_time:
            # Get audio length and check if enough time has passed
            duration = voice.get_length()
            elapsed = time.time() - self.voice_start_time[key]
            if elapsed >= duration:
                self.voice_finished[key] = True
                self.waiting_for_audio = False
                return True
        
        return False
    
    def initgame(self):
        """Initialize/Reset game state"""
        # Random field type with truly random seed
        random.seed(time.time())
        self.fieldtype = random.choice(["Fire", "Electric", "Water"])
        
        # Create agents with EXACTLY equal conditions
        self.ash = Agent("Ash", [Pokemon(n, t) for n, t in ASHTEAMSPECIES])
        self.rocket = Agent("Team Rocket", [Pokemon(n, t) for n, t in ROCKETTEAMSPECIES])
        
        # Grid for catching phase
        self.grid = [[0 for _ in range(GRIDW)] for _ in range(GRIDH)]
        self.genobstacles(0.08)
        
        # Spawn pokemon at fixed locations
        self.spawncatchtargets()
        
        # Position trainers at starting locations
        self.positiontrainers()
        
        # Catching state
        self.pokemon_caught = {"Ash": [], "Team Rocket": []}
        self.current_target = {"Ash": 0, "Team Rocket": 0}
        
        # Battle state
        self.bs = BattleState(self.fieldtype)
        self.nextdecisiontime = 0.0
        
        # Visual effects
        self.activeattackeffects: List[Tuple[Agent, Pokemon, float]] = []
        self.damagepopups: List[DamagePopup] = []
        self.particles: List[Particle] = []
        self.screenshake = 0
        
        # Elixir animation
        self.elixir_coins = {"Ash": [], "Team Rocket": []}
        
        # Winner
        self.winner = None
        self.celebration_time = 0
    
    def loadsprites(self) -> Dict[str, pygame.Surface]:
        """Load all image assets"""
        sprites = {}
        pokemonnames = {name for name, _ in ASHTEAMSPECIES} | {name for name, _ in ROCKETTEAMSPECIES}
        
        for name, filename in IMAGEASSETS.items():
            try:
                img = pygame.image.load(filename).convert_alpha()
                # Store original images, will scale on render
                sprites[f"{name}_original"] = img
            except pygame.error as e:
                print(f"Warning: Could not load {filename}: {e}")
        
        # Load elixir image
        try:
            elixir_img = pygame.image.load("elixir.png").convert_alpha()
            sprites["elixir_original"] = elixir_img
        except:
            print("Warning: Could not load elixir.png")
        
        return sprites
    
    def get_scaled_sprite(self, name: str, size_type: str):
        """Get scaled sprite based on current window size"""
        original = self.sprites.get(f"{name}_original")
        if not original:
            return None
        
        if size_type == "battle":
            target_size = self.get_scaled_size(BASE_BATTLESPRITESIZE)
        elif size_type == "token":
            target_size = self.get_scaled_size(BASE_TOKENSPRITESIZE)
        elif size_type == "trainer":
            target_size = self.get_scaled_size(BASE_TRAINERSPRITESIZE)
        elif size_type == "attack":
            target_size = self.get_scaled_size(BASE_ATTACKICONSIZE)
        elif size_type == "elixir":
            target_size = self.get_scaled_size(BASE_ELIXIRSIZE)
        else:
            return original
        
        return pygame.transform.smoothscale(original, target_size)
    
    def loadbackgrounds(self) -> Dict[str, pygame.Surface]:
        """Load background images"""
        bgs = {}
        for key, filename in BACKGROUNDS.items():
            try:
                img = pygame.image.load(filename).convert()
                bgs[f"{key}_original"] = img
                print(f"Loaded background: {filename}")
            except pygame.error as e:
                print(f"Warning: Could not load background {filename}: {e}")
        return bgs
    
    def get_scaled_background(self, key: str):
        """Get scaled background based on current window size"""
        original = self.backgrounds.get(f"{key}_original")
        if not original:
            return None
        return pygame.transform.smoothscale(original, (self.current_width, self.current_height))
    
    def genobstacles(self, density: float):
        """Generate random obstacles on grid"""
        rng = random.Random(42)
        for y in range(GRIDH):
            for x in range(GRIDW):
                if rng.random() < density:
                    if x > 0 and x < GRIDW - 1 and y > 0 and y < GRIDH - 1:
                        self.grid[y][x] = 1
    
    def spawncatchtargets(self):
        """Spawn pokemon at FIXED locations"""
        rng = random.Random(int(time.time()))  # Different seed each time
        
        def randcell():
            attempts = 0
            while attempts < 100:
                x, y = rng.randrange(2, GRIDW - 2), rng.randrange(2, GRIDH - 2)
                if self.grid[y][x] == 0:
                    return (x, y)
                attempts += 1
            return (GRIDW // 2, GRIDH // 2)
        
        self.pokemon_locations = {
            "Ash": {name: randcell() for name, _ in ASHTEAMSPECIES},
            "Team Rocket": {name: randcell() for name, _ in ROCKETTEAMSPECIES}
        }
    
    def positiontrainers(self):
        """Position trainers at starting locations"""
        self.ash.position = (1.0, GRIDH - 2.0)
        self.ash.targetpos = self.ash.position
        self.ash.current_path = []
        self.ash.path_index = 0
        
        self.rocket.position = (GRIDW - 2.0, 1.0)
        self.rocket.targetpos = self.rocket.position
        self.rocket.current_path = []
        self.rocket.path_index = 0
    
    def gridtopixel(self, gridpos: Tuple[float, float]) -> Tuple[float, float]:
        """Convert grid coordinates to pixel coordinates (scaled)"""
        x, y = gridpos
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        tile_size = TILE * scale
        offsetx = (self.current_width - GRIDW * tile_size) // 2
        offsety = 100 * scale
        return (offsetx + x * tile_size + tile_size / 2, offsety + y * tile_size + tile_size / 2)
    
    def handle_resize(self, new_width, new_height):
        """Handle window resize event"""
        self.current_width = new_width
        self.current_height = new_height
        self.create_fonts()
    
    def update(self, dt: float):
        """Main update loop"""
        for p in self.ash.team + self.rocket.team:
            p.update(dt)
        
        self.updateanimations(dt)
        
        if self.state == GStateEnum.INTRO:
            self.updateintro(dt)
        elif self.state == GStateEnum.CATCH:
            self.updatecatch(dt)
        elif self.state == GStateEnum.ELIXIR:
            self.updateelixir(dt)
        elif self.state == GStateEnum.BATTLE:
            self.updatebattle(dt)
        elif self.state == GStateEnum.GAMEOVER:
            self.updategameover(dt)
    
    def updateintro(self, dt: float):
        """Update intro screen"""
        if not self.voice_played["intro"]:
            self.play_voice("intro")
        
        elapsed = time.time() - self.intro_start_time
        if elapsed > INTRO_TIME:
            self.gotocatchphase()
    
    def gotocatchphase(self):
        """Transition to catching phase"""
        self.state = GStateEnum.CATCH
        self.log.add("Phase 1: Catching Pokemon begins!")
        self.sfx['transition'].play()
        self.play_voice("phase1")
        # Don't start timer yet - wait for audio to finish
    
    def updatecatch(self, dt: float):
        """Update catching phase - trainers continuously move to catch pokemon"""
        # Wait for audio to finish before starting phase
        if self.waiting_for_audio and not self.is_voice_finished("phase1"):
            return
        
        # Start timer after audio finishes
        if not hasattr(self, 'phase_start_time') or self.phase_start_time == 0:
            self.phase_start_time = time.time()
        
        elapsed = time.time() - self.phase_start_time
        remaining = max(0.0, PHASE1_TIME - elapsed)
        
        if remaining == 0 or (len(self.pokemon_caught["Ash"]) >= 3 and len(self.pokemon_caught["Team Rocket"]) >= 3):
            self.goelixirphase()
            return
        
        # Update trainer AI - FIXED: Trainers keep moving
        self.movetrainer(self.ash, "Ash", dt)
        self.movetrainer(self.rocket, "Team Rocket", dt)
    
    def movetrainer(self, agent: Agent, tag: str, dt: float):
        """Move trainer to catch pokemon using A* - FIXED: Continuous movement"""
        # Check if already caught all pokemon
        if len(self.pokemon_caught[tag]) >= 3:
            return
        
        # Get current target
        target_idx = self.current_target[tag]
        if target_idx >= len(ASHTEAMSPECIES if tag == "Ash" else ROCKETTEAMSPECIES):
            return
        
        pokemon_name = (ASHTEAMSPECIES if tag == "Ash" else ROCKETTEAMSPECIES)[target_idx][0]
        if pokemon_name in self.pokemon_caught[tag]:
            self.current_target[tag] += 1
            agent.current_path = []
            agent.path_index = 0
            return
        
        goal = self.pokemon_locations[tag][pokemon_name]
        current_grid = (int(round(agent.position[0])), int(round(agent.position[1])))
        
        # Check if reached goal
        if current_grid == goal:
            if agent.fuel >= FUELPERCATCH:
                agent.fuel -= FUELPERCATCH
                self.pokemon_caught[tag].append(pokemon_name)
                self.log.add(f"{tag} caught {pokemon_name}!")
                self.sfx['catch'].play()
                self.current_target[tag] += 1
                agent.current_path = []
                agent.path_index = 0
            return
        
        # Calculate new path if needed
        if not agent.current_path or agent.path_index >= len(agent.current_path) - 1:
            path = astar(self.grid, current_grid, goal)
            if path and len(path) > 1:
                agent.current_path = path
                agent.path_index = 0
        
        # Move along path
        if agent.current_path and agent.path_index < len(agent.current_path) - 1:
            next_idx = agent.path_index + 1
            next_cell = agent.current_path[next_idx]
            agent.targetpos = (float(next_cell[0]), float(next_cell[1]))
            
            # Move towards target
            dx = agent.targetpos[0] - agent.position[0]
            dy = agent.targetpos[1] - agent.position[1]
            dist = math.hypot(dx, dy)
            
            if dist < 0.1:
                agent.position = agent.targetpos
                agent.path_index = next_idx
            else:
                speed = MOVESPEEDPX * dt
                if speed > dist:
                    agent.position = agent.targetpos
                    agent.path_index = next_idx
                else:
                    agent.position = (
                        agent.position[0] + dx / dist * speed,
                        agent.position[1] + dy / dist * speed
                    )
    
    def goelixirphase(self):
        """Transition to elixir buying phase"""
        self.state = GStateEnum.ELIXIR
        self.ash.coins = COINSPERAGENT
        self.rocket.coins = COINSPERAGENT
        self.log.add("Phase 2: Buying Elixirs begins!")
        self.sfx['transition'].play()
        self.play_voice("phase2")
        self.doelixirpurchases()
        self.init_elixir_animation()
        # Don't start timer yet - wait for audio to finish
        self.phase_start_time = 0
    
    def init_elixir_animation(self):
        """Initialize elixir collection animations"""
        for agent_name in ["Ash", "Team Rocket"]:
            agent = self.ash if agent_name == "Ash" else self.rocket
            count = sum(agent.elixirs.values())
            for i in range(count):
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(50, 150)
                self.elixir_coins[agent_name].append({
                    "pos": [self.current_width // 2, self.current_height // 2],
                    "vel": [math.cos(angle) * radius, math.sin(angle) * radius],
                    "collected": False
                })
    
    def updateelixir(self, dt: float):
        """Update elixir phase - show collection animations"""
        # Wait for audio to finish before starting phase
        if self.waiting_for_audio and not self.is_voice_finished("phase2"):
            return
        
        # Start timer after audio finishes
        if self.phase_start_time == 0:
            self.phase_start_time = time.time()
        
        elapsed = time.time() - self.phase_start_time
        if elapsed > PHASE2_TIME:
            self.gobattlephase()
            return
        
        # Animate elixir collection
        for agent_name in ["Ash", "Team Rocket"]:
            target_x = self.current_width // 4 if agent_name == "Ash" else 3 * self.current_width // 4
            target_y = self.current_height // 2
            
            for coin in self.elixir_coins[agent_name]:
                if not coin["collected"]:
                    dx = target_x - coin["pos"][0]
                    dy = target_y - coin["pos"][1]
                    dist = math.hypot(dx, dy)
                    if dist < 10:
                        coin["collected"] = True
                    else:
                        speed = 300 * dt
                        coin["pos"][0] += dx / dist * speed
                        coin["pos"][1] += dy / dist * speed
    
    def doelixirpurchases(self):
        """AI agents purchase elixirs"""
        def buylogic(agent: Agent):
            for k in ELIXIRS:
                agent.elixirs[k] = 0
            
            coins = agent.coins
            items = sorted(ELIXIRS.items(), key=lambda kv: kv[1][0] / kv[1][1], reverse=True)
            
            for name, (healamt, price) in items:
                while coins >= price:
                    agent.elixirs[name] = agent.elixirs.get(name, 0) + 1
                    coins -= price
                    if coins < price:
                        break
            
            agent.coins = coins
        
        buylogic(self.ash)
        buylogic(self.rocket)
        self.log.add(f"Ash bought: {self.format_elixirs(self.ash.elixirs)}")
        self.log.add(f"Team Rocket bought: {self.format_elixirs(self.rocket.elixirs)}")
    
    def format_elixirs(self, elixirs: Dict[str, int]) -> str:
        """Format elixir dict for display"""
        items = [f"{v}x{k}" for k, v in elixirs.items() if v > 0]
        return ", ".join(items) if items else "none"
    
    def gobattlephase(self):
        """Transition to battle phase"""
        self.state = GStateEnum.BATTLE
        self.log.add(f"Phase 3: Battle begins! Field: {self.fieldtype}")
        self.sfx['transition'].play()
        self.play_voice("phase3")
        # Don't start timer yet - wait for audio to finish
        self.phase_start_time = 0
        self.nextdecisiontime = 0
    
    def updatebattle(self, dt: float):
        """Update battle phase - turn-based combat"""
        # Wait for audio to finish before starting phase
        if self.waiting_for_audio and not self.is_voice_finished("phase3"):
            return
        
        # Start timer after audio finishes
        if self.phase_start_time == 0:
            self.phase_start_time = time.time()
            self.nextdecisiontime = time.time() + 1.0
        
        ash_alive = any(p.alive for p in self.ash.team)
        rocket_alive = any(p.alive for p in self.rocket.team)
        
        if not ash_alive or not rocket_alive:
            self.winner = "Team Rocket" if not ash_alive else "Ash"
            self.gogameover()
            return
        
        elapsed = time.time() - self.phase_start_time
        if elapsed > PHASE3_TIME:
            ash_hp = sum(p.hp for p in self.ash.team)
            rocket_hp = sum(p.hp for p in self.rocket.team)
            if ash_hp > rocket_hp:
                self.winner = "Ash"
            elif rocket_hp > ash_hp:
                self.winner = "Team Rocket"
            else:
                self.winner = "Draw"
            self.gogameover()
            return
        
        now = time.time()
        if now < self.nextdecisiontime:
            return
        
        self.nextdecisiontime = now + 0.7
        
        # EQUAL depth for both agents
        ashact = minimaxalpha(self.ash, self.rocket, self.bs, meisash=True, depth=3, game=self)
        rocketact = minimaxalpha(self.rocket, self.ash, self.bs, meisash=False, depth=3, game=self)
        
        stepbattle(self.ash, self.rocket, self.bs, ashact, rocketact, self)
        self.logturn(ashact, rocketact)
    
    def logturn(self, aact: BattleAction, ract: BattleAction):
        """Log battle turn actions"""
        def actstr(name, act, agent, idx):
            pname = agent.team[idx].name
            if act.kind == BActEnum.ATTACK:
                return f"{pname} attacks!"
            if act.kind == BActEnum.DEFEND:
                return f"{pname} defends!"
            if act.kind == BActEnum.SWAP:
                return f"{name} swaps Pokemon!"
            if act.kind == BActEnum.HEAL:
                return f"{name} uses {act.arg} elixir!"
            return f"{name} waits"
        
        self.log.add(actstr("Ash", aact, self.ash, self.bs.ashactive))
        self.log.add(actstr("TR", ract, self.rocket, self.bs.rocketactive))
    
    def gogameover(self):
        """Transition to game over screen"""
        self.state = GStateEnum.GAMEOVER
        self.phase_start_time = time.time()
        self.celebration_time = time.time()
        
        if self.winner == "Draw":
            self.log.add("Game Over - It's a Draw!")
            self.play_voice("draw")
        elif self.winner == "Ash":
            self.log.add("Game Over - Ash Wins!")
            self.play_voice("ash_wins")
        else:
            self.log.add("Game Over - Team Rocket Wins!")
            self.play_voice("rocket_wins")
        
        self.sfx['gameover'].play()
    
    def updategameover(self, dt: float):
        """Update game over screen"""
        pass
    
    def updateanimations(self, dt: float):
        """Update all visual effects"""
        now = time.time()
        
        self.activeattackeffects = [fx for fx in self.activeattackeffects if now < fx[2]]
        self.damagepopups = [p for p in self.damagepopups if now < p.starttime + p.duration]
        
        newparticles = []
        for p in self.particles:
            p.pos[0] += p.vel[0] * dt
            p.pos[1] += p.vel[1] * dt
            p.lifespan -= dt
            if p.lifespan > 0:
                newparticles.append(p)
        self.particles = newparticles
        
        if self.screenshake > 0:
            self.screenshake -= 1
    
    def draw(self):
        """Main draw loop"""
        renderoffset = (0, 0)
        if self.screenshake > 0:
            renderoffset = (random.randint(-6, 6), random.randint(-6, 6))
        
        tempsurface = self.screen.copy()
        
        if self.state == GStateEnum.INTRO:
            self.drawintro(tempsurface)
        elif self.state == GStateEnum.CATCH:
            self.drawcatchphase(tempsurface)
        elif self.state == GStateEnum.ELIXIR:
            self.drawelixirphase(tempsurface)
        elif self.state == GStateEnum.BATTLE:
            self.drawbattlephase(tempsurface)
        elif self.state == GStateEnum.GAMEOVER:
            self.drawgameover(tempsurface)
        elif self.state == GStateEnum.PAUSED:
            if self.paused_from_state == GStateEnum.CATCH:
                self.drawcatchphase(tempsurface)
            elif self.paused_from_state == GStateEnum.ELIXIR:
                self.drawelixirphase(tempsurface)
            elif self.paused_from_state == GStateEnum.BATTLE:
                self.drawbattlephase(tempsurface)
            self.drawpausedoverlay(tempsurface)
        
        self.screen.blit(tempsurface, renderoffset)
        pygame.display.flip()
    
    def drawintro(self, surf: pygame.Surface):
        """Draw intro screen with background image"""
        bg = self.get_scaled_background("intro")
        if bg:
            surf.blit(bg, (0, 0))
        else:
            surf.fill((20, 40, 60))
        
        overlay = pygame.Surface((self.current_width, self.current_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surf.blit(overlay, (0, 0))
        
        title_text = "Pokemon Battle Arena"
        for offset in [(-3, -3), (-3, 3), (3, -3), (3, 3)]:
            title_outline = self.font_title.render(title_text, True, (0, 0, 0))
            surf.blit(title_outline, (self.current_width // 2 - title_outline.get_width() // 2 + offset[0], int(80 * self.current_height / BASE_HEIGHT) + offset[1]))
        title = self.font_title.render(title_text, True, (255, 255, 100))
        surf.blit(title, (self.current_width // 2 - title.get_width() // 2, int(80 * self.current_height / BASE_HEIGHT)))
        
        subtitle = self.font_big.render("AI Battle System", True, (255, 255, 255))
        surf.blit(subtitle, subtitle.get_rect(center=(self.current_width // 2, int(180 * self.current_height / BASE_HEIGHT))))
        
        rules = [
            "GAME RULES",
            "",
            "Two AI agents compete: Ash vs Team Rocket",
            "",
            "Phase 1 (30s): Catch 3 Pokemon using A* pathfinding",
            "Phase 2 (5s): Buy healing elixirs with coins",
            "Phase 3 (130s): Turn-based Pokemon battle",
            "  - Minimax with Alpha-Beta Pruning + Fuzzy Logic",
            "  - Type advantages: Fire>Electric, Electric>Water, Water>Fire",
            "",
            "Controls: [P] Pause  [R] Resume  [E] Exit  [A] Play Again",
            "",
            "Starting in a moment...",
        ]
        
        y = int(260 * self.current_height / BASE_HEIGHT)
        for line in rules:
            if line == "GAME RULES":
                for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                    outline = self.font_big.render(line, True, (0, 0, 0))
                    surf.blit(outline, (self.current_width // 2 - outline.get_width() // 2 + ox, y + oy))
                text = self.font_big.render(line, True, (255, 255, 100))
            elif line.startswith("Phase"):
                text = self.font.render(line, True, (100, 255, 200))
            elif line == "":
                y += int(5 * self.current_height / BASE_HEIGHT)
                continue
            else:
                text = self.font_small.render(line, True, (255, 255, 255))
            surf.blit(text, (self.current_width // 2 - text.get_width() // 2, y))
            y += int(28 * self.current_height / BASE_HEIGHT)
    
    def drawcatchphase(self, surf: pygame.Surface):
        """Draw catching phase with forest background"""
        bg = self.get_scaled_background("forest")
        if bg:
            surf.blit(bg, (0, 0))
        else:
            surf.fill((40, 90, 60))
        
        self.drawgrid(surf)
        
        # Draw FIXED pokemon locations
        for agent_name in ["Ash", "Team Rocket"]:
            for pokemon_name, gridpos in self.pokemon_locations[agent_name].items():
                if pokemon_name not in self.pokemon_caught[agent_name]:
                    pixelpos = self.gridtopixel((float(gridpos[0]), float(gridpos[1])))
                    sprite = self.get_scaled_sprite(pokemon_name, "token")
                    if sprite:
                        bob = math.sin(time.time() * 6) * 4
                        rect = sprite.get_rect(center=(int(pixelpos[0]), int(pixelpos[1] + bob)))
                        surf.blit(sprite, rect)
                        label = self.font_small.render(pokemon_name[:7], True, (255, 255, 0))
                        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
                        labelrect = label.get_rect(center=(int(pixelpos[0]), int(pixelpos[1]) + int(40 * scale)))
                        surf.blit(label, labelrect)
        
        # Draw MOVING trainers
        for agent, agent_name in [(self.ash, "Ash"), (self.rocket, "Team Rocket")]:
            pixelpos = self.gridtopixel(agent.position)
            sprite = self.get_scaled_sprite(agent_name, "trainer")
            if sprite:
                rect = sprite.get_rect(center=(int(pixelpos[0]), int(pixelpos[1])))
                surf.blit(sprite, rect)
                label = self.font.render(agent_name, True, (255, 255, 255))
                label_bg = self.font.render(agent_name, True, (0, 0, 0))
                scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
                labelrect = label.get_rect(center=(int(pixelpos[0]), int(pixelpos[1]) - int(50 * scale)))
                surf.blit(label_bg, labelrect.move(2, 2))
                surf.blit(label, labelrect)
        
        self.drawhud(surf, "PHASE 1: CATCHING POKEMON", PHASE1_TIME)
    
    def drawelixirphase(self, surf: pygame.Surface):
        """Draw elixir buying phase with animations"""
        bg = self.get_scaled_background("elixir")
        if bg:
            surf.blit(bg, (0, 0))
        else:
            surf.fill((60, 40, 100))
        
        overlay = pygame.Surface((self.current_width, self.current_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surf.blit(overlay, (0, 0))
        
        title = self.font_huge.render("PHASE 2", True, (255, 200, 100))
        surf.blit(title, title.get_rect(center=(self.current_width // 2, int(80 * self.current_height / BASE_HEIGHT))))
        
        subtitle = self.font_big.render("Collecting Elixirs", True, (200, 255, 200))
        surf.blit(subtitle, subtitle.get_rect(center=(self.current_width // 2, int(160 * self.current_height / BASE_HEIGHT))))
        
        # Draw animated elixir coins
        elixir_sprite = self.get_scaled_sprite("elixir", "elixir")
        for agent_name in ["Ash", "Team Rocket"]:
            for coin in self.elixir_coins[agent_name]:
                if elixir_sprite:
                    rect = elixir_sprite.get_rect(center=(int(coin["pos"][0]), int(coin["pos"][1])))
                    surf.blit(elixir_sprite, rect)
        
        # Show purchases
        y = int(250 * self.current_height / BASE_HEIGHT)
        
        ash_title = self.font_big.render("Ash's Elixirs:", True, (100, 200, 255))
        surf.blit(ash_title, (self.current_width // 4 - ash_title.get_width() // 2, y))
        y += int(60 * self.current_height / BASE_HEIGHT)
        for elixir, count in self.ash.elixirs.items():
            if count > 0:
                healamt, price = ELIXIRS[elixir]
                text = self.font.render(f"{count}x {elixir} (heals {healamt} HP)", True, (255, 255, 255))
                surf.blit(text, (self.current_width // 4 - text.get_width() // 2, y))
                y += int(40 * self.current_height / BASE_HEIGHT)
        
        y = int(250 * self.current_height / BASE_HEIGHT)
        rocket_title = self.font_big.render("Team Rocket's Elixirs:", True, (255, 100, 100))
        surf.blit(rocket_title, (3 * self.current_width // 4 - rocket_title.get_width() // 2, y))
        y += int(60 * self.current_height / BASE_HEIGHT)
        for elixir, count in self.rocket.elixirs.items():
            if count > 0:
                healamt, price = ELIXIRS[elixir]
                text = self.font.render(f"{count}x {elixir} (heals {healamt} HP)", True, (255, 255, 255))
                surf.blit(text, (3 * self.current_width // 4 - text.get_width() // 2, y))
                y += int(40 * self.current_height / BASE_HEIGHT)
        
        elapsed = time.time() - self.phase_start_time
        remaining = max(0, PHASE2_TIME - elapsed)
        timer = self.font_big.render(f"Time: {remaining:.1f}s", True, (255, 255, 100))
        surf.blit(timer, timer.get_rect(center=(self.current_width // 2, self.current_height - int(120 * self.current_height / BASE_HEIGHT))))
        
        self.drawcontrols(surf)
    
    def drawbattlephase(self, surf: pygame.Surface):
        """Draw battle phase with battleground background"""
        bg = self.get_scaled_background("battle")
        if bg:
            surf.blit(bg, (0, 0))
        else:
            fieldcolor = TYPECOLOR.get(self.fieldtype, (50, 50, 50))
            bgcolor = tuple(c // 3 for c in fieldcolor)
            surf.fill(bgcolor)
        
        self.drawbattlescene(surf)
        self.draweffects(surf)
        self.drawhud(surf, "PHASE 3: BATTLE!", PHASE3_TIME)
    
    def drawbattlescene(self, surf: pygame.Surface):
        """Draw battle arena with Pokemon"""
        cx, cy = self.current_width // 2, self.current_height // 2
        
        a = self.ash.team[self.bs.ashactive]
        r = self.rocket.team[self.bs.rocketactive]
        
        # Calculate attack animations
        now = time.time()
        ashlunge = 0
        rocketlunge = 0
        
        for side, _, endtime in reversed(self.activeattackeffects):
            progress = 1.0 - max(0, (endtime - now) / ATTACKEFFECTDURATION)
            if 0 < progress < 1:
                scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
                lunge = math.sin(progress * math.pi) * 60 * scale
                if side.name == "Ash":
                    ashlunge = lunge
                else:
                    rocketlunge = lunge
        
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        offset_x = int(300 * scale)
        
        # Draw Pokemon
        if a.alive:
            ashsprite = self.get_scaled_sprite(a.name, "battle")
            if ashsprite:
                pos = (cx - offset_x + ashlunge, cy + a.boboffset)
                rect = ashsprite.get_rect(center=pos)
                surf.blit(ashsprite, rect)
                self.drawpokemonhp(surf, a, cx - int(400 * scale), cy + int(120 * scale))
                # Action label BEHIND pokemon (left side) - increased distance
                action_text = self.font.render(f"{self.last_action['Ash']}", True, (255, 255, 100))
                action_bg = self.font.render(f"{self.last_action['Ash']}", True, (0, 0, 0))
                action_x = cx - offset_x - int(200 * scale)  # Increased from 150 to 200
                action_y = cy
                surf.blit(action_bg, (action_x + 2, action_y + 2))
                surf.blit(action_text, (action_x, action_y))
        
        if r.alive:
            rocketsprite = self.get_scaled_sprite(r.name, "battle")
            if rocketsprite:
                pos = (cx + offset_x - rocketlunge, cy + r.boboffset)
                rect = rocketsprite.get_rect(center=pos)
                surf.blit(rocketsprite, rect)
                self.drawpokemonhp(surf, r, cx + int(200 * scale), cy + int(120 * scale))
                # Action label BEHIND pokemon (right side) - increased distance
                action_text = self.font.render(f"{self.last_action['Team Rocket']}", True, (255, 255, 100))
                action_bg = self.font.render(f"{self.last_action['Team Rocket']}", True, (0, 0, 0))
                action_x = cx + offset_x + int(100 * scale)  # Increased from 50 to 100
                action_y = cy
                surf.blit(action_bg, (action_x + 2, action_y + 2))
                surf.blit(action_text, (action_x, action_y))
        
        # Draw trainer info panels (FIXED: Position properly to avoid cropping)
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        panel_y = int(100 * scale)  # More space from top
        self.drawtrainerinfo(surf, self.ash, int(30 * scale), panel_y)
        self.drawtrainerinfo(surf, self.rocket, self.current_width - int(400 * scale), panel_y)  # Increased from 380 to 400
    
    def drawpokemonhp(self, surf: pygame.Surface, pokemon: Pokemon, x: int, y: int):
        """Draw Pokemon HP bar"""
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        w, h = int(250 * scale), int(24 * scale)
        frac = pokemon.displayhp / pokemon.maxhp if pokemon.maxhp > 0 else 0
        
        pygame.draw.rect(surf, (40, 40, 40), (x, y, w, h), border_radius=int(8 * scale))
        if frac > 0.5:
            color = (80, 220, 80)
        elif frac > 0.25:
            color = (220, 220, 80)
        else:
            color = (220, 80, 80)
        pygame.draw.rect(surf, color, (x, y, int(w * frac), h), border_radius=int(8 * scale))
        pygame.draw.rect(surf, (255, 255, 255), (x, y, w, h), int(3 * scale), border_radius=int(8 * scale))
        
        hptext = self.font.render(f"{int(pokemon.displayhp)}/{pokemon.maxhp}", True, (255, 255, 255))
        surf.blit(hptext, (x + w // 2 - hptext.get_width() // 2, y + int(3 * scale)))
        
        nametext = self.font_big.render(pokemon.name, True, (255, 255, 255))
        for ox, oy in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
            outline = self.font_big.render(pokemon.name, True, (0, 0, 0))
            surf.blit(outline, (x + ox, y - int(35 * scale) + oy))
        surf.blit(nametext, (x, y - int(35 * scale)))
    
    def drawtrainerinfo(self, surf: pygame.Surface, agent: Agent, x: int, y: int):
        """Draw trainer info panel"""
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        panel_width = int(360 * scale)  # Increased from 350
        panel_height = int(260 * scale)  # Increased from 220
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        surf.blit(panel, (x, y))
        pygame.draw.rect(surf, (255, 255, 255), (x, y, panel_width, panel_height), int(3 * scale), border_radius=int(12 * scale))
        
        trainersprite = self.get_scaled_sprite(agent.name, "trainer")
        if trainersprite:
            surf.blit(trainersprite, (x + int(10 * scale), y + int(10 * scale)))
        
        name = self.font_big.render(agent.name, True, (255, 255, 100))
        surf.blit(name, (x + int(100 * scale), y + int(25 * scale)))  # Increased from 20 to 25
        
        activeidx = self.bs.ashactive if agent.name == "Ash" else self.bs.rocketactive
        py = y + int(95 * scale)  # Increased from 80 to 95
        for i, p in enumerate(agent.team):
            prefix = "▶ " if i == activeidx and p.alive else "  "
            color = (255, 255, 255) if p.alive else (120, 120, 120)
            status = "✓" if p.alive else "✗"
            text = self.font_small.render(f"{prefix}{p.name} {status}", True, color)
            surf.blit(text, (x + int(15 * scale), py))
            
            if p.alive:
                barw = int(120 * scale)
                barh = int(10 * scale)
                frac = p.displayhp / p.maxhp
                pygame.draw.rect(surf, (60, 60, 60), (x + int(200 * scale), py + int(3 * scale), barw, barh))
                pygame.draw.rect(surf, (80, 200, 80), (x + int(200 * scale), py + int(3 * scale), int(barw * frac), barh))
            
            py += int(35 * scale)  # Increased spacing from 32 to 35
        
        elixir_text = f"Elixirs: {self.format_elixirs(agent.elixirs)}"
        elixir = self.font_small.render(elixir_text, True, (200, 255, 200))
        surf.blit(elixir, (x + int(15 * scale), py + int(12 * scale)))
    
    def draweffects(self, surf: pygame.Surface):
        """Draw battle effects"""
        cx, cy = self.current_width // 2, self.current_height // 2
        now = time.time()
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        
        # Draw attack icons
        lastashattack = None
        lastrocketattack = None
        
        for side, attacker, endtime in reversed(self.activeattackeffects):
            if side.name == "Ash" and lastashattack is None:
                lastashattack = (attacker, endtime)
            elif side.name == "Team Rocket" and lastrocketattack is None:
                lastrocketattack = (attacker, endtime)
        
        if lastashattack:
            attacker, endtime = lastashattack
            progress = 1 - (endtime - now) / ATTACKEFFECTDURATION
            target_size = self.get_scaled_size(BASE_ATTACKICONSIZE)
            size = (int(target_size[0] * (1 + progress * 0.6)), int(target_size[1] * (1 + progress * 0.6)))
            alpha = int(255 * (1 - progress))
            
            icon_name = None
            if attacker.name == "Pikachu":
                icon_name = "electricright"
            elif attacker.name == "Charmander":
                icon_name = "fireright"
            elif attacker.name == "Squirtle":
                icon_name = "waterright"
            
            if icon_name:
                original = self.sprites.get(f"{icon_name}_original")
                if original:
                    scaledicon = pygame.transform.smoothscale(original, size)
                    scaledicon.set_alpha(alpha)
                    posx = cx - int(100 * scale)
                    iconrect = scaledicon.get_rect(center=(posx, cy))
                    surf.blit(scaledicon, iconrect)
        
        if lastrocketattack:
            attacker, endtime = lastrocketattack
            progress = 1 - (endtime - now) / ATTACKEFFECTDURATION
            target_size = self.get_scaled_size(BASE_ATTACKICONSIZE)
            size = (int(target_size[0] * (1 + progress * 0.6)), int(target_size[1] * (1 + progress * 0.6)))
            alpha = int(255 * (1 - progress))
            
            icon_name = None
            if attacker.name == "Meowth":
                icon_name = "electricleft"
            elif attacker.name == "Weezing":
                icon_name = "fireleft"
            elif attacker.name == "Wobbuffet":
                icon_name = "waterleft"
            
            if icon_name:
                original = self.sprites.get(f"{icon_name}_original")
                if original:
                    scaledicon = pygame.transform.smoothscale(original, size)
                    scaledicon.set_alpha(alpha)
                    posx = cx + int(100 * scale)
                    iconrect = scaledicon.get_rect(center=(posx, cy))
                    surf.blit(scaledicon, iconrect)
        
        # Draw damage popups
        for popup in self.damagepopups:
            progress = (now - popup.starttime) / popup.duration
            yoffset = -80 * progress * scale
            alpha = int(255 * (1 - progress ** 2))
            fontsurf = self.font_huge.render(popup.text, True, popup.color)
            fontsurf.set_alpha(alpha)
            pos = (popup.pos[0], popup.pos[1] + yoffset)
            surf.blit(fontsurf, fontsurf.get_rect(center=pos))
        
        # Draw particles
        for p in self.particles:
            alpha = int(255 * (p.lifespan / p.startlife))
            size = int(12 * (p.lifespan / p.startlife) * scale)
            if size > 0:
                partsurf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                color = (*p.color, alpha)
                pygame.draw.circle(partsurf, color, (size, size), size)
                surf.blit(partsurf, (p.pos[0] - size, p.pos[1] - size), special_flags=pygame.BLEND_RGBA_ADD)
    
    def drawhud(self, surf: pygame.Surface, phase_title: str, phase_duration: float):
        """Draw HUD with phase info and timer"""
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        pygame.draw.rect(surf, (20, 20, 20, 220), (0, 0, self.current_width, int(90 * scale)))
        
        title = self.font_big.render(phase_title, True, (255, 255, 100))
        surf.blit(title, (int(30 * scale), int(25 * scale)))
        
        elapsed = time.time() - self.phase_start_time
        remaining = max(0, phase_duration - elapsed)
        timer_color = (255, 100, 100) if remaining < 20 else (100, 255, 100)
        timer = self.font_big.render(f"Time: {remaining:.1f}s", True, timer_color)
        surf.blit(timer, (self.current_width - timer.get_width() - int(30 * scale), int(25 * scale)))
        
        if self.state == GStateEnum.BATTLE:
            fieldcolor = TYPECOLOR.get(self.fieldtype, (255, 255, 255))
            field = self.font.render(f"Field: {self.fieldtype}", True, fieldcolor)
            surf.blit(field, (self.current_width // 2 - field.get_width() // 2, int(35 * scale)))
        
        self.drawlogwindow(surf)
        self.drawcontrols(surf)
    
    def drawlogwindow(self, surf: pygame.Surface):
        """Draw battle log window"""
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        log_y = self.current_height - int(200 * scale)
        pygame.draw.rect(surf, (20, 20, 20, 220), (int(15 * scale), log_y, self.current_width - int(30 * scale), int(150 * scale)))
        pygame.draw.rect(surf, (100, 100, 100), (int(15 * scale), log_y, self.current_width - int(30 * scale), int(150 * scale)), int(3 * scale))
        
        log_title = self.font.render("Battle Log", True, (255, 255, 100))
        surf.blit(log_title, (int(30 * scale), log_y + int(8 * scale)))
        
        y = log_y + int(40 * scale)
        for line in self.log.lines[-5:]:
            text = self.font_small.render(line, True, (240, 240, 240))
            surf.blit(text, (int(30 * scale), y))
            y += int(22 * scale)
    
    def drawcontrols(self, surf: pygame.Surface):
        """Draw control instructions"""
        controls = "[P] Pause  [R] Resume  [E] Exit  [A] Play Again"
        text = self.font_small.render(controls, True, (200, 200, 200))
        surf.blit(text, (self.current_width // 2 - text.get_width() // 2, self.current_height - int(35 * self.current_height / BASE_HEIGHT)))
    
    def drawgameover(self, surf: pygame.Surface):
        """Draw game over screen with winner image and celebration"""
        for y in range(self.current_height):
            ratio = y / self.current_height
            if self.winner == "Ash":
                color = (int(20 + ratio * 60), int(40 + ratio * 100), int(100 + ratio * 140))
            elif self.winner == "Team Rocket":
                color = (int(100 + ratio * 120), int(20 + ratio * 60), int(40 + ratio * 100))
            else:
                color = (int(60 + ratio * 80), int(60 + ratio * 80), int(60 + ratio * 80))
            pygame.draw.line(surf, color, (0, y), (self.current_width, y))
        
        y = int(120 * self.current_height / BASE_HEIGHT)
        if self.winner == "Draw":
            title = self.font_huge.render("IT'S A DRAW!", True, (255, 255, 255))
        else:
            title = self.font_huge.render(f"{self.winner} WINS!", True, (255, 255, 100))
        surf.blit(title, title.get_rect(center=(self.current_width // 2, y)))
        
        if self.winner != "Draw":
            elapsed = time.time() - self.celebration_time
            scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
            bounce = abs(math.sin(elapsed * 4)) * 30 * scale
            
            winner_sprite = self.get_scaled_sprite(self.winner, "trainer")
            if winner_sprite:
                big_sprite = pygame.transform.scale(winner_sprite, (int(200 * scale), int(200 * scale)))
                rect = big_sprite.get_rect(center=(self.current_width // 2, int((y + 180) * self.current_height / BASE_HEIGHT + bounce)))
                surf.blit(big_sprite, rect)
            
            congrats = self.font_big.render("🏆 CONGRATULATIONS! 🏆", True, (255, 215, 0))
            surf.blit(congrats, congrats.get_rect(center=(self.current_width // 2, int((y + 340) * self.current_height / BASE_HEIGHT))))
            
            if int(elapsed * 10) % 5 == 0:
                for _ in range(3):
                    self.addparticleeffect((self.current_width // 2, int((y + 180) * self.current_height / BASE_HEIGHT)), (255, 215, 0), 10)
        
        y = self.current_height - int(300 * self.current_height / BASE_HEIGHT)
        stats = [
            "Final Stats:",
            "",
            f"Ash - {sum(p.hp for p in self.ash.team)} HP remaining",
            f"Team Rocket - {sum(p.hp for p in self.rocket.team)} HP remaining",
            "",
            "Controls:",
            "[A] Play Again    [E] Exit",
        ]
        
        for line in stats:
            if line == "Final Stats:" or line == "Controls:":
                text = self.font_big.render(line, True, (255, 255, 100))
            elif line == "":
                y += int(12 * self.current_height / BASE_HEIGHT)
                continue
            else:
                text = self.font.render(line, True, (255, 255, 255))
            surf.blit(text, text.get_rect(center=(self.current_width // 2, y)))
            y += int(38 * self.current_height / BASE_HEIGHT)
        
        self.drawlogwindow(surf)
    
    def drawpausedoverlay(self, surf: pygame.Surface):
        """Draw pause overlay"""
        overlay = pygame.Surface((self.current_width, self.current_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surf.blit(overlay, (0, 0))
        
        paused = self.font_huge.render("PAUSED", True, (255, 255, 100))
        surf.blit(paused, paused.get_rect(center=(self.current_width // 2, self.current_height // 2 - int(60 * self.current_height / BASE_HEIGHT))))
        
        instructions = self.font_big.render("Press [R] to Resume", True, (255, 255, 255))
        surf.blit(instructions, instructions.get_rect(center=(self.current_width // 2, self.current_height // 2 + int(60 * self.current_height / BASE_HEIGHT))))
    
    def drawgrid(self, surf: pygame.Surface):
        """Draw grid for catching phase"""
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        tile_size = int(TILE * scale)
        offsetx = (self.current_width - GRIDW * tile_size) // 2
        offsety = int(100 * scale)
        
        grid_surface = pygame.Surface((GRIDW * tile_size, GRIDH * tile_size), pygame.SRCALPHA)
        
        for y in range(GRIDH):
            for x in range(GRIDW):
                r = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
                if self.grid[y][x] == 0:
                    color = (50, 120, 80, 100)
                else:
                    color = (40, 80, 50, 150)
                pygame.draw.rect(grid_surface, color, r)
                pygame.draw.rect(grid_surface, (30, 60, 40, 150), r, 1)
        
        surf.blit(grid_surface, (offsetx, offsety))
    
    def addattackeffect(self, side: Agent, attacker: Pokemon):
        """Add attack animation effect"""
        self.activeattackeffects.append((side, attacker, time.time() + ATTACKEFFECTDURATION))
        target_pos = self.getpokemonscreenpos("rocket" if side.name == "Ash" else "ash")
        self.addparticleeffect(target_pos, TYPECOLOR.get(attacker.ptype, (255, 255, 255)), 40)
    
    def adddamagepopup(self, damage: int, targetside: str):
        """Add damage number popup"""
        pos = self.getpokemonscreenpos(targetside)
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        self.damagepopups.append(DamagePopup(str(damage), (pos[0], pos[1] - int(60 * scale)), time.time()))
    
    def triggerscreenshake(self, intensity: int):
        """Trigger screen shake effect"""
        self.screenshake = intensity
    
    def getpokemonscreenpos(self, side: str) -> Tuple[float, float]:
        """Get screen position of active Pokemon"""
        cx, cy = self.current_width // 2, self.current_height // 2
        scale = min(self.current_width / BASE_WIDTH, self.current_height / BASE_HEIGHT)
        offset = int(300 * scale)
        return (cx + offset, cy) if side == "rocket" else (cx - offset, cy)
    
    def addparticleeffect(self, pos: Tuple[float, float], color: Tuple[int, int, int], count: int):
        """Add particle burst effect"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 250)
            vel = [math.cos(angle) * speed, math.sin(angle) * speed]
            lifespan = random.uniform(0.5, 1.2)
            self.particles.append(Particle(list(pos), vel, lifespan, lifespan, color))
    
    def handle_input(self, event: pygame.event.Event):
        """Handle keyboard input"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                if self.state != GStateEnum.PAUSED:
                    self.paused_from_state = self.state
                    self.state = GStateEnum.PAUSED
            elif event.key == pygame.K_r:
                if self.state == GStateEnum.PAUSED:
                    self.state = self.paused_from_state
            elif event.key == pygame.K_e:
                self.running = False
            elif event.key == pygame.K_a:
                if self.state == GStateEnum.GAMEOVER:
                    # Reset everything
                    self.voice_played = {"intro": False, "phase1": False, "phase2": False, "phase3": False, "result": False}
                    self.voice_start_time = {}
                    self.voice_finished = {"intro": False, "phase1": False, "phase2": False, "phase3": False, "result": False}
                    self.waiting_for_audio = False
                    self.initgame()
                    self.state = GStateEnum.INTRO
                    self.intro_start_time = time.time()
                    self.log.clear()

# ==================== MAIN ENTRY POINT ====================
def main():
    """Main game loop"""
    pygame.init()
    screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Pokemon Battle Arena 4.0 - Audio-Synced & Enhanced UI")
    
    game = Game(screen)
    
    print("=" * 70)
    print("POKEMON BATTLE ARENA 4.0 - AUDIO-SYNCED & ENHANCED UI")
    print("=" * 70)
    print("Features:")
    print("  - Audio-Synced Phase Timing (events start after voice finishes)")
    print("  - Stunning Attack Icons (200x200px)")
    print("  - Improved Layout (no text/icon overlap)")
    print("  - A* Pathfinding + Minimax + Alpha-Beta + Fuzzy Logic")
    print("  - MP3 Voice Narration for Each Phase")
    print("  - Fully Scalable UI (maximizable window)")
    print("  - Perfect Balance: Both AI agents equal strength")
    print("=" * 70)
    print("Controls:")
    print("  [P] Pause    [R] Resume")
    print("  [E] Exit     [A] Play Again")
    print("=" * 70)
    print(f"Window Size: {BASE_WIDTH}x{BASE_HEIGHT} (Resizable)")
    print("=" * 70)
    
    while game.running:
        dt = game.clock.tick(FPS) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game.running = False
                else:
                    game.handle_input(event)
            elif event.type == pygame.VIDEORESIZE:
                # Handle window resize
                game.handle_resize(event.w, event.h)
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                game.screen = screen
        
        if game.state != GStateEnum.PAUSED:
            game.update(dt)
        game.draw()
    
    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()


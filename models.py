"""
Data models for Pokemon Battle Arena
"""
import math
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Union
from enum import Enum, auto
from config import IDLEANIMSPEED, IDLEANIMBOB, HPBARANIMSPEED


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
    coins: int = 0
    fuel: int = 0
    elixirs: Dict[str, int] = field(default_factory=dict)
    position: Tuple[float, float] = (0, 0)
    targetpos: Tuple[float, float] = (0, 0)
    current_path: List[Tuple[int, int]] = field(default_factory=list)
    path_index: int = 0


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


class GStateEnum(Enum):
    INTRO = auto()
    CATCH = auto()
    ELIXIR = auto()
    BATTLE = auto()
    PAUSED = auto()
    GAMEOVER = auto()


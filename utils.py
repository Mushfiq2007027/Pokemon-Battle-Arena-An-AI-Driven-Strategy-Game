"""
Utility functions for Pokemon Battle Arena
Includes: A* Pathfinding, Fuzzy Logic, Sound Generation
"""
import random
import numpy as np
import pygame
from typing import List, Tuple, Dict
from config import GRIDW, GRIDH, DIRS, TYPEADV


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


# ==================== A* PATHFINDING ====================
Grid = List[List[int]]

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


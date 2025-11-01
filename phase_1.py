"""
Phase 1: Catching Pokemon Module
"""
import math
import time
import random
import pygame
from typing import Dict, Tuple
from utils import astar
from config import (PHASE1_TIME, FUELPERCATCH, ASHTEAMSPECIES, ROCKETTEAMSPECIES,
                   GRIDW, GRIDH, MOVESPEEDPX, TILE, BASE_WIDTH, BASE_HEIGHT)


class Phase1:
    def __init__(self, game):
        self.game = game
        self.phase_start_time = 0
        self.pokemon_caught = {"Ash": [], "Team Rocket": []}
        self.current_target = {"Ash": 0, "Team Rocket": 0}
        self.pokemon_locations: Dict[str, Dict[str, Tuple[int, int]]] = {"Ash": {}, "Team Rocket": {}}
        
        # Initialize grid and spawn targets
        self.init_phase()
    
    def init_phase(self):
        """Initialize phase 1"""
        # Spawn pokemon at fixed locations
        self.spawncatchtargets()
        
        # Position trainers at starting locations
        self.game.ash.position = (1.0, GRIDH - 2.0)
        self.game.ash.targetpos = self.game.ash.position
        self.game.ash.current_path = []
        self.game.ash.path_index = 0
        
        self.game.rocket.position = (GRIDW - 2.0, 1.0)
        self.game.rocket.targetpos = self.game.rocket.position
        self.game.rocket.current_path = []
        self.game.rocket.path_index = 0
    
    def spawncatchtargets(self):
        """Spawn pokemon at FIXED locations"""
        rng = random.Random(int(time.time()))
        
        def randcell():
            attempts = 0
            while attempts < 100:
                x, y = rng.randrange(2, GRIDW - 2), rng.randrange(2, GRIDH - 2)
                if self.game.grid[y][x] == 0:
                    return (x, y)
                attempts += 1
            return (GRIDW // 2, GRIDH // 2)
        
        self.pokemon_locations = {
            "Ash": {name: randcell() for name, _ in ASHTEAMSPECIES},
            "Team Rocket": {name: randcell() for name, _ in ROCKETTEAMSPECIES}
        }
    
    def update(self, dt: float) -> bool:
        """Update catching phase, returns True if should transition to next phase"""
        # Wait for audio to finish before starting phase
        if self.game.waiting_for_audio and not self.game.is_voice_finished("phase1"):
            return False
        
        # Start timer after audio finishes
        if self.phase_start_time == 0:
            self.phase_start_time = time.time()
        
        elapsed = time.time() - self.phase_start_time
        remaining = max(0.0, PHASE1_TIME - elapsed)
        
        if remaining == 0 or (len(self.pokemon_caught["Ash"]) >= 3 and len(self.pokemon_caught["Team Rocket"]) >= 3):
            return True
        
        # Update trainer AI
        self.movetrainer(self.game.ash, "Ash", dt)
        self.movetrainer(self.game.rocket, "Team Rocket", dt)
        
        return False
    
    def movetrainer(self, agent, tag: str, dt: float):
        """Move trainer to catch pokemon using A*"""
        if len(self.pokemon_caught[tag]) >= 3:
            return
        
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
        
        if current_grid == goal:
            if agent.fuel >= FUELPERCATCH:
                agent.fuel -= FUELPERCATCH
                self.pokemon_caught[tag].append(pokemon_name)
                self.game.sfx['catch'].play()
                self.current_target[tag] += 1
                agent.current_path = []
                agent.path_index = 0
            return
        
        if not agent.current_path or agent.path_index >= len(agent.current_path) - 1:
            path = astar(self.game.grid, current_grid, goal)
            if path and len(path) > 1:
                agent.current_path = path
                agent.path_index = 0
        
        if agent.current_path and agent.path_index < len(agent.current_path) - 1:
            next_idx = agent.path_index + 1
            next_cell = agent.current_path[next_idx]
            agent.targetpos = (float(next_cell[0]), float(next_cell[1]))
            
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
    
    def draw(self, surf: pygame.Surface):
        """Draw catching phase with forest background (NO BATTLE LOG)"""
        bg = self.game.get_scaled_background("forest")
        if bg:
            surf.blit(bg, (0, 0))
        else:
            surf.fill((40, 90, 60))
        
        self.drawgrid(surf)
        
        # Draw pokemon locations
        for agent_name in ["Ash", "Team Rocket"]:
            for pokemon_name, gridpos in self.pokemon_locations[agent_name].items():
                if pokemon_name not in self.pokemon_caught[agent_name]:
                    pixelpos = self.game.gridtopixel((float(gridpos[0]), float(gridpos[1])))
                    sprite = self.game.get_scaled_sprite(pokemon_name, "token")
                    if sprite:
                        bob = math.sin(time.time() * 6) * 4
                        rect = sprite.get_rect(center=(int(pixelpos[0]), int(pixelpos[1] + bob)))
                        surf.blit(sprite, rect)
                        label = self.game.font_small.render(pokemon_name[:7], True, (255, 255, 0))
                        scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
                        labelrect = label.get_rect(center=(int(pixelpos[0]), int(pixelpos[1]) + int(40 * scale)))
                        surf.blit(label, labelrect)
        
        # Draw trainers
        for agent, agent_name in [(self.game.ash, "Ash"), (self.game.rocket, "Team Rocket")]:
            pixelpos = self.game.gridtopixel(agent.position)
            sprite = self.game.get_scaled_sprite(agent_name, "trainer")
            if sprite:
                rect = sprite.get_rect(center=(int(pixelpos[0]), int(pixelpos[1])))
                surf.blit(sprite, rect)
                label = self.game.font.render(agent_name, True, (255, 255, 255))
                label_bg = self.game.font.render(agent_name, True, (0, 0, 0))
                scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
                labelrect = label.get_rect(center=(int(pixelpos[0]), int(pixelpos[1]) - int(50 * scale)))
                surf.blit(label_bg, labelrect.move(2, 2))
                surf.blit(label, labelrect)
        
        self.drawhud(surf)
    
    def drawhud(self, surf: pygame.Surface):
        """Draw HUD with phase info and timer (NO BATTLE LOG)"""
        scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
        pygame.draw.rect(surf, (20, 20, 20, 220), (0, 0, self.game.current_width, int(90 * scale)))
        
        title = self.game.font_big.render("PHASE 1: CATCHING POKEMON", True, (255, 255, 100))
        surf.blit(title, (int(30 * scale), int(25 * scale)))
        
        elapsed = time.time() - self.phase_start_time
        remaining = max(0, PHASE1_TIME - elapsed)
        timer_color = (255, 100, 100) if remaining < 20 else (100, 255, 100)
        timer = self.game.font_big.render(f"Time: {remaining:.1f}s", True, timer_color)
        surf.blit(timer, (self.game.current_width - timer.get_width() - int(30 * scale), int(25 * scale)))
        
        # Draw controls
        self.drawcontrols(surf)
    
    def drawcontrols(self, surf: pygame.Surface):
        """Draw control instructions"""
        controls = "[P] Pause  [R] Resume  [E] Exit  [A] Play Again"
        text = self.game.font_small.render(controls, True, (200, 200, 200))
        surf.blit(text, (self.game.current_width // 2 - text.get_width() // 2, self.game.current_height - int(35 * self.game.current_height / BASE_HEIGHT)))
    
    def drawgrid(self, surf: pygame.Surface):
        """Draw grid for catching phase"""
        scale = min(self.game.current_width / BASE_WIDTH, self.game.current_height / BASE_HEIGHT)
        tile_size = int(TILE * scale)
        offsetx = (self.game.current_width - GRIDW * tile_size) // 2
        offsety = int(100 * scale)
        
        grid_surface = pygame.Surface((GRIDW * tile_size, GRIDH * tile_size), pygame.SRCALPHA)
        
        for y in range(GRIDH):
            for x in range(GRIDW):
                r = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
                if self.game.grid[y][x] == 0:
                    color = (50, 120, 80, 100)
                else:
                    color = (40, 80, 50, 150)
                pygame.draw.rect(grid_surface, color, r)
                pygame.draw.rect(grid_surface, (30, 60, 40, 150), r, 1)
        
        surf.blit(grid_surface, (offsetx, offsety))


"""
Pokemon Battle Arena 4.0 - Modular Structure
Main Entry Point
"""
import math
import random
import time
import sys
import pygame
import numpy as np
from typing import List, Tuple, Dict

# Import configuration
from config import (BASE_WIDTH, BASE_HEIGHT, FPS, FONTNAME, GRIDW, GRIDH, 
                   ASHTEAMSPECIES, ROCKETTEAMSPECIES, STARTFUEL, COINSPERAGENT,
                   IMAGEASSETS, BACKGROUNDS, VOICE_FILES, BASE_BATTLESPRITESIZE,
                   BASE_TOKENSPRITESIZE, BASE_TRAINERSPRITESIZE, BASE_ATTACKICONSIZE,
                   BASE_ELIXIRSIZE, TYPECOLOR)

# Import models
from models import Pokemon, Agent, BattleState, GStateEnum, DamagePopup, Particle

# Import utilities
from utils import maketone, makeblastsound

# Import phase modules
from game_intro import GameIntro
from phase_1 import Phase1
from phase_2 import Phase2
from phase_3 import Phase3
from game_result import GameResult


# ==================== MAIN GAME CLASS ====================
class Game:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GStateEnum.INTRO
        self.paused_from_state = None
        
        # Window size tracking
        self.current_width = BASE_WIDTH
        self.current_height = BASE_HEIGHT
        
        # Initialize fonts
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
        
        # Initialize game data
        self.initgame()
        
        # Initialize phase modules
        self.game_intro = None
        self.phase1 = None
        self.phase2 = None
        self.phase3 = None
        self.game_result = None
    
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
                sound.set_volume(1.0)
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
            duration = voice.get_length()
            elapsed = time.time() - self.voice_start_time[key]
            if elapsed >= duration:
                self.voice_finished[key] = True
                self.waiting_for_audio = False
                return True
        
        return False
    
    def initgame(self):
        """Initialize/Reset game state"""
        random.seed(time.time())
        self.fieldtype = random.choice(["Fire", "Electric", "Water"])
        
        # Create agents
        self.ash = Agent("Ash", [Pokemon(n, t) for n, t in ASHTEAMSPECIES], 
                        coins=COINSPERAGENT, fuel=STARTFUEL)
        self.rocket = Agent("Team Rocket", [Pokemon(n, t) for n, t in ROCKETTEAMSPECIES],
                           coins=COINSPERAGENT, fuel=STARTFUEL)
        
        # Grid for catching phase
        self.grid = [[0 for _ in range(GRIDW)] for _ in range(GRIDH)]
        self.genobstacles(0.08)
        
        # Battle state
        self.bs = BattleState(self.fieldtype)
        
        # Visual effects
        self.activeattackeffects: List[Tuple[Agent, Pokemon, float]] = []
        self.damagepopups: List[DamagePopup] = []
        self.particles: List[Particle] = []
        self.screenshake = 0
        
        # Winner
        self.winner = None
    
    def loadsprites(self) -> Dict[str, pygame.Surface]:
        """Load all image assets"""
        sprites = {}
        
        for name, filename in IMAGEASSETS.items():
            try:
                img = pygame.image.load(filename).convert_alpha()
                sprites[f"{name}_original"] = img
            except pygame.error as e:
                print(f"Warning: Could not load {filename}: {e}")
        
        # Load elixir image
        try:
            elixir_img = pygame.image.load("images/elixir.png").convert_alpha()
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
    
    def gridtopixel(self, gridpos: Tuple[float, float]) -> Tuple[float, float]:
        """Convert grid coordinates to pixel coordinates"""
        from config import TILE
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
            if self.game_intro is None:
                self.game_intro = GameIntro(self)
            if self.game_intro.update(dt):
                self.gotocatchphase()
        
        elif self.state == GStateEnum.CATCH:
            if self.phase1.update(dt):
                self.goelixirphase()
        
        elif self.state == GStateEnum.ELIXIR:
            if self.phase2.update(dt):
                self.gobattlephase()
        
        elif self.state == GStateEnum.BATTLE:
            should_transition, winner = self.phase3.update(dt)
            if should_transition:
                self.winner = winner
                self.gogameover()
        
        elif self.state == GStateEnum.GAMEOVER:
            self.game_result.update(dt)
    
    def gotocatchphase(self):
        """Transition to catching phase"""
        self.state = GStateEnum.CATCH
        self.sfx['transition'].play()
        self.play_voice("phase1")
        self.phase1 = Phase1(self)
    
    def goelixirphase(self):
        """Transition to elixir buying phase"""
        self.state = GStateEnum.ELIXIR
        self.play_voice("phase2")
        self.phase2 = Phase2(self)
    
    def gobattlephase(self):
        """Transition to battle phase"""
        self.state = GStateEnum.BATTLE
        self.play_voice("phase3")
        self.phase3 = Phase3(self)
    
    def gogameover(self):
        """Transition to game over screen"""
        self.state = GStateEnum.GAMEOVER
        self.game_result = GameResult(self, self.winner)
    
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
            if self.game_intro:
                self.game_intro.draw(tempsurface)
        
        elif self.state == GStateEnum.CATCH:
            if self.phase1:
                self.phase1.draw(tempsurface)
        
        elif self.state == GStateEnum.ELIXIR:
            if self.phase2:
                self.phase2.draw(tempsurface)
        
        elif self.state == GStateEnum.BATTLE:
            if self.phase3:
                self.phase3.draw(tempsurface)
        
        elif self.state == GStateEnum.GAMEOVER:
            if self.game_result:
                self.game_result.draw(tempsurface)
        
        elif self.state == GStateEnum.PAUSED:
            # Draw previous state, then overlay
            if self.paused_from_state == GStateEnum.CATCH:
                if self.phase1:
                    self.phase1.draw(tempsurface)
            elif self.paused_from_state == GStateEnum.ELIXIR:
                if self.phase2:
                    self.phase2.draw(tempsurface)
            elif self.paused_from_state == GStateEnum.BATTLE:
                if self.phase3:
                    self.phase3.draw(tempsurface)
            self.drawpausedoverlay(tempsurface)
        
        self.screen.blit(tempsurface, renderoffset)
        pygame.display.flip()
    
    def drawpausedoverlay(self, surf: pygame.Surface):
        """Draw pause overlay"""
        overlay = pygame.Surface((self.current_width, self.current_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surf.blit(overlay, (0, 0))
        
        paused = self.font_huge.render("PAUSED", True, (255, 255, 100))
        surf.blit(paused, paused.get_rect(center=(self.current_width // 2, self.current_height // 2 - int(60 * self.current_height / BASE_HEIGHT))))
        
        instructions = self.font_big.render("Press [R] to Resume", True, (255, 255, 255))
        surf.blit(instructions, instructions.get_rect(center=(self.current_width // 2, self.current_height // 2 + int(60 * self.current_height / BASE_HEIGHT))))
    
    def addattackeffect(self, side: Agent, attacker: Pokemon):
        """Add attack animation effect"""
        from config import ATTACKEFFECTDURATION
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
                    self.game_intro = GameIntro(self)


# ==================== MAIN ENTRY POINT ====================
def main():
    """Main game loop"""
    pygame.init()
    screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Pokemon Battle Arena 4.0 - Modular Structure")
    
    game = Game(screen)
    
    print("=" * 70)
    print("POKEMON BATTLE ARENA 4.0 - MODULAR STRUCTURE")
    print("=" * 70)
    print("Features:")
    print("  - Modular code structure (multiple files and folders)")
    print("  - Audio-Synced Phase Timing")
    print("  - Stunning Attack Icons")
    print("  - A* Pathfinding + Minimax + Alpha-Beta + Fuzzy Logic")
    print("  - MP3 Voice Narration")
    print("  - Fully Scalable UI")
    print("  - NO BATTLE LOG (Clean UI)")
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


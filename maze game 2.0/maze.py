import pygame
import random
import math
import time
import json
import os
from pygame import mixer
from enum import Enum

# =========================
# Init
# =========================
pygame.init()
try:
    mixer.init()
except Exception:
    pass

# =========================
# Constants
# =========================
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
CELL_SIZE = 40          # Grid granularity (kept constant; maze "size" is world scale)
SAVE_FILE = "savegame.json"
MAX_LEVELS = 1000

# =========================
# Themes (Dark/Light)
# =========================
class Theme:
    def __init__(self, dark=True):
        if dark:
            # Pro Slate (Dark)
            self.BG_TOP = (14, 16, 24)
            self.BG_BOTTOM = (22, 26, 38)
            self.GLASS = (28, 32, 44, 200)
            self.BORDER = (175, 185, 205)
            self.BORDER_SOFT = (110, 120, 140)
            self.WHITE = (245, 248, 252)
            self.OFFWHITE = (218, 224, 236)
            self.MUTED = (150, 158, 175)
            self.ACCENT_1 = (160, 200, 255)   # blue
            self.ACCENT_2 = (255, 185, 95)    # amber
            self.ACCENT_3 = (120, 230, 170)   # mint
            self.ACCENT_4 = (255, 120, 150)   # rose
            self.RED = (240, 90, 90)
            # World
            self.WALL = (220, 228, 240)
            self.ENEMY = (240, 120, 130)
            self.ENEMY_SPECTRAL = (230, 140, 255)
            self.PORTAL = (140, 210, 255)
            self.END_ZONE = (130, 220, 170)
        else:
            # Pro Slate (Light)
            self.BG_TOP = (232, 236, 246)
            self.BG_BOTTOM = (214, 224, 240)
            self.GLASS = (255, 255, 255, 210)
            self.BORDER = (120, 130, 150)
            self.BORDER_SOFT = (150, 160, 180)
            self.WHITE = (20, 24, 32)
            self.OFFWHITE = (50, 60, 76)
            self.MUTED = (90, 100, 120)
            self.ACCENT_1 = (40, 120, 255)
            self.ACCENT_2 = (240, 150, 40)
            self.ACCENT_3 = (30, 180, 120)
            self.ACCENT_4 = (220, 60, 100)
            self.RED = (200, 40, 40)
            # World
            self.WALL = (70, 90, 120)
            self.ENEMY = (200, 60, 90)
            self.ENEMY_SPECTRAL = (160, 70, 220)
            self.PORTAL = (40, 160, 220)
            self.END_ZONE = (30, 160, 110)

THEME = Theme(dark=True)  # default; can toggle in settings

# =========================
# Game States
# =========================
class GameState(Enum):
    MENU = 1
    PLAYING = 2
    PAUSED = 3
    GAME_OVER = 4
    LEVEL_COMPLETE = 5
    SETTINGS = 6
    LEVEL_SELECT = 7

# =========================
# Realities
# =========================
class Reality(Enum):
    NORMAL = 1
    SPECTRAL = 2
    TIME_SHIFT = 3
    GRAVITY_SHIFT = 4
    QUANTUM = 5

# =========================
# UI Helpers
# =========================
def draw_vertical_gradient(surface, top_color, bottom_color):
    height = surface.get_height()
    width = surface.get_width()
    for y in range(height):
        t = y / (height - 1)
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

def draw_glass(surface, rect, radius=10, border=1):
    # shadow
    shadow = pygame.Surface((rect.w + 10, rect.h + 10), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 50), shadow.get_rect(), border_radius=radius+8)
    surface.blit(shadow, (rect.x - 5, rect.y - 5))
    # glass
    glass = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    glass.fill(THEME.GLASS)
    surface.blit(glass, (rect.x, rect.y))
    pygame.draw.rect(surface, THEME.BORDER, rect, border, border_radius=radius)

class Button:
    def __init__(self, x, y, w, h, text, base_col, hover_col=None, text_col=None, font_size=22, radius=10):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.base_col = base_col
        self.hover_col = hover_col or base_col
        self.text_col = text_col or THEME.WHITE
        self.font = pygame.font.Font(None, font_size)
        self.radius = radius
        self.hover = False

    def update(self, mouse_pos):
        self.hover = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        col = self.hover_col if self.hover else self.base_col
        draw_glass(screen, self.rect, self.radius, 1)
        pygame.draw.rect(screen, col, self.rect, 2, border_radius=self.radius)
        txt = self.font.render(self.text, True, self.text_col)
        screen.blit(txt, txt.get_rect(center=self.rect.center))

    def clicked(self, mouse_pos, click):
        return click and self.rect.collidepoint(mouse_pos)

class IconButton(Button):
    def __init__(self, x, y, size, label="✕", color=None):
        super().__init__(x, y, size, size, label, color or THEME.ACCENT_4, THEME.ACCENT_1, THEME.WHITE, 20, 8)

class Toggle:
    def __init__(self, x, y, w, h, value=False, label=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.value = value
        self.label = label
        self.font = pygame.font.Font(None, 24)

    def draw(self, screen, mouse_pos, click):
        draw_glass(screen, self.rect, 12, 1)
        knob_r = self.rect.h // 2 - 3
        on = self.value
        bar_col = THEME.ACCENT_3 if on else THEME.BORDER_SOFT
        pygame.draw.rect(screen, bar_col, self.rect, 0, border_radius=knob_r+3)
        kx = self.rect.x + (self.rect.w - (knob_r*2) - 6 if on else 6)
        ky = self.rect.y + 3
        pygame.draw.rect(screen, THEME.WHITE, pygame.Rect(kx, ky, knob_r*2, knob_r*2), 0, border_radius=knob_r)
        label_s = self.font.render(self.label, True, THEME.OFFWHITE)
        screen.blit(label_s, (self.rect.right + 10, self.rect.y + self.rect.h//2 - label_s.get_height()//2))
        if click and self.rect.collidepoint(mouse_pos):
            self.value = not self.value

class Dropdown:
    def __init__(self, x, y, w, items, on_select, title="AUTO ▼", open=False):
        self.x, self.y, self.w = x, y, w
        self.items = items  # list of (label, key)
        self.on_select = on_select
        self.open = open
        self.item_h = 34
        self.header_h = 34
        self.font = pygame.font.Font(None, 22)
        self.header_btn = Button(x, y, w, self.header_h, title, THEME.ACCENT_1, THEME.ACCENT_2, THEME.WHITE, 20, 8)
        self.close_btn = IconButton(x + w - 26, y + 4, 22, "✕", THEME.ACCENT_4)

    def draw(self, screen, mouse_pos, click):
        self.header_btn.update(mouse_pos)
        self.header_btn.draw(screen)
        if self.header_btn.clicked(mouse_pos, click):
            self.open = not self.open

        if self.open:
            body_rect = pygame.Rect(self.x, self.y + self.header_h, self.w, self.item_h * len(self.items))
            draw_glass(screen, body_rect, 8, 1)
            self.close_btn.update(mouse_pos)
            self.close_btn.draw(screen)
            if self.close_btn.clicked(mouse_pos, click):
                self.open = False
            for i, (label, key) in enumerate(self.items):
                r = pygame.Rect(self.x + 6, self.y + self.header_h + i*self.item_h + 4, self.w - 12, self.item_h - 8)
                hover = r.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (46, 50, 64, 140) if isinstance(THEME.GLASS, tuple) else (46, 50, 64), r, 0, border_radius=6)
                if hover:
                    pygame.draw.rect(screen, THEME.ACCENT_1, r, 2, border_radius=6)
                txt = self.font.render(label, True, THEME.WHITE)
                screen.blit(txt, txt.get_rect(midleft=(r.x + 10, r.centery)))
                if click and hover:
                    self.on_select(key)
                    self.open = False

# Bottom action bar (ONLY bar)
class BottomBar:
    def __init__(self, width, height):
        self.h = 56
        self.rect = pygame.Rect(0, height - self.h, width, self.h)
        pad = 10
        btn_h = 34
        y = self.rect.y + (self.h - btn_h)//2
        x = 10
        self.buttons = {}
        self.buttons["auto"] = Button(x, y, 140, btn_h, "AUTO ▼", THEME.ACCENT_1, THEME.ACCENT_2); x += 140 + pad
        self.buttons["reverse"] = Button(x, y, 120, btn_h, "REVERSE", THEME.ACCENT_2, THEME.ACCENT_1); x += 120 + pad
        self.buttons["pause"] = Button(x, y, 140, btn_h, "PAUSE/RESUME", THEME.ACCENT_3, THEME.ACCENT_1); x += 160 + pad
        self.buttons["savequit"] = Button(x, y, 160, btn_h, "SAVE & QUIT", THEME.ACCENT_4, THEME.ACCENT_2)

    def draw(self, screen, mouse_pos, click):
        draw_glass(screen, self.rect, 0, 0)
        actions = []
        for name, btn in self.buttons.items():
            btn.update(mouse_pos)
            btn.draw(screen)
            if btn.clicked(mouse_pos, click):
                actions.append(name)
        return actions

# =========================
# Background
# =========================
class AnimatedBackground:
    def __init__(self):
        self.particles = []
        self.generate_particles(50)

    def generate_particles(self, count):
        for _ in range(count):
            self.particles.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'size': random.randint(1, 3),
                'speed': random.uniform(0.4, 1.0),
                'color': random.choice([(120, 160, 220), (160, 190, 240), (140, 175, 230)]),
                'direction': random.uniform(0, 2 * math.pi)
            })

    def update(self):
        for p in self.particles:
            p['x'] += math.cos(p['direction']) * p['speed']
            p['y'] += math.sin(p['direction']) * p['speed']
            if p['x'] < 0: p['x'] = SCREEN_WIDTH
            if p['x'] > SCREEN_WIDTH: p['x'] = 0
            if p['y'] < 0: p['y'] = SCREEN_HEIGHT
            if p['y'] > SCREEN_HEIGHT: p['y'] = 0

    def draw(self, screen):
        for p in self.particles:
            pygame.draw.circle(screen, p['color'], (int(p['x']), int(p['y'])), p['size'])

# =========================
# Sound
# =========================
class SoundManager:
    def __init__(self, volume=0.7):
        self.volume = volume
        try:
            pygame.mixer.music.set_volume(self.volume)
        except Exception:
            pass

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        try:
            pygame.mixer.music.set_volume(self.volume)
        except Exception:
            pass

# =========================
# Particles
# =========================
class ParticleSystem:
    def __init__(self):
        self.particles = []

    def add(self, x, y, color, count=10, speed=1.8, life=36):
        for _ in range(count):
            ang = random.uniform(0, 2*math.pi)
            spd = random.uniform(0.5, 1.2) * speed
            self.particles.append({
                'x': x, 'y': y,
                'vx': math.cos(ang)*spd, 'vy': math.sin(ang)*spd,
                'life': life, 'color': color, 'size': random.randint(2, 4)
            })

    def update(self):
        for p in self.particles[:]:
            p['x'] += p['vx']; p['y'] += p['vy']
            p['life'] -= 1
            p['vy'] += 0.07
            if p['life'] <= 0:
                self.particles.remove(p)

    def draw(self, screen, camx, camy):
        for p in self.particles:
            pygame.draw.circle(screen, p['color'], (int(p['x']-camx), int(p['y']-camy)), p['size'])

# =========================
# Portals
# =========================
class Portal:
    def __init__(self, x1, y1, x2, y2):
        self.entrance = (x1, y1)
        self.exit = (x2, y2)
        self.t = 0
    def update(self): self.t = (self.t + 1) % 360
    def draw(self, screen, camx, camy):
        r = 14 + 3*math.sin(self.t * math.pi / 90)
        pygame.draw.circle(screen, THEME.PORTAL, (int(self.entrance[0]-camx), int(self.entrance[1]-camy)), int(r), 2)
        pygame.draw.circle(screen, THEME.PORTAL, (int(self.exit[0]-camx), int(self.exit[1]-camy)), int(r), 2)

# =========================
# Time Manipulator (kept for future)
# =========================
class TimeManipulator:
    def __init__(self):
        self.active = False
        self.time_scale = 1.0
        self.cooldown = 0
        self.max_cooldown = 300
    def activate(self):
        if self.cooldown <= 0:
            self.active = not self.active
            self.time_scale = 0.3 if self.active else 1.0
            self.cooldown = self.max_cooldown if self.active else 0
            return True
        return False
    def update(self):
        if self.cooldown > 0:
            self.cooldown -= 1
            if self.cooldown <= 0 and self.active:
                self.active = False
                self.time_scale = 1.0

# =========================
# Player
# =========================
class Player:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.w = 28
        self.h = 28
        self.speed = 5
        self.reality = Reality.NORMAL
        self.health = 100
        self.max_health = 100
        self.invuln = 0
        self.trail = []
        self.trail_max = 14
        self.gravity_dir = 1

    def move(self, dx, dy, walls, reality, dt_scale=1.0):
        if self.invuln > 0:
            self.invuln -= 1
        spd = self.speed * dt_scale
        if reality == Reality.TIME_SHIFT:
            spd *= 0.7
        if reality == Reality.GRAVITY_SHIFT and self.gravity_dir == -1:
            dy = -dy

        nx, ny = self.x + dx * spd, self.y + dy * spd
        fut = pygame.Rect(nx, ny, self.w, self.h)
        if not any(fut.colliderect(w) for w in walls):
            self.trail.append((self.x, self.y))
            if len(self.trail) > self.trail_max:
                self.trail.pop(0)
            self.x, self.y = nx, ny
            return True
        return False

    def damage(self, n):
        if self.invuln <= 0:
            self.health -= n
            self.invuln = 24
            return True
        return False

    def draw(self, screen, camx, camy):
        for (tx, ty) in self.trail:
            pygame.draw.circle(screen, THEME.ACCENT_1, (int(tx - camx), int(ty - camy)), 3)
        rect = pygame.Rect(int(self.x - camx), int(self.y - camy), self.w, self.h)
        pygame.draw.rect(screen, THEME.ACCENT_3, rect, border_radius=6)


# =========================
# Enemy
# =========================
class Enemy:
    def __init__(self, x, y, enemy_type="normal"):
        self.x = float(x); self.y = float(y)
        self.w = 30; self.h = 30
        self.type = enemy_type
        self.speed = 2
        self.range = 200
        self.angle = 0
        self.tele_cd = 0
        if enemy_type == "spectral":
            self.speed = 3; self.range = 300
        if enemy_type == "time_warper":
            self.speed = 1.5; self.tele_cd = 0

    def update(self, px, py, walls, reality, dt_scale=1.0):
        self.angle += 0.05
        spd = self.speed * dt_scale * (0.7 if reality == Reality.TIME_SHIFT else 1.0)
        dx, dy = px - self.x, py - self.y
        d = math.hypot(dx, dy)
        if d < self.range and d > 0:
            dx, dy = dx/d, dy/d
            nx, ny = self.x + dx*spd, self.y + dy*spd
            fut = pygame.Rect(nx, ny, self.w, self.h)
            if not any(fut.colliderect(w) for w in walls):
                self.x, self.y = nx, ny
        if self.type == "time_warper" and self.tele_cd <= 0 and d < 150:
            ang = random.uniform(0, 2*math.pi)
            self.x, self.y = px + math.cos(ang)*90, py + math.sin(ang)*90
            self.tele_cd = 160
        if self.tele_cd > 0: self.tele_cd -= 1

    def draw(self, screen, camx, camy):
        pos = (int(self.x - camx), int(self.y - camy))
        if self.type == "spectral":
            pygame.draw.circle(screen, THEME.ENEMY_SPECTRAL, pos, self.w//2)
        elif self.type == "time_warper":
            size = self.w//2 + 3*math.sin(self.angle*2)
            pygame.draw.circle(screen, THEME.ACCENT_2, pos, int(size))
        else:
            pygame.draw.rect(screen, THEME.ENEMY, (pos[0]-self.w//2, pos[1]-self.h//2, self.w, self.h), border_radius=6)

# =========================
# Level (world size + density configurable)
# =========================
class Level:
    def __init__(self, num, reality, world_scale=2.0, wall_density=0.20):
        self.num = num
        self.reality = reality
        self.scale = world_scale
        self.world_w = int(SCREEN_WIDTH * self.scale)
        self.world_h = int(SCREEN_HEIGHT * self.scale)
        self.density = wall_density
        self.walls = []
        self.portals = []
        self.enemies = []
        self.collectibles = []
        self.start = (50, 50)
        self.end = (self.world_w - 120, self.world_h - 120)
        self.time_limit = 120
        self.flags = []      # progress flags along shortest path
        self.generate()

    def generate(self):
        self.walls.clear(); self.portals.clear(); self.enemies.clear(); self.collectibles.clear(); self.flags.clear()
        # borders
        for x in range(0, self.world_w, CELL_SIZE):
            self.walls.append(pygame.Rect(x, 0, CELL_SIZE, CELL_SIZE))
            self.walls.append(pygame.Rect(x, self.world_h - CELL_SIZE, CELL_SIZE, CELL_SIZE))
        for y in range(0, self.world_h, CELL_SIZE):
            self.walls.append(pygame.Rect(0, y, CELL_SIZE, CELL_SIZE))
            self.walls.append(pygame.Rect(self.world_w - CELL_SIZE, y, CELL_SIZE, CELL_SIZE))
        # random blocks by density
        for x in range(CELL_SIZE*2, self.world_w - CELL_SIZE*2, CELL_SIZE):
            for y in range(CELL_SIZE*2, self.world_h - CELL_SIZE*2, CELL_SIZE):
                if random.random() < self.density:
                    self.walls.append(pygame.Rect(x, y, CELL_SIZE, CELL_SIZE))

        # enemies & portals per reality
        if self.reality == Reality.SPECTRAL:
            for _ in range(6):
                self.enemies.append(Enemy(random.randint(120, self.world_w-120),
                                          random.randint(120, self.world_h-120),
                                          "spectral"))
        elif self.reality == Reality.TIME_SHIFT:
            for _ in range(5):
                self.enemies.append(Enemy(random.randint(120, self.world_w-120),
                                          random.randint(120, self.world_h-120),
                                          "time_warper"))
        elif self.reality == Reality.GRAVITY_SHIFT:
            for _ in range(6):
                self.enemies.append(Enemy(random.randint(120, self.world_w-120),
                                          random.randint(120, self.world_h-120),
                                          "normal"))
            for _ in range(2):
                self.portals.append(Portal(random.randint(200, self.world_w-200),
                                           random.randint(200, self.world_h-200),
                                           random.randint(200, self.world_w-200),
                                           random.randint(200, self.world_h-200)))
        elif self.reality == Reality.QUANTUM:
            for _ in range(8):
                t = random.choice(["normal","spectral","time_warper"])
                self.enemies.append(Enemy(random.randint(120, self.world_w-120),
                                          random.randint(120, self.world_h-120), t))
            for _ in range(3):
                self.portals.append(Portal(random.randint(200, self.world_w-200),
                                           random.randint(200, self.world_h-200),
                                           random.randint(200, self.world_w-200),
                                           random.randint(200, self.world_h-200)))
        else:  # NORMAL
            for _ in range(4):
                self.enemies.append(Enemy(random.randint(120, self.world_w-120),
                                          random.randint(120, self.world_h-120),
                                          "normal"))

        # collectibles
        for _ in range(8):
            self.collectibles.append({"type":"key","x":random.randint(60, self.world_w-60),
                                      "y":random.randint(60, self.world_h-60), "collected":False})

        # compute progress flags along shortest path (start->end)
        try:
            pf = PathFinder(self)
            sp = pf.shortest(self.start, self.end)
            if len(sp) > 8:
                n = len(sp)
                idxs = sorted(set([int(n*0.25), int(n/3)]))
                labels = ["1/4", "1/3"]
                for i, idx in enumerate(idxs[:2]):
                    pos = sp[min(max(1, idx), n-2)]
                    self.flags.append({"pos": pos, "label": labels[i] if i < len(labels) else f"{int(idx/n*100)}%", "hit": False})
        except Exception:
            pass

# =========================
# Slider
# =========================
class Slider:
    def __init__(self, x, y, w, min_val, max_val, initial, label=""):
        self.rect = pygame.Rect(x, y, w, 8)
        self.min, self.max = min_val, max_val
        self.value = initial
        self.knob_r = 10
        self.label = label
        self.font = pygame.font.Font(None, 22)
        self.drag = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.inflate(0, 18).collidepoint(event.pos):
            self.drag = True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.drag = False
        elif event.type == pygame.MOUSEMOTION and self.drag:
            relx = max(self.rect.x, min(self.rect.right, event.pos[0]))
            t = (relx - self.rect.x) / self.rect.w
            self.value = self.min + t * (self.max - self.min)

    def draw(self, screen):
        draw_glass(screen, self.rect.inflate(0, 8), 6, 1)
        t = (self.value - self.min) / (self.max - self.min)
        kx = int(self.rect.x + t*self.rect.w)
        pygame.draw.circle(screen, THEME.ACCENT_1, (kx, self.rect.centery), self.knob_r)
        txt = self.font.render(f"{self.label}: {self.display_value()}", True, THEME.WHITE)
        screen.blit(txt, (self.rect.x, self.rect.y - 24))

    def display_value(self):
        return f"{int(self.value*100)}%" if self.max <= 1.0 else f"{self.value:.2f}x"

# =========================
# Pathfinding
# =========================
class PathFinder:
    def __init__(self, level: Level):
        self.level = level
        self.cols = int(level.world_w // CELL_SIZE)
        self.rows = int(level.world_h // CELL_SIZE)
        self.blocked = set()
        for w in self.level.walls:
            x0 = max(0, w.left // CELL_SIZE); y0 = max(0, w.top // CELL_SIZE)
            x1 = min(self.cols - 1, (w.right - 1) // CELL_SIZE)
            y1 = min(self.rows - 1, (w.bottom - 1) // CELL_SIZE)
            for cx in range(x0, x1+1):
                for cy in range(y0, y1+1):
                    self.blocked.add((cx, cy))

    def _pt_to_cell(self, x, y):
        return (max(0, min(self.cols-1, int(x//CELL_SIZE))),
                max(0, min(self.rows-1, int(y//CELL_SIZE))))

    def _cell_to_pt(self, c):
        return (c[0]*CELL_SIZE + CELL_SIZE//2, c[1]*CELL_SIZE + CELL_SIZE//2)

    def _neighbors(self, c):
        cx, cy = c
        for nx, ny in ((cx+1, cy),(cx-1, cy),(cx, cy+1),(cx, cy-1)):
            if 0 <= nx < self.cols and 0 <= ny < self.rows and (nx, ny) not in self.blocked:
                yield (nx, ny)

    def shortest(self, start_px, goal_px):
        import heapq
        s = self._pt_to_cell(*start_px); g = self._pt_to_cell(*goal_px)
        if s in self.blocked or g in self.blocked: return []
        def h(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
        pq = []; heapq.heappush(pq, (h(s,g), 0, s, None))
        came = {}; gscore = {s:0}
        while pq:
            _, d, cur, par = heapq.heappop(pq)
            if cur not in came: came[cur] = par
            if cur == g: break
            for n in self._neighbors(cur):
                nd = d + 1
                if nd < gscore.get(n, 1e9):
                    gscore[n] = nd
                    heapq.heappush(pq, (nd + h(n,g), nd, n, cur))
        if g not in came: return []
        path = []
        c = g
        while c is not None:
            path.append(c); c = came[c]
        path.reverse()
        return [self._cell_to_pt(p) for p in path]

    def longest_approx(self, start_px):
        from collections import deque
        def bfs(start):
            q = deque([start]); dist={start:0}; par={start:None}
            while q:
                c = q.popleft()
                for n in self._neighbors(c):
                    if n not in dist:
                        dist[n] = dist[c]+1; par[n]=c; q.append(n)
            far = max(dist, key=lambda k: dist[k])
            return far, dist, par

        s = self._pt_to_cell(*start_px)
        if s in self.blocked:
            for cy in range(self.rows):
                for cx in range(self.cols):
                    if (cx,cy) not in self.blocked:
                        s=(cx,cy); break
                else: continue
                break
        A,_,_ = bfs(s)
        B,_,par = bfs(A)
        path=[]; c=B
        while c is not None:
            path.append(c); c=par[c]
        path.reverse()
        return [self._cell_to_pt(p) for p in path]

# =========================
# Move Recorder (for true reverse/undo)
# =========================
class MoveRecorder:
    """
    Records the player trajectory and can generate a smooth backtrack path.
    It samples positions to avoid massive arrays and to keep movement smooth.
    """
    def __init__(self, sample_dist=8.0, max_points=20000):
        self.sample_dist = sample_dist
        self.max_points = max_points
        self.points = []   # [(x,y), ...]
        self._last = None

    def clear(self):
        self.points.clear()
        self._last = None

    def add(self, pos):
        """Add a position only if we've moved at least sample_dist from last sample."""
        x, y = pos
        if not self.points:
            self.points.append((float(x), float(y)))
            self._last = (float(x), float(y))
            return
        lx, ly = self._last
        if (x - lx) * (x - lx) + (y - ly) * (y - ly) >= self.sample_dist * self.sample_dist:
            self.points.append((float(x), float(y)))
            self._last = (float(x), float(y))
            if len(self.points) > self.max_points:
                self.points = self.points[-self.max_points:]

    def backtrack_from(self, current_pos, include_current=True):
        """
        Return a reversed path (list of waypoints) following recorded moves backward
        from the nearest point to current_pos to the beginning.
        """
        if not self.points:
            return []
        cx, cy = current_pos
        best_i, best_d2 = 0, float('inf')
        for i, (px, py) in enumerate(self.points):
            d2 = (px - cx) * (px - cx) + (py - cy) * (py - cy)
            if d2 < best_d2:
                best_d2 = d2
                best_i = i
        back = self.points[:best_i + 1]
        if include_current and back:
            back[-1] = (float(cx), float(cy))
        back.reverse()
        return back

# =========================
# Game
# =========================
class QuantumMazeGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("QUANTUM MAZE • Pro Slate")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MENU
        self.current_index = 0
        self.levels = []           # [{num, reality, obj=None}, ...]
        self.player = None
        self.sound = SoundManager()
        self.particles = ParticleSystem()
        self.timefx = TimeManipulator()
        self.bg = AnimatedBackground()
        self.camx = 0; self.camy = 0

        # Fonts
        self.title_font = pygame.font.Font(None, 60)
        self.h1 = pygame.font.Font(None, 36)
        self.h2 = pygame.font.Font(None, 28)
        self.small = pygame.font.Font(None, 20)

        # Bottom Bar only
        self.bottombar = BottomBar(SCREEN_WIDTH, SCREEN_HEIGHT)

        # AUTO dropdown (anchors to bottom bar's AUTO)
        self.auto_dropdown = Dropdown(10, 9, 140,
                                      [("Shortest (A*)", "short"), ("Longest (Approx)", "long")],
                                      self._auto_select, title="AUTO ▼", open=False)

        # Settings widgets
        self.volume_slider = Slider(SCREEN_WIDTH//2 - 180, 360, 360, 0.0, 1.0, 0.7, "Volume")
        self.density_slider = Slider(SCREEN_WIDTH//2 - 180, 420, 360, 0.10, 0.35, 0.20, "Maze Density")
        self.scale_slider = Slider(SCREEN_WIDTH//2 - 180, 480, 360, 1.0, 3.0, 2.0, "Maze Size")
        self.dark_toggle = Toggle(SCREEN_WIDTH//2 - 60, 520, 60, 26, value=True, label="Dark Mode")
        self.apply_btn = Button(SCREEN_WIDTH//2 - 120, 560, 240, 34, "APPLY & REGENERATE", THEME.ACCENT_3, THEME.ACCENT_1)
        self.size_minus_btn = Button(SCREEN_WIDTH//2 - 220, 480, 34, 34, "−", THEME.ACCENT_2, THEME.ACCENT_1)
        self.size_plus_btn  = Button(SCREEN_WIDTH//2 + 190, 480, 34, 34, "+", THEME.ACCENT_2, THEME.ACCENT_1)

        # Level select
        self.level_input = 1
        self.level_minus_btn = Button(SCREEN_WIDTH//2 - 140, 430, 40, 34, "−", THEME.ACCENT_2, THEME.ACCENT_1)
        self.level_plus_btn  = Button(SCREEN_WIDTH//2 + 100, 430, 40, 34, "+", THEME.ACCENT_2, THEME.ACCENT_1)
        self.level_go_btn    = Button(SCREEN_WIDTH//2 - 80, 480, 160, 34, "START LEVEL", THEME.ACCENT_1, THEME.ACCENT_2)

        # Auto / Reverse
        self.auto_mode = False
        self.reverse_mode = False
        self.auto_path = []
        self.auto_index = 0
        self.auto_type = None  # "short" | "long" | "reverse"

        # movement recorder for reverse
        self.moves = MoveRecorder()

        # progress toast
        self.toast_text = ""
        self.toast_timer = 0

        # Save defaults
        self.save = {
            "level_index": 0,
            "volume": 0.7,
            "dark_mode": True,
            "maze_density": 0.20,
            "maze_scale": 2.0
        }

        self._generate_levels()
        self._load_progress()
        self._apply_theme()

    # ---------- Persistence ----------
    def _load_progress(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    data = json.load(f)
                    self.save.update(data)
            except Exception:
                pass
        self.sound.set_volume(self.save.get("volume", 0.7))
        self.volume_slider.value = self.save.get("volume", 0.7)
        self.density_slider.value = self.save.get("maze_density", 0.20)
        self.scale_slider.value = self.save.get("maze_scale", 2.0)
        self.dark_toggle.value = self.save.get("dark_mode", True)

    def _save_progress(self):
        self.save["level_index"] = self.current_index
        self.save["volume"] = self.sound.volume
        self.save["dark_mode"] = self.dark_toggle.value
        self.save["maze_density"] = self.density_slider.value
        self.save["maze_scale"] = self.scale_slider.value
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(self.save, f, indent=2)
        except Exception:
            pass

    # ---------- Levels ----------
    def _generate_levels(self):
        realities = list(Reality)
        self.levels = [{"num": i, "reality": realities[(i-1)%len(realities)], "obj": None}
                       for i in range(1, MAX_LEVELS+1)]

    def _level_obj(self, idx):
        meta = self.levels[idx]
        if meta["obj"] is None:
            meta["obj"] = Level(
                meta["num"],
                meta["reality"],
                world_scale=self.scale_slider.value,
                wall_density=self.density_slider.value
            )
        return meta["obj"]

    def start_level(self, idx):
        self.current_index = max(0, min(len(self.levels)-1, idx))
        lvl = self._level_obj(self.current_index)
        self.player = Player(*lvl.start)
        self.level_start = time.time()
        self.state = GameState.PLAYING
        self.auto_mode = False
        self.reverse_mode = False
        self.auto_path = []
        self.auto_index = 0
        self.auto_type = None
        self.camx = 0; self.camy = 0
        self.toast_text = ""; self.toast_timer = 0
        self.moves.clear()
        self.moves.add((self.player.x + self.player.w*0.5, self.player.y + self.player.h*0.5))

    # ---------- Theme ----------
    def _apply_theme(self):
        global THEME
        THEME = Theme(dark=self.dark_toggle.value)
        # re-create bottom bar & dropdown with new theme colors
        self.bottombar = BottomBar(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.auto_dropdown = Dropdown(10, 9, 140,
                                      [("Shortest (A*)", "short"), ("Longest (Approx)", "long")],
                                      self._auto_select, title="AUTO ▼", open=False)

    # ---------- UI Actions ----------
    def _auto_select(self, key):
        # Build path and start auto-move immediately to destination
        lvl = self._level_obj(self.current_index)
        pf = PathFinder(lvl)
        start_center = (self.player.x + self.player.w*0.5, self.player.y + self.player.h*0.5)
        if key == "short":
            path = pf.shortest(start_center, lvl.end)
            self.auto_type = "short"
        else:
            path = pf.longest_approx(start_center)
            self.auto_type = "long"
        if len(path) >= 2:
            self.reverse_mode = False
            self.auto_mode = True
            self.auto_path = path
            self.auto_index = 1
        else:
            self.particles.add(self.player.x, self.player.y, THEME.RED, 16, 2.4, 30)

    def _reverse_moves(self):
        start_center = (self.player.x + self.player.w*0.5, self.player.y + self.player.h*0.5)
        path = self.moves.backtrack_from(start_center, include_current=True)
        if len(path) >= 2:
            self.auto_mode = True
            self.reverse_mode = True
            self.auto_path = path
            self.auto_index = 1
            self.auto_type = "reverse"
        else:
            self.particles.add(self.player.x, self.player.y, THEME.RED, 12, 2.0, 24)

    def _quit_and_save(self):
        self._save_progress()
        self.running = False

    # ---------- Toast ----------
    def _show_toast(self, msg, dur=90):
        self.toast_text = msg
        self.toast_timer = dur

    def _draw_toast(self):
        if self.toast_timer > 0 and self.toast_text:
            rect = pygame.Rect(SCREEN_WIDTH//2 - 180, 100, 360, 36)
            draw_glass(self.screen, rect, 8, 1)
            t = self.h2.render(self.toast_text, True, THEME.WHITE)
            self.screen.blit(t, (rect.centerx - t.get_width()//2, rect.y + 6))
            self.toast_timer -= 1

    # ---------- Events ----------
    def handle_events(self):
        mouse = pygame.mouse.get_pos()
        click = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit_and_save()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click = True

            # settings widgets
            if self.state == GameState.SETTINGS:
                self.volume_slider.handle_event(event)
                self.density_slider.handle_event(event)
                self.scale_slider.handle_event(event)
                self.sound.set_volume(self.volume_slider.value)

            if event.type == pygame.KEYDOWN:
                if self.state == GameState.PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PAUSED
                    elif event.key == pygame.K_a:
                        # open the dropdown anchored to bottom bar AUTO
                        self.auto_dropdown.open = True
                    elif event.key == pygame.K_r:
                        self._reverse_moves()

                elif self.state == GameState.PAUSED and event.key == pygame.K_ESCAPE:
                    self.state = GameState.PLAYING

                elif self.state in (GameState.GAME_OVER, GameState.LEVEL_COMPLETE) and event.key == pygame.K_SPACE:
                    if self.state == GameState.LEVEL_COMPLETE:
                        self.start_level(self.current_index + 1)
                    else:
                        self.start_level(self.current_index)

        # Bars and dropdown (gameplay screens)
        if self.state in (GameState.PLAYING, GameState.PAUSED, GameState.GAME_OVER, GameState.LEVEL_COMPLETE):
            # Process button clicks now (also draws early; safe)
            bottom_actions = self.bottombar.draw(self.screen, mouse, click)

            # Anchor dropdown above bottom AUTO button
            auto_btn = self.bottombar.buttons["auto"].rect
            self.auto_dropdown.x = auto_btn.x
            self.auto_dropdown.y = auto_btn.y - (self.auto_dropdown.header_h + self.auto_dropdown.item_h*len(self.auto_dropdown.items)) - 8
            self.auto_dropdown.w = auto_btn.w
            self.auto_dropdown.draw(self.screen, mouse, click)

            if "auto" in bottom_actions:
                self.auto_dropdown.open = not self.auto_dropdown.open
            if "reverse" in bottom_actions:
                self._reverse_moves()
            if "pause" in bottom_actions:
                self.state = GameState.PAUSED if self.state == GameState.PLAYING else GameState.PLAYING
            if "savequit" in bottom_actions:
                self._quit_and_save()

        # cancel auto if moving manually
        if self.auto_mode and self.state == GameState.PLAYING:
            keys = pygame.key.get_pressed()
            if any([keys[k] for k in [pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]]):
                self.auto_mode = False
                self.reverse_mode = False

    # ---------- Update (follows waypoints using player CENTER) ----------
    def update(self, dt):
        self.bg.update()

        if self.state == GameState.PLAYING and self.player:
            lvl = self._level_obj(self.current_index)
            dt_scale = self.timefx.time_scale

            dx = dy = 0.0

            # AUTO FOLLOW
            if self.auto_mode and len(self.auto_path) >= 2 and self.auto_index < len(self.auto_path):
                tx, ty = self.auto_path[self.auto_index]                 # target waypoint (cell center)
                pcx = self.player.x + self.player.w * 0.5               # player's center
                pcy = self.player.y + self.player.h * 0.5
                vx, vy = tx - pcx, ty - pcy
                d = math.hypot(vx, vy)

                if d < max(8, CELL_SIZE * 0.2):                         # arrive threshold
                    self.auto_index += 1
                    if self.auto_index >= len(self.auto_path):
                        self.auto_mode = False
                        self.reverse_mode = False
                else:
                    if d != 0:
                        vx /= d; vy /= d
                    dx, dy = vx, vy
            else:
                # MANUAL
                keys = pygame.key.get_pressed()
                if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= 1
                if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
                if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= 1
                if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += 1
                if dx != 0 and dy != 0:
                    inv = 1 / math.sqrt(2); dx *= inv; dy *= inv

            moved = self.player.move(dx, dy, lvl.walls, lvl.reality, dt_scale)
            if moved:
                self.moves.add((self.player.x + self.player.w*0.5, self.player.y + self.player.h*0.5))

            self.timefx.update()

            # enemies
            pr = pygame.Rect(int(self.player.x), int(self.player.y), self.player.w, self.player.h)
            for e in lvl.enemies:
                e.update(self.player.x, self.player.y, lvl.walls, lvl.reality, dt_scale)
                er = pygame.Rect(int(e.x), int(e.y), e.w, e.h)
                if pr.colliderect(er):
                    if self.player.damage(1):
                        self.particles.add(self.player.x, self.player.y, THEME.RED, 14, 2.0, 26)

            # collectibles
            for c in lvl.collectibles:
                if not c["collected"]:
                    cr = pygame.Rect(c["x"]-10, c["y"]-10, 20, 20)
                    if pr.colliderect(cr):
                        c["collected"] = True
                        self.particles.add(c["x"], c["y"], THEME.ACCENT_2, 12, 1.6, 26)

            # portals
            for p in lvl.portals:
                p.update()
                if math.hypot(self.player.x - p.entrance[0], self.player.y - p.entrance[1]) < 24:
                    self.player.x, self.player.y = p.exit
                    self.particles.add(self.player.x, self.player.y, THEME.ACCENT_1, 16, 2.2, 30)
                    self.moves.add((self.player.x + self.player.w*0.5, self.player.y + self.player.h*0.5))

            # progress flags
            for flg in lvl.flags:
                if not flg["hit"] and math.hypot(self.player.x - flg["pos"][0], self.player.y - flg["pos"][1]) < 24:
                    flg["hit"] = True
                    self.particles.add(flg["pos"][0], flg["pos"][1], THEME.ACCENT_1, 20, 2.0, 36)
                    self._show_toast(f"{flg['label']} way completed!", 120)

            # timer/health
            elapsed = int(time.time() - self.level_start)
            if elapsed > lvl.time_limit or self.player.health <= 0:
                self.state = GameState.GAME_OVER
                self.auto_mode = False
                self.reverse_mode = False

            # end zone
            end_rect = pygame.Rect(lvl.end[0]-20, lvl.end[1]-20, 40, 40)
            if pr.colliderect(end_rect):
                self.state = GameState.LEVEL_COMPLETE
                self.auto_mode = False
                self.reverse_mode = False

            self.particles.update()

            # camera clamp to world size
            self.camx = max(0, min(lvl.world_w - SCREEN_WIDTH, int(self.player.x - SCREEN_WIDTH//2)))
            self.camy = max(0, min(lvl.world_h - SCREEN_HEIGHT, int(self.player.y - SCREEN_HEIGHT//2)))

    # ---------- Draw ----------
    def _draw_world(self):
        lvl = self._level_obj(self.current_index)
        # walls
        for w in lvl.walls:
            pygame.draw.rect(self.screen, THEME.WALL,
                             pygame.Rect(w.x - self.camx, w.y - self.camy, w.w, w.h))
        # end
        pygame.draw.rect(self.screen, THEME.END_ZONE,
                         (int(lvl.end[0]-20-self.camx), int(lvl.end[1]-20-self.camy), 40, 40), 3)
        # portals
        for p in lvl.portals:
            p.draw(self.screen, self.camx, self.camy)
        # enemies
        for e in lvl.enemies:
            e.draw(self.screen, self.camx, self.camy)
        # collectibles
        for c in lvl.collectibles:
            if not c["collected"]:
                col = THEME.ACCENT_2 if c["type"] == "key" else THEME.ACCENT_1
                pygame.draw.circle(self.screen, col, (int(c["x"]-self.camx), int(c["y"]-self.camy)), 6)
        # flags
        for flg in lvl.flags:
            x, y = int(flg["pos"][0]-self.camx), int(flg["pos"][1]-self.camy)
            pole = pygame.Rect(x-2, y-18, 4, 20)
            pygame.draw.rect(self.screen, THEME.BORDER_SOFT, pole)
            tri = [(x, y-18), (x+14, y-12), (x, y-6)]
            color = THEME.ACCENT_1 if flg["label"] == "1/4" else THEME.ACCENT_2
            pygame.draw.polygon(self.screen, color, tri)
            lbl = self.small.render(flg["label"] , True, THEME.OFFWHITE)
            self.screen.blit(lbl, (x - lbl.get_width()//2, y - 30))

        # player + particles
        self.particles.draw(self.screen, self.camx, self.camy)
        self.player.draw(self.screen, self.camx, self.camy)

        # path overlay
        if len(self.auto_path) >= 2:
            color = {
                "short": THEME.ACCENT_1,
                "long": THEME.ACCENT_4,
                "reverse": THEME.BORDER_SOFT
            }.get(self.auto_type, THEME.ACCENT_1)
            for i in range(len(self.auto_path)-1):
                x1 = int(self.auto_path[i][0]-self.camx); y1 = int(self.auto_path[i][1]-self.camy)
                x2 = int(self.auto_path[i+1][0]-self.camx); y2 = int(self.auto_path[i+1][1]-self.camy)
                pygame.draw.line(self.screen, color, (x1,y1), (x2,y2), 4)

    def _draw_hud(self):
        # health
        maxw = 200
        hpw = int(max(0, min(1.0, self.player.health/self.player.max_health)) * maxw)
        bar = pygame.Rect(16, 56, maxw, 12)
        draw_glass(self.screen, bar.inflate(4, 6), 6, 1)
        pygame.draw.rect(self.screen, (60, 28, 36), bar, border_radius=6)
        pygame.draw.rect(self.screen, THEME.ACCENT_3, (bar.x, bar.y, hpw, bar.h), border_radius=6)

        # info
        lvl = self._level_obj(self.current_index)
        elapsed = int(time.time() - self.level_start)
        left = max(0, lvl.time_limit - elapsed)
        info = self.small.render(f"L{lvl.num} • {lvl.reality.name} • {left}s", True, THEME.OFFWHITE)
        self.screen.blit(info, (16, 74))

        # toast
        self._draw_toast()

        if self.auto_mode and self.auto_type:
            b = self.small.render(f"AUTO: {self.auto_type.upper()}", True, THEME.ACCENT_1)
            self.screen.blit(b, (SCREEN_WIDTH-180, 56))

    def _panel_message(self, title, subtitle):
        rect = pygame.Rect(SCREEN_WIDTH//2 - 320, SCREEN_HEIGHT//2 - 110, 640, 200)
        draw_glass(self.screen, rect, 12, 1)
        t = self.h1.render(title, True, THEME.WHITE)
        s = self.h2.render(subtitle, True, THEME.OFFWHITE)
        self.screen.blit(t, (rect.centerx - t.get_width()//2, rect.y + 26))
        self.screen.blit(s, (rect.centerx - s.get_width()//2, rect.y + 94))
        cross = IconButton(rect.right - 34, rect.y + 8, 24, "✕", THEME.ACCENT_4)
        cross.update(pygame.mouse.get_pos()); cross.draw(self.screen)
        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1 and cross.rect.collidepoint(event.pos):
                if self.state in (GameState.GAME_OVER, GameState.LEVEL_COMPLETE, GameState.PAUSED):
                    self.state = GameState.PLAYING

    def _settings_panel(self):
        rect = pygame.Rect(SCREEN_WIDTH//2 - 320, SCREEN_HEIGHT//2 - 190, 640, 380)
        draw_glass(self.screen, rect, 12, 1)
        t = self.h1.render("SETTINGS", True, THEME.WHITE)
        self.screen.blit(t, (rect.centerx - t.get_width()//2, rect.y + 16))

        # Volume/Density/Size
        self.volume_slider.draw(self.screen)
        self.density_slider.draw(self.screen)
        label_density = self.small.render(f"({self.density_slider.value:.2f}) lower=fewer walls", True, THEME.MUTED)
        self.screen.blit(label_density, (self.density_slider.rect.right - 180, self.density_slider.rect.y - 24))

        self.scale_slider.draw(self.screen)
        # Size +/- buttons (instant apply)
        self.size_minus_btn.update(pygame.mouse.get_pos()); self.size_minus_btn.draw(self.screen)
        self.size_plus_btn.update(pygame.mouse.get_pos());  self.size_plus_btn.draw(self.screen)

        # Dark toggle
        self.dark_toggle.draw(self.screen, pygame.mouse.get_pos(), False)

        # Apply & Regenerate (for density/slider changes)
        self.apply_btn.update(pygame.mouse.get_pos())
        self.apply_btn.draw(self.screen)

        # Close
        cross = IconButton(rect.right - 34, rect.y + 8, 24, "✕", THEME.ACCENT_4)
        cross.update(pygame.mouse.get_pos()); cross.draw(self.screen)

        # Click handling here
        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1:
                if self.apply_btn.rect.collidepoint(event.pos):
                    self._apply_theme()
                    self.levels[self.current_index]["obj"] = None
                    self.start_level(self.current_index)
                    self._save_progress()
                if self.dark_toggle.rect.collidepoint(event.pos):
                    self.dark_toggle.value = not self.dark_toggle.value
                    self._apply_theme()
                if self.size_minus_btn.rect.collidepoint(event.pos):
                    self.scale_slider.value = max(1.0, round(self.scale_slider.value - 0.25, 2))
                    self.levels[self.current_index]["obj"] = None
                    self.start_level(self.current_index)
                    self._save_progress()
                    self._show_toast(f"Maze size: {self.scale_slider.value:.2f}x", 90)
                if self.size_plus_btn.rect.collidepoint(event.pos):
                    self.scale_slider.value = min(3.0, round(self.scale_slider.value + 0.25, 2))
                    self.levels[self.current_index]["obj"] = None
                    self.start_level(self.current_index)
                    self._save_progress()
                    self._show_toast(f"Maze size: {self.scale_slider.value:.2f}x", 90)
                if cross.rect.collidepoint(event.pos):
                    self.state = GameState.PLAYING

    def _menu_panel(self):
        rect = pygame.Rect(SCREEN_WIDTH//2 - 300, SCREEN_HEIGHT//2 - 220, 600, 400)
        draw_glass(self.screen, rect, 12, 1)
        title = self.title_font.render("QUANTUM MAZE", True, THEME.WHITE)
        self.screen.blit(title, (rect.centerx - title.get_width()//2, rect.y + 24))

        btn_w, btn_h, gap = 220, 36, 14
        bx = rect.centerx - btn_w//2
        by = rect.y + 100
        btns = {
            "continue": Button(bx, by, btn_w, btn_h, "CONTINUE GAME", THEME.ACCENT_1, THEME.ACCENT_2),
            "new":      Button(bx, by + (btn_h+gap), btn_w, btn_h, "START NEW GAME", THEME.ACCENT_3, THEME.ACCENT_1),
            "levels":   Button(bx, by + 2*(btn_h+gap), btn_w, btn_h, "LEVEL SELECT", THEME.ACCENT_2, THEME.ACCENT_1),
            "settings": Button(bx, by + 3*(btn_h+gap), btn_w, btn_h, "SETTINGS", THEME.ACCENT_1, THEME.ACCENT_3),
        }
        mouse = pygame.mouse.get_pos()
        click = False
        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1: click = True

        for b in btns.values():
            b.update(mouse); b.draw(self.screen)

        if btns["continue"].clicked(mouse, click):
            self.start_level(self.save.get("level_index", 0))
        if btns["new"].clicked(mouse, click):
            self.start_level(0)
        if btns["levels"].clicked(mouse, click):
            self.state = GameState.LEVEL_SELECT
        if btns["settings"].clicked(mouse, click):
            self.state = GameState.SETTINGS

        # Bottom "Save & Quit" on menu
        bottom_quit = Button(rect.centerx - 110, rect.bottom - 56, 220, 36, "SAVE & QUIT", THEME.ACCENT_4, THEME.ACCENT_2)
        bottom_quit.update(mouse); bottom_quit.draw(self.screen)
        if bottom_quit.clicked(mouse, click):
            self._quit_and_save()

    def _level_select_panel(self):
        rect = pygame.Rect(SCREEN_WIDTH//2 - 300, SCREEN_HEIGHT//2 - 180, 600, 320)
        draw_glass(self.screen, rect, 12, 1)
        t = self.h1.render("LEVEL SELECT", True, THEME.WHITE)
        self.screen.blit(t, (rect.centerx - t.get_width()//2, rect.y + 16))

        disp = self.h2.render(f"Level: {self.level_input}", True, THEME.OFFWHITE)
        self.screen.blit(disp, (SCREEN_WIDTH//2 - disp.get_width()//2, 390))

        self.level_minus_btn.update(pygame.mouse.get_pos()); self.level_minus_btn.draw(self.screen)
        self.level_plus_btn.update(pygame.mouse.get_pos());  self.level_plus_btn.draw(self.screen)
        self.level_go_btn.update(pygame.mouse.get_pos());    self.level_go_btn.draw(self.screen)

        cross = IconButton(rect.right - 34, rect.y + 8, 24, "✕", THEME.ACCENT_4)
        cross.update(pygame.mouse.get_pos()); cross.draw(self.screen)

        for event in pygame.event.get([pygame.MOUSEBUTTONDOWN]):
            if event.button == 1:
                if self.level_minus_btn.rect.collidepoint(event.pos):
                    self.level_input = max(1, self.level_input - 1)
                if self.level_plus_btn.rect.collidepoint(event.pos):
                    self.level_input = min(MAX_LEVELS, self.level_input + 1)
                if self.level_go_btn.rect.collidepoint(event.pos):
                    self.start_level(self.level_input - 1)
                if cross.rect.collidepoint(event.pos):
                    self.state = GameState.MENU

    def draw(self):
        draw_vertical_gradient(self.screen, THEME.BG_TOP, THEME.BG_BOTTOM)
        self.bg.draw(self.screen)

        if self.state == GameState.MENU:
            self._menu_panel()

        elif self.state in (GameState.PLAYING, GameState.PAUSED, GameState.GAME_OVER, GameState.LEVEL_COMPLETE):
            self._draw_world()
            self._draw_hud()

            # Bottom bar (drawn again to ensure on-top look)
            self.bottombar.draw(self.screen, pygame.mouse.get_pos(), False)

            # Keep dropdown anchored if open
            if self.auto_dropdown.open:
                auto_btn = self.bottombar.buttons["auto"].rect
                self.auto_dropdown.x = auto_btn.x
                self.auto_dropdown.y = auto_btn.y - (self.auto_dropdown.header_h + self.auto_dropdown.item_h*len(self.auto_dropdown.items)) - 8
                self.auto_dropdown.w = auto_btn.w
                self.auto_dropdown.draw(self.screen, pygame.mouse.get_pos(), False)

            if self.state == GameState.PAUSED:
                self._panel_message("PAUSED", "ESC to resume • SAVE & QUIT to store progress")
            if self.state == GameState.GAME_OVER:
                self._panel_message("GAME OVER", "Press SPACE to retry this level")
            if self.state == GameState.LEVEL_COMPLETE:
                self._panel_message("LEVEL COMPLETE", "Press SPACE for next level")

        elif self.state == GameState.SETTINGS:
            self._settings_panel()

        elif self.state == GameState.LEVEL_SELECT:
            self._level_select_panel()

        pygame.display.flip()

    # ---------- Run ----------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        self._save_progress()
        pygame.quit()

# =========================
# Main
# =========================
if __name__ == "__main__":
    game = QuantumMazeGame()
    game.run()

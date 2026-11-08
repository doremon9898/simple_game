"""Zombie Top-down Shooter (tkinter)
พัฒนาโดย: nitithon zojimax
ควบคุม:
    หน้าเมนู:
        1-5 / คลิกการ์ด    - เลือกอาวุธ
        ← → / คลิกฉาก     - เลือกฉาก
        Enter / คลิกปุ่ม   - เริ่มเกม
    ในเกม:
        W A S D / ลูกศร  - เดิน
        เมาส์             - เล็ง
        คลิกซ้าย (ค้างได้) - ยิง
        Space             - พุ่งหลบ (Dash) ไม่โดนดาเมจระหว่างพุ่ง
        R                 - รีโหลด
        P                 - หยุดเกมชั่วคราว
    จบเกม:
        Enter             - เล่นใหม่ (อาวุธ/ฉากเดิม)
        M                 - กลับเมนู
"""

import math
import os
import random
import sys
import tkinter as tk

WIDTH, HEIGHT = 960, 640
FPS = 60
DT = 1 / FPS

PLAYER_SPEED = 230
PLAYER_RADIUS = 14
PLAYER_MAX_HP = 100

BULLET_RADIUS = 4
DASH_SPEED = 720
DASH_TIME = 0.15
DASH_COOLDOWN = 1.5

HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")

# อาวุธ: delay = เวลาระหว่างนัด, range = อายุกระสุน (วินาที), pierce = ทะลุได้กี่ตัว, blast = รัศมีระเบิด
WEAPONS = [
    dict(name="Pistol", th="ปืนพก", desc="แม่นยำ ยิงทีละนัด\nรีโหลดไว",
         delay=0.25, mag=12, reload=0.8, dmg=2, pellets=1, spread=0.02, speed=780,
         range=1.5, auto=False, pierce=0, blast=0, color="#ffe27a", width=3),
    dict(name="Assault Rifle", th="ไรเฟิลจู่โจม", desc="ยิงรัว กดค้างได้\nกระสุนเยอะ",
         delay=0.09, mag=30, reload=1.4, dmg=1, pellets=1, spread=0.07, speed=840,
         range=1.5, auto=True, pierce=0, blast=0, color="#ffd04a", width=3),
    dict(name="Shotgun", th="ลูกซอง", desc="กระจาย 7 นัด\nระยะใกล้แรงมาก",
         delay=0.7, mag=6, reload=1.6, dmg=1, pellets=7, spread=0.32, speed=680,
         range=0.38, auto=False, pierce=0, blast=0, color="#ffb35a", width=2),
    dict(name="Sniper", th="สไนเปอร์", desc="ดาเมจสูง\nทะลุได้ 4 ตัว",
         delay=0.9, mag=5, reload=1.8, dmg=8, pellets=1, spread=0.0, speed=1500,
         range=1.0, auto=False, pierce=4, blast=0, color="#9ef0ff", width=4),
    dict(name="Grenade Launcher", th="เครื่องยิงระเบิด", desc="ระเบิดวงกว้าง\nกวาดฝูงซอมบี้",
         delay=0.85, mag=4, reload=2.0, dmg=5, pellets=1, spread=0.03, speed=480,
         range=0.9, auto=False, pierce=0, blast=85, color="#7ddc5a", width=7),
]

# ฉาก: zspeed = ตัวคูณความเร็วซอมบี้
MAPS = [
    dict(name="สุสานร้าง", desc="ป้ายหลุมศพขวางทาง\nสมดุล เหมาะกับมือใหม่",
         bg="#1e1f1a", dot="#2a2c22", obstacles=["tomb"], count=12, zspeed=1.0),
    dict(name="เมืองร้าง", desc="ยิงถังน้ำมันให้ระเบิดได้!\nระวังอย่ายืนใกล้",
         bg="#2b2b30", dot="#36363c", obstacles=["barrel", "barrel", "crate"], count=13, zspeed=1.0),
    dict(name="ป่ามืด", desc="ต้นไม้หนาแน่น\nซอมบี้เร็วขึ้น 15%",
         bg="#13221a", dot="#1c3326", obstacles=["tree", "tree", "rock"], count=16, zspeed=1.15),
]

OBSTACLE_SIZES = {"tomb": 18, "barrel": 16, "crate": 20, "tree": 26, "rock": 20}

# ชนิดซอมบี้: ความเร็ว, เลือด, รัศมี, ดาเมจต่อวินาที, คะแนน, สี
ZOMBIE_TYPES = {
    "walker": dict(speed=70, hp=3, radius=15, dps=20, score=10, color="#5a8f3c"),
    "runner": dict(speed=135, hp=2, radius=12, dps=15, score=15, color="#9bc43a"),
    "brute": dict(speed=45, hp=12, radius=24, dps=40, score=40, color="#3d5e2a"),
    "boss": dict(speed=55, hp=60, radius=34, dps=55, score=300, color="#6b3d8f"),
}

# keycode บน Windows ไม่ขึ้นกับภาษาแป้นพิมพ์ ทำให้เล่นได้แม้สลับเป็นภาษาไทย
WIN_KEYCODES = {87: "w", 65: "a", 83: "s", 68: "d", 82: "r", 80: "p", 77: "m",
                49: "1", 50: "2", 51: "3", 52: "4", 53: "5"}


def load_high_score():
    try:
        with open(HIGHSCORE_FILE, encoding="utf-8") as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def save_high_score(score):
    try:
        with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            f.write(str(score))
    except OSError:
        pass


class Bullet:
    def __init__(self, x, y, angle, weapon):
        speed = weapon["speed"]
        if weapon["pellets"] > 1:
            speed *= random.uniform(0.85, 1.1)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.dmg = weapon["dmg"]
        self.pierce = weapon["pierce"]
        self.blast = weapon["blast"]
        self.life = weapon["range"]
        self.color = weapon["color"]
        self.width = weapon["width"]
        self.hit = set()
        self.alive = True

    def update(self):
        self.x += self.vx * DT
        self.y += self.vy * DT
        self.life -= DT
        if self.life <= 0 or not (-20 < self.x < WIDTH + 20 and -20 < self.y < HEIGHT + 20):
            self.alive = False


class Zombie:
    def __init__(self, kind, wave, speed_mult=1.0):
        spec = ZOMBIE_TYPES[kind]
        self.kind = kind
        self.speed = spec["speed"] * (1 + 0.04 * (wave - 1)) * speed_mult
        self.max_hp = round(spec["hp"] * (1 + 0.12 * (wave - 1)))
        self.hp = self.max_hp
        self.radius = spec["radius"]
        self.dps = spec["dps"]
        self.score = spec["score"]
        self.color = spec["color"]
        self.flash = 0.0
        self.dead = False
        self.wobble = random.uniform(0, math.tau)

        # เกิดนอกขอบจอด้านใดด้านหนึ่ง
        side = random.randint(0, 3)
        m = 40
        if side == 0:
            self.x, self.y = random.uniform(0, WIDTH), -m
        elif side == 1:
            self.x, self.y = WIDTH + m, random.uniform(0, HEIGHT)
        elif side == 2:
            self.x, self.y = random.uniform(0, WIDTH), HEIGHT + m
        else:
            self.x, self.y = -m, random.uniform(0, HEIGHT)

    def update(self, px, py):
        self.wobble += DT * 6
        dx, dy = px - self.x, py - self.y
        dist = math.hypot(dx, dy) or 1
        # เดินโยกเยกเล็กน้อยให้ดูเป็นซอมบี้
        sway = math.sin(self.wobble) * 0.35
        ang = math.atan2(dy, dx) + sway
        self.x += math.cos(ang) * self.speed * DT
        self.y += math.sin(ang) * self.speed * DT
        self.flash = max(0.0, self.flash - DT)
        return dist


class Obstacle:
    def __init__(self, x, y, r, kind):
        self.x, self.y, self.r = x, y, r
        self.kind = kind


class Pickup:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.life = 10.0
        self.radius = 10


class Particle:
    def __init__(self, x, y, color, speed=220):
        a = random.uniform(0, math.tau)
        s = random.uniform(60, speed)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * s, math.sin(a) * s
        self.life = random.uniform(0.25, 0.6)
        self.color = color

    def update(self):
        self.x += self.vx * DT
        self.y += self.vy * DT
        self.vx *= 0.9
        self.vy *= 0.9
        self.life -= DT


class Game:
    def __init__(self, root):
        self.root = root
        root.title("Zombie Shooter")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#1e1f1a",
                                highlightthickness=0, cursor="none")
        self.canvas.pack()

        self.keys = set()
        self.mouse_x, self.mouse_y = WIDTH / 2, HEIGHT / 2
        self.mouse_down = False
        self.trigger_used = False
        self.high_score = load_high_score()

        self.state = "menu"  # menu / play / over
        self.weapon_idx = 0
        self.map_idx = 0
        self.menu_buttons = []

        root.bind("<KeyPress>", self.on_key_down)
        root.bind("<KeyRelease>", self.on_key_up)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.reset()
        self.loop()

    # ---------- state ----------
    @property
    def weapon(self):
        return WEAPONS[self.weapon_idx]

    @property
    def map(self):
        return MAPS[self.map_idx]

    def reset(self):
        self.px, self.py = WIDTH / 2, HEIGHT / 2
        self.hp = PLAYER_MAX_HP
        self.score = 0
        self.kills = 0
        self.ammo = self.weapon["mag"]
        self.reload_timer = 0.0
        self.fire_cooldown = 0.0
        self.hurt_timer = 0.0
        self.muzzle = 0.0
        self.shake = 0.0
        self.dash_time = 0.0
        self.dash_cd = 0.0
        self.dash_dir = (0.0, 0.0)
        self.bullets = []
        self.zombies = []
        self.pickups = []
        self.particles = []
        self.blasts = []
        self.wave = 0
        self.to_spawn = 0
        self.spawn_timer = 0.0
        self.wave_banner = 0.0
        self.paused = False
        self.new_record = False

        m = self.map
        self.canvas.config(bg=m["bg"])
        self.ground = [(random.uniform(0, WIDTH), random.uniform(0, HEIGHT),
                        random.uniform(2, 6)) for _ in range(90)]
        self.obstacles = self.build_obstacles()
        self.next_wave()

    def build_obstacles(self):
        m = self.map
        obs = []
        tries = 0
        while len(obs) < m["count"] and tries < 1000:
            tries += 1
            kind = random.choice(m["obstacles"])
            r = OBSTACLE_SIZES[kind] * random.uniform(0.85, 1.2)
            x = random.uniform(60, WIDTH - 60)
            y = random.uniform(100, HEIGHT - 60)
            # เว้นที่ว่างตรงกลางให้ผู้เล่นเกิด และเว้นช่องระหว่างสิ่งกีดขวางให้เดินผ่านได้
            if math.hypot(x - WIDTH / 2, y - HEIGHT / 2) < 140:
                continue
            if any(math.hypot(x - o.x, y - o.y) < r + o.r + 50 for o in obs):
                continue
            obs.append(Obstacle(x, y, r, kind))
        return obs

    def next_wave(self):
        self.wave += 1
        self.to_spawn = 6 + self.wave * 4
        self.spawn_timer = 1.5
        self.wave_banner = 2.0
        if self.wave % 5 == 0:
            self.zombies.append(Zombie("boss", self.wave, self.map["zspeed"]))

    def start_game(self):
        self.state = "play"
        self.trigger_used = True
        self.reset()

    # ---------- input ----------
    def key_name(self, event):
        if sys.platform == "win32" and event.keycode in WIN_KEYCODES:
            return WIN_KEYCODES[event.keycode]
        return event.keysym.lower()

    def on_key_down(self, event):
        k = self.key_name(event)
        self.keys.add(k)
        if self.state == "menu":
            if k in ("1", "2", "3", "4", "5"):
                self.weapon_idx = int(k) - 1
            elif k in ("left", "a"):
                self.map_idx = (self.map_idx - 1) % len(MAPS)
            elif k in ("right", "d"):
                self.map_idx = (self.map_idx + 1) % len(MAPS)
            elif k == "return":
                self.start_game()
        elif self.state == "play":
            if k == "r":
                self.start_reload()
            elif k == "p":
                self.paused = not self.paused
            elif k == "space":
                self.start_dash()
        elif self.state == "over":
            if k == "return":
                self.start_game()
            elif k == "m":
                self.state = "menu"

    def on_key_up(self, event):
        self.keys.discard(self.key_name(event))

    def on_motion(self, event):
        self.mouse_x, self.mouse_y = event.x, event.y

    def on_mouse_down(self, event):
        self.on_motion(event)
        if self.state == "menu":
            for x1, y1, x2, y2, action in self.menu_buttons:
                if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                    action()
                    break
            return
        self.mouse_down = True

    def on_mouse_up(self, _event):
        self.mouse_down = False
        self.trigger_used = False

    def start_reload(self):
        if self.reload_timer <= 0 and self.ammo < self.weapon["mag"]:
            self.reload_timer = self.weapon["reload"]

    def start_dash(self):
        if self.dash_cd > 0 or self.paused:
            return
        dx, dy = self.move_input()
        if not (dx or dy):
            a = self.aim_angle()
            dx, dy = math.cos(a), math.sin(a)
        n = math.hypot(dx, dy)
        self.dash_dir = (dx / n, dy / n)
        self.dash_time = DASH_TIME
        self.dash_cd = DASH_COOLDOWN

    def move_input(self):
        dx = ("d" in self.keys or "right" in self.keys) - ("a" in self.keys or "left" in self.keys)
        dy = ("s" in self.keys or "down" in self.keys) - ("w" in self.keys or "up" in self.keys)
        return dx, dy

    # ---------- update ----------
    def update(self):
        if self.state != "play" or self.paused:
            return

        # เดิน / พุ่ง
        if self.dash_time > 0:
            self.dash_time -= DT
            self.px += self.dash_dir[0] * DASH_SPEED * DT
            self.py += self.dash_dir[1] * DASH_SPEED * DT
            self.particles.append(Particle(self.px, self.py, "#7fb3e8", speed=60))
        else:
            dx, dy = self.move_input()
            if dx or dy:
                n = math.hypot(dx, dy)
                self.px += dx / n * PLAYER_SPEED * DT
                self.py += dy / n * PLAYER_SPEED * DT
        self.dash_cd = max(0.0, self.dash_cd - DT)
        self.px, self.py = self.push_out(self.px, self.py, PLAYER_RADIUS)
        self.px = min(max(self.px, PLAYER_RADIUS), WIDTH - PLAYER_RADIUS)
        self.py = min(max(self.py, PLAYER_RADIUS), HEIGHT - PLAYER_RADIUS)

        self.update_weapon()

        # กระสุนเดิน / ชนสิ่งกีดขวาง
        for b in self.bullets:
            b.update()
            hit_obs = self.obstacle_at(b.x, b.y)
            if b.alive and hit_obs:
                b.alive = False
                if hit_obs.kind == "barrel":
                    self.obstacles.remove(hit_obs)
                    self.explode(hit_obs.x, hit_obs.y, 110, 8, hurt_player=True)
                elif b.blast:
                    self.explode(b.x, b.y, b.blast, b.dmg)
                else:
                    for _ in range(3):
                        self.particles.append(Particle(b.x, b.y, "#aaaaaa", speed=120))
            elif not b.alive and b.blast and b.life <= 0:
                # ลูกระเบิดตกถึงระยะแล้วระเบิดเอง
                self.explode(b.x, b.y, b.blast, b.dmg)

        # เกิดซอมบี้
        if self.to_spawn > 0:
            self.spawn_timer -= DT
            if self.spawn_timer <= 0:
                self.zombies.append(Zombie(self.pick_zombie_kind(), self.wave, self.map["zspeed"]))
                self.to_spawn -= 1
                self.spawn_timer = max(0.25, 1.0 - self.wave * 0.06) * random.uniform(0.6, 1.2)
        elif not self.zombies:
            self.score += self.wave * 25  # โบนัสผ่านด่าน
            self.next_wave()

        # ซอมบี้เดิน + ทำดาเมจ (ไม่โดนดาเมจระหว่างพุ่ง)
        for z in self.zombies:
            dist = z.update(self.px, self.py)
            z.x, z.y = self.push_out(z.x, z.y, z.radius)
            if dist < z.radius + PLAYER_RADIUS and self.dash_time <= 0:
                self.hp -= z.dps * DT
                self.hurt_timer = 0.15

        # ซอมบี้ดันกันไม่ให้ซ้อนทับ
        zs = self.zombies
        for i in range(len(zs)):
            a = zs[i]
            for j in range(i + 1, len(zs)):
                b = zs[j]
                ddx, ddy = b.x - a.x, b.y - a.y
                d = math.hypot(ddx, ddy)
                min_d = a.radius + b.radius
                if 0 < d < min_d:
                    push = (min_d - d) / 2
                    ddx, ddy = ddx / d * push, ddy / d * push
                    a.x -= ddx; a.y -= ddy
                    b.x += ddx; b.y += ddy

        # กระสุนชนซอมบี้
        for b in self.bullets:
            if not b.alive:
                continue
            for z in self.zombies:
                if z.dead or z in b.hit:
                    continue
                if math.hypot(b.x - z.x, b.y - z.y) < z.radius + BULLET_RADIUS:
                    if b.blast:
                        b.alive = False
                        self.explode(b.x, b.y, b.blast, b.dmg)
                        break
                    b.hit.add(z)
                    self.damage_zombie(z, b.dmg, b.vx * 0.008, b.vy * 0.008)
                    if b.pierce > 0:
                        b.pierce -= 1
                    else:
                        b.alive = False
                        break

        self.bullets = [b for b in self.bullets if b.alive]
        self.zombies = [z for z in self.zombies if not z.dead]

        # ไอเท็มเลือด
        for p in self.pickups:
            p.life -= DT
            if math.hypot(p.x - self.px, p.y - self.py) < p.radius + PLAYER_RADIUS:
                self.hp = min(PLAYER_MAX_HP, self.hp + 25)
                p.life = 0
        self.pickups = [p for p in self.pickups if p.life > 0]

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]
        for bl in self.blasts:
            bl[3] -= DT
        self.blasts = [bl for bl in self.blasts if bl[3] > 0]

        self.hurt_timer = max(0.0, self.hurt_timer - DT)
        self.wave_banner = max(0.0, self.wave_banner - DT)
        self.muzzle = max(0.0, self.muzzle - DT)
        self.shake = max(0.0, self.shake - DT * 30)

        if self.hp <= 0:
            self.hp = 0
            self.state = "over"
            if self.score > self.high_score:
                self.high_score = self.score
                self.new_record = True
                save_high_score(self.score)

    def update_weapon(self):
        w = self.weapon
        if self.reload_timer > 0:
            self.reload_timer -= DT
            if self.reload_timer <= 0:
                self.ammo = w["mag"]
        self.fire_cooldown = max(0.0, self.fire_cooldown - DT)
        wants_fire = self.mouse_down and (w["auto"] or not self.trigger_used)
        if not wants_fire or self.fire_cooldown > 0 or self.reload_timer > 0:
            return
        if self.ammo <= 0:
            self.start_reload()
            return
        base = self.aim_angle()
        for _ in range(w["pellets"]):
            angle = base + random.uniform(-w["spread"], w["spread"])
            gx = self.px + math.cos(base) * 24
            gy = self.py + math.sin(base) * 24
            self.bullets.append(Bullet(gx, gy, angle, w))
        self.ammo -= 1
        self.fire_cooldown = w["delay"]
        self.muzzle = 0.05
        self.shake = max(self.shake, 2 + w["dmg"] * w["pellets"] * 0.6)
        self.trigger_used = True
        if self.ammo == 0:
            self.start_reload()

    def push_out(self, x, y, rad):
        for o in self.obstacles:
            dx, dy = x - o.x, y - o.y
            d = math.hypot(dx, dy)
            m = rad + o.r
            if d < m:
                if d == 0:
                    dx, dy, d = 1.0, 0.0, 1.0
                x = o.x + dx / d * m
                y = o.y + dy / d * m
        return x, y

    def obstacle_at(self, x, y):
        for o in self.obstacles:
            if math.hypot(x - o.x, y - o.y) < o.r:
                return o
        return None

    def explode(self, x, y, radius, dmg, hurt_player=False):
        self.blasts.append([x, y, radius, 0.3])
        self.shake = max(self.shake, 14)
        for _ in range(30):
            self.particles.append(Particle(x, y, random.choice(["#ff9a2a", "#ffd34a", "#ff5a1a", "#555"]),
                                           speed=radius * 4))
        for z in self.zombies:
            d = math.hypot(z.x - x, z.y - y)
            if not z.dead and d < radius + z.radius:
                d = d or 1
                self.damage_zombie(z, dmg, (z.x - x) / d * 18, (z.y - y) / d * 18)
        if hurt_player and self.dash_time <= 0 and math.hypot(self.px - x, self.py - y) < radius:
            self.hp -= 25
            self.hurt_timer = 0.3
        # ระเบิดต่อเนื่อง: ถังน้ำมันที่อยู่ในรัศมีจะระเบิดตาม
        chain = [o for o in self.obstacles
                 if o.kind == "barrel" and math.hypot(o.x - x, o.y - y) < radius + o.r]
        for o in chain:
            if o in self.obstacles:
                self.obstacles.remove(o)
                self.explode(o.x, o.y, 110, 8, hurt_player=True)

    def damage_zombie(self, z, dmg, kx, ky):
        z.hp -= dmg
        z.flash = 0.08
        # กระเด็นถอยหลังเล็กน้อย (บอสหนักกว่า กระเด็นน้อยกว่า)
        k = 0.3 if z.kind == "boss" else 1.0
        z.x += kx * k
        z.y += ky * k
        for _ in range(4):
            self.particles.append(Particle(z.x, z.y, "#7a1010"))
        if z.hp <= 0 and not z.dead:
            z.dead = True
            self.kill_zombie(z)

    def pick_zombie_kind(self):
        r = random.random()
        if self.wave >= 3 and r < min(0.15, 0.03 * self.wave):
            return "brute"
        if self.wave >= 2 and r < 0.35:
            return "runner"
        return "walker"

    def kill_zombie(self, z):
        self.score += z.score
        self.kills += 1
        n = 40 if z.kind == "boss" else 14
        for _ in range(n):
            self.particles.append(Particle(z.x, z.y, random.choice(["#7a1010", z.color])))
        if z.kind == "boss":
            self.shake = max(self.shake, 18)
            for _ in range(3):
                self.pickups.append(Pickup(z.x + random.uniform(-30, 30), z.y + random.uniform(-30, 30)))
        elif random.random() < 0.08:
            self.pickups.append(Pickup(z.x, z.y))

    def aim_angle(self):
        return math.atan2(self.mouse_y - self.py, self.mouse_x - self.px)

    # ---------- draw ----------
    def draw(self):
        c = self.canvas
        c.delete("all")
        if self.state == "menu":
            self.draw_menu()
            self.draw_crosshair()
            return

        self.draw_ground()
        for o in self.obstacles:
            self.draw_obstacle(o)

        for p in self.pickups:
            if p.life > 3 or int(p.life * 8) % 2 == 0:
                c.create_rectangle(p.x - 9, p.y - 9, p.x + 9, p.y + 9, fill="#eeeeee", outline="#aa0000", width=2)
                c.create_rectangle(p.x - 2, p.y - 6, p.x + 2, p.y + 6, fill="#cc0000", outline="")
                c.create_rectangle(p.x - 6, p.y - 2, p.x + 6, p.y + 2, fill="#cc0000", outline="")

        for p in self.particles:
            s = 2 + p.life * 4
            c.create_oval(p.x - s, p.y - s, p.x + s, p.y + s, fill=p.color, outline="")

        for z in self.zombies:
            self.draw_zombie(z)

        for b in self.bullets:
            if b.blast:
                c.create_oval(b.x - 5, b.y - 5, b.x + 5, b.y + 5, fill=b.color, outline="#2d4a20")
            else:
                c.create_line(b.x, b.y, b.x - b.vx * 0.02, b.y - b.vy * 0.02, fill=b.color, width=b.width)

        for x, y, r, life in self.blasts:
            rr = r * (1.1 - life / 0.3 * 0.6)
            c.create_oval(x - rr, y - rr, x + rr, y + rr, outline="#ffb340", width=4)
            if life > 0.2:
                c.create_oval(x - rr * 0.6, y - rr * 0.6, x + rr * 0.6, y + rr * 0.6, fill="#ffe08a", outline="")

        self.draw_player()

        # สั่นจอ: ขยับทุกอย่างในโลก ก่อนวาด HUD
        if self.shake > 0:
            c.move("all", random.uniform(-self.shake, self.shake), random.uniform(-self.shake, self.shake))

        self.draw_crosshair()
        self.draw_hud()

    def draw_ground(self):
        c = self.canvas
        m = self.map
        if self.map_idx == 1:
            # ถนนกลางเมือง
            c.create_rectangle(0, HEIGHT / 2 - 60, WIDTH, HEIGHT / 2 + 60, fill="#232327", outline="")
            for x in range(0, WIDTH, 60):
                c.create_rectangle(x, HEIGHT / 2 - 3, x + 30, HEIGHT / 2 + 3, fill="#8a7a3a", outline="")
        for gx, gy, r in self.ground:
            c.create_oval(gx - r, gy - r, gx + r, gy + r, fill=m["dot"], outline="")

    def draw_obstacle(self, o):
        c = self.canvas
        x, y, r = o.x, o.y, o.r
        c.create_oval(x - r + 4, y - r * 0.6 + 8, x + r + 4, y + r * 0.6 + 8, fill="#000000",
                      stipple="gray25", outline="")
        if o.kind == "tomb":
            c.create_rectangle(x - r * 0.7, y - r, x + r * 0.7, y + r, fill="#6e6e70", outline="#3c3c3e", width=2)
            c.create_line(x, y - r * 0.6, x, y + r * 0.3, fill="#3c3c3e", width=3)
            c.create_line(x - r * 0.35, y - r * 0.3, x + r * 0.35, y - r * 0.3, fill="#3c3c3e", width=3)
        elif o.kind == "barrel":
            c.create_oval(x - r, y - r, x + r, y + r, fill="#a8441e", outline="#4a1c0a", width=2)
            c.create_oval(x - r * 0.6, y - r * 0.6, x + r * 0.6, y + r * 0.6, outline="#d76a2e", width=2)
            c.create_text(x, y, text="!", fill="#ffd34a", font=("Tahoma", int(r * 0.8), "bold"))
        elif o.kind == "crate":
            s = r * 0.85
            c.create_rectangle(x - s, y - s, x + s, y + s, fill="#8b6a3e", outline="#4a3720", width=2)
            c.create_line(x - s, y - s, x + s, y + s, fill="#5c4528", width=2)
            c.create_line(x - s, y + s, x + s, y - s, fill="#5c4528", width=2)
        elif o.kind == "tree":
            c.create_oval(x - r, y - r, x + r, y + r, fill="#1d4027", outline="#0f2416", width=2)
            c.create_oval(x - r * 0.6 - 4, y - r * 0.6 - 4, x + r * 0.6 - 4, y + r * 0.6 - 4,
                          fill="#2b5e35", outline="")
            c.create_oval(x - r * 0.25 - 6, y - r * 0.25 - 6, x + r * 0.25 - 6, y + r * 0.25 - 6,
                          fill="#3a7444", outline="")
        else:  # rock
            c.create_oval(x - r, y - r * 0.85, x + r, y + r * 0.85, fill="#5b5f5a", outline="#2e302d", width=2)
            c.create_oval(x - r * 0.5, y - r * 0.6, x + r * 0.2, y - r * 0.1, fill="#727670", outline="")

    def draw_zombie(self, z):
        c = self.canvas
        ang = math.atan2(self.py - z.y, self.px - z.x)
        r = z.radius
        # แขนยื่นไปข้างหน้า
        for side in (-1, 1):
            sx = z.x + math.cos(ang + side * 0.9) * r * 0.8
            sy = z.y + math.sin(ang + side * 0.9) * r * 0.8
            ex = sx + math.cos(ang) * r * 0.9
            ey = sy + math.sin(ang) * r * 0.9
            c.create_line(sx, sy, ex, ey, fill=z.color, width=max(4, r // 3), capstyle="round")
        fill = "#ffffff" if z.flash > 0 else z.color
        c.create_oval(z.x - r, z.y - r, z.x + r, z.y + r, fill=fill, outline="#1b2a12", width=2)
        if z.kind == "boss":
            # เขาบนหัวบอส
            for side in (-1, 1):
                bx = z.x + math.cos(ang + side * 1.2) * r * 0.8
                by = z.y + math.sin(ang + side * 1.2) * r * 0.8
                tx = z.x + math.cos(ang + side * 0.8) * r * 1.35
                ty = z.y + math.sin(ang + side * 0.8) * r * 1.35
                c.create_line(bx, by, tx, ty, fill="#d8d0c0", width=5, capstyle="round")
        # ตาแดง
        eye = 4 if z.kind == "boss" else 2.5
        for side in (-1, 1):
            ex = z.x + math.cos(ang + side * 0.45) * r * 0.55
            ey = z.y + math.sin(ang + side * 0.45) * r * 0.55
            c.create_oval(ex - eye, ey - eye, ex + eye, ey + eye, fill="#ff2a2a", outline="")
        if z.hp < z.max_hp and z.kind != "boss":
            w = r * 2
            c.create_rectangle(z.x - r, z.y - r - 9, z.x - r + w, z.y - r - 5, fill="#400", outline="")
            c.create_rectangle(z.x - r, z.y - r - 9, z.x - r + w * z.hp / z.max_hp, z.y - r - 5,
                               fill="#e03b3b", outline="")

    def draw_player(self):
        c = self.canvas
        ang = self.aim_angle()
        x, y, r = self.px, self.py, PLAYER_RADIUS
        # ความยาว/ความหนาปืนต่างกันตามอาวุธ
        length = {0: 10, 1: 16, 2: 14, 3: 22, 4: 14}[self.weapon_idx]
        thick = {0: 4, 1: 5, 2: 6, 3: 4, 4: 8}[self.weapon_idx]
        gx = x + math.cos(ang) * (r + length)
        gy = y + math.sin(ang) * (r + length)
        c.create_line(x, y, gx, gy, fill="#333", width=thick + 3)
        c.create_line(x, y, gx, gy, fill="#666", width=thick)
        if self.muzzle > 0:
            c.create_oval(gx - 7, gy - 7, gx + 7, gy + 7, fill="#fff2a0", outline="")
        if self.dash_time > 0:
            body = "#bfe0ff"
        elif self.hurt_timer > 0:
            body = "#ff6b6b"
        else:
            body = "#4a90d9"
        c.create_oval(x - r, y - r, x + r, y + r, fill=body, outline="#1c3c5e", width=2)
        hx = x + math.cos(ang) * 4
        hy = y + math.sin(ang) * 4
        c.create_oval(hx - 7, hy - 7, hx + 7, hy + 7, fill="#f1c89b", outline="#8a6a45")

    def draw_crosshair(self):
        c = self.canvas
        mx, my = self.mouse_x, self.mouse_y
        col = "#ff5555" if self.state == "play" and self.reload_timer > 0 else "#ffffff"
        c.create_oval(mx - 10, my - 10, mx + 10, my + 10, outline=col, width=2)
        c.create_line(mx - 16, my, mx - 5, my, fill=col, width=2)
        c.create_line(mx + 5, my, mx + 16, my, fill=col, width=2)
        c.create_line(mx, my - 16, mx, my - 5, fill=col, width=2)
        c.create_line(mx, my + 5, mx, my + 16, fill=col, width=2)

    def draw_hud(self):
        c = self.canvas
        font = ("Tahoma", 13, "bold")
        w = self.weapon

        # หลอดเลือด
        c.create_rectangle(20, 20, 240, 40, fill="#3a0d0d", outline="#000")
        hp_col = "#3fcf5a" if self.hp > 50 else "#e0c13b" if self.hp > 25 else "#e03b3b"
        c.create_rectangle(20, 20, 20 + 220 * self.hp / PLAYER_MAX_HP, 40, fill=hp_col, outline="")
        c.create_text(130, 30, text=f"HP {int(self.hp)}", fill="white", font=("Tahoma", 10, "bold"))

        # อาวุธ + กระสุน
        c.create_text(20, 56, text=w["th"], anchor="w", fill="#dddddd", font=("Tahoma", 11))
        if self.reload_timer > 0:
            ammo_text = "กำลังรีโหลด..."
            prog = 1 - self.reload_timer / w["reload"]
            c.create_rectangle(20, 92, 20 + 160 * prog, 96, fill="#ffe27a", outline="")
        else:
            ammo_text = f"กระสุน {self.ammo}/{w['mag']}"
        c.create_text(20, 78, text=ammo_text, anchor="w", fill="#ffe27a", font=font)

        # Dash
        ready = self.dash_cd <= 0
        c.create_text(20, 112, text="Dash [Space]", anchor="w",
                      fill="#7fb3e8" if ready else "#556677", font=("Tahoma", 10, "bold"))
        c.create_rectangle(110, 107, 190, 117, outline="#556677")
        c.create_rectangle(110, 107, 110 + 80 * (1 - self.dash_cd / DASH_COOLDOWN), 117,
                           fill="#7fb3e8", outline="")

        c.create_text(WIDTH - 20, 22, text=f"คะแนน {self.score}", anchor="e", fill="white", font=font)
        c.create_text(WIDTH - 20, 46, text=f"Wave {self.wave}  ·  {self.map['name']}", anchor="e",
                      fill="#9bc43a", font=font)
        c.create_text(WIDTH - 20, 70, text=f"ซอมบี้เหลือ {self.to_spawn + len(self.zombies)}",
                      anchor="e", fill="#bbbbbb", font=("Tahoma", 11))

        # หลอดเลือดบอส
        boss = next((z for z in self.zombies if z.kind == "boss"), None)
        if boss:
            bw = 360
            x1 = WIDTH / 2 - bw / 2
            c.create_text(WIDTH / 2, HEIGHT - 52, text="☠ ราชาซอมบี้ ☠", fill="#d8b0ff",
                          font=("Tahoma", 12, "bold"))
            c.create_rectangle(x1, HEIGHT - 40, x1 + bw, HEIGHT - 26, fill="#2a1438", outline="#000")
            c.create_rectangle(x1, HEIGHT - 40, x1 + bw * max(0, boss.hp) / boss.max_hp, HEIGHT - 26,
                               fill="#a35cd6", outline="")

        if self.wave_banner > 0 and self.state == "play":
            c.create_text(WIDTH / 2, HEIGHT / 3, text=f"WAVE {self.wave}",
                          fill="#d4f07a", font=("Tahoma", 40, "bold"))
            if self.wave % 5 == 0:
                c.create_text(WIDTH / 2, HEIGHT / 3 + 45, text="บอสมาแล้ว!",
                              fill="#d8b0ff", font=("Tahoma", 20, "bold"))

        if self.paused:
            self.overlay("หยุดชั่วคราว", "กด P เพื่อเล่นต่อ")
        elif self.state == "over":
            record = "★ สถิติใหม่! ★" if self.new_record else f"สถิติสูงสุด {self.high_score}"
            self.overlay("GAME OVER",
                         f"คะแนน {self.score}   ฆ่าไป {self.kills} ตัว   ถึง Wave {self.wave}\n"
                         f"{record}\n\nEnter = เล่นใหม่     M = กลับเมนู")

    def draw_menu(self):
        c = self.canvas
        c.config(bg="#15160f")
        self.menu_buttons = []
        c.create_text(WIDTH / 2, 58, text="ZOMBIE SHOOTER", fill="#d4f07a", font=("Tahoma", 42, "bold"))
        c.create_text(WIDTH / 2, 100, text=f"สถิติสูงสุด {self.high_score}", fill="#999999",
                      font=("Tahoma", 11))

        # การ์ดเลือกอาวุธ
        c.create_text(31, 135, text="เลือกอาวุธ  [1-5]", anchor="w", fill="white", font=("Tahoma", 14, "bold"))
        cw, ch, gap = 170, 230, 12
        top = 152
        for i, w in enumerate(WEAPONS):
            x1 = 31 + i * (cw + gap)
            sel = i == self.weapon_idx
            c.create_rectangle(x1, top, x1 + cw, top + ch, fill="#2f3a22" if sel else "#22241c",
                               outline="#d4f07a" if sel else "#4a4c40", width=3 if sel else 1)
            c.create_text(x1 + 10, top + 14, text=str(i + 1), anchor="w", fill="#888", font=("Tahoma", 10, "bold"))
            c.create_text(x1 + cw / 2, top + 34, text=w["th"], fill="white", font=("Tahoma", 13, "bold"))
            c.create_text(x1 + cw / 2, top + 55, text=w["name"], fill="#999", font=("Tahoma", 9))
            # รูปปืนแบบง่าย
            gl = 30 + w["range"] * 10 + (20 if w["pierce"] else 0)
            gt = 4 + w["pellets"] // 2 + (5 if w["blast"] else 0)
            c.create_line(x1 + cw / 2 - gl / 2, top + 82, x1 + cw / 2 + gl / 2, top + 82,
                          fill="#777", width=gt + 2, capstyle="round")
            c.create_line(x1 + cw / 2 - gl / 2 + 4, top + 82, x1 + cw / 2 - gl / 2 + 4, top + 94,
                          fill="#777", width=5)
            c.create_text(x1 + cw / 2, top + 120, text=w["desc"], fill="#cccccc",
                          font=("Tahoma", 10), justify="center")
            power = min(1.0, (w["dmg"] * w["pellets"] + (3 if w["blast"] else 0)) / 8)
            rate = min(1.0, (1 / w["delay"]) / 11)
            mag = min(1.0, w["mag"] / 30)
            for j, (label, val, col) in enumerate((("พลัง", power, "#e05a3b"),
                                                   ("ยิงเร็ว", rate, "#e0c13b"),
                                                   ("กระสุน", mag, "#3fb0cf"))):
                yy = top + 160 + j * 20
                c.create_text(x1 + 12, yy, text=label, anchor="w", fill="#aaa", font=("Tahoma", 9))
                c.create_rectangle(x1 + 62, yy - 4, x1 + cw - 12, yy + 4, fill="#111", outline="")
                c.create_rectangle(x1 + 62, yy - 4, x1 + 62 + (cw - 74) * val, yy + 4, fill=col, outline="")
            self.menu_buttons.append((x1, top, x1 + cw, top + ch, lambda i=i: setattr(self, "weapon_idx", i)))

        # เลือกฉาก
        c.create_text(31, 410, text="เลือกฉาก  [← →]", anchor="w", fill="white", font=("Tahoma", 14, "bold"))
        mw, mh, mgap = 286, 100, 15
        mtop = 428
        for i, m in enumerate(MAPS):
            x1 = 31 + i * (mw + mgap)
            sel = i == self.map_idx
            c.create_rectangle(x1, mtop, x1 + mw, mtop + mh, fill=m["bg"],
                               outline="#d4f07a" if sel else "#4a4c40", width=3 if sel else 1)
            # ตัวอย่างสิ่งกีดขวางเล็ก ๆ
            for k, kind in enumerate(m["obstacles"][:3]):
                self.draw_obstacle(Obstacle(x1 + mw - 30 - k * 36, mtop + mh / 2, 12, kind))
            c.create_text(x1 + 14, mtop + 26, text=m["name"], anchor="w", fill="white",
                          font=("Tahoma", 14, "bold"))
            c.create_text(x1 + 14, mtop + 66, text=m["desc"], anchor="w", fill="#cccccc",
                          font=("Tahoma", 9), justify="left")
            self.menu_buttons.append((x1, mtop, x1 + mw, mtop + mh, lambda i=i: setattr(self, "map_idx", i)))

        # ปุ่มเริ่ม
        bx1, by1, bx2, by2 = WIDTH / 2 - 130, 552, WIDTH / 2 + 130, 600
        hover = bx1 <= self.mouse_x <= bx2 and by1 <= self.mouse_y <= by2
        c.create_rectangle(bx1, by1, bx2, by2, fill="#6a9a2e" if hover else "#4f7a22",
                           outline="#d4f07a", width=2)
        c.create_text(WIDTH / 2, (by1 + by2) / 2, text="เริ่มเกม  (Enter)", fill="white",
                      font=("Tahoma", 16, "bold"))
        self.menu_buttons.append((bx1, by1, bx2, by2, self.start_game))
        c.create_text(WIDTH / 2, 622, text="WASD เดิน · เมาส์เล็ง/ยิง · Space พุ่งหลบ · R รีโหลด · P หยุด",
                      fill="#777", font=("Tahoma", 10))

    def overlay(self, title, sub):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#000000", stipple="gray50", outline="")
        c.create_text(WIDTH / 2, HEIGHT / 2 - 50, text=title, fill="#ff4444", font=("Tahoma", 44, "bold"))
        c.create_text(WIDTH / 2, HEIGHT / 2 + 30, text=sub, fill="white",
                      font=("Tahoma", 15), justify="center")

    def loop(self):
        self.update()
        self.draw()
        self.root.after(int(1000 / FPS), self.loop)


if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()

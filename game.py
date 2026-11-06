"""Zombie Top-down Shooter (tkinter)
พัฒนาโดย: nitithon
ควบคุม:
    W A S D / ลูกศร  - เดิน
    เมาส์             - เล็ง
    คลิกซ้าย (ค้างได้) - ยิง
    R                 - รีโหลด
    P                 - หยุดเกมชั่วคราว
    Enter             - เริ่มใหม่หลังจบเกม
"""

import math
import random
import sys
import tkinter as tk

WIDTH, HEIGHT = 960, 640
FPS = 60
DT = 1 / FPS

PLAYER_SPEED = 230
PLAYER_RADIUS = 14
PLAYER_MAX_HP = 100

BULLET_SPEED = 720
BULLET_RADIUS = 4
FIRE_DELAY = 0.12
MAG_SIZE = 20
RELOAD_TIME = 1.2

# ชนิดซอมบี้: ความเร็ว, เลือด, รัศมี, ดาเมจต่อวินาที, คะแนน, สี
ZOMBIE_TYPES = {
    "walker": dict(speed=70, hp=3, radius=15, dps=20, score=10, color="#5a8f3c"),
    "runner": dict(speed=135, hp=2, radius=12, dps=15, score=15, color="#9bc43a"),
    "brute": dict(speed=45, hp=12, radius=24, dps=40, score=40, color="#3d5e2a"),
}

# keycode บน Windows ไม่ขึ้นกับภาษาแป้นพิมพ์ ทำให้เล่นได้แม้สลับเป็นภาษาไทย
WIN_KEYCODES = {87: "w", 65: "a", 83: "s", 68: "d", 82: "r", 80: "p"}


class Bullet:
    def __init__(self, x, y, angle):
        self.x, self.y = x, y
        self.vx = math.cos(angle) * BULLET_SPEED
        self.vy = math.sin(angle) * BULLET_SPEED
        self.alive = True

    def update(self):
        self.x += self.vx * DT
        self.y += self.vy * DT
        if not (-20 < self.x < WIDTH + 20 and -20 < self.y < HEIGHT + 20):
            self.alive = False


class Zombie:
    def __init__(self, kind, wave):
        spec = ZOMBIE_TYPES[kind]
        self.kind = kind
        self.speed = spec["speed"] * (1 + 0.04 * (wave - 1))
        self.max_hp = spec["hp"] + (wave - 1) // 3
        self.hp = self.max_hp
        self.radius = spec["radius"]
        self.dps = spec["dps"]
        self.score = spec["score"]
        self.color = spec["color"]
        self.flash = 0.0
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


class Pickup:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.life = 10.0
        self.radius = 10


class Particle:
    def __init__(self, x, y, color):
        a = random.uniform(0, math.tau)
        s = random.uniform(60, 220)
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
        self.high_score = 0

        # จุดตกแต่งพื้น สุ่มครั้งเดียว
        self.ground = [(random.uniform(0, WIDTH), random.uniform(0, HEIGHT),
                        random.uniform(2, 6)) for _ in range(90)]

        root.bind("<KeyPress>", self.on_key_down)
        root.bind("<KeyRelease>", self.on_key_up)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.reset()
        self.loop()

    # ---------- state ----------
    def reset(self):
        self.px, self.py = WIDTH / 2, HEIGHT / 2
        self.hp = PLAYER_MAX_HP
        self.score = 0
        self.kills = 0
        self.ammo = MAG_SIZE
        self.reload_timer = 0.0
        self.fire_cooldown = 0.0
        self.hurt_timer = 0.0
        self.bullets = []
        self.zombies = []
        self.pickups = []
        self.particles = []
        self.wave = 0
        self.to_spawn = 0
        self.spawn_timer = 0.0
        self.wave_banner = 0.0
        self.paused = False
        self.game_over = False
        self.next_wave()

    def next_wave(self):
        self.wave += 1
        self.to_spawn = 6 + self.wave * 4
        self.spawn_timer = 1.5
        self.wave_banner = 2.0

    # ---------- input ----------
    def key_name(self, event):
        if sys.platform == "win32" and event.keycode in WIN_KEYCODES:
            return WIN_KEYCODES[event.keycode]
        return event.keysym.lower()

    def on_key_down(self, event):
        k = self.key_name(event)
        self.keys.add(k)
        if k == "r":
            self.start_reload()
        elif k == "p" and not self.game_over:
            self.paused = not self.paused
        elif k == "return" and self.game_over:
            self.reset()

    def on_key_up(self, event):
        self.keys.discard(self.key_name(event))

    def on_motion(self, event):
        self.mouse_x, self.mouse_y = event.x, event.y

    def on_mouse_down(self, event):
        self.mouse_down = True
        self.on_motion(event)

    def on_mouse_up(self, _event):
        self.mouse_down = False

    def start_reload(self):
        if self.reload_timer <= 0 and self.ammo < MAG_SIZE and not self.game_over:
            self.reload_timer = RELOAD_TIME

    # ---------- update ----------
    def update(self):
        if self.game_over or self.paused:
            return

        # เดิน
        dx = ("d" in self.keys or "right" in self.keys) - ("a" in self.keys or "left" in self.keys)
        dy = ("s" in self.keys or "down" in self.keys) - ("w" in self.keys or "up" in self.keys)
        if dx or dy:
            n = math.hypot(dx, dy)
            self.px += dx / n * PLAYER_SPEED * DT
            self.py += dy / n * PLAYER_SPEED * DT
        self.px = min(max(self.px, PLAYER_RADIUS), WIDTH - PLAYER_RADIUS)
        self.py = min(max(self.py, PLAYER_RADIUS), HEIGHT - PLAYER_RADIUS)

        # รีโหลด / ยิง
        if self.reload_timer > 0:
            self.reload_timer -= DT
            if self.reload_timer <= 0:
                self.ammo = MAG_SIZE
        self.fire_cooldown = max(0.0, self.fire_cooldown - DT)
        if self.mouse_down and self.fire_cooldown <= 0 and self.reload_timer <= 0:
            if self.ammo > 0:
                angle = self.aim_angle() + random.uniform(-0.04, 0.04)
                gx = self.px + math.cos(angle) * 22
                gy = self.py + math.sin(angle) * 22
                self.bullets.append(Bullet(gx, gy, angle))
                self.ammo -= 1
                self.fire_cooldown = FIRE_DELAY
            else:
                self.start_reload()

        for b in self.bullets:
            b.update()

        # เกิดซอมบี้
        if self.to_spawn > 0:
            self.spawn_timer -= DT
            if self.spawn_timer <= 0:
                self.zombies.append(Zombie(self.pick_zombie_kind(), self.wave))
                self.to_spawn -= 1
                self.spawn_timer = max(0.25, 1.0 - self.wave * 0.06) * random.uniform(0.6, 1.2)
        elif not self.zombies:
            self.next_wave()

        # ซอมบี้เดิน + ทำดาเมจ
        for z in self.zombies:
            dist = z.update(self.px, self.py)
            if dist < z.radius + PLAYER_RADIUS:
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
                if z.hp > 0 and math.hypot(b.x - z.x, b.y - z.y) < z.radius + BULLET_RADIUS:
                    b.alive = False
                    z.hp -= 1
                    z.flash = 0.08
                    # กระเด็นถอยหลังเล็กน้อย
                    z.x += b.vx * 0.008
                    z.y += b.vy * 0.008
                    for _ in range(4):
                        self.particles.append(Particle(b.x, b.y, "#7a1010"))
                    if z.hp <= 0:
                        self.kill_zombie(z)
                    break

        self.bullets = [b for b in self.bullets if b.alive]
        self.zombies = [z for z in self.zombies if z.hp > 0]

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

        self.hurt_timer = max(0.0, self.hurt_timer - DT)
        self.wave_banner = max(0.0, self.wave_banner - DT)

        if self.hp <= 0:
            self.hp = 0
            self.game_over = True
            self.high_score = max(self.high_score, self.score)

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
        for _ in range(14):
            self.particles.append(Particle(z.x, z.y, random.choice(["#7a1010", z.color])))
        if random.random() < 0.08:
            self.pickups.append(Pickup(z.x, z.y))

    def aim_angle(self):
        return math.atan2(self.mouse_y - self.py, self.mouse_x - self.px)

    # ---------- draw ----------
    def draw(self):
        c = self.canvas
        c.delete("all")

        for gx, gy, r in self.ground:
            c.create_oval(gx - r, gy - r, gx + r, gy + r, fill="#26281f", outline="")

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
            c.create_line(b.x, b.y, b.x - b.vx * 0.02, b.y - b.vy * 0.02, fill="#ffe27a", width=3)

        self.draw_player()
        self.draw_crosshair()
        self.draw_hud()

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
        # ตาแดง
        for side in (-1, 1):
            ex = z.x + math.cos(ang + side * 0.45) * r * 0.55
            ey = z.y + math.sin(ang + side * 0.45) * r * 0.55
            c.create_oval(ex - 2.5, ey - 2.5, ex + 2.5, ey + 2.5, fill="#ff2a2a", outline="")
        if z.hp < z.max_hp:
            w = r * 2
            c.create_rectangle(z.x - r, z.y - r - 9, z.x - r + w, z.y - r - 5, fill="#400", outline="")
            c.create_rectangle(z.x - r, z.y - r - 9, z.x - r + w * z.hp / z.max_hp, z.y - r - 5,
                               fill="#e03b3b", outline="")

    def draw_player(self):
        c = self.canvas
        ang = self.aim_angle()
        x, y, r = self.px, self.py, PLAYER_RADIUS
        gx = x + math.cos(ang) * (r + 12)
        gy = y + math.sin(ang) * (r + 12)
        c.create_line(x, y, gx, gy, fill="#333", width=7)
        c.create_line(x, y, gx, gy, fill="#666", width=4)
        body = "#ff6b6b" if self.hurt_timer > 0 else "#4a90d9"
        c.create_oval(x - r, y - r, x + r, y + r, fill=body, outline="#1c3c5e", width=2)
        hx = x + math.cos(ang) * 4
        hy = y + math.sin(ang) * 4
        c.create_oval(hx - 7, hy - 7, hx + 7, hy + 7, fill="#f1c89b", outline="#8a6a45")

    def draw_crosshair(self):
        c = self.canvas
        mx, my = self.mouse_x, self.mouse_y
        col = "#ff5555" if self.reload_timer > 0 else "#ffffff"
        c.create_oval(mx - 10, my - 10, mx + 10, my + 10, outline=col, width=2)
        c.create_line(mx - 16, my, mx - 5, my, fill=col, width=2)
        c.create_line(mx + 5, my, mx + 16, my, fill=col, width=2)
        c.create_line(mx, my - 16, mx, my - 5, fill=col, width=2)
        c.create_line(mx, my + 5, mx, my + 16, fill=col, width=2)

    def draw_hud(self):
        c = self.canvas
        font = ("Tahoma", 13, "bold")

        # หลอดเลือด
        c.create_rectangle(20, 20, 240, 40, fill="#3a0d0d", outline="#000")
        hp_col = "#3fcf5a" if self.hp > 50 else "#e0c13b" if self.hp > 25 else "#e03b3b"
        c.create_rectangle(20, 20, 20 + 220 * self.hp / PLAYER_MAX_HP, 40, fill=hp_col, outline="")
        c.create_text(130, 30, text=f"HP {int(self.hp)}", fill="white", font=("Tahoma", 10, "bold"))

        # กระสุน
        if self.reload_timer > 0:
            ammo_text = "กำลังรีโหลด..."
            prog = 1 - self.reload_timer / RELOAD_TIME
            c.create_rectangle(20, 74, 20 + 160 * prog, 78, fill="#ffe27a", outline="")
        else:
            ammo_text = f"กระสุน {self.ammo}/{MAG_SIZE}"
        c.create_text(20, 58, text=ammo_text, anchor="w", fill="#ffe27a", font=font)

        c.create_text(WIDTH - 20, 22, text=f"คะแนน {self.score}", anchor="e", fill="white", font=font)
        c.create_text(WIDTH - 20, 46, text=f"Wave {self.wave}", anchor="e", fill="#9bc43a", font=font)
        c.create_text(WIDTH - 20, 70, text=f"ซอมบี้เหลือ {self.to_spawn + len(self.zombies)}",
                      anchor="e", fill="#bbbbbb", font=("Tahoma", 11))

        if self.wave_banner > 0 and not self.game_over:
            c.create_text(WIDTH / 2, HEIGHT / 3, text=f"WAVE {self.wave}",
                          fill="#d4f07a", font=("Tahoma", 40, "bold"))

        if self.paused:
            self.overlay("หยุดชั่วคราว", "กด P เพื่อเล่นต่อ")
        elif self.game_over:
            self.overlay("GAME OVER",
                         f"คะแนน {self.score}   ฆ่าไป {self.kills} ตัว   ถึง Wave {self.wave}\n"
                         f"สถิติสูงสุด {self.high_score}\n\nกด Enter เพื่อเล่นใหม่")

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

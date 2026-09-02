import pygame
import sys
import math
import random
import os
import io
import wave
import struct
import time

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Screen dimensions
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 600
FPS = 60

# Playable pitch bounds (top and bottom)
FIELD_TOP = 150
FIELD_BOTTOM = SCREEN_HEIGHT - 20

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
GREEN = (34, 139, 34)
DARK_GREEN = (20, 90, 20)
SEAT_COLOR = (50, 50, 80)
LIGHTS = (255, 240, 200)
HIGHLIGHT = (255, 220, 80)

# Paddle dimensions
PADDLE_WIDTH = 15
PADDLE_HEIGHT = 100
PADDLE_SPEED = 6

# Ball dimensions
BALL_SIZE = 14  # used as diameter for drawing circle
BALL_SPEED = 5
BALL_RADIUS = BALL_SIZE // 2

# Lives
MAX_LIVES = 5

# Files
HIGHSCORE_FILE = "highscore.txt"

# Game setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pong Game - Stadium Edition")
clock = pygame.time.Clock()
font_score = pygame.font.Font(None, 74)
font_info = pygame.font.Font(None, 36)
font_big = pygame.font.Font(None, 96)
font_large = pygame.font.Font(None, 140)


# -- Highscore persistence (file-based) --
def load_highscore():
    try:
        if os.path.exists(HIGHSCORE_FILE):
            with open(HIGHSCORE_FILE, "r") as f:
                return int(f.read().strip() or 0)
    except Exception:
        pass
    return 0


def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(int(score)))
    except Exception:
        pass


def clear_highscore():
    try:
        if os.path.exists(HIGHSCORE_FILE):
            os.remove(HIGHSCORE_FILE)
    except Exception:
        pass


# -- Simple in-memory WAV generator to avoid external assets --
def make_sine_wav(freq=440.0, duration_ms=120, volume=0.5, sample_rate=44100):
    """Generate a WAV in-memory for a sine tone and return bytes."""
    n_samples = int(sample_rate * (duration_ms / 1000.0))
    buf = io.BytesIO()
    wav = wave.open(buf, 'wb')
    wav.setnchannels(1)
    wav.setsampwidth(2)
    wav.setframerate(sample_rate)
    max_amp = 32767 * volume
    for i in range(n_samples):
        t = float(i) / sample_rate
        sample = int(max_amp * math.sin(2.0 * math.pi * freq * t))
        wav.writeframes(struct.pack('<h', sample))
    wav.close()
    buf.seek(0)
    return buf


def make_sound(freq=440.0, duration_ms=120, volume=0.5):
    buf = make_sine_wav(freq, duration_ms, volume)
    try:
        return pygame.mixer.Sound(file=buf)
    except Exception:
        # Fallback silent sound
        return None


class Paddle:
    def __init__(self, x, y, color=WHITE, stripe_color=None):
        self.rect = pygame.Rect(x, y, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.speed = PADDLE_SPEED
        self.color = color
        # stripe color default to a contrasting color
        self.stripe_color = stripe_color if stripe_color is not None else (255 - color[0], 255 - color[1], 255 - color[2])

    def draw(self, surface):
        # Draw paddle with a main color and a colorful stripe to look more realistic
        pygame.draw.rect(surface, self.color, self.rect)
        # Draw a central vertical stripe
        stripe_rect = pygame.Rect(self.rect.x + 3, self.rect.y + 10, max(4, self.rect.width - 6), self.rect.height - 20)
        pygame.draw.rect(surface, self.stripe_color, stripe_rect)

    def move_up(self):
        if self.rect.top > FIELD_TOP:
            self.rect.y -= self.speed

    def move_down(self):
        if self.rect.bottom < FIELD_BOTTOM:
            self.rect.y += self.speed

    def set_position(self, y):
        """Set paddle position constrained inside the pitch (FIELD_TOP..FIELD_BOTTOM)"""
        self.rect.y = max(FIELD_TOP, min(y, FIELD_BOTTOM - PADDLE_HEIGHT))


class Ball:
    def __init__(self, speed_multiplier=1.0):
        center_y = (FIELD_TOP + FIELD_BOTTOM) // 2
        self.rect = pygame.Rect(SCREEN_WIDTH // 2 - BALL_RADIUS, center_y - BALL_RADIUS, BALL_SIZE, BALL_SIZE)
        self.base_speed = BALL_SPEED
        self.speed_multiplier = speed_multiplier
        self.velocity_x = self.base_speed * self.speed_multiplier * random.choice([-1, 1])
        self.velocity_y = self.base_speed * self.speed_multiplier * random.choice([-1, 1])

    def draw(self, surface):
        # Draw a round ball using circle centered on rect
        center = (self.rect.centerx, self.rect.centery)
        pygame.draw.circle(surface, WHITE, center, BALL_RADIUS)

    def update(self):
        self.rect.x += int(self.velocity_x)
        self.rect.y += int(self.velocity_y)

        # Bounce off pitch top and bottom
        if self.rect.top <= FIELD_TOP or self.rect.bottom >= FIELD_BOTTOM:
            self.velocity_y *= -1
            self.rect.y = max(FIELD_TOP, min(self.rect.y, FIELD_BOTTOM - BALL_SIZE))
            return 'wall'
        return None

    def reset(self, speed_multiplier=1.0, away_from=None):
        """Reset ball to center of the pitch"""
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.centery = (FIELD_TOP + FIELD_BOTTOM) // 2
        self.speed_multiplier = speed_multiplier
        # Give the ball an initial X direction away from last scorer at random
        dir_choice = random.choice([-1, 1])
        if away_from == 'player':
            dir_choice = -1
        elif away_from == 'computer':
            dir_choice = 1
        self.velocity_x = self.base_speed * self.speed_multiplier * dir_choice
        # small random Y
        self.velocity_y = self.base_speed * self.speed_multiplier * random.choice([-1, 1]) * 0.5

    def check_paddle_collision(self, paddle):
        """Check collision with paddle and adjust velocity"""
        if self.rect.colliderect(paddle.rect):
            # Determine collision side
            if self.velocity_x > 0:  # Ball moving right
                self.rect.right = paddle.rect.left
                self.velocity_x *= -1
            else:  # Ball moving left
                self.rect.left = paddle.rect.right
                self.velocity_x *= -1

            # Add spin based on where ball hits paddle
            hit_pos = (self.rect.centery - paddle.rect.centery) / (PADDLE_HEIGHT / 2)
            hit_pos = max(-1, min(1, hit_pos))  # Clamp between -1 and 1
            self.velocity_y += hit_pos * 3

            # Slightly increase speed to keep game dynamic
            if abs(self.velocity_x) < 12:
                self.velocity_x *= 1.03
            return True
        return False


def draw_stadium(surface):
    """Draw a stylized stadium background: smaller stands, bigger pitch"""
    # Sky / top background
    surface.fill((30, 35, 45))

    # Smaller stands (left and right)
    stand_height = 80
    stand_top = 40
    for i in range(4):
        y = stand_top + i * (stand_height // 4)
        color = (40 + i * 6, 40 + i * 6, 60 + i * 8)
        pygame.draw.rect(surface, color, (0, y, SCREEN_WIDTH, stand_height // 4))

    # Crowd as small rectangles in gradient (reduced size)
    rows = 4
    cols = 60
    start_y = stand_top + 6
    row_height = 16
    for r in range(rows):
        for c in range(cols):
            x = int(c * (SCREEN_WIDTH / cols))
            y = start_y + r * row_height
            shade = 60 + (r * 20) + (c % 3) * 10
            pygame.draw.rect(surface, (shade, max(0, shade - 20), min(255, shade + 10)), (x, y, int(SCREEN_WIDTH / cols) - 2, row_height - 4))

    # Field (bigger pitch)
    pygame.draw.rect(surface, DARK_GREEN, (0, FIELD_TOP, SCREEN_WIDTH, FIELD_BOTTOM - FIELD_TOP))
    pygame.draw.rect(surface, GREEN, (60, FIELD_TOP + 20, SCREEN_WIDTH - 120, FIELD_BOTTOM - FIELD_TOP - 40))

    # Field markings
    center_x = SCREEN_WIDTH // 2
    pygame.draw.line(surface, WHITE, (center_x, FIELD_TOP + 20), (center_x, FIELD_BOTTOM - 20), 4)
    pygame.draw.circle(surface, WHITE, (center_x, (FIELD_TOP + FIELD_BOTTOM) // 2), 60, 4)

    # Flood lights
    light_positions = [(80, 40), (SCREEN_WIDTH - 80, 40), (SCREEN_WIDTH // 2, 20)]
    for lp in light_positions:
        pygame.draw.circle(surface, LIGHTS, lp, 18)
        for i in range(1, 6):
            pygame.draw.circle(surface, (255, 255 - i * 20, 200 - i * 10), lp, 18 + i * 8, 2)


class Game:
    def __init__(self):
        player_start_y = (FIELD_TOP + FIELD_BOTTOM) // 2 - PADDLE_HEIGHT // 2
        computer_start_y = player_start_y
        # More realistic/colorful paddles: wooden look with team stripe
        self.player_paddle = Paddle(20, player_start_y, color=(200, 160, 100), stripe_color=(30, 144, 255))
        self.computer_paddle = Paddle(SCREEN_WIDTH - PADDLE_WIDTH - 20, computer_start_y, color=(180, 100, 120), stripe_color=(220, 20, 60))
        # speed multiplier configurable in settings
        self.speed_multiplier = 1.0
        self.ball = Ball(speed_multiplier=self.speed_multiplier)
        self.player_score = 0
        self.computer_score = 0
        self.highscore = load_highscore()
        self.player_lives = MAX_LIVES
        self.paused = False
        self.game_over = False

        # UI state machine
        self.state = 'MENU'  # MENU, SETTINGS, COUNTDOWN, PLAYING, PAUSED, GAME_OVER

        # Menu UI elements
        self.menu_icon = self._make_icon_surface()
        self.btn_continue = pygame.Rect(SCREEN_WIDTH // 2 - 140, SCREEN_HEIGHT // 2 - 40, 280, 50)
        self.btn_new = pygame.Rect(SCREEN_WIDTH // 2 - 140, SCREEN_HEIGHT // 2 + 20, 280, 50)
        self.btn_settings = pygame.Rect(SCREEN_WIDTH // 2 - 140, SCREEN_HEIGHT // 2 + 80, 140, 40)
        self.btn_quit = pygame.Rect(SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT // 2 + 80, 140, 40)

        # Settings UI
        self.settings_slider_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 20, 400, 6)
        self.settings_knob_rect = pygame.Rect(0, 0, 14, 28)
        self.settings_min = 0.5
        self.settings_max = 3.0
        self._update_knob_position()
        self.btn_fastest = pygame.Rect(SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT // 2 + 40, 120, 36)
        self.btn_settings_back = pygame.Rect(20, 20, 100, 36)

        # Countdown
        self.countdown_start = None
        self.countdown_duration = 3.5  # includes 'Go'

        # Milestone animation
        self.milestone_timer = 0
        self.milestone_value = 0
        self.milestone_duration = 1.0

        # Sounds
        self.sfx_paddle = make_sound(freq=900.0, duration_ms=90, volume=0.6)
        self.sfx_wall = make_sound(freq=400.0, duration_ms=120, volume=0.5)

    def _make_icon_surface(self):
        surf = pygame.Surface((128, 128), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        pygame.draw.circle(surf, WHITE, (64, 64), 54)
        pygame.draw.circle(surf, DARK_GREEN, (64, 64), 48)
        pygame.draw.circle(surf, WHITE, (64, 64), 6)
        pygame.draw.rect(surf, (200, 160, 100), (12, 54, 18, 40))
        pygame.draw.rect(surf, (180, 100, 120), (98, 54, 18, 40))
        return surf

    def _update_knob_position(self):
        frac = (self.speed_multiplier - self.settings_min) / (self.settings_max - self.settings_min)
        x = int(self.settings_slider_rect.x + frac * self.settings_slider_rect.width)
        self.settings_knob_rect.center = (x, self.settings_slider_rect.centery)

    def handle_input(self):
        """Handle player input"""
        keys = pygame.key.get_pressed()
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # Mouse control for left paddle (constrained to pitch)
        if self.state in ('PLAYING', 'PAUSED'):
            self.player_paddle.set_position(mouse_y - PADDLE_HEIGHT // 2)

        # Arrow key control (alternative)
        if keys[pygame.K_UP]:
            self.player_paddle.move_up()
        if keys[pygame.K_DOWN]:
            self.player_paddle.move_down()

    def update_ai(self):
        """Update computer paddle AI"""
        paddle_center = self.computer_paddle.rect.centery
        ball_center = self.ball.rect.centery
        ai_speed = int(PADDLE_SPEED * 0.75)  # Slightly slower than player

        # AI tries to follow the ball but only inside the pitch
        if paddle_center < ball_center - 35:
            self.computer_paddle.rect.y += ai_speed
        elif paddle_center > ball_center + 35:
            self.computer_paddle.rect.y -= ai_speed

        # Keep paddle in pitch bounds
        self.computer_paddle.rect.y = max(FIELD_TOP, min(self.computer_paddle.rect.y, FIELD_BOTTOM - PADDLE_HEIGHT))

    def restart(self):
        self.player_score = 0
        self.computer_score = 0
        self.player_lives = MAX_LIVES
        self.ball.reset(speed_multiplier=self.speed_multiplier)
        self.game_over = False
        self.paused = False
        self.state = 'COUNTDOWN'
        self.countdown_start = time.time()

    def update(self):
        """Update game state"""
        if self.state == 'PLAYING':
            if self.paused or self.game_over:
                return

            wall_bounce = self.ball.update()
            if wall_bounce == 'wall':
                if self.sfx_wall:
                    self.sfx_wall.play()

            # Check paddle collisions
            if self.ball.check_paddle_collision(self.player_paddle):
                if self.sfx_paddle:
                    self.sfx_paddle.play()
            if self.ball.check_paddle_collision(self.computer_paddle):
                if self.sfx_paddle:
                    self.sfx_paddle.play()

            # Check if ball is out of bounds (left/right)
            if self.ball.rect.left < 0:
                # Computer scored against player -> lose a life
                self.computer_score += 1
                self.player_lives -= 1
                self.ball.reset(speed_multiplier=self.speed_multiplier, away_from='computer')
                if self.player_lives <= 0:
                    self.game_over = True
                    # update highscore
                    if self.player_score > self.highscore:
                        self.highscore = self.player_score
                        save_highscore(self.highscore)
                    self.state = 'GAME_OVER'
            elif self.ball.rect.right > SCREEN_WIDTH:
                # Player scored
                self.player_score += 1
                # Check milestone
                if self.player_score % 10 == 0:
                    self.milestone_value = self.player_score
                    self.milestone_timer = time.time()

                # Update highscore live
                if self.player_score > self.highscore:
                    self.highscore = self.player_score
                    save_highscore(self.highscore)
                self.ball.reset(speed_multiplier=self.speed_multiplier, away_from='player')

            self.update_ai()

        elif self.state == 'COUNTDOWN':
            # Check countdown finish
            if self.countdown_start is None:
                self.countdown_start = time.time()
            elapsed = time.time() - self.countdown_start
            if elapsed >= self.countdown_duration:
                self.state = 'PLAYING'
                self.countdown_start = None
                # ensure ball has proper speed
                self.ball.reset(speed_multiplier=self.speed_multiplier)

    def draw_hud(self):
        # Scores
        player_text = font_score.render(str(self.player_score), True, WHITE)
        computer_text = font_score.render(str(self.computer_score), True, WHITE)
        screen.blit(player_text, (SCREEN_WIDTH // 4 - 20, 30))
        screen.blit(computer_text, (3 * SCREEN_WIDTH // 4 - 50, 30))

        # Lives
        lives_text = font_info.render(f"Lives: {self.player_lives}", True, WHITE)
        screen.blit(lives_text, (20, SCREEN_HEIGHT - 40))

        # Highscore
        hs_text = font_info.render(f"Highscore: {self.highscore}", True, WHITE)
        screen.blit(hs_text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 40))

    def draw_pause_menu(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        pause_text = font_big.render("PAUSED", True, WHITE)
        press_text = font_info.render("Press Space to Resume | R to Restart | Q to Quit", True, WHITE)
        screen.blit(pause_text, (SCREEN_WIDTH // 2 - pause_text.get_width() // 2, SCREEN_HEIGHT // 2 - 80))
        screen.blit(press_text, (SCREEN_WIDTH // 2 - press_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        lost_text = font_big.render("YOU LOSE", True, WHITE)
        score_text = font_info.render(f"Score: {self.player_score}  Highscore: {self.highscore}", True, WHITE)
        press_text = font_info.render("Press R to Restart or Q to Quit", True, WHITE)
        screen.blit(lost_text, (SCREEN_WIDTH // 2 - lost_text.get_width() // 2, SCREEN_HEIGHT // 2 - 80))
        screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2 + 10))
        screen.blit(press_text, (SCREEN_WIDTH // 2 - press_text.get_width() // 2, SCREEN_HEIGHT // 2 + 50))

    def draw_menu(self):
        screen.fill((18, 24, 32))
        # draw icon
        screen.blit(self.menu_icon, (SCREEN_WIDTH // 2 - 64, 60))
        title = font_big.render("PONG - Stadium Edition", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 220))

        # Highscore
        hs = font_info.render(f"Highscore: {self.highscore}", True, HIGHLIGHT)
        screen.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2, 280))

        # Buttons
        pygame.draw.rect(screen, (40, 40, 60), self.btn_continue)
        cont_text = font_info.render("Continue (keep highscore)", True, WHITE)
        screen.blit(cont_text, (self.btn_continue.x + 12, self.btn_continue.y + 12))

        pygame.draw.rect(screen, (40, 40, 60), self.btn_new)
        new_text = font_info.render("New Game (reset highscore)", True, WHITE)
        screen.blit(new_text, (self.btn_new.x + 12, self.btn_new.y + 12))

        pygame.draw.rect(screen, (70, 70, 90), self.btn_settings)
        set_text = font_info.render("Settings", True, WHITE)
        screen.blit(set_text, (self.btn_settings.x + 12, self.btn_settings.y + 6))

        pygame.draw.rect(screen, (70, 70, 90), self.btn_quit)
        q_text = font_info.render("Quit", True, WHITE)
        screen.blit(q_text, (self.btn_quit.x + 40, self.btn_quit.y + 6))

    def draw_settings(self):
        screen.fill((12, 16, 22))
        title = font_big.render("Settings", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 80))

        # Slider label
        lbl = font_info.render("Ball speed:", True, WHITE)
        screen.blit(lbl, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 60))

        # Slider track
        pygame.draw.rect(screen, (80, 80, 90), self.settings_slider_rect)
        # Knob
        pygame.draw.rect(screen, (220, 220, 220), self.settings_knob_rect)

        # Numeric value and fastest button
        val_text = font_info.render(f"{self.speed_multiplier:.2f}x", True, HIGHLIGHT)
        screen.blit(val_text, (SCREEN_WIDTH // 2 + 220, SCREEN_HEIGHT // 2 - 30))

        pygame.draw.rect(screen, (70, 70, 90), self.btn_fastest)
        f_text = font_info.render("Fastest", True, WHITE)
        screen.blit(f_text, (self.btn_fastest.x + 18, self.btn_fastest.y + 6))

        pygame.draw.rect(screen, (70, 70, 90), self.btn_settings_back)
        b_text = font_info.render("Back", True, WHITE)
        screen.blit(b_text, (self.btn_settings_back.x + 12, self.btn_settings_back.y + 6))

    def draw_countdown(self):
        draw_stadium(screen)
        # big countdown number centered
        if self.countdown_start is None:
            return
        elapsed = time.time() - self.countdown_start
        remaining = self.countdown_duration - elapsed
        if remaining <= 0:
            txt = "Go!"
        else:
            val = int(math.ceil(remaining))
            txt = str(val)
        txt_surf = font_large.render(txt, True, HIGHLIGHT)
        # animate scale: simple pulse
        scale = 1.0 + 0.2 * math.sin((time.time() - self.countdown_start) * 8.0)
        s = pygame.transform.rotozoom(txt_surf, 0, scale)
        screen.blit(s, (SCREEN_WIDTH // 2 - s.get_width() // 2, SCREEN_HEIGHT // 2 - s.get_height() // 2))

    def draw_milestone(self):
        if self.milestone_timer == 0:
            return
        elapsed = time.time() - self.milestone_timer
        if elapsed > self.milestone_duration:
            self.milestone_timer = 0
            return
        t = elapsed / self.milestone_duration
        # scale from 1.0 to 1.8 and fade out
        scale = 1.0 + 0.8 * (1 - t)
        alpha = int(255 * (1 - t))
        txt = font_large.render(str(self.milestone_value), True, HIGHLIGHT)
        s = pygame.transform.rotozoom(txt, 0, scale)
        tmp = s.copy()
        tmp.fill((255, 255, 255, alpha), None, pygame.BLEND_RGBA_MULT)
        screen.blit(tmp, (SCREEN_WIDTH // 2 - tmp.get_width() // 2, SCREEN_HEIGHT // 2 - tmp.get_height() // 2 - 60))

    def draw(self):
        """Draw all game elements depending on state"""
        if self.state == 'MENU':
            self.draw_menu()
            pygame.display.flip()
            return
        elif self.state == 'SETTINGS':
            self.draw_settings()
            pygame.display.flip()
            return
        elif self.state == 'COUNTDOWN':
            self.draw_countdown()
            pygame.display.flip()
            return

        # default drawing for PLAYING/PAUSED/GAME_OVER
        draw_stadium(screen)

        # Draw center dashed line over the pitch area
        for y in range(FIELD_TOP + 20, FIELD_BOTTOM - 20, 20):
            pygame.draw.line(screen, WHITE, (SCREEN_WIDTH // 2, y), (SCREEN_WIDTH // 2, y + 10), 2)

        # Draw paddles and ball
        self.player_paddle.draw(screen)
        self.computer_paddle.draw(screen)
        self.ball.draw(screen)

        # HUD
        self.draw_hud()

        # Controls info
        info_text = font_info.render("Mouse or Arrow Keys to Control Left Paddle | Space: Pause", True, WHITE)
        screen.blit(info_text, (SCREEN_WIDTH // 2 - 300, SCREEN_HEIGHT - 70))

        # milestone
        self.draw_milestone()

        if self.paused:
            self.draw_pause_menu()

        if self.game_over:
            self.draw_game_over()

        pygame.display.flip()

    def _handle_menu_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.btn_continue.collidepoint(mx, my):
                # Continue: keep highscore, start countdown
                self.state = 'COUNTDOWN'
                self.countdown_start = time.time()
                return
            if self.btn_new.collidepoint(mx, my):
                # New game: clear highscore and restart
                clear_highscore()
                self.highscore = 0
                self.restart()
                return
            if self.btn_settings.collidepoint(mx, my):
                self.state = 'SETTINGS'
                return
            if self.btn_quit.collidepoint(mx, my):
                pygame.quit()
                sys.exit()

    def _handle_settings_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # knob drag or track click
            if self.settings_knob_rect.collidepoint(mx, my) or self.settings_slider_rect.collidepoint(mx, my):
                # set knob to mouse x
                frac = (mx - self.settings_slider_rect.x) / self.settings_slider_rect.width
                frac = max(0.0, min(1.0, frac))
                self.speed_multiplier = self.settings_min + frac * (self.settings_max - self.settings_min)
                self._update_knob_position()
                return
            if self.btn_fastest.collidepoint(mx, my):
                self.speed_multiplier = self.settings_max
                self._update_knob_position()
                return
            if self.btn_settings_back.collidepoint(mx, my):
                self.state = 'MENU'
                return
        elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
            mx, my = event.pos
            if self.settings_slider_rect.collidepoint(mx, my):
                frac = (mx - self.settings_slider_rect.x) / self.settings_slider_rect.width
                frac = max(0.0, min(1.0, frac))
                self.speed_multiplier = self.settings_min + frac * (self.settings_max - self.settings_min)
                self._update_knob_position()

    def run(self):
        """Main game loop"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if self.state == 'PLAYING':
                        if event.key == pygame.K_SPACE:
                            # Toggle pause unless game_over
                            if not self.game_over:
                                self.paused = not self.paused
                                if self.paused:
                                    self.state = 'PAUSED'
                                else:
                                    self.state = 'PLAYING'
                        elif event.key == pygame.K_r:
                            self.restart()
                        elif event.key == pygame.K_q:
                            running = False
                    elif self.state == 'PAUSED':
                        if event.key == pygame.K_SPACE:
                            self.paused = False
                            self.state = 'PLAYING'
                    elif self.state == 'GAME_OVER':
                        if event.key == pygame.K_r:
                            # restart a fresh match
                            self.restart()
                        elif event.key == pygame.K_q:
                            running = False

                # State-specific pointer events
                if self.state == 'MENU':
                    self._handle_menu_event(event)
                elif self.state == 'SETTINGS':
                    self._handle_settings_event(event)

            # Update logic
            if self.state == 'PLAYING':
                self.handle_input()
                self.update()
            elif self.state == 'COUNTDOWN':
                # still allow paddle to follow mouse for effect
                self.handle_input()
                self.update()
            else:
                # Menu/Settings/Paused/GameOver
                self.handle_input()

            # Draw
            self.draw()
            clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    # set window icon from generated surface
    g = Game()
    try:
        icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(icon, WHITE, (16, 16), 15)
        pygame.display.set_icon(icon)
    except Exception:
        pass
    g.run()

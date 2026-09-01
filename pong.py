import pygame
import sys
import math
import random
import os

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
GREEN = (34, 139, 34)
DARK_GREEN = (20, 90, 20)
SEAT_COLOR = (50, 50, 80)
LIGHTS = (255, 240, 200)

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


class Paddle:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.speed = PADDLE_SPEED

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, self.rect)

    def move_up(self):
        if self.rect.top > 0:
            self.rect.y -= self.speed

    def move_down(self):
        if self.rect.bottom < SCREEN_HEIGHT:
            self.rect.y += self.speed

    def set_position(self, y):
        """Set paddle position with boundaries"""
        self.rect.y = max(0, min(y, SCREEN_HEIGHT - PADDLE_HEIGHT))


class Ball:
    def __init__(self):
        self.rect = pygame.Rect(SCREEN_WIDTH // 2 - BALL_RADIUS, SCREEN_HEIGHT // 2 - BALL_RADIUS, BALL_SIZE, BALL_SIZE)
        self.velocity_x = BALL_SPEED * random.choice([-1, 1])
        self.velocity_y = BALL_SPEED * random.choice([-1, 1])

    def draw(self, surface):
        # Draw a round ball using circle centered on rect
        center = (self.rect.centerx, self.rect.centery)
        pygame.draw.circle(surface, WHITE, center, BALL_RADIUS)

    def update(self):
        self.rect.x += int(self.velocity_x)
        self.rect.y += int(self.velocity_y)

        # Bounce off top and bottom walls
        if self.rect.top <= 0 or self.rect.bottom >= SCREEN_HEIGHT:
            self.velocity_y *= -1
            self.rect.y = max(0, min(self.rect.y, SCREEN_HEIGHT - BALL_SIZE))

    def reset(self):
        """Reset ball to center"""
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.centery = SCREEN_HEIGHT // 2
        # Give the ball an initial X direction away from last scorer at random
        self.velocity_x = BALL_SPEED * random.choice([-1, 1])
        # small random Y
        self.velocity_y = BALL_SPEED * random.choice([-1, 1]) * 0.5

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
    """Draw a stylized stadium background: crowd stands, field, lights"""
    # Sky / top background
    surface.fill((30, 35, 45))

    # Draw stands (left and right)
    stand_height = 140
    for i in range(6):
        y = 40 + i * (stand_height // 6)
        color = (40 + i * 6, 40 + i * 6, 60 + i * 8)
        pygame.draw.rect(surface, color, (0, y, SCREEN_WIDTH, stand_height // 6))

    # Crowd as small rectangles in gradient
    rows = 6
    cols = 60
    start_y = 50
    row_height = 18
    for r in range(rows):
        for c in range(cols):
            x = int(c * (SCREEN_WIDTH / cols))
            y = start_y + r * row_height
            # randomize a bit for color
            shade = 60 + (r * 20) + (c % 3) * 10
            pygame.draw.rect(surface, (shade, shade - 20, shade + 10), (x, y, int(SCREEN_WIDTH / cols) - 2, row_height - 4))

    # Field
    field_y = 220
    pygame.draw.rect(surface, DARK_GREEN, (0, field_y, SCREEN_WIDTH, SCREEN_HEIGHT - field_y))
    pygame.draw.rect(surface, GREEN, (60, field_y + 20, SCREEN_WIDTH - 120, SCREEN_HEIGHT - field_y - 40))

    # Field markings
    center_x = SCREEN_WIDTH // 2
    pygame.draw.line(surface, WHITE, (center_x, field_y + 20), (center_x, SCREEN_HEIGHT - 20), 4)
    pygame.draw.circle(surface, WHITE, (center_x, (field_y + SCREEN_HEIGHT) // 2), 60, 4)

    # Flood lights
    light_positions = [(80, 40), (SCREEN_WIDTH - 80, 40), (SCREEN_WIDTH // 2, 20)]
    for lp in light_positions:
        pygame.draw.circle(surface, LIGHTS, lp, 18)
        for i in range(1, 6):
            pygame.draw.circle(surface, (255, 255 - i * 20, 200 - i * 10), lp, 18 + i * 8, 2)


class Game:
    def __init__(self):
        self.player_paddle = Paddle(20, SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2)
        self.computer_paddle = Paddle(SCREEN_WIDTH - PADDLE_WIDTH - 20, SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2)
        self.ball = Ball()
        self.player_score = 0
        self.computer_score = 0
        self.highscore = load_highscore()
        self.player_lives = MAX_LIVES
        self.paused = False
        self.game_over = False

    def handle_input(self):
        """Handle player input"""
        keys = pygame.key.get_pressed()
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # Mouse control for left paddle
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
        ai_speed = PADDLE_SPEED * 0.75  # Slightly slower than player

        # AI tries to follow the ball
        if paddle_center < ball_center - 35:
            self.computer_paddle.rect.y += ai_speed
        elif paddle_center > ball_center + 35:
            self.computer_paddle.rect.y -= ai_speed

        # Keep paddle in bounds
        self.computer_paddle.rect.y = max(0, min(self.computer_paddle.rect.y, SCREEN_HEIGHT - PADDLE_HEIGHT))

    def restart(self):
        self.player_score = 0
        self.computer_score = 0
        self.player_lives = MAX_LIVES
        self.ball.reset()
        self.game_over = False
        self.paused = False

    def update(self):
        """Update game state"""
        if self.paused or self.game_over:
            return

        self.ball.update()

        # Check paddle collisions
        self.ball.check_paddle_collision(self.player_paddle)
        self.ball.check_paddle_collision(self.computer_paddle)

        # Check if ball is out of bounds
        if self.ball.rect.left < 0:
            # Computer scored against player -> lose a life
            self.computer_score += 1
            self.player_lives -= 1
            self.ball.reset()
            if self.player_lives <= 0:
                self.game_over = True
                # update highscore
                if self.player_score > self.highscore:
                    self.highscore = self.player_score
                    save_highscore(self.highscore)
        elif self.ball.rect.right > SCREEN_WIDTH:
            # Player scored
            self.player_score += 1
            # Update highscore live
            if self.player_score > self.highscore:
                self.highscore = self.player_score
                save_highscore(self.highscore)
            self.ball.reset()

        self.update_ai()

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
        screen.blit(hs_text, (SCREEN_WIDTH - 220, SCREEN_HEIGHT - 40))

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

    def draw(self):
        """Draw all game elements"""
        draw_stadium(screen)

        # Draw center dashed line over the field area
        for y in range(240, SCREEN_HEIGHT - 20, 20):
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

        if self.paused:
            self.draw_pause_menu()

        if self.game_over:
            self.draw_game_over()

        pygame.display.flip()

    def run(self):
        """Main game loop"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        # Toggle pause unless game_over
                        if not self.game_over:
                            self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.restart()
                    elif event.key == pygame.K_q:
                        running = False

            if not self.paused and not self.game_over:
                self.handle_input()
                self.update()
            else:
                # Even when paused/game_over, allow mouse to move paddle in the menu for nicer effect
                self.handle_input()

            self.draw()
            clock.tick(FPS)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()

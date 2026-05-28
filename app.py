import os
import math

import app
from app_components import clear_background
from app_components.tokens import set_color, label_font_size, heading_font_size
from events.input import Buttons, BUTTON_TYPES

try:
    import imu
except ImportError:
    imu = None

# Tier display order: palladium first, then gold, then badge
_TIER_ORDER = {"palladium": 0, "gold": 1, "badge": 2}

# Sponsor manifest — list of (tier, name, filename, width, height)
_SPONSORS = [
    ("palladium", "Nationwide", "nationwide.png", 200, 26),
    ("gold", "Foundry Zero", "foundry_zero.png", 200, 87),
    ("gold", "zzoomm", "zzoomm.png", 200, 91),
    ("gold", "FullFIbre", "fullfibre.png", 200, 36),
    ("gold", "MathWorks", "mathworks.png", 200, 40),
    ("badge", "Bosch Sensortec", "bosch_sensortec.png", 200, 113),
]


def _find_logo_dir():
    """Find the logo directory on the badge filesystem."""
    candidates = [
        "/apps/sammachin_SponsorLogos/logos",
        "/apps/sammachin_SponsorLogos",
    ]
    for path in candidates:
        try:
            os.listdir(path)
            return path
        except OSError:
            continue
    return candidates[0]


class Sponsors(app.App):
    DISPLAY_TIME_MS = 4000  # Time each logo is shown before auto-advancing
    TRANSITION_MS = 500  # Crossfade duration

    def __init__(self):
        super().__init__()
        self.button_states = Buttons(self)
        self.sponsors = sorted(_SPONSORS, key=lambda s: _TIER_ORDER.get(s[0], 99))
        self.logo_dir = _find_logo_dir()
        self.current_index = 0
        self.timer = 0
        self.transitioning = False
        self.transition_timer = 0
        self.prev_index = -1
        # IMU mode
        self.imu_mode = False
        self.badge_angle = 0.0  # current rotation angle in radians
        self.smoothed_angle = 0.0  # smoothed angle for display counter-rotation

    def update(self, delta):
        if len(self.sponsors) == 0:
            return True

        # Handle button input
        if self.button_states.get(BUTTON_TYPES["CANCEL"]):
            self.button_states.clear()
            self.minimise()
            return False

        # Toggle IMU mode with confirm/OK button
        if self.button_states.get(BUTTON_TYPES["CONFIRM"]):
            self.button_states.clear()
            self.imu_mode = not self.imu_mode
            if not self.imu_mode:
                # Switching back to auto mode, reset timer
                self.timer = 0
                self.smoothed_angle = 0.0
            return True

        if self.imu_mode:
            self._update_imu(delta)
        else:
            # Manual navigation
            if self.button_states.get(BUTTON_TYPES["RIGHT"]) or self.button_states.get(
                BUTTON_TYPES["DOWN"]
            ):
                self.button_states.clear()
                self._advance(1)
                return True

            if self.button_states.get(BUTTON_TYPES["LEFT"]) or self.button_states.get(
                BUTTON_TYPES["UP"]
            ):
                self.button_states.clear()
                self._advance(-1)
                return True

            # Auto-advance timer
            self.timer += delta
            if self.timer >= self.DISPLAY_TIME_MS:
                self._advance(1)

        # Update transition
        if self.transitioning:
            self.transition_timer += delta
            if self.transition_timer >= self.TRANSITION_MS:
                self.transitioning = False
                self.transition_timer = 0

        return True

    def _update_imu(self, delta):
        """Read IMU and select logo based on badge rotation angle."""
        if imu is None:
            return

        try:
            acc = imu.acc_read()
        except Exception:
            return

        ax, ay = acc[0], acc[1]

        # Get angle of rotation around Z axis from accelerometer
        raw_angle = math.atan2(ay, ax)

        # Smooth the angle to avoid jitter (exponential moving average)
        # Handle wraparound by working with the difference
        diff = raw_angle - self.smoothed_angle
        # Normalise difference to [-pi, pi]
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        alpha = 0.15  # smoothing factor (lower = smoother)
        self.smoothed_angle += alpha * diff
        # Keep in [-pi, pi]
        while self.smoothed_angle > math.pi:
            self.smoothed_angle -= 2 * math.pi
        while self.smoothed_angle < -math.pi:
            self.smoothed_angle += 2 * math.pi

        self.badge_angle = self.smoothed_angle

        # Map the angle to a sponsor index
        # Divide the full 360 degrees into equal segments
        n = len(self.sponsors)
        # Shift angle to [0, 2*pi]
        norm_angle = self.badge_angle % (2 * math.pi)
        segment = 2 * math.pi / n
        new_index = int(norm_angle / segment) % n

        if new_index != self.current_index:
            self.prev_index = self.current_index
            self.current_index = new_index
            self.transitioning = True
            self.transition_timer = 0

    def _advance(self, direction):
        """Move to next/previous logo."""
        if len(self.sponsors) == 0:
            return
        self.prev_index = self.current_index
        self.current_index = (self.current_index + direction) % len(self.sponsors)
        self.timer = 0
        self.transitioning = True
        self.transition_timer = 0

    def _logo_path(self, index):
        """Get the filesystem path for a logo by index."""
        _, _, filename, _, _ = self.sponsors[index]
        return f"{self.logo_dir}/{filename}"

    def draw(self, ctx):
        ctx.rgb(1.0, 1.0, 1.0).rectangle(-120, -120, 240, 240).fill()

        if len(self.sponsors) == 0:
            ctx.save()
            ctx.rgb(0.0, 0.0, 0.0)
            ctx.font_size = label_font_size
            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE
            ctx.move_to(0, 0).text("No sponsor logos found")
            ctx.restore()
            return

        ctx.save()

        # In IMU mode, counter-rotate the canvas so content stays upright
        if self.imu_mode:
            ctx.rotate(-self.badge_angle)

        # Draw current logo
        if self.transitioning and self.prev_index >= 0:
            progress = min(1.0, self.transition_timer / self.TRANSITION_MS)

            ctx.global_alpha = 1.0 - progress
            self._draw_logo(ctx, self.prev_index)

            ctx.global_alpha = progress
            self._draw_logo(ctx, self.current_index)

            ctx.global_alpha = 1.0
        else:
            self._draw_logo(ctx, self.current_index)

        # Draw tier label at top (subtle grey)
        tier, name, _, _, _ = self.sponsors[self.current_index]
        ctx.rgba(0.6, 0.6, 0.6, 0.6)
        ctx.font_size = label_font_size
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.TOP
        ctx.move_to(0, -100).text(tier.upper())

        # Draw dot indicators
        self._draw_dots(ctx)

        ctx.restore()

    def _draw_logo(self, ctx, index):
        """Draw a sponsor logo centered on the display, preserving aspect ratio."""
        path = self._logo_path(index)
        _, _, _, orig_w, orig_h = self.sponsors[index]
        max_w = 180
        max_h = 120
        scale = min(max_w / orig_w, max_h / orig_h)
        draw_w = orig_w * scale
        draw_h = orig_h * scale
        try:
            ctx.image(path, -draw_w / 2, -draw_h / 2, draw_w, draw_h)
        except Exception as e:
            _, name, _, _, _ = self.sponsors[index]
            ctx.rgb(0.0, 0.0, 0.0)
            ctx.font_size = heading_font_size
            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE
            ctx.move_to(0, 0).text(name)

    def _draw_dots(self, ctx):
        """Draw pagination dots at the bottom."""
        n = len(self.sponsors)
        if n <= 1:
            return
        dot_spacing = 12
        total_width = (n - 1) * dot_spacing
        start_x = -total_width / 2
        y = 85

        for i in range(n):
            x = start_x + i * dot_spacing
            if i == self.current_index:
                ctx.rgb(0.3, 0.3, 0.3)
                ctx.round_rectangle(x - 3, y - 3, 6, 6, 3).fill()
            else:
                ctx.rgba(0.6, 0.6, 0.6, 0.5)
                ctx.round_rectangle(x - 2, y - 2, 4, 4, 2).fill()


__app_export__ = Sponsors

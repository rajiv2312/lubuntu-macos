#!/usr/bin/env python3
"""macOS-style Notification Center: slides in from the right under the top bar.

Shows a Calendar widget and a World Clock widget. Running it again while it is
open closes it (single instance via Gtk.Application); clicking elsewhere or
pressing Esc also closes it. Undo: ~/.local/share/macos-theme/undo-notification-center
"""
import calendar
import datetime
import math
from zoneinfo import ZoneInfo

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, GLib, Gtk, Pango, PangoCairo  # noqa: E402

TOP_BAR = 30          # height of the top bar
MARGIN = 10           # gap to the screen edge / top bar
WIDTH = 360           # widget column width (macOS medium widget ~ 329pt)
CARD_H = 170
GAP = 12
RADIUS = 20
FONT = "Inter"
RED = (1.0, 0.23, 0.19)          # macOS system red #ff3b30
TEXT = (0.11, 0.11, 0.12)
GREY = (0.56, 0.56, 0.58)
CITIES = [("Cupertino", "America/Los_Angeles"), ("New York", "America/New_York"),
          ("London", "Europe/London"), ("India", "Asia/Kolkata")]
SLIDE_MS = 180


def text(cr, s, x, y, size, weight=Pango.Weight.NORMAL, rgb=TEXT, align="left", width=None):
    layout = PangoCairo.create_layout(cr)
    desc = Pango.FontDescription(f"{FONT} {size}px")
    desc.set_weight(weight)
    layout.set_font_description(desc)
    layout.set_text(s, -1)
    w, h = layout.get_pixel_size()
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    cr.set_source_rgb(*rgb)
    cr.move_to(x, y)
    PangoCairo.show_layout(cr, layout)
    return w, h


def rounded(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def card(cr, x, y, w, h):
    # soft shadow, then the translucent white card with a hairline border
    for i, a in ((6, 0.03), (4, 0.04), (2, 0.05)):
        rounded(cr, x - i / 2, y - i / 2 + 2, w + i, h + i, RADIUS + i / 2)
        cr.set_source_rgba(0, 0, 0, a)
        cr.fill()
    rounded(cr, x, y, w, h, RADIUS)
    cr.set_source_rgba(1, 1, 1, 0.985)
    cr.fill_preserve()
    cr.set_source_rgba(0, 0, 0, 0.08)
    cr.set_line_width(1)
    cr.stroke()


def draw_calendar(cr, x, y, now):
    card(cr, x, y, WIDTH, CARD_H)
    # left half: weekday + big date + events line
    text(cr, now.strftime("%A").upper(), x + 18, y + 16, 12, Pango.Weight.BOLD, RED)
    text(cr, str(now.day), x + 16, y + 30, 44, Pango.Weight.NORMAL, TEXT)
    text(cr, "No more events today", x + 18, y + CARD_H - 34, 12, Pango.Weight.NORMAL, GREY)
    # right half: month grid, weeks start on Sunday (US)
    gx, gy, cw, rh = x + WIDTH / 2 + 4, y + 16, 22, 19
    text(cr, now.strftime("%B").upper(), gx + 2, gy, 11, Pango.Weight.BOLD, RED)
    for i, d in enumerate("SMTWTFS"):
        text(cr, d, gx + 11 + i * cw, gy + 20, 10, Pango.Weight.BOLD, GREY, "center")
    weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(now.year, now.month)
    for r, week in enumerate(weeks):
        for c, day in enumerate(week):
            if not day:
                continue
            cx, cy = gx + 11 + c * cw, gy + 38 + r * rh
            if day == now.day:
                cr.set_source_rgb(*RED)
                cr.arc(cx, cy + 7, 9, 0, 2 * math.pi)
                cr.fill()
                text(cr, str(day), cx, cy, 10, Pango.Weight.BOLD, (1, 1, 1), "center")
            else:
                text(cr, str(day), cx, cy, 10, Pango.Weight.NORMAL, TEXT, "center")


def draw_clock_face(cr, cx, cy, r, t):
    night = t.hour < 6 or t.hour >= 18
    face, ink = ((0.11, 0.11, 0.12), (1, 1, 1)) if night else ((1, 1, 1), TEXT)
    cr.set_source_rgb(*face)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.fill_preserve()
    cr.set_source_rgba(0, 0, 0, 0.12)
    cr.set_line_width(1)
    cr.stroke()
    for h in range(1, 13):
        a = h / 12 * 2 * math.pi
        text(cr, str(h), cx + math.sin(a) * (r - 8), cy - math.cos(a) * (r - 8) - 5,
             7.5, Pango.Weight.NORMAL, ink, "center")

    def hand(angle, length, width, rgb):
        cr.set_source_rgb(*rgb)
        cr.set_line_width(width)
        cr.set_line_cap(1)
        cr.move_to(cx, cy)
        cr.line_to(cx + math.sin(angle) * length, cy - math.cos(angle) * length)
        cr.stroke()
    hand((t.hour % 12 + t.minute / 60) / 12 * 2 * math.pi, r * 0.5, 2.6, ink)
    hand((t.minute + t.second / 60) / 60 * 2 * math.pi, r * 0.75, 2.0, ink)
    hand(t.second / 60 * 2 * math.pi, r * 0.8, 1.0, (1.0, 0.58, 0.0))
    cr.set_source_rgb(1.0, 0.58, 0.0)
    cr.arc(cx, cy, 2, 0, 2 * math.pi)
    cr.fill()


def draw_world_clock(cr, x, y, now):
    card(cr, x, y, WIDTH, CARD_H)
    local = now.astimezone()
    col = WIDTH / 4
    for i, (city, tz) in enumerate(CITIES):
        t = now.astimezone(ZoneInfo(tz))
        cx = x + col * i + col / 2
        draw_clock_face(cr, cx, y + 62, 34, t)
        text(cr, city, cx, y + 106, 11.5, Pango.Weight.SEMIBOLD, TEXT, "center")
        mins = round((t.utcoffset() - local.utcoffset()).total_seconds() / 60)
        diff = f"{'+' if mins > 0 else '-'}{abs(mins) // 60}" + (f":{abs(mins) % 60:02d}" if mins % 60 else "")
        day = "Today" if t.date() == local.date() else ("Tomorrow" if t.date() > local.date() else "Yesterday")
        text(cr, day, cx, y + 124, 10, Pango.Weight.NORMAL, GREY, "center")
        text(cr, f"{diff}HRS" if mins else "Local", cx, y + 138, 10, Pango.Weight.NORMAL, GREY, "center")


class Center(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.w, self.h = WIDTH + 12, 2 * CARD_H + GAP + 12
        self.set_default_size(self.w, self.h)
        area = Gtk.DrawingArea()
        area.connect("draw", self.on_draw)
        self.add(area)
        self.area = area
        geo = Gdk.Display.get_default().get_primary_monitor().get_geometry()
        self.final_x = geo.x + geo.width - self.w - MARGIN + 6
        self.off_x = geo.x + geo.width + 4
        self.y = geo.y + TOP_BAR + MARGIN - 6
        self.move(self.off_x, self.y)
        self.connect("key-press-event", self.on_key)
        self.connect("focus-out-event", lambda *a: self.close_animated())
        self.closing = False
        GLib.timeout_add(1000, self.tick)

    def tick(self):
        self.area.queue_draw()
        return True

    def on_draw(self, widget, cr):
        cr.set_operator(0)  # CLEAR: fully transparent background
        cr.paint()
        cr.set_operator(2)  # OVER
        now = datetime.datetime.now().astimezone()
        draw_calendar(cr, 6, 6, now)
        draw_world_clock(cr, 6, 6 + CARD_H + GAP, now)
        return False

    def on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close_animated()

    def slide(self, start, end, done=None):
        t0 = GLib.get_monotonic_time()

        def step():
            p = min(1.0, (GLib.get_monotonic_time() - t0) / 1000 / SLIDE_MS)
            e = 1 - (1 - p) ** 3  # ease-out
            self.move(int(start + (end - start) * e), self.y)
            if p >= 1.0:
                if done:
                    done()
                return False
            return True
        GLib.timeout_add(12, step)

    def open_animated(self):
        self.show_all()
        self.present()
        self.slide(self.off_x, self.final_x)

    def close_animated(self):
        if self.closing:
            return
        self.closing = True
        self.slide(self.final_x, self.off_x, self.get_application().quit)


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.macostheme.NotificationCenter")
        self.win = None

    def do_activate(self):
        if self.win:            # launched again while open: toggle closed
            self.win.close_animated()
            return
        self.win = Center(self)
        self.win.open_animated()


if __name__ == "__main__":
    App().run(None)

#!/usr/bin/env python3
"""macOS-style Wi-Fi and Bluetooth menus for the top bar.

    status-menu.py wifi        drop-down under the pointer, toggles if already open
    status-menu.py bluetooth

Wi-Fi uses nmcli; joining a new secured network lets NetworkManager ask for the
password through the running password agent (nm-tray), so no password passes
through this script. Bluetooth uses bluetoothctl. Undo:
~/.local/share/macos-theme/undo-status-menus
"""
import os
import re
import subprocess
import sys

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

TOP_BAR = 30
WIDTH = 300

CSS = b"""
window.status-menu { background: transparent; }
.card {
    background: rgba(246, 246, 246, 0.985);
    border: 1px solid rgba(0, 0, 0, 0.13);
    border-radius: 12px;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.16);
    margin: 10px;
    padding: 6px;
}
.header { padding: 6px 10px 6px 10px; }
.header label { font-weight: bold; }
.section { color: #8a8a8e; font-weight: bold; font-size: 0.85em; padding: 8px 10px 2px 10px; }
.empty { color: #8a8a8e; padding: 4px 10px 6px 10px; }
button.row {
    background: none; border: none; box-shadow: none; border-radius: 6px;
    padding: 3px 8px; min-height: 0;
}
button.row:hover { background: rgba(0, 0, 0, 0.07); }
button.row label { font-weight: normal; }
button.row .sub { color: #8a8a8e; font-size: 0.85em; }
.circle {
    background: #dcdcdf; border-radius: 99px;
    min-width: 26px; min-height: 26px;
}
.circle image { color: #1d1d1f; }
.circle.active { background: #007aff; }
.circle.active image { color: #ffffff; }
.lock { color: #8a8a8e; }
.note-card {
    background: #ffffff; border: 1px solid rgba(0, 0, 0, 0.08); border-radius: 10px;
    padding: 8px 10px; margin: 3px 4px;
}
.note-card .app { color: #8a8a8e; font-size: 0.8em; font-weight: bold; }
.note-card .when { color: #8a8a8e; font-size: 0.8em; }
.note-card .title { font-weight: bold; }
button.clear, button.close-note {
    background: none; border: none; box-shadow: none; padding: 0 4px; min-height: 0; min-width: 0;
    color: #8a8a8e;
}
button.clear:hover, button.close-note:hover { color: #1d1d1f; }
.header .value { color: #8a8a8e; font-weight: normal; }
.info { padding: 1px 10px 1px 10px; }
.info.dim { color: #8a8a8e; }
.slider-row { padding: 2px 10px 8px 10px; }
.slider-row image { color: #6e6e73; }
.slider-row scale { min-height: 20px; }
separator { margin: 4px 10px; background: rgba(0, 0, 0, 0.10); min-height: 1px; }
"""


def run(cmd, timeout=6):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def spawn(cmd):
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

def spawn_gui(cmd):
    # For GUI applications like kdialog that need X11 display
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def split_terse(line):
    # nmcli -t escapes ':' inside values as '\:'
    out, cur, esc = [], "", False
    for ch in line:
        if esc:
            cur += ch
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == ":":
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return out


def signal_icon(sig):
    s = int(sig or 0)
    level = "excellent" if s >= 75 else "good" if s >= 50 else "ok" if s >= 25 else "weak"
    return f"network-wireless-signal-{level}-symbolic"


class Menu(Gtk.ApplicationWindow):
    def __init__(self, app, kind):
        super().__init__(application=app)
        self.kind = kind
        self.get_style_context().add_class("status-menu")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.card.get_style_context().add_class("card")
        self.card.set_size_request(WIDTH, -1)
        self.add(self.card)
        self.connect("key-press-event", self.on_key)
        self.connect("focus-out-event", lambda *a: self.get_application().quit())
        self.busy = False
        self.build()
        self.place()
        if kind == "wifi":   # like macOS: rescan when the menu opens, then refresh the list
            spawn(["nmcli", "device", "wifi", "rescan"])
            self.refresh_later(3000)
            self.refresh_later(7000)

    # ---------- layout helpers ----------
    def clear(self):
        for child in self.card.get_children():
            self.card.remove(child)

    def header(self, title, active, on_toggle):
        box = Gtk.Box(spacing=8)
        box.get_style_context().add_class("header")
        label = Gtk.Label(label=title, xalign=0)
        box.pack_start(label, True, True, 0)
        sw = Gtk.Switch(active=active, valign=Gtk.Align.CENTER)
        sw.connect("state-set", lambda w, state: on_toggle(state) or False)
        box.pack_end(sw, False, False, 0)
        self.card.pack_start(box, False, False, 0)

    def section(self, text):
        label = Gtk.Label(label=text, xalign=0)
        label.get_style_context().add_class("section")
        self.card.pack_start(label, False, False, 0)

    def note(self, text):
        label = Gtk.Label(label=text, xalign=0)
        label.get_style_context().add_class("empty")
        self.card.pack_start(label, False, False, 0)

    def row(self, icon, title, sub=None, active=False, lock=False, on_click=None):
        btn = Gtk.Button()
        btn.get_style_context().add_class("row")
        btn.set_relief(Gtk.ReliefStyle.NONE)
        box = Gtk.Box(spacing=10)
        circle = Gtk.Box(valign=Gtk.Align.CENTER)
        circle.get_style_context().add_class("circle")
        if active:
            circle.get_style_context().add_class("active")
        img = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)
        img.set_halign(Gtk.Align.CENTER)
        img.set_valign(Gtk.Align.CENTER)
        circle.set_size_request(26, 26)
        circle.set_center_widget(img)
        box.pack_start(circle, False, False, 0)
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        t = Gtk.Label(label=title)
        t.set_xalign(0.0)
        t.set_hexpand(True)
        t.set_ellipsize(3)  # END
        t.set_max_width_chars(24)
        texts.pack_start(t, False, False, 0)
        if sub:
            s = Gtk.Label(label=sub)
            s.set_xalign(0.0)
            s.get_style_context().add_class("sub")
            texts.pack_start(s, False, False, 0)
        box.pack_start(texts, True, True, 0)
        if lock:
            lk = Gtk.Image.new_from_icon_name("changes-prevent-symbolic", Gtk.IconSize.MENU)
            lk.get_style_context().add_class("lock")
            box.pack_end(lk, False, False, 0)
        btn.add(box)
        if on_click:
            btn.connect("clicked", lambda *_: on_click())
        self.card.pack_start(btn, False, False, 0)

    def link(self, text, cmd):
        btn = Gtk.Button()
        btn.get_style_context().add_class("row")
        btn.set_relief(Gtk.ReliefStyle.NONE)
        lab = Gtk.Label(label=text, xalign=0, halign=Gtk.Align.START, hexpand=True)
        btn.add(lab)
        btn.connect("clicked", lambda *_: (spawn(cmd), self.get_application().quit()))
        self.card.pack_start(btn, False, False, 0)

    def sep(self):
        self.card.pack_start(Gtk.Separator(), False, False, 0)

    # ---------- content ----------
    def build(self):
        self.clear()
        {"wifi": self.build_wifi, "bluetooth": self.build_bluetooth, "sound": self.build_sound,
         "battery": self.build_battery, "notifications": self.build_notifications}[self.kind]()
        self.card.show_all()
        self.resize(1, 1)

    def refresh_later(self, ms=1500):
        GLib.timeout_add(ms, lambda: (self.build(), False)[1])

    def build_wifi(self):
        on = run(["nmcli", "-t", "-f", "WIFI", "radio"]).strip() == "enabled"
        self.header("Wi-Fi", on, self.toggle_wifi)
        if on:
            known = set()
            for line in run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"]).splitlines():
                parts = split_terse(line)
                if len(parts) >= 2 and parts[1] == "802-11-wireless":
                    known.add(parts[0])
            nets = {}
            for line in run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi", "list", "--rescan", "no"]).splitlines():
                p = split_terse(line)
                if len(p) < 4 or not p[1]:
                    continue
                use, ssid, sig, sec = p[0] == "*", p[1], int(p[2] or 0), p[3]
                old = nets.get(ssid)
                if not old or use or (sig > old["sig"] and not old["use"]):
                    nets[ssid] = {"use": use or bool(old and old["use"]), "sig": sig, "sec": sec not in ("", "--")}
            current = [s for s, n in nets.items() if n["use"]]
            for s in current:
                n = nets[s]
                self.row(signal_icon(n["sig"]), s, None, active=True, lock=n["sec"])
            kn = sorted((s for s in nets if s in known and s not in current), key=lambda s: -nets[s]["sig"])
            if kn:
                self.section("Known Networks")
                for s in kn:
                    self.row(signal_icon(nets[s]["sig"]), s, lock=nets[s]["sec"], on_click=lambda s=s: self.join(s, True))
            other = sorted((s for s in nets if s not in known and s not in current), key=lambda s: -nets[s]["sig"])[:8]
            if other:
                self.section("Other Networks")
                for s in other:
                    self.row(signal_icon(nets[s]["sig"]), s, lock=nets[s]["sec"], on_click=lambda s=s: self.join(s, False))
            if not nets:
                self.note("No networks found")
        self.sep()
        self.link("Wi-Fi Settings…", ["nm-connection-editor"])

    def toggle_wifi(self, state):
        spawn(["nmcli", "radio", "wifi", "on" if state else "off"])
        self.refresh_later(2500 if state else 1000)

    def join(self, ssid, known):
        if known:
            spawn(["nmcli", "connection", "up", "id", ssid])
        else:
            # Show macOS-style password dialog for new networks
            # Use spawn_gui to preserve X11 display connection
            spawn_gui(["/home/trishul2/.local/share/macos-theme/macos-wifi-password", ssid])
        self.get_application().quit()

    def build_bluetooth(self):
        show = run(["bluetoothctl", "show"])
        on = "Powered: yes" in show
        self.header("Bluetooth", on, self.toggle_bt)
        if on:
            self.section("Devices")
            devs = []
            for line in run(["bluetoothctl", "devices", "Paired"]).splitlines():
                parts = line.split(" ", 2)
                if len(parts) == 3 and parts[0] == "Device":
                    devs.append((parts[1], parts[2]))
            if not devs:
                self.note("No paired devices")
            for mac, name in devs:
                info = run(["bluetoothctl", "info", mac])
                connected = "Connected: yes" in info
                icon_hint = next((l.split(":", 1)[1].strip() for l in info.splitlines() if l.strip().startswith("Icon:")), "")
                icon = {"audio-headphones": "audio-headphones-symbolic", "audio-headset": "audio-headphones-symbolic",
                        "input-keyboard": "input-keyboard-symbolic", "input-mouse": "input-mouse-symbolic",
                        "phone": "phone-symbolic", "computer": "computer-symbolic"}.get(icon_hint, "bluetooth-active-symbolic")
                self.row(icon, name, "Connected" if connected else None, active=connected,
                         on_click=lambda mac=mac, c=connected: self.bt_connect(mac, c))
        self.sep()
        self.link("Bluetooth Settings…", ["blueman-manager"])

    def toggle_bt(self, state):
        spawn(["bluetoothctl", "power", "on" if state else "off"])
        self.refresh_later(1500)

    def bt_connect(self, mac, connected):
        spawn(["bluetoothctl", "disconnect" if connected else "connect", mac])
        self.refresh_later(4000)

    def build_sound(self):
        label = Gtk.Label(label="Sound", xalign=0)
        head = Gtk.Box()
        head.get_style_context().add_class("header")
        head.pack_start(label, True, True, 0)
        self.card.pack_start(head, False, False, 0)
        out = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
        try:
            vol = float(out.split()[1])
        except (IndexError, ValueError):
            vol = 0.0
        if "MUTED" in out:
            vol = 0.0
        row = Gtk.Box(spacing=8)
        row.get_style_context().add_class("slider-row")
        row.pack_start(Gtk.Image.new_from_icon_name("audio-volume-low-symbolic", Gtk.IconSize.MENU), False, False, 0)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_draw_value(False)
        scale.set_value(round(vol * 100))
        scale.set_hexpand(True)
        scale.connect("value-changed", self.on_volume)
        row.pack_start(scale, True, True, 0)
        row.pack_start(Gtk.Image.new_from_icon_name("audio-volume-high-symbolic", Gtk.IconSize.MENU), False, False, 0)
        self.card.pack_start(row, False, False, 0)
        sinks, in_sinks = [], False
        for line in run(["wpctl", "status"]).splitlines():
            if "Sinks:" in line:
                in_sinks = True
                continue
            if in_sinks and ("Sources:" in line or "Filters:" in line or "Streams:" in line):
                break
            m = re.match(r"^[\s│├└─]*(\*)?\s*(\d+)\.\s+(.+?)\s+\[vol:", line)
            if in_sinks and m:
                sinks.append((m.group(2), m.group(3), bool(m.group(1))))
        self.section("Output")
        if not sinks:
            self.note("No output devices")
        for sid, name, default in sinks:
            self.row("audio-speakers-symbolic", name, active=default,
                     on_click=None if default else (lambda sid=sid: self.set_output(sid)))
        self.sep()
        self.link("Sound Settings…", ["pavucontrol-qt"])

    def on_volume(self, scale):
        v = int(scale.get_value())
        spawn(["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", f"{v}%"])
        spawn(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if v == 0 else "0"])

    def set_output(self, sid):
        spawn(["wpctl", "set-default", sid])
        self.refresh_later(800)

    def build_battery(self):
        dev = next((l.strip() for l in run(["upower", "-e"]).splitlines() if "battery_" in l), "")
        info = {}
        for line in run(["upower", "-i", dev]).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info.setdefault(k.strip(), v.strip())
        ac = any("yes" in run(["upower", "-i", l.strip()]) for l in run(["upower", "-e"]).splitlines() if "line_power" in l)
        pct = info.get("percentage", "?")
        head = Gtk.Box()
        head.get_style_context().add_class("header")
        head.pack_start(Gtk.Label(label="Battery", xalign=0), True, True, 0)
        val = Gtk.Label(label=pct)
        val.get_style_context().add_class("value")
        head.pack_end(val, False, False, 0)
        self.card.pack_start(head, False, False, 0)
        state = info.get("state", "")
        if state == "fully-charged" or (ac and state in ("pending-charge", "")):
            status = "Fully Charged" if state == "fully-charged" else "Not Charging"
        elif state == "charging":
            t = info.get("time to full")
            status = f"Charging — {self.hm(t)} until full" if t else "Charging"
        else:
            t = info.get("time to empty")
            status = f"{self.hm(t)} remaining" if t else "On Battery"
        for text, dim in ((f"Power Source: {'Power Adapter' if ac else 'Battery'}", False), (status, True)):
            lab = Gtk.Label(label=text, xalign=0)
            lab.get_style_context().add_class("info")
            if dim:
                lab.get_style_context().add_class("dim")
            self.card.pack_start(lab, False, False, 0)
        self.sep()
        self.section("Using Significant Energy")
        hogs = []
        for line in run(["ps", "-eo", "pcpu=,comm=", "--sort=-pcpu"]).splitlines()[:8]:
            parts = line.split(None, 1)
            if len(parts) == 2 and float(parts[0]) >= 10 and parts[1] not in ("ps", "python3"):
                hogs.append(parts[1])
        if hogs:
            for name in hogs[:4]:
                self.row("application-x-executable-symbolic", name)
        else:
            self.note("No Apps Using Significant Energy")
        self.sep()
        self.link("Battery Settings…", ["lxqt-config-powermanagement"])

    @staticmethod
    def hm(text):
        # upower gives "2.3 hours" / "45.0 minutes" / "197.8 days"
        try:
            n, unit = text.split()
            n = float(n)
        except ValueError:
            return text
        mins = n * 60 if unit.startswith("hour") else n * 1440 if unit.startswith("day") else n
        return f"{int(mins // 60)}:{int(mins % 60):02d}"

    NOTE_STORE = "~/.local/share/macos-theme/notifications.json"

    def notes_load(self):
        import json, os
        try:
            with open(os.path.expanduser(self.NOTE_STORE)) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {"items": [], "seen": 0}

    def notes_save(self, data):
        import json, os
        path = os.path.expanduser(self.NOTE_STORE)
        fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(path + ".tmp", path)

    @staticmethod
    def ago(t):
        import time, datetime
        d = time.time() - t
        if d < 60:
            return "now"
        if d < 3600:
            return f"{int(d // 60)}m ago"
        if d < 86400:
            return f"{int(d // 3600)}h ago"
        return datetime.datetime.fromtimestamp(t).strftime("%-d %b")

    def build_notifications(self):
        import time
        data = self.notes_load()
        head = Gtk.Box()
        head.get_style_context().add_class("header")
        head.pack_start(Gtk.Label(label="Notifications", xalign=0), True, True, 0)
        if data["items"]:
            clear = Gtk.Button(label="Clear All")
            clear.get_style_context().add_class("clear")
            clear.set_relief(Gtk.ReliefStyle.NONE)
            clear.connect("clicked", lambda *_: self.notes_clear(None))
            head.pack_end(clear, False, False, 0)
        self.card.pack_start(head, False, False, 0)
        if not data["items"]:
            self.note("No Notifications")
        else:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            for i, n in enumerate(data["items"]):
                c = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
                c.get_style_context().add_class("note-card")
                top = Gtk.Box(spacing=6)
                app = Gtk.Label(label=(n.get("app") or "").upper(), xalign=0)
                app.get_style_context().add_class("app")
                app.set_ellipsize(3)
                top.pack_start(app, True, True, 0)
                when = Gtk.Label(label=self.ago(n.get("time", 0)))
                when.get_style_context().add_class("when")
                top.pack_start(when, False, False, 0)
                x = Gtk.Button(label="×")
                x.get_style_context().add_class("close-note")
                x.set_relief(Gtk.ReliefStyle.NONE)
                x.connect("clicked", lambda *_, i=i: self.notes_clear(i))
                top.pack_start(x, False, False, 0)
                c.pack_start(top, False, False, 0)
                if n.get("summary"):
                    t = Gtk.Label(label=n["summary"], xalign=0)
                    t.get_style_context().add_class("title")
                    t.set_line_wrap(True)
                    t.set_max_width_chars(34)
                    c.pack_start(t, False, False, 0)
                if n.get("body"):
                    b = Gtk.Label(label=n["body"], xalign=0)
                    b.set_line_wrap(True)
                    b.set_max_width_chars(34)
                    b.set_lines(3)
                    b.set_ellipsize(3)
                    c.pack_start(b, False, False, 0)
                box.pack_start(c, False, False, 0)
            sc = Gtk.ScrolledWindow()
            sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sc.set_min_content_height(min(520, 118 * len(data["items"])))
            sc.add(box)
            self.card.pack_start(sc, False, False, 0)
        data["seen"] = time.time()   # opening the list marks everything as read
        self.notes_save(data)

    def notes_clear(self, index):
        data = self.notes_load()
        if index is None:
            data["items"] = []
        elif 0 <= index < len(data["items"]):
            del data["items"][index]
        self.notes_save(data)
        self.build()

    # ---------- window behaviour ----------
    def place(self):
        display = Gdk.Display.get_default()
        _, px, _py = display.get_default_seat().get_pointer().get_position()
        geo = display.get_primary_monitor().get_geometry()
        width = WIDTH + 20
        x = min(max(px - 30, geo.x + 4), geo.x + geo.width - width - 4)
        self.move(x, geo.y + TOP_BAR - 6)

    def on_key(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.get_application().quit()


class App(Gtk.Application):
    def __init__(self, kind):
        super().__init__(application_id=f"org.macostheme.{kind.capitalize()}Menu")
        self.kind = kind
        self.win = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

    def do_activate(self):
        if self.win:          # clicked again while open: close
            self.quit()
            return
        self.win = Menu(self, self.kind)
        self.win.show_all()
        self.win.present()


if __name__ == "__main__":
    kind = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("wifi", "bluetooth", "sound", "battery", "notifications") else "wifi"
    App(kind).run(None)

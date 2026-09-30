#!/usr/bin/env python3
"""Record desktop notifications so the macOS-style notification list can show them.

Watches org.freedesktop.Notifications.Notify calls on the session bus (read-only
D-Bus monitor) and keeps the last 50 in ~/.local/share/macos-theme/notifications.json
(mode 600). Started at login from ~/.config/autostart/macos-notification-log.desktop.
"""
import json
import os
import time

import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

STORE = os.path.expanduser("~/.local/share/macos-theme/notifications.json")
KEEP = 50


def load():
    try:
        with open(STORE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"items": [], "seen": 0}


def save(data):
    tmp = STORE + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f)
    os.replace(tmp, STORE)


def record(app, icon, summary, body):
    if app in ("notify-send",) and not summary:
        return
    data = load()
    data["items"].insert(0, {"app": app or "Notification", "icon": icon, "summary": summary,
                             "body": body, "time": time.time()})
    data["items"] = data["items"][:KEEP]
    save(data)


def on_message(connection, message, incoming):
    try:
        if (message.get_message_type() == Gio.DBusMessageType.METHOD_CALL
                and message.get_interface() == "org.freedesktop.Notifications"
                and message.get_member() == "Notify"):
            body = message.get_body()
            if body is not None and body.n_children() >= 5:
                app, _replaces, icon, summary, text = (body.get_child_value(i).unpack() for i in range(5))
                GLib.idle_add(lambda: (record(app, icon, summary, text), False)[1])
            return None  # a monitor must not handle (or reply to) the observed call
    except Exception:
        return None
    return message  # everything else, e.g. the reply to BecomeMonitor


def main():
    address = Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION, None)
    conn = Gio.DBusConnection.new_for_address_sync(
        address,
        Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
        None, None)
    conn.add_filter(on_message)
    conn.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus.Monitoring",
                   "BecomeMonitor",
                   GLib.Variant("(asu)", (["type='method_call',interface='org.freedesktop.Notifications',member='Notify'"], 0)),
                   None, Gio.DBusCallFlags.NONE, -1, None)
    if not os.path.exists(STORE):
        save({"items": [], "seen": 0})
    GLib.MainLoop().run()


if __name__ == "__main__":
    main()

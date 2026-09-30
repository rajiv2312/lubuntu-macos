# Every change, explained

This is the full log of what was changed to make Lubuntu 26.04 (LXQt 2.3) look and behave like macOS:
what each change does, **where** it lives, and **why** it was done that way. Everything here is
reproduced by [`lubuntu/install.sh`](https://github.com/rajiv2312/lubuntu-macos/blob/main/lubuntu/install.sh); the files it copies are under
[`lubuntu/files/`](https://github.com/rajiv2312/lubuntu-macos/tree/main/lubuntu/files).

Paths use `~` for your home folder. In the repository, personal values are placeholders that the
installer fills in: `@HOME@` (your home folder) and `@REALNAME@` (your name, used in "Log Out …").

Items marked **(personal preference)** are the author's own choices rather than part of the macOS
look. They are included so the result matches the screenshots; change them freely.

- [How it was done](#how-it-was-done)
- [1. Themes, icons, cursors and fonts](#1-themes-icons-cursors-and-fonts)
- [2. Windows and title bars](#2-windows-and-title-bars)
- [3. The menu bar (top bar)](#3-the-menu-bar-top-bar)
- [4. Drop-down menus: Wi-Fi, Bluetooth, Sound, Battery, Notifications](#4-drop-down-menus-wi-fi-bluetooth-sound-battery-notifications)
- [5. Notification Center (click the clock)](#5-notification-center-click-the-clock)
- [6. The Dock](#6-the-dock)
- [7. Launchpad and Spotlight](#7-launchpad-and-spotlight)
- [8. Finder](#8-finder)
- [9. Terminal](#9-terminal)
- [10. Apps renamed like macOS](#10-apps-renamed-like-macos)
- [11. Notifications, dialogs and the password prompt](#11-notifications-dialogs-and-the-password-prompt)
- [12. Wallpapers and screensaver](#12-wallpapers-and-screensaver)
- [13. Login screen and lock screen](#13-login-screen-and-lock-screen)
- [14. Personal preferences](#14-personal-preferences)
- [Programs written for this project](#programs-written-for-this-project)
- [System files (outside your home folder)](#system-files-outside-your-home-folder)
- [Quirks worth knowing](#quirks-worth-knowing)
- [Undo](#undo)

## How it was done

The whole setup was built over a few days by describing each change to an AI coding agent
([Claude Code](https://claude.com/claude-code)), checking the result on screen, and iterating.
Nothing was edited by hand. Two rules were followed throughout:

- **Back up first.** Before the first change, every file that would be touched was copied to a
  dated backup folder together with a `restore.sh` that puts it all back. The installer does the same
  (`~/macos-look-backup/<date>/restore.sh`).
- **Verify, don't assume.** Every change was checked afterwards (config re-read, screenshot measured,
  click simulated), and bigger features got their own undo script.

Third-party themes come from [vinceliuice](https://github.com/vinceliuice)'s WhiteSur and McMojave
projects and are downloaded by the installer at pinned versions (not copied into this repository).

## 1. Themes, icons, cursors and fonts

| What | Setting | Where |
|---|---|---|
| **GTK apps** use WhiteSur-Light (light mode, like macOS "Light" appearance). WhiteSur-Dark is also built so you can switch. | `gtk-theme-name = WhiteSur-Light` | `~/.config/gtk-3.0/settings.ini`, `~/.config/gtk-4.0/settings.ini`, `~/.gtkrc-2.0`, gsettings `org.gnome.desktop.interface gtk-theme`, `color-scheme 'prefer-light'` |
| **Qt/LXQt apps** use the WhiteSur Kvantum theme through LXQt's own settings (not qt5ct, which would break LXQt 2's Qt6 apps). | `style=kvantum` | `~/.config/lxqt/lxqt.conf`, `~/.config/Kvantum/kvantum.kvconfig` (`theme=WhiteSur`) |
| Kvantum fixes: **opaque windows** (WhiteSur makes them see-through expecting a blur the compositor doesn't do), **bigger tabs**, text-only dialog buttons, **blue default button**. | `translucent_windows=false`, `reduce_*_opacity=0`, `[Tab] text.margin.*`, `iconless_pushbutton=true` | `~/.config/Kvantum/WhiteSur/WhiteSur.kvconfig` and `WhiteSurDark.kvconfig`, `WhiteSur.svg` |
| Kvantum: **Finder-style column headers**: thin grey divider between column titles and titles centred vertically. | SVG element `header-separator`; `[HeaderSection] frame.top=0 frame.bottom=4` | same files |
| **Icons**: WhiteSur. A small companion theme **WhiteSur-macOS** uses WhiteSur's *colour* folder icons at 24 px (Finder's list view) while keeping the monochrome ones at 16/22 px (Finder sidebar), like macOS. | `icon_theme=WhiteSur-macOS` | `~/.local/share/icons/WhiteSur-macOS/` (symlinks into WhiteSur), `~/.config/lxqt/lxqt.conf` |
| **Cursors**: McMojave, plus **McMojave-macOS**, which maps every resize cursor to macOS-style double arrows. | `cursor_theme=McMojave-macOS` | `~/.local/share/icons/McMojave-macOS/`, `~/.icons/default/index.theme`, `~/.config/lxqt/session.conf`, GTK settings, `~/.Xresources` |
| **Font**: Inter (a free font close to Apple's San Francisco, which can't be redistributed) at **12 pt everywhere**, which on a 14" 1080p screen is the same physical size as macOS's 13 pt system font. | Qt `font="Inter,12,…"`, GTK `Inter 12` | `lxqt.conf`, GTK settings, gsettings `font-name`, Openbox, desktop, Launchpad |

## 2. Windows and title bars

| What | Where |
|---|---|
| **Openbox themes WhiteSur-Light-Openbox / WhiteSur-Dark-Openbox**: made for this project. Red/yellow/green **traffic-light buttons** drawn as 16 px circle bitmaps with per-button colours (the ×, −, + glyph appears on hover), grey buttons on inactive windows, WhiteSur colours. | `~/.themes/WhiteSur-*-Openbox/openbox-3/` (`themerc` + `*.xbm`) |
| Buttons on the **left** in macOS order, **Inter 12 bold** titles (title bars are 32 px). Openbox sizes buttons from the title font, so the font must be at least 12 pt for 16 px buttons. | `~/.config/openbox/rc.xml`: `<titleLayout>CIML</titleLayout>`, `<font place="ActiveWindow">` |
| Dragging the **top edge** of a title bar moves the window (Openbox made the top 6 px a resize strip); dragging a **maximised** window's title bar un-maximises it. | `rc.xml` `<context name="Top">` / `"Titlebar"` mouse bindings |
| **Pull a maximised window out** by its header bar, for apps that draw their own title bar (GNOME Terminal). Openbox refuses to move maximised client-side-decorated windows. | program `~/.local/share/macos-theme/drag-unmaximize` (autostart) |
| **Invisible resize zones** a few pixels outside the front window's edges, like macOS (Openbox only resizes from its 1 px border). | program `resize-zones` (autostart) |
| **Inactive windows look inactive** in GTK header-bar apps (lighter title bar, grey traffic lights). GTK needs `_NET_WM_STATE_FOCUSED`, which Openbox doesn't provide. | program `focus-hint` (autostart) |
| GTK header bars: soft grey, hairline outline, no white shadow band, **GNOME Terminal's header bar pulled in to 32 px** so it matches the other title bars. | `~/.config/gtk-3.0/gtk.css`, `~/.config/gtk-4.0/gtk.css` (`terminal-window headerbar { margin: -11px … }`) |
| **Rounded corners** (10 px windows, 6 px menus) and subtle **open/close animations**. | `~/.config/picom.conf` (a copy is kept as `~/.local/share/macos-theme/picom-animations.conf`; undo: `undo-animations`) |

## 3. The menu bar (top bar)

The top bar is two panels side by side: a **global menu** on the left and LXQt's panel on the right.

| What | Where |
|---|---|
| **Global menu** (app name + File / Edit / View…, like macOS) with the **Apple menu** (About This Computer, System Settings…, App Store…, Force Quit…, Sleep, Restart…, Shut Down…, Lock Screen, Log Out *name*…). Built with vala-panel + vala-panel-appmenu; apps that export menus (Chrome, GTK apps) show them. | profile `~/.config/vala-panel/macos-menu`, Apple menu `~/.local/share/macos-theme/apple-menu.ui`, private style `~/.local/share/macos-theme/vala-panel-config/gtk-3.0/gtk.css`, autostart `macos-global-menu.desktop` |
| Menu titles at **16 px = 12 pt** (vala-panel's font size is in *pixels*), **~24 px apart** like macOS's 20 pt gaps, app name in bold. | `font='Inter 16'` in the profile; `menubar > menuitem { padding: 0 11px }` |
| Right side: **30 px light bar** (`#f2f2f2`), 18 px icons, **dark monochrome tray icons** (Papirus-Light, only for the panel), regular-weight clock. | `~/.config/lxqt/panel.conf` (`panelSize=30`, `iconSize=18`, `background-color`, `[General] iconTheme=Papirus-Light`) |
| **No hover tooltips** on menu-bar icons (macOS doesn't show them). | `~/.local/share/lxqt/themes/kvantum-macos/lxqt-panel.qss` (`QToolTip { opacity: 0 }`) |
| Apps that only draw colour icons (Lubuntu Update, clipboard manager) sit behind the **"+"** button; apps replaced by our own menus are hidden. | `panel.conf` `[statusnotifier] autoHideList=…`, `hideList=nm-tray, blueman, lxqt-powermanagement, lxqt-notificationd` |
| The LXQt panel theme **kvantum-macos** is a copy of LXQt's *kvantum* theme with a light, readable style. | `~/.local/share/lxqt/themes/kvantum-macos/` |
| **Spotlight** magnifier and **clock** (see sections 5 and 7). | `panel.conf` `[spotlight]`, `[nclock]` |

## 4. Drop-down menus: Wi-Fi, Bluetooth, Sound, Battery, Notifications

On macOS, clicking a menu-bar icon opens a small rounded panel instead of an app. One small GTK program
draws all five: [`status-menu.py`](https://github.com/rajiv2312/lubuntu-macos/blob/main/lubuntu/files/home/.local/share/macos-theme/status-menu.py).
Each icon in the top bar is an LXQt "custom command" widget whose icon comes from
`status-icon <kind>` (refreshed every few seconds) and whose click runs `status-menu <kind>`.

| Menu | What it shows | Uses |
|---|---|---|
| **Wi-Fi** | On/off switch, current network (blue), known and other networks with signal and lock icons, "Wi-Fi Settings…". Rescans when opened. | `nmcli`. A new secured network is joined through NetworkManager, which asks for the password through the existing password agent (nm-tray), so no password passes through this program. |
| **Bluetooth** | On/off switch, paired devices (click to connect/disconnect), "Bluetooth Settings…". | `bluetoothctl`, Blueman |
| **Sound** | Horizontal volume slider, output devices, "Sound Settings…". Scrolling on the icon changes the volume. | `wpctl` (PipeWire), pavucontrol-qt |
| **Battery** | Percentage, power source, "Fully Charged" / time remaining, apps using lots of CPU, "Battery Settings…". | `upower`, `ps`, LXQt power settings |
| **Notifications** (bell) | Notification cards (app, time, title, text, ×), "Clear All", unread dot on the bell. | history recorded by `notification-log.py` (see below) |

Widgets in `panel.conf`: `[bellstatus] [batstatus] [btstatus] [wifistatus] [soundstatus]`
(`type=customcommand`, `outputFormat=1` = icon from theme name). Undo: `~/.local/share/macos-theme/undo-status-menus`.

**Notification history.** LXQt keeps no history other programs can read, so
[`notification-log.py`](https://github.com/rajiv2312/lubuntu-macos/blob/main/lubuntu/files/home/.local/share/macos-theme/notification-log.py) (autostart)
watches notifications on the session D-Bus read-only and keeps the last 50 in
`~/.local/share/macos-theme/notifications.json` (readable only by you). It never sends or changes anything.

## 5. Notification Center (click the clock)

Clicking the date/time opens a **Notification Center** that slides in from the right with a
**Calendar** widget (weekday in red, big date, month grid with today circled) and a **World Clock**
widget (four analog clocks, dark faces at night, "Today/Tomorrow" and hour offsets including
half-hour zones). Clicking the clock again, clicking elsewhere or pressing Esc closes it.

- program: [`notification-center.py`](https://github.com/rajiv2312/lubuntu-macos/blob/main/lubuntu/files/home/.local/share/macos-theme/notification-center.py)
- clock text: `notification-center-clock` (same format as before: `Mon 28 Sep  11:28 PM`)
- panel widget `[nclock]` replaces LXQt's clock (whose click opened a calendar app)
- world clocks: Cupertino, New York, London, **India** **(personal preference)**: edit `CITIES` in the program

## 6. The Dock

- **Plank**, bottom centre, 64 px icons with **200 % magnification** on hover, intelligent auto-hide,
  **white translucent background** with a hairline border.
  Settings: gsettings `net.launchpad.plank.dock.settings` (`lubuntu/files/gsettings/plank-dock1.txt`),
  theme `~/.local/share/plank/themes/WhiteSur-Dark/dock.theme`, autostart `plank.desktop`.
- Pinned: **Finder, Launchpad, Chrome, Terminal, Claude, Photo Booth, Preview, Trash**
  **(personal preference)**. The installer only pins apps that are installed.
- Hover labels use macOS names. For renamed apps, Plank/BAMF only matches windows to the renamed
  launcher if it has `StartupWMClass=`; without it the dock shows a duplicate icon.
- The clipboard manager's popup is kept out of the dock (Openbox rule `skip_taskbar` in `rc.xml`).

## 7. Launchpad and Spotlight

Both are [rofi](https://github.com/davatorium/rofi) with custom themes.

| | Opens with | Look | Files |
|---|---|---|---|
| **Launchpad** | `F4`, rocket in the Dock | Full-screen grid of large app icons over a blurred, darkened wallpaper, search field at the top, one click opens | `~/.local/share/macos-theme/launchpad` + `launchpad.rasi` + `launchpad-bg.jpg` |
| **Spotlight** | `Super+Space`, magnifier in the menu bar | Rounded light search bar in the upper middle, results with icons and blue highlight | `spotlight` + `spotlight.rasi` (dark variant `spotlight-dark.rasi`) |

Shortcuts are in `~/.config/lxqt/globalkeyshortcuts.conf`. The key name must be `space`
(X keysym), not `Space`.

## 8. Finder

PCManFM-Qt, renamed **Finder** (launcher `~/.local/share/applications/pcmanfm-qt.desktop`, WhiteSur's Finder icon).

| What | Setting (`~/.config/pcmanfm-qt/lxqt/settings.conf`) |
|---|---|
| Sidebar: Places list instead of a folder tree; Computer and Trash hidden (Trash lives in the Dock); Favorites-style bookmarks for Documents, Downloads, Pictures, Music, Videos | `SidePaneMode=places`, `HiddenPlaces=computer:///, trash:///`, bookmarks in `~/.config/gtk-3.0/bookmarks` |
| No in-window menu bar (a ☰ button instead) | `ShowMenuBar=false` |
| **List view by default**, columns **Name, Type, Size, Modified** (Created/Owner/Group hidden), **resizable columns** | `Mode=detailed`, `HiddenColumns=4, 6, 7`, `CustomColumnWidths=…` (setting widths turns off auto-resize, so the dividers can be dragged) |
| Sort by **Modified**, window maximised, column widths | `SortColumn=mtime`, `LastWindowMaximized=true`, `CustomColumnWidths=353, 130, 119, 180, …` **(personal preference)** |
| Column titles indented from the divider like Finder | two leading spaces in the translation file (below) |
| macOS wording in dialogs ("Are you sure you want to move the selected items to the Trash?", "Making aliases for:", …) and the column titles | custom translation `/usr/share/libfm-qt6/translations/libfm-qt_en_US.qm`, source [`libfm-qt_en_US.ts`](https://github.com/rajiv2312/lubuntu-macos/blob/main/lubuntu/files/system/libfm-qt_en_US.ts) (compiled with `lrelease`) |

Not possible (tested): hiding the sidebar's "Lists" drop-down or colouring the sidebar. Any Qt
stylesheet makes the desktop process (which also runs Finder) crash, even an empty one.

## 9. Terminal

**GNOME Terminal** (chosen over QTerminal because it has a visible "+" new-tab button in the title bar).

- gsettings `org.gnome.Terminal.Legacy.Settings`: `headerbar true` (header bar with traffic lights
  and "+"), `default-show-menubar false` (`lubuntu/files/gsettings/gnome-terminal-app.txt`)
- profile font **DejaVu Sans Mono 12** (DejaVu Sans Mono is what Apple's Menlo is based on)
- Dock pin, desktop icon, `Ctrl+Alt+T` and Finder's "Open in Terminal" all use GNOME Terminal;
  QTerminal stays installed but hidden. QTerminal settings (light colours, no menu bar, bigger
  tabs via `~/.config/qterminal.org/style.qss`) are included in case you prefer it.

## 10. Apps renamed like macOS

User copies in `~/.local/share/applications/` (the system files are untouched), each with
`StartupWMClass=` so the Dock groups windows correctly:

| Linux app | Shown as |
|---|---|
| PCManFM-Qt | **Finder** |
| GNOME Terminal / QTerminal | **Terminal** |
| LXImage-Qt | **Preview** |
| FeatherPad | **TextEdit** |
| Cheese (snap) | **Photo Booth** (optional, the installer adds it if Cheese is installed) |

## 11. Notifications, dialogs and the password prompt

- **Notification pop-ups**: light rounded cards at the top right
  (`~/.local/share/lxqt/themes/kvantum-macos/lxqt-notificationd.qss`, `~/.config/lxqt/notifications.conf` `placement=top-right`).
- **Password prompt** (when an app needs admin rights): the MATE polkit agent instead of LXQt's,
  centred, no title bar, rounded, "Details" hidden, blue default button
  (`~/.config/autostart/polkit-mate-authentication-agent-1.desktop`,
  `~/.local/share/macos-theme/polkit-agent-config/gtk-3.0/gtk.css`, Openbox and picom rules; LXQt's agent disabled with `Hidden=true`).
- **Default buttons are blue** in GTK dialogs (`~/.config/gtk-3.0/gtk.css`) and Qt dialogs (Kvantum).

## 12. Wallpapers and screensaver

- Wallpapers: the MIT-licensed [WhiteSur wallpaper pack](https://github.com/vinceliuice/WhiteSur-wallpapers)
  (Big Sur and Monterey in four times of day, Ventura and Sonoma light/dark; macOS-style recreations,
  not Apple's own images), saved at 1080p in `~/.local/share/macos-theme/wallpapers/`.
  Desktop, Launchpad background and login screen use **Sonoma Light**.
- Screensaver (xscreensaver, `~/.xscreensaver`): **Ken Burns** slideshow (`glslideshow`) after 10 minutes over
  the **colour** wallpapers, linked in `~/.local/share/macos-theme/screensaver/` (Big Sur Dark and Monterey Dark
  are greyscale images and made the screensaver look monochrome, so they are left out). **Flurry** (a port of the
  classic Mac OS X screensaver) is the alternative.

## 13. Login screen and lock screen

- **Login screen**: a small SDDM theme written for this project (`/usr/share/sddm/themes/macos/`,
  source [`sddm-theme-macos/Main.qml`](https://github.com/rajiv2312/lubuntu-macos/blob/main/lubuntu/files/system/sddm-theme-macos/Main.qml)): blurred
  wallpaper, date and big clock, round avatar, pill-shaped password field that shakes on a wrong
  password, Sleep/Restart/Shut Down buttons, session picker. It only uses QtQuick (no KDE Plasma
  libraries). Enabled by `/etc/sddm.conf.d/zz-macos-theme.conf`.
- **Lock screen = the same macOS screen.** On macOS the lock and login screens are the same.
  [`macos-lock`](https://github.com/rajiv2312/lubuntu-macos/blob/main/lubuntu/files/home/.local/share/macos-theme/macos-lock) asks SDDM to show its login
  screen while your session keeps running (D-Bus `SwitchToGreeter`); logging in there returns to your
  session. Used by the Apple menu's Lock Screen, `Ctrl+Alt+L` and closing the lid
  (`~/.config/lxqt/lxqt.conf` `[Screensaver] lock_command`).
- **Why it is safe:** your unlocked session is still running on another console, so the login screen
  must not allow `Ctrl+Alt+F1…F12`. Three lines added to `/usr/share/sddm/scripts/Xsetup` apply
  `setxkbmap -option srvrkeys:none` to the login screen only. `macos-lock` checks those lines **every
  time** and falls back to xscreensaver's classic lock if they're missing (for example after an SDDM
  update), if SDDM can't switch, or if the switch doesn't happen within 5 seconds. It also waits until
  the login screen is on screen before letting the laptop sleep.
  (Xorg's `-novtswitch` looks like it would do this but doesn't block the keys.)
- Undo: `~/.local/share/macos-theme/undo-macos-lock`.

## 14. Personal preferences

Included on purpose so the result matches the author's machine. Change them if you like:

- Finder: sort by Modified, column widths, maximised window
- Dock pins: Chrome, Claude, Photo Booth
- World clocks: Cupertino, New York, London, India
- Wallpaper: Sonoma Light; screensaver: Ken Burns
- Light mode (WhiteSur-Dark and the dark Openbox theme are installed too)

## Programs written for this project

All in `~/.local/share/macos-theme/`. Small, commented, no extra dependencies beyond Python 3 and GTK 3.

| Program | What it does |
|---|---|
| `notification-center.py` (+ `notification-center`, `notification-center-clock`) | Notification Center with Calendar and World Clock widgets, opened from the clock |
| `status-menu.py` (+ `status-menu`, `status-icon`) | The Wi-Fi, Bluetooth, Sound, Battery and Notifications drop-down menus and their menu-bar icons |
| `notification-log.py` | Records notifications for the bell's list (read-only D-Bus monitor) |
| `macos-lock` | Lock screen via the macOS login screen, with safe fallback |
| `launchpad`, `spotlight` | Open/close the rofi Launchpad and Spotlight |
| `drag-unmaximize` | Drag a maximised header-bar window out |
| `resize-zones` | Invisible resize margins around the front window |
| `focus-hint` | Makes GTK header bars show inactive windows |
| `undo-status-menus`, `undo-macos-lock`, `undo-animations` | Remove individual features and put the originals back |

## System files (outside your home folder)

The installer changes only these (with `sudo`), and `restore.sh` removes them again:

| File | Why |
|---|---|
| `/usr/share/sddm/themes/macos/` | the login screen theme |
| `/etc/sddm.conf.d/zz-macos-theme.conf` | makes SDDM use it |
| `/usr/share/sddm/themes/lubuntu/theme.conf.user` | same wallpaper on the stock Lubuntu login theme (fallback) |
| `/usr/share/backgrounds/macos-look-wallpaper.jpg` | login wallpaper (SDDM can't read your home folder) |
| `/usr/share/sddm/scripts/Xsetup` (3 lines) | blocks Ctrl+Alt+F-keys on the login screen so it can be the lock screen |
| `/usr/share/libfm-qt6/translations/libfm-qt_en_US.qm` | Finder's macOS wording and column titles |

## Quirks worth knowing

Things that took a while to find out, in case you build on this:

- LXQt 2 is Qt6: use Kvantum through LXQt's own settings, not `QT_QPA_PLATFORMTHEME=qt5ct`.
- The LXQt menu needs `ownIcon=true` next to `icon=` for a custom icon; the panel's own icon theme
  (`iconTheme=`) must be in `[General]` of `panel.conf`, not in the panel section.
- LXQt "custom command" widgets: `outputFormat=1` shows an icon from the theme name ("icon" is not
  valid); the click command must return immediately, or later clicks are ignored.
- Openbox: button size = title font height − 2. `rc.xml` has comment lines inside `<font>` blocks.
- Plank deletes half-written `.dockitem` files: stop Plank before writing them. BAMF only matches a
  renamed launcher with `StartupWMClass=`.
- GTK 3 keeps GNOME Terminal's header bar at 36 px whatever `min-height` says; negative margins
  scoped to `terminal-window headerbar` work.
- Kvantum ignores `text.margin` for list headers; use the `header-separator` element and frame sizes.
- A Qt stylesheet on PCManFM-Qt's desktop process crashes it, even an empty one.
- vala-panel's font size is in pixels.
- xscreensaver image screensavers need `/usr/libexec/xscreensaver` on `PATH` when started by hand
  (the daemon adds it itself).
- SDDM `SwitchToGreeter` + logging in returns to the existing session (the same user and session type).

## Undo

- Everything: `~/macos-look-backup/<date>/restore.sh` (printed by the installer), then log out and back in.
- Single features: `~/.local/share/macos-theme/undo-status-menus`, `undo-macos-lock`, `undo-animations`.

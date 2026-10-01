#!/usr/bin/env bash
# Linux, dressed as macOS: installer for Lubuntu 26.04 (LXQt)
#
# What it does:
#   1. backs up everything it will touch and writes a restore.sh next to the backup
#   2. installs packages (Inter font, Plank dock, rofi, global menu, GNOME Terminal, ...)
#   3. downloads WhiteSur / McMojave themes at pinned versions and builds them
#   4. copies the configs (menu bar, dock, Launchpad, Spotlight, Finder, title bars, ...)
#   5. installs the macOS-style login screen (needs sudo)
#
# Undo: run the restore.sh printed at the end, then log out and back in.
# Not affiliated with Apple. Themes by vinceliuice (WhiteSur, McMojave), see README.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILES="$HERE/files"
MT="$HOME/.local/share/macos-theme"
TS="$(date +%Y%m%d-%H%M%S)"
BK="$HOME/macos-look-backup/$TS"
WORK="$(mktemp -d)"
REALNAME="$(getent passwd "$USER" | cut -d: -f5 | cut -d, -f1)"; REALNAME="${REALNAME:-$USER}"

say(){ printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn(){ printf '\033[33m!! %s\033[0m\n' "$*"; }
trap 'rm -rf "$WORK"' EXIT

# ---------------------------------------------------------------- checks
[ "$(id -u)" -ne 0 ] || { echo "Run as your normal user, not root (sudo is used where needed)."; exit 1; }
command -v lxqt-panel >/dev/null || { echo "This script is for Lubuntu / LXQt (lxqt-panel not found). For regular Ubuntu use ../gnome/install.sh"; exit 1; }
. /etc/os-release
[ "${VERSION_ID:-}" = "26.04" ] || warn "Built and tested on Ubuntu/Lubuntu 26.04; you have ${PRETTY_NAME:-unknown}. Continuing anyway."
[ -n "${DISPLAY:-}" ] || warn "No graphical session detected; some settings may only apply after you log in."

cat <<EOF
This will restyle your Lubuntu desktop to look like macOS.
A full backup goes to: $BK
It needs sudo for packages and the login screen.
EOF
read -rp "Continue? [y/N] " a; [[ "$a" =~ ^[Yy]$ ]] || exit 0
sudo -v

# ---------------------------------------------------------------- 1. backup
say "Backing up current settings to $BK"
mkdir -p "$BK/files"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"; DESKTOP_REL="${DESKTOP_DIR#"$HOME"/}"
PATHS=(.gtkrc-2.0 .xscreensaver .Xresources .icons/default
  .config/gtk-3.0 .config/gtk-4.0 .config/lxqt .config/pcmanfm-qt .config/openbox .config/Kvantum
  .config/picom.conf .config/xdg-desktop-portal .config/vala-panel .config/qterminal.org .config/autostart .config/plank
  .local/share/macos-theme .local/share/lxqt .local/share/plank .local/share/applications
  .local/share/icons/WhiteSur-macOS .local/share/icons/McMojave-macOS
  .themes/WhiteSur-Light-Openbox .themes/WhiteSur-Dark-Openbox
  "$DESKTOP_REL/org.gnome.Terminal.desktop" "$DESKTOP_REL/computer.desktop" "$DESKTOP_REL/network.desktop" "$DESKTOP_REL/lubuntu-manual.desktop")
: > "$BK/manifest.txt"
for p in "${PATHS[@]}"; do
  if [ -e "$HOME/$p" ] || [ -L "$HOME/$p" ]; then
    mkdir -p "$BK/files/$(dirname "$p")"; cp -a "$HOME/$p" "$BK/files/$p"; echo "EXISTED $p" >> "$BK/manifest.txt"
  else echo "ABSENT $p" >> "$BK/manifest.txt"; fi
done
# gsettings we will change
{
  for k in gtk-theme icon-theme cursor-theme font-name color-scheme; do echo "org.gnome.desktop.interface $k $(gsettings get org.gnome.desktop.interface $k)"; done
} > "$BK/gsettings.txt" 2>/dev/null || true
gsettings list-recursively net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ > "$BK/plank.txt" 2>/dev/null || true
gsettings list-recursively org.gnome.Terminal.Legacy.Settings > "$BK/gnome-terminal.txt" 2>/dev/null || true

cat > "$BK/restore.sh" <<'RESTORE'
#!/usr/bin/env bash
# Undo "Linux, dressed as macOS": puts back every file that was backed up, removes the rest.
set -uo pipefail
B="$(cd "$(dirname "$0")" && pwd)"
pkill -x plank 2>/dev/null; pkill -x vala-panel 2>/dev/null
while read -r state p; do
  if [ "$state" = EXISTED ]; then rm -rf -- "$HOME/$p"; mkdir -p "$(dirname "$HOME/$p")"; cp -a "$B/files/$p" "$HOME/$p"; echo "restored ~/$p"
  elif [ -e "$HOME/$p" ] || [ -L "$HOME/$p" ]; then rm -rf -- "$HOME/$p"; echo "removed  ~/$p"; fi
done < "$B/manifest.txt"
while read -r schema key value; do gsettings set "$schema" "$key" "$value" 2>/dev/null; done < "$B/gsettings.txt"
gsettings reset-recursively net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ 2>/dev/null
gsettings reset-recursively org.gnome.Terminal.Legacy.Settings 2>/dev/null
pkill -f "$HOME/.local/share/macos-theme/" 2>/dev/null   # notification recorder, focus hint, resize zones, menus
echo "Removing the login screen theme and lock-screen protection (needs sudo)..."
sudo rm -rf /usr/share/sddm/themes/macos /etc/sddm.conf.d/zz-macos-theme.conf \
  /usr/share/sddm/themes/lubuntu/theme.conf.user /usr/share/backgrounds/macos-look-whitesur-light.jpg \
  /usr/share/backgrounds/macos-look-whitesur-dark.jpg /usr/share/backgrounds/macos-look-wallpaper.jpg \
  /usr/share/libfm-qt6/translations/libfm-qt_en_US.qm
[ -f /usr/share/sddm/scripts/Xsetup ] && sudo sed -i '/^# macos-lock: no Ctrl+Alt+F1-F12/,/^setxkbmap -option srvrkeys:none/d' /usr/share/sddm/scripts/Xsetup
echo; echo "Done. Installed packages and downloaded themes were left in place (unused)."
echo "Log out and back in to finish."
RESTORE
chmod +x "$BK/restore.sh"

# ---------------------------------------------------------------- 2. packages
say "Installing packages"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git sassc libgio-2.0-dev-bin libxml2-utils python3-pil \
  fonts-inter plank rofi picom papirus-icon-theme qt-style-kvantum \
  vala-panel vala-panel-appmenu appmenu-registrar appmenu-gtk3-module \
  gnome-terminal mate-polkit xscreensaver xscreensaver-gl fastfetch \
  upower bluez wireplumber python3-gi pavucontrol-qt nm-connection-editor imagemagick

# ---------------------------------------------------------------- 3. themes (pinned versions)
fetch(){ # repo sha dir
  git init -q "$3"; git -C "$3" fetch -q --depth 1 "https://github.com/vinceliuice/$1.git" "$2"; git -C "$3" checkout -q FETCH_HEAD; }
say "Downloading WhiteSur and McMojave themes"
fetch WhiteSur-gtk-theme  d5782652d412137e26fb8ff55b55a5572e4c6995 "$WORK/gtk"
fetch WhiteSur-icon-theme 73d8040da51a9ed74e47c7366e7e9ff437601a5c "$WORK/icons"
fetch McMojave-cursors    7d0bfc1f91028191cdc220b87fd335a235ee4439 "$WORK/cursors"
fetch WhiteSur-kde        cf4df59ce91004f7ea39358b1b8ff917d5c329f7 "$WORK/kde"
fetch WhiteSur-wallpapers 5c1d7ca20b8de0a7efe443792c19e49277262e02 "$WORK/wallpapers"

say "Building GTK themes (light + dark)"
( cd "$WORK/gtk" && ./install.sh -c light >/dev/null && ./install.sh -c dark >/dev/null )
say "Installing icons and cursors"
( cd "$WORK/icons" && ./install.sh >/dev/null )
( cd "$WORK/cursors" && ./install.sh >/dev/null )

# Finder list view: colour folder icons at 24px (WhiteSur draws them as grey outlines at 16-24px),
# monochrome ones kept for the 16/22px sidebar. Qt takes every size from the first theme that has
# an icon, so all three sizes are linked here. (index.theme comes from files/home.)
ICONS="$HOME/.local/share/icons"; WS="$ICONS/WhiteSur"; WM="$ICONS/WhiteSur-macOS"
rm -rf "$WM"/places; mkdir -p "$WM/places/16" "$WM/places/22" "$WM/places/24"
for f in "$WS"/places/scalable/*.svg; do b="$(basename "$f")"; [ -e "$WS/places/24/$b" ] && ln -sf "$(readlink -f "$f")" "$WM/places/24/$b"; done
for sz in 16 22; do for f in "$WS/places/$sz"/*.svg; do ln -sf "$(readlink -f "$f")" "$WM/places/$sz/$(basename "$f")"; done; done

# macOS-style double-arrow resize cursors on top of McMojave
MC="$ICONS/McMojave-macOS/cursors"; mkdir -p "$MC"
while IFS=: read -r name target; do ln -sfn "$ICONS/McMojave-cursors/cursors/$target" "$MC/$name"; done <<'MAP'
bottom_left_corner:size_bdiag
bottom_right_corner:size_fdiag
bottom_side:size_ver
e-resize:size_hor
ew-resize:size_hor
left_side:size_hor
ne-resize:size_bdiag
n-resize:size_ver
ns-resize:size_ver
nw-resize:size_fdiag
right_side:size_hor
se-resize:size_fdiag
s-resize:size_ver
sw-resize:size_bdiag
top_left_corner:size_fdiag
top_right_corner:size_bdiag
top_side:size_ver
w-resize:size_hor
MAP

say "Installing Kvantum theme (with fixes: opaque windows, bigger tabs, blue default button)"
mkdir -p "$HOME/.config/Kvantum"; rm -rf "$HOME/.config/Kvantum/WhiteSur"; cp -r "$WORK/kde/Kvantum/WhiteSur" "$HOME/.config/Kvantum/"
K="$HOME/.config/Kvantum/WhiteSur"
for v in WhiteSur WhiteSurDark; do
  sed -i 's/^translucent_windows=true/translucent_windows=false/; s/^reduce_window_opacity=.*/reduce_window_opacity=0/; s/^reduce_menu_opacity=.*/reduce_menu_opacity=0/; s/^iconless_pushbutton=false/iconless_pushbutton=true/; s/^normal_default_pushbutton=true/normal_default_pushbutton=false/' "$K/$v.kvconfig"
  python3 - "$K/$v.kvconfig" <<'PY'
import sys,re;p=sys.argv[1];s=open(p).read()
a=s.index('[Tab]\n'); b=s.index('\n[',a+1); t=s[a:b]
for k,v in (('left',16),('right',16),('top',8),('bottom',8)): t=re.sub(rf'text\.margin\.{k}=\d+',f'text.margin.{k}={v}',t)
open(p,'w').write(s[:a]+t+s[b:])
PY
done
sed -i 's/style="opacity:0.6;fill:#a0a0a0"/style="opacity:0.9;fill:#007aff"/' "$K/WhiteSur.svg"
sed -i 's/style="opacity:0.15;fill:#ffffff;fill-opacity:0.16751272"/style="opacity:0.9;fill:#0a84ff;fill-opacity:0.16751272"/' "$K/WhiteSurDark.svg"
# Finder-style column headers: thin grey divider between column titles (Kvantum's own
# "header-separator" element, which WhiteSur doesn't ship) and titles centred vertically
for v in WhiteSur:c8c8c8 WhiteSurDark:4a4a4a; do n="${v%%:*}"; c="${v##*:}"
  grep -q 'id="header-separator"' "$K/$n.svg" || sed -i "s|</svg>|<g id=\"header-separator\"><rect x=\"-2900\" y=\"-3000\" width=\"1\" height=\"20\" fill=\"#000000\" fill-opacity=\"0\"/><rect x=\"-2900\" y=\"-2996\" width=\"1\" height=\"12\" fill=\"#$c\"/></g>\n</svg>|" "$K/$n.svg"
  sed -i '/^\[HeaderSection\]/,/^\[/{s/^frame.top=.*/frame.top=0/; s/^frame.bottom=.*/frame.bottom=4/}' "$K/$n.kvconfig"
done
printf '[General]\ntheme=WhiteSur\n' > "$HOME/.config/Kvantum/kvantum.kvconfig"

# ---------------------------------------------------------------- 4. configs
say "Copying configuration"
mkdir -p "$MT"
tmpl(){ # copy tree $1 -> $2, filling in @HOME@ / @REALNAME@ in text files
  cp -a "$1/." "$2/"
  ( cd "$1" && find . -type f ) | while read -r f; do
    if grep -Iq . "$2/$f" 2>/dev/null; then sed -i "s|@HOME@|$HOME|g; s|@REALNAME@|$REALNAME|g" "$2/$f"; fi
  done
}
tmpl "$FILES/home" "$HOME"

# links that point into this user's home
ln -sfn "$HOME/.config/vala-panel" "$MT/vala-panel-config/vala-panel"
mkdir -p "$MT/vala-panel-config/gtk-3.0" "$MT/polkit-agent-config/gtk-3.0" "$MT/polkit-agent-config/gtk-4.0"
ln -sf "$HOME/.config/gtk-3.0/settings.ini" "$MT/vala-panel-config/gtk-3.0/settings.ini"
ln -sf "$HOME/.config/gtk-3.0/settings.ini" "$MT/polkit-agent-config/gtk-3.0/settings.ini"

# Apple logo (taken from the WhiteSur download, not shipped in this repo)
sed 's|width="48" height="48"|width="40" height="40" viewBox="3.16 4.05 40 40"|' \
  "$WORK/gtk/src/assets/gnome-shell/activities/activities-apple.svg" > "$MT/apple-menu.svg"
sed 's/fill:#fff/fill:#1d1d1f/' "$MT/apple-menu.svg" > "$MT/apple-menu-dark.svg"

# wallpapers: the WhiteSur pack (Big Sur, Monterey, Ventura, Sonoma) at 1080p, used by the desktop,
# the Ken Burns screensaver (~/.xscreensaver) and the login screen; plus the blurred Launchpad background
python3 - "$WORK/wallpapers" "$MT/wallpapers" <<'PY'
import os, sys; from PIL import Image
src, dst = sys.argv[1:]; os.makedirs(dst, exist_ok=True)
for n in ['WhiteSur-light','WhiteSur','WhiteSur-morning','WhiteSur-dark','Monterey-light','Monterey','Monterey-morning',
          'Monterey-dark','Ventura-light','Ventura-dark','Sonoma-light','Sonoma-dark']:
    p = next((f'{src}/{r}/{n}.jpg' for r in ('1080p','4k') if os.path.exists(f'{src}/{r}/{n}.jpg')), None)
    if not p: continue
    im = Image.open(p).convert('RGB')
    if im.size != (1920, 1080): im = im.resize((1920, 1080), Image.LANCZOS)
    base, _, var = n.partition('-')
    im.save(f"{dst}/{'Big Sur' if base == 'WhiteSur' else base}{' ' + var.capitalize() if var else ' Day'}.jpg", quality=92)
PY
# screensaver: colour wallpapers only (Big Sur Dark and Monterey Dark are greyscale images)
mkdir -p "$MT/screensaver"; rm -f "$MT/screensaver"/*
for f in "$MT"/wallpapers/*.jpg; do case "$(basename "$f")" in "Big Sur Dark.jpg"|"Monterey Dark.jpg") ;; *) ln -sf "$f" "$MT/screensaver/";; esac; done
python3 - "$MT" <<'PY'
import sys; from PIL import Image, ImageFilter, ImageEnhance
m=sys.argv[1]; im=Image.open(m+'/wallpapers/Sonoma Light.jpg').convert('RGB')
im=im.resize((480,270),Image.LANCZOS).filter(ImageFilter.GaussianBlur(10)).resize((1920,1080),Image.BICUBIC)
ImageEnhance.Brightness(im).enhance(0.72).save(m+'/launchpad-bg.jpg',quality=90)
PY
gtk-update-icon-cache -f "$HOME/.local/share/icons/WhiteSur-macOS" >/dev/null 2>&1 || true

# Finder bookmarks (the usual folders, if they exist)
: > "$HOME/.config/gtk-3.0/bookmarks"
for d in DOCUMENTS DOWNLOAD PICTURES MUSIC VIDEOS; do
  p="$(xdg-user-dir $d 2>/dev/null || true)"
  if [ -n "$p" ] && [ "$p" != "$HOME" ] && [ -d "$p" ]; then echo "file://$p $(basename "$p")" >> "$HOME/.config/gtk-3.0/bookmarks"; fi
done

# cursor for LXQt session
S="$HOME/.config/lxqt/session.conf"; touch "$S"
grep -q '^\[Mouse\]' "$S" || printf '\n[Mouse]\n' >> "$S"
sed -i '/^cursor_theme=/d; /^cursor_size=/d' "$S"; sed -i '/^\[Mouse\]/a cursor_theme=McMojave-macOS\ncursor_size=24' "$S"

# desktop: renamed Terminal launcher, drop the Computer/Network/Manual shortcuts (moved into the backup)
mkdir -p "$DESKTOP_DIR"
for f in computer network lubuntu-manual; do rm -f "$DESKTOP_DIR/$f.desktop"; done
cp "$FILES/desktop/org.gnome.Terminal.desktop" "$DESKTOP_DIR/"; chmod +x "$DESKTOP_DIR/org.gnome.Terminal.desktop"
gio set "$DESKTOP_DIR/org.gnome.Terminal.desktop" metadata::trusted true 2>/dev/null || true

# dock: pin only apps that exist here
DOCK="'finder.dockitem', 'launchpad.dockitem'"
if [ -e /usr/share/applications/google-chrome.desktop ]; then DOCK="$DOCK, 'google-chrome.dockitem'"; else rm -f "$HOME/.config/plank/dock1/launchers/google-chrome.dockitem"; fi
DOCK="$DOCK, 'terminal.dockitem'"
# Claude desktop app, if installed (its launcher comes with the app, not from this repo)
if [ -e "$HOME/.local/share/applications/com.anthropic.Claude.desktop" ] || [ -e /usr/share/applications/com.anthropic.Claude.desktop ]; then
  DOCK="$DOCK, 'claude.dockitem'"
  [ -e "$HOME/.local/share/applications/com.anthropic.Claude.desktop" ] || \
    sed -i 's|@HOME@/.local/share/applications/|/usr/share/applications/|; s|'"$HOME"'/.local/share/applications/|/usr/share/applications/|' "$HOME/.config/plank/dock1/launchers/claude.dockitem"
else rm -f "$HOME/.config/plank/dock1/launchers/claude.dockitem"; fi
# Photo Booth (the Cheese snap, renamed) only if it is installed: sudo snap install cheese
if [ -x /snap/bin/cheese ]; then DOCK="$DOCK, 'photobooth.dockitem'"
else rm -f "$HOME/.config/plank/dock1/launchers/photobooth.dockitem" "$HOME/.local/share/applications/cheese_cheese.desktop"; fi
DOCK="$DOCK, 'lximage-qt.dockitem', 'trash.dockitem'"

say "Applying settings"
gsettings set org.gnome.desktop.interface gtk-theme 'WhiteSur-Light'
gsettings set org.gnome.desktop.interface icon-theme 'WhiteSur'
gsettings set org.gnome.desktop.interface cursor-theme 'McMojave-macOS'
gsettings set org.gnome.desktop.interface font-name 'Inter 12'
gsettings set org.gnome.desktop.interface color-scheme 'prefer-light'
apply_list(){ # "schema key value" lines -> gsettings set (optional schema override in $2)
  while read -r schema key value; do [ -n "$key" ] || continue; gsettings set "${2:-$schema}" "$key" "$value" 2>/dev/null || warn "could not set $key"; done < "$1"; }
apply_list <(grep -v ' dock-items ' "$FILES/gsettings/plank-dock1.txt") net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/
gsettings set net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/ dock-items "[$DOCK]"
apply_list <(grep -vE ' (schema-version|always-check-default-terminal) ' "$FILES/gsettings/gnome-terminal-app.txt")
PROFILE="$(gsettings get org.gnome.Terminal.ProfilesList default 2>/dev/null | tr -d "'" || true)"
if [ -n "$PROFILE" ]; then
  apply_list <(grep -E ' (font|use-system-font|default-size-columns|default-size-rows) ' "$FILES/gsettings/gnome-terminal-profile.txt") \
    "org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:$PROFILE/"
fi

# ---------------------------------------------------------------- 5. system (sudo)
say "Installing the macOS-style login screen (sudo)"
sudo install -m 644 "$MT/wallpapers/Sonoma Light.jpg" /usr/share/backgrounds/macos-look-wallpaper.jpg
sudo rm -rf /usr/share/sddm/themes/macos; sudo cp -r "$FILES/system/sddm-theme-macos" /usr/share/sddm/themes/macos
sudo sed -i 's|^background=.*|background=/usr/share/backgrounds/macos-look-wallpaper.jpg|' /usr/share/sddm/themes/macos/theme.conf
sudo chown -R root:root /usr/share/sddm/themes/macos; sudo chmod -R u=rwX,go=rX /usr/share/sddm/themes/macos
sudo mkdir -p /etc/sddm.conf.d; printf '[Theme]\nCurrent=macos\n' | sudo tee /etc/sddm.conf.d/zz-macos-theme.conf >/dev/null
if [ -d /usr/share/sddm/themes/lubuntu ]; then
  printf '[General]\nbackground=/usr/share/backgrounds/macos-look-wallpaper.jpg\n' | sudo tee /usr/share/sddm/themes/lubuntu/theme.conf.user >/dev/null
fi

# Lock screen = the macOS login screen (macos-lock switches to it while your session keeps running).
# That is only safe if Ctrl+Alt+F1-F12 can't jump from the login screen to the unlocked session,
# so the login screen's keyboard gets srvrkeys:none. macos-lock checks for these lines every time
# and falls back to xscreensaver's lock if they are missing (e.g. after an SDDM update).
X=/usr/share/sddm/scripts/Xsetup
if [ -f "$X" ] && ! grep -q '^# macos-lock:' "$X"; then
  sudo sed -i '1a\
# macos-lock: no Ctrl+Alt+F1-F12 / Ctrl+Alt+Backspace on the login screen, so a locked\
# session on another console cannot be reached without the password (undo: remove these 3 lines)\
setxkbmap -option srvrkeys:none 2>/dev/null' "$X"
fi
if [ -f "$FILES/system/libfm-qt_en_US.qm" ] && [ -d /usr/share/libfm-qt6/translations ]; then
  sudo install -m 644 "$FILES/system/libfm-qt_en_US.qm" /usr/share/libfm-qt6/translations/libfm-qt_en_US.qm   # Finder-style dialog wording
fi

# ---------------------------------------------------------------- done
say "All done"
cat <<EOF

  Log out and back in to see everything (menu bar, dock, Launchpad, title bars).

  Shortcuts:  F4 = Launchpad    Super+Space = Spotlight
  Undo:       $BK/restore.sh   (then log out and back in)

EOF

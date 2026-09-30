# Edits panel.conf back to the original volume widget and tray icons; other settings are kept.
import re, sys
p = sys.argv[1]; s = open(p).read()
s = s.replace("bellstatus, batstatus, btstatus, wifistatus, soundstatus, ", "volume, ")
s = s.replace("batstatus, btstatus, wifistatus, soundstatus, ", "volume, ")
s = s.replace("btstatus, wifistatus, soundstatus, ", "volume, ")
s = s.replace("btstatus, wifistatus, ", "")
s = re.sub(r"^hideList=.*\n", "", s, flags=re.M)
s = re.sub(r"^(autoHideList=.*?)(, nm-tray)?(, blueman)?$", r"\1", s, flags=re.M)
s = re.sub(r"\n\[(bellstatus|batstatus|btstatus|wifistatus|soundstatus)\]\n(?:[^\[\n][^\n]*\n)*", "\n", s)
open(p, "w").write(s)

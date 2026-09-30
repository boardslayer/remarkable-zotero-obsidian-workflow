#!/bin/zsh
# Finder "Send to reMarkable" -- replacement for nautilus/remarkable.py.
#
# Set up as a Quick Action:
#   1. Open Automator -> New Document -> Quick Action
#   2. "Workflow receives current": files or folders, in: Finder
#   3. Add a "Run Shell Script" action, Shell: /bin/zsh, Pass input: as arguments
#   4. Paste this file's contents in, or just:  exec /path/to/send-to-remarkable.sh "$@"
#   5. Save as "Send to reMarkable". It appears under right-click -> Quick Actions.
#
# Quick Actions start with a minimal environment, so PATH and RM_DEST are set
# here rather than inherited.

export PATH="$HOME/go/bin:/opt/homebrew/bin:/usr/bin:/bin"
RM_DEST="${RM_DEST:-/Papers}"

notify() {
    # Title and body are passed as arguments, never spliced into the
    # AppleScript source, so a filename containing quotes cannot break out.
    osascript \
        -e 'on run argv' \
        -e 'display notification (item 2 of argv) with title (item 1 of argv)' \
        -e 'end run' \
        "$1" "$2"
}

if ! command -v rmapi >/dev/null; then
    notify "reMarkable" "rmapi not found on PATH"
    exit 1
fi

sent=() failed=()
for f in "$@"; do
    [[ -d "$f" ]] && continue
    case "${f:l}" in
        *.pdf|*.epub|*.rmdoc) ;;
        *) failed+=("${f:t}: unsupported type"); continue ;;
    esac
    # rmapi refuses to overwrite an existing document, which is what we want:
    # an annotated local copy must never replace the tablet's original.
    if out=$(rmapi put "$f" "$RM_DEST" 2>&1); then
        sent+=("${f:t}")
    else
        failed+=("${f:t}: ${${(f)out}[-1]}")
    fi
done

if (( ${#failed} )); then
    notify "${#failed} of $(( ${#sent} + ${#failed} )) not sent to reMarkable" "${(F)failed}"
    exit 1
fi
(( ${#sent} )) && notify "Sent ${#sent} file(s) to reMarkable" "${(F)sent}"

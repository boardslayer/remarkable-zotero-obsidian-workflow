"""Nautilus context-menu entry: "Send to reMarkable".

Uploads the selected PDF/EPUB files to the reMarkable cloud with `rmapi put`,
the same way the sync script's --push does, so a paper sent from here comes
back annotated through the normal sync.

Install by linking this file into nautilus-python's extension directory:

    mkdir -p ~/.local/share/nautilus-python/extensions
    ln -s "$PWD/nautilus/remarkable.py" ~/.local/share/nautilus-python/extensions/
    nautilus -q   # Nautilus only scans for extensions at startup

The destination folder on the tablet is $RM_DEST (default "/"), the same
variable the sync script uses. Nautilus is started by the session, not a
shell, so set it in ~/.config/environment.d/, not in .bashrc.

Uploads run in a background thread so the file manager stays responsive, and
the outcome is reported with notify-send. rmapi refuses to overwrite a
document that already exists on the tablet, which is the behaviour we want:
an annotated copy must never replace the tablet's original (see push_new in
scripts/remarkable_zotero_sync.py).
"""

import os
import shutil
import subprocess
import threading

from gi import require_version

require_version("Nautilus", "4.1")

from gi.repository import GObject, Nautilus  # noqa: E402

# What `rmapi put` accepts. .rmdoc is a bundle previously fetched with `rmapi get`.
SUPPORTED_SUFFIXES = (".pdf", ".epub", ".rmdoc")


def destination():
    return os.environ.get("RM_DEST", "/")


def notify(summary, body="", urgency="normal"):
    notify_send = shutil.which("notify-send")
    if not notify_send:
        return
    subprocess.run(
        [
            notify_send,
            "--app-name=reMarkable",
            "--icon=tablet",
            f"--urgency={urgency}",
            summary,
            body,
        ],
        check=False,
    )


def upload(paths):
    """Run `rmapi put` per file, sequentially, and report once at the end."""
    dest = destination()
    failed = []
    for path in paths:
        result = subprocess.run(
            ["rmapi", "put", path, dest],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip().splitlines()
            failed.append((os.path.basename(path), message[-1] if message else "rmapi failed"))

    sent = len(paths) - len(failed)
    if not failed:
        summary = f"Sent {sent} file(s) to reMarkable"
        body = "\n".join(os.path.basename(p) for p in paths)
        notify(summary, body)
        return

    summary = f"{len(failed)} of {len(paths)} file(s) not sent to reMarkable"
    body = "\n".join(f"{name}: {why}" for name, why in failed)
    notify(summary, body, urgency="critical")


class SendToRemarkable(GObject.GObject, Nautilus.MenuProvider):
    def _selected_paths(self, files):
        paths = []
        for file in files:
            if file.is_directory():
                continue
            location = file.get_location()
            path = location.get_path() if location else None
            if not path or path in paths:
                continue
            if path.lower().endswith(SUPPORTED_SUFFIXES):
                paths.append(path)
        return paths

    def _on_activate(self, _menu, paths):
        notify(
            f"Sending {len(paths)} file(s) to reMarkable…",
            f"Destination: {destination()}",
            urgency="low",
        )
        threading.Thread(target=upload, args=(paths,), daemon=True).start()

    def get_file_items(self, *args):
        files = args[0] if len(args) == 1 else args[1]
        if not shutil.which("rmapi"):
            return []

        paths = self._selected_paths(files)
        # Only offer the entry when everything selected can go, so the menu
        # never silently drops part of a selection.
        if not paths or len(paths) != len(files):
            return []

        label = "Send to reMarkable" if len(paths) == 1 else "Send selected to reMarkable"
        item = Nautilus.MenuItem(
            name="RemarkableNautilus::send_to_remarkable",
            label=label,
            icon="tablet",
        )
        item.connect("activate", self._on_activate, paths)
        return [item]

# reMarkable + Zotero + Obsidian workflow (macOS)

Move papers from Zotero to a reMarkable, and bring the highlights made on the
tablet back into Zotero as real annotations.

```
Zotero + ZotMoov  ->  ~/papers
      |  rmapi put
      v
reMarkable cloud  ->  read and highlight on the tablet
      |  rmapi get
      v
     remarks  ->  PDF with real highlight annotations
      |
      v
~/papers  ->  Zotero: File -> Import Annotations
```

Everything goes through reMarkable's cloud via rmapi. Exports that flatten
annotations into the page lose the highlighted text, so they are not used.

## Setup

### Zotero

1. Zotero -> Settings (⌘,)
2. `Sync`: check `Sync automatically`
3. `Advanced` -> `Files and Folders`: set `Linked Attachment Base Directory`
   to `~/papers`

Keep this folder outside Documents, Desktop and iCloud Drive. macOS blocks
background jobs from those without Full Disk Access, and iCloud's
"Optimize Mac Storage" replaces files with placeholders the sync cannot use.

### ZotMoov

[ZotMoov](https://github.com/wileyyugioh/zotmoov) keeps a flat folder of
predictably named PDFs, which is what lets a tablet document be matched back
to a library item.

1. Install ZotMoov
2. Zotero -> Settings -> `ZotMoov`: set the destination to `~/papers`
3. Check `Automatically Move/Copy Files When Added`

### rmapi

Use the [ddvk fork](https://github.com/ddvk/rmapi); `juruen/rmapi` is archived.

```
brew install go
go install github.com/ddvk/rmapi@latest     # installs to ~/go/bin
```

Pair it once: get an 8-character code from
<https://my.remarkable.com/device/browser/connect> and run `rmapi ls`. The
token is saved in `~/.config/rmapi/rmapi.conf`; it grants full access to your
reMarkable account, so keep it `chmod 600` and out of backups and dotfiles.

### remarks

Use the [Scrybbling-together fork](https://github.com/Scrybbling-together/remarks);
upstream cannot read firmware 3.0 or later. It must be installed with poetry,
not pip:

```
brew install poetry
git clone https://github.com/Scrybbling-together/remarks.git ~/src/remarks
cd ~/src/remarks
poetry config virtualenvs.in-project true --local
poetry install
mkdir -p ~/.local/bin && ln -s ~/src/remarks/.venv/bin/remarks ~/.local/bin/remarks
remarks --version
```

## Syncing

```
./scripts/remarkable_zotero_sync.py --zotero-dir ~/papers --rm-folder /Papers            # report only
./scripts/remarkable_zotero_sync.py --zotero-dir ~/papers --rm-folder /Papers --install  # apply
```

Nothing is written without `--install`. Add `--push` to also upload library
papers the tablet does not have yet. Options can be set through
`ZOTERO_LINKED_DIR`, `RM_FOLDER`, `RM_DEST`, `RM_WORK_DIR` and `REMARKS_CMD`.

Limit `--rm-folder` to the folder your papers live in. Otherwise every
notebook on the tablet is downloaded and cached in
`~/Library/Caches/remarkable-zotero-sync`.

After a sync, open each listed item in Zotero and use
`File -> Import Annotations`. Back up `~/papers` before the first `--install`.

To check the converted PDFs carry importable highlights:

```
"$(dirname "$(readlink -f "$(command -v remarks)")")/python" \
  scripts/show_highlights.py ~/Library/Caches/remarkable-zotero-sync/out
```

remarks warnings such as `Some data has not been read` are harmless.

## Running it hourly

`macos/com.user.remarkable-sync.plist` is a LaunchAgent. Check the paths in
it, then:

```
cp macos/com.user.remarkable-sync.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.remarkable-sync.plist
tail -f ~/Library/Logs/remarkable-sync.log
```

Stop it with `launchctl bootout gui/$(id -u)/com.user.remarkable-sync`. It
never passes `--push`, and only runs while you are logged in.

## Send to reMarkable from Finder

`macos/send-to-remarkable.sh` becomes a right-click Quick Action:

1. Automator -> New Document -> Quick Action
2. Workflow receives `files or folders` in `Finder`
3. Add `Run Shell Script`, shell `/bin/zsh`, pass input `as arguments`, with:
   `exec ~/Developer/remarkable-zotero-obsidian-workflow/macos/send-to-remarkable.sh "$@"`
4. Save as "Send to reMarkable"

It uploads PDFs, EPUBs and `.rmdoc` files to `$RM_DEST` (default `/Papers`)
and never replaces a document already on the tablet. Send papers from
`~/papers` if you want their highlights to come back through the sync.

## Known limitations

- **Import is manual, and re-importing duplicates.** Delete an item's existing
  Zotero annotations before importing it again.
- **Handwriting stays flat.** Only text highlights become annotations.
- **Matching is by filename.** Duplicate or renamed names are reported and skipped.
- **rmapi is unofficial.** A firmware update can break it.

## Obsidian

remarks also writes markdown of the highlights next to each converted PDF.
Nothing moves it into a vault yet; an Obsidian Zotero plugin that reads
annotations from Zotero is the simpler route.

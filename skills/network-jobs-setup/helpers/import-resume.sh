#!/usr/bin/env bash
# Store a résumé under ~/.network-jobs/resume/ and extract text when possible.
set -euo pipefail

SRC="${1:-}"
OUT="${2:-${NETWORK_JOBS_HOME:-$HOME/.network-jobs}}"

if [[ -z "$SRC" || ! -f "$SRC" ]]; then
  echo "Usage: import-resume.sh <resume-file> [data-home]" >&2
  exit 1
fi

RESUME_DIR="$OUT/resume"
mkdir -p "$RESUME_DIR" "$OUT/logs"

ext="${SRC##*.}"
ext="$(printf '%s' "$ext" | tr '[:upper:]' '[:lower:]')"
[[ "$SRC" == *.* ]] || ext="bin"

shopt -s nullglob
rm -f "$RESUME_DIR"/source.*
shopt -u nullglob

dest="$RESUME_DIR/source.$ext"
cp "$SRC" "$dest"

text_path="$RESUME_DIR/text.md"
extracted=0
note=""

write_text() {
  {
    echo "<!-- extracted $(date -u +%Y-%m-%dT%H:%M:%SZ) from $(basename "$SRC") -->"
    echo
    printf '%s\n' "$1"
  } > "$text_path"
  extracted=1
}

case "$ext" in
  md|txt|text|markdown)
    write_text "$(cat "$SRC")"
    note="copied plain text"
    ;;
  pdf)
    if command -v pdftotext >/dev/null 2>&1; then
      raw="$(pdftotext -layout "$SRC" - 2>/dev/null || true)"
      if [[ -n "${raw//[[:space:]]/}" ]]; then
        write_text "$raw"
        note="pdftotext"
      else
        note="pdftotext returned empty"
      fi
    else
      note="pdftotext not installed — agent should read source.pdf"
    fi
    ;;
  docx)
    raw="$(python3 - "$SRC" <<'PY' 2>/dev/null || true
import sys, zipfile, xml.etree.ElementTree as ET
path = sys.argv[1]
try:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
except Exception:
    sys.exit(0)
root = ET.fromstring(xml)
parts = []
for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
    texts = [t.text or "" for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")]
    line = "".join(texts).strip()
    if line:
        parts.append(line)
print("\n".join(parts))
PY
)"
    if [[ -n "${raw//[[:space:]]/}" ]]; then
      write_text "$raw"
      note="python docx extract"
    else
      note="docx extract empty — agent should read source.docx"
    fi
    ;;
  *)
    note="no local extractor for .$ext — agent should read source.$ext"
    ;;
esac

email_hint=""
if [[ -f "$text_path" ]]; then
  email_hint="$(grep -Eo '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' "$text_path" 2>/dev/null | head -1 || true)"
fi

ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 -c "
import json
from pathlib import Path
payload = {
  'timestamp': '''$ts''',
  'sourceStored': '''$dest''',
  'textExtracted': $extracted == 1,
  'emailHint': '''$email_hint''' or None,
  'notes': '''$note''',
}
print(json.dumps(payload, indent=2))
Path('''$OUT/logs''').mkdir(parents=True, exist_ok=True)
Path('''$OUT/logs/resume-import-${ts//:/}.json''').write_text(json.dumps(payload, indent=2) + '\n')
"

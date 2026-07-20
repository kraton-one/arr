#!/bin/sh

# This script only COPIES files from the seedbox to local storage.
# It does NOT delete, move, or modify source files on the seedbox.
# If shows/movies are disappearing from the seedbox, check your *arr
# download client settings (Sonarr/Radarr) for "Remove from {app}"
# or qBittorrent's "Delete .torrent + files" option on the seedbox.

LOCAL_PATH="/downloads/complete/"
INTERVAL=120
SEEDBOX_PORT=${SEEDBOX_PORT:-22}
# Minimum age a remote file must reach before rclone copies it locally.
# Increase this to let torrents seed on the seedbox before you pull them.
# Example: 24h, 48h, 7d. See rclone docs for accepted suffixes.
SEEDBOX_MIN_AGE=${SEEDBOX_MIN_AGE:-1m}

echo "Starting seedbox sync: ${SEEDBOX_HOST}:${SEEDBOX_REMOTE_PATH} -> ${LOCAL_PATH}"
echo "Sync interval: ${INTERVAL}s"
echo "Minimum seedbox file age before copy: ${SEEDBOX_MIN_AGE}"
echo "NOTE: rclone copy does not delete source files on the seedbox."

while true; do
  # rclone copy: copies new/changed files from seedbox to local.
  # It never deletes files on the seedbox (source) or local (destination).
  rclone copy ":sftp:${SEEDBOX_REMOTE_PATH}" "$LOCAL_PATH" \
    --sftp-host "${SEEDBOX_HOST}" \
    --sftp-port "${SEEDBOX_PORT}" \
    --sftp-user "${SEEDBOX_USER}" \
    --sftp-pass "$(rclone obscure "${SEEDBOX_PASS}")" \
    --transfers 2 \
    --min-age "${SEEDBOX_MIN_AGE}" \
    --log-level INFO

  # Extract archives in book downloads (zip->rar->epub pattern from scene releases)
  find "${LOCAL_PATH}books" -name "*.zip" -type f 2>/dev/null | while read -r zipfile; do
    [ -f "${zipfile}.extracted" ] && continue
    dir=$(dirname "$zipfile")
    echo "Unzipping: $zipfile"
    unzip -o -d "$dir" "$zipfile" && touch "${zipfile}.extracted"
  done

  find "${LOCAL_PATH}books" -name "*.rar" -type f 2>/dev/null | while read -r rarfile; do
    [ -f "${rarfile}.extracted" ] && continue
    dir=$(dirname "$rarfile")
    echo "Extracting RAR: $rarfile"
    unrar x -o+ "$rarfile" "$dir/" && touch "${rarfile}.extracted"
  done

  # Repackage exploded epub directories (mimetype + META-INF + OEBPS) into .epub files
  find "${LOCAL_PATH}books" -name "mimetype" -type f 2>/dev/null | while read -r mimefile; do
    dir=$(dirname "$mimefile")
    metainf="$dir/META-INF"
    oebps="$dir/OEBPS"
    if [ -d "$metainf" ] && [ -d "$oebps" ]; then
      dirname=$(basename "$dir")
      epubfile="$dir/${dirname}.epub"
      if [ ! -f "$epubfile" ]; then
        echo "Repackaging epub: $epubfile"
        (
          cd "$dir" || exit 1
          # epub spec: mimetype must be first, uncompressed
          zip -X0 "$epubfile" mimetype
          zip -Xr9 "$epubfile" META-INF OEBPS
          # Add any .opf/.ncx files at root level
          for f in "$dir"/*.opf "$dir"/*.ncx; do
            [ -f "$f" ] && zip -Xr9 "$epubfile" "$(basename "$f")"
          done
          # Clean up exploded files after successful packaging
          rm -rf mimetype META-INF OEBPS *.opf *.ncx *.nfo file_id.diz 2>/dev/null
          echo "Created: $epubfile"
        ) || echo "FAILED to create: $epubfile"
      fi
    fi
  done

  sleep "$INTERVAL"
done

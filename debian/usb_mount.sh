#!/bin/sh
set -eu

ACTION="${1:-}"
DEVNAME="${2:-}"

DEV="/dev/${DEVNAME}"
MOUNT_ROOT="/mnt/heikodiscopi-usb"
MP="${MOUNT_ROOT}/${DEVNAME}"

log() { echo "heikodiscopi-usb: $*" >&2; }

mkdir -p "${MOUNT_ROOT}"

case "${ACTION}" in
  add)
    if [ ! -b "${DEV}" ]; then
      log "device not block: ${DEV}"
      exit 0
    fi

    mkdir -p "${MP}"

    # If already mounted, do nothing
    if mountpoint -q "${MP}"; then
      exit 0
    fi

    # Safer mount options for removable media (read-only is usually enough for playback)
    # For FAT/exFAT, uid/gid matters; use root here and just read.
    # If you want write access, drop "ro".
    OPTS="ro,nosuid,nodev,noexec"

    # Try normal mount; relies on installed FS helpers (vfat/exfat/ntfs/etc.)
    if mount -o "${OPTS}" "${DEV}" "${MP}"; then
      log "mounted ${DEV} -> ${MP}"
      exit 0
    fi

    # Fallback: try with type auto
    if mount -t auto -o "${OPTS}" "${DEV}" "${MP}"; then
      log "mounted(auto) ${DEV} -> ${MP}"
      exit 0
    fi

    log "failed to mount ${DEV}"
    rmdir "${MP}" 2>/dev/null || true
    exit 0
    ;;

  remove)
    if mountpoint -q "${MP}"; then
      umount "${MP}" || true
      log "unmounted ${MP}"
    fi
    rmdir "${MP}" 2>/dev/null || true
    exit 0
    ;;

  *)
    log "usage: $0 {add|remove} <devname>"
    exit 2
    ;;
esac

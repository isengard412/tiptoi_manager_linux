"""Locate a tiptoi pen, install .gme files onto it, and report outdated titles."""

from tiptoi_linux.pen._base import PEN_LABEL, PROTECTED_NAMES, Pen, PenError, disk_space
from tiptoi_linux.pen.detect import (
    device_mounted,
    device_plugged_in,
    find_pen,
    mount_pen,
    pen_mount_alive,
    unmount_pen,
)
from tiptoi_linux.pen.gme import read_gme_version
from tiptoi_linux.pen.install import Phase, PhaseProgress, install_file, install_title
from tiptoi_linux.pen.library import (
    OutdatedTitle,
    PenSummary,
    delete_title,
    empty_trash,
    installed_gme_files,
    outdated_titles,
    pen_summary,
)
from tiptoi_linux.pen.firmware import (
    FIRMWARE_FILE_NAME,
    FirmwareError,
    FirmwareInfo,
    download_firmware,
    install_firmware,
    parse_firmware_info,
    read_pen_log,
    verify_checksum,
)

__all__ = [
    "PEN_LABEL",
    "PROTECTED_NAMES",
    "OutdatedTitle",
    "Pen",
    "PenError",
    "PenSummary",
    "Phase",
    "PhaseProgress",
    "delete_title",
    "device_mounted",
    "device_plugged_in",
    "disk_space",
    "download_firmware",
    "empty_trash",
    "find_pen",
    "FIRMWARE_FILE_NAME",
    "FirmwareError",
    "FirmwareInfo",
    "install_firmware",
    "install_file",
    "install_title",
    "installed_gme_files",
    "mount_pen",
    "outdated_titles",
    "parse_firmware_info",
    "pen_mount_alive",
    "pen_summary",
    "read_gme_version",
    "read_pen_log",
    "unmount_pen",
    "verify_checksum",
]

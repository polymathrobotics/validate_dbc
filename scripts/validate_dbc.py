#!/usr/bin/env python3
"""Validate .dbc files for syntax and structural defects.

Runs the CI-automatable subset of a DBC lint checks inspired by DBC Utility's DBC Validation Release Checklist
(https://dbcutility.com/blog/dbc-validation-release-checklist/) against the
DBC files passed as command-line arguments.
"""

from __future__ import annotations

import re
import sys

import cantools

# Valid CAN FD data-length-code payload sizes, in bytes.
CAN_FD_VALID_LENGTHS = {0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64}
CLASSICAL_CAN_MAX_LENGTH = 8
STANDARD_ID_MAX = 0x7FF

_LINE_RE = re.compile(r'at line (\d+)')


class Finding:
    """A single validation finding tied to a file (and optionally a line)."""

    def __init__(self, path, level, message, line=None):
        self.path = path
        self.level = level  # 'error' or 'warning'
        self.message = message
        self.line = line

    def annotation(self):
        """Render as a GitHub Actions workflow command."""
        location = f'file={self.path}'
        if self.line is not None:
            location += f',line={self.line}'
        text = self.message.replace('\n', ' ').strip()
        return f'::{self.level} {location}::{text}'


def _line_from_error(exc):
    """Pull a line number out of a cantools error message, if present."""
    match = _LINE_RE.search(str(exc))
    return int(match.group(1)) if match else None


def _check_parse(path):
    """Load with strict=False. Returns (db, findings); db is None on failure."""
    try:
        db = cantools.database.load_file(path, strict=False)
    except Exception as exc:  # noqa: BLE001 - any load failure is a syntax/format error
        return None, [Finding(path, 'error', f'Failed to parse: {exc}', _line_from_error(exc))]
    return db, []


def _check_strict(path):
    """Semantic checks (overlap / bounds / mux) via cantools strict mode.

    cantools strict mode does the byte-order-aware bit-layout math itself, so we
    reuse it instead of re-implementing Motorola/Intel bit numbering by hand.
    """
    try:
        cantools.database.load_file(path, strict=True)
    except Exception as exc:  # noqa: BLE001 - strict-only failures are structural defects
        return [Finding(path, 'error', f'Structural error (overlap/bounds/mux): {exc}',
                        _line_from_error(exc))]
    return []


def _check_signal_ranges(path, msg):
    """Warn when a declared physical range cannot fit the signal's bit width."""
    findings = []
    for sig in msg.signals:
        if sig.minimum is None or sig.maximum is None or not sig.scale:
            continue
        raw_span = (2 ** sig.length) - 1
        representable = abs(raw_span * sig.scale)
        declared = abs(sig.maximum - sig.minimum)
        # Allow one scale step of tolerance for rounding in the DBC.
        if declared > representable + abs(sig.scale):
            findings.append(Finding(
                path, 'warning',
                f'Signal "{msg.name}.{sig.name}" declared range [{sig.minimum}, {sig.maximum}] '
                f'exceeds what {sig.length} bits at scale {sig.scale} can represent (~{representable})'))
    return findings


def _check_messages(path, db):
    """Structural checks cantools does not perform on its own."""
    findings = []
    seen_ids = {}

    for msg in db.messages:
        seen_ids.setdefault((msg.frame_id, bool(msg.is_extended_frame)), []).append(msg.name)

        if not msg.is_fd and msg.length > CLASSICAL_CAN_MAX_LENGTH:
            findings.append(Finding(
                path, 'error',
                f'Message "{msg.name}" is classical CAN but has payload length '
                f'{msg.length} > {CLASSICAL_CAN_MAX_LENGTH} bytes'))

        if msg.is_fd and msg.length not in CAN_FD_VALID_LENGTHS:
            findings.append(Finding(
                path, 'warning',
                f'Message "{msg.name}" is CAN FD with non-standard payload length {msg.length}'))

        if not msg.is_extended_frame and msg.frame_id > STANDARD_ID_MAX:
            findings.append(Finding(
                path, 'warning',
                f'Message "{msg.name}" id 0x{msg.frame_id:X} exceeds 11 bits but is not marked extended'))

        counts = {}
        for sig in msg.signals:
            counts[sig.name] = counts.get(sig.name, 0) + 1
        for name, count in counts.items():
            if count > 1:
                findings.append(Finding(
                    path, 'error',
                    f'Message "{msg.name}" has duplicate signal name "{name}"'))

        findings.extend(_check_signal_ranges(path, msg))

    for (frame_id, extended), names in seen_ids.items():
        if len(names) > 1:
            kind = 'extended' if extended else 'standard'
            findings.append(Finding(
                path, 'warning',
                f'Duplicate {kind} frame id 0x{frame_id:X} used by messages: {", ".join(names)}'))

    return findings


def validate_file(path):
    """Run every check against a single file and return its findings."""
    db, findings = _check_parse(path)
    if db is None:
        return findings
    signal_count = sum(len(m.signals) for m in db.messages)
    print(f'{path}: parsed OK ({len(db.messages)} messages, {signal_count} signals)')
    findings.extend(_check_strict(path))
    findings.extend(_check_messages(path, db))
    return findings


def main(argv):
    paths = argv[1:]
    if not paths:
        print('No DBC files to validate.')
        return 0

    all_findings = []
    for path in paths:
        all_findings.extend(validate_file(path))

    for finding in all_findings:
        print(finding.annotation())

    errors = [f for f in all_findings if f.level == 'error']
    warnings = [f for f in all_findings if f.level == 'warning']
    print(f'\nSummary: {len(errors)} error(s), {len(warnings)} warning(s) '
          f'across {len(paths)} file(s).')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

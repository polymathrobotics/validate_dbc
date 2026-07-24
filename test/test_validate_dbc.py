"""Per-case tests for the DBC validator.

Each fixture in test/fixtures/ exercises one check. A `valid` fixture must be
clean; each `error_*` fixture must yield at least one error-level finding whose
message contains the expected phrase; each `warning_*` fixture must yield the
expected warning and NO errors.

Note: the "standard id above 11 bits not marked extended" warning is not
reachable as a standalone case -- cantools rejects such a file at parse time,
so it surfaces as a parse error (covered by error_syntax-style parse failures).
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

HERE = pathlib.Path(__file__).resolve().parent
FIXTURES = HERE / 'fixtures'

# Import the validator that ships with the action (../scripts/validate_dbc.py).
_spec = importlib.util.spec_from_file_location(
    'validate_dbc', HERE.parent / 'scripts' / 'validate_dbc.py')
validate_dbc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate_dbc)

# fixture filename -> substring expected in an ERROR-level finding
ERROR_CASES = {
    'error_syntax.dbc': 'Failed to parse',
    'error_overlap.dbc': 'overlapping',
    'error_classical_oversize.dbc': 'payload length',
    'error_duplicate_signal_name.dbc': 'duplicate signal name',
}

# fixture filename -> substring expected in a WARNING-level finding
WARNING_CASES = {
    'warning_duplicate_frame_id.dbc': 'Duplicate',
    'warning_canfd_length.dbc': 'CAN FD with non-standard payload length',
    'warning_signal_range.dbc': 'exceeds what',
}


def findings_for(name):
    return validate_dbc.validate_file(str(FIXTURES / name))


def test_valid_fixture_is_clean():
    assert findings_for('valid.dbc') == []


@pytest.mark.parametrize('fixture, phrase', sorted(ERROR_CASES.items()))
def test_error_fixture(fixture, phrase):
    findings = findings_for(fixture)
    errors = [f for f in findings if f.level == 'error']
    assert errors, f'{fixture} should produce at least one error'
    assert any(phrase in f.message for f in errors), \
        f'{fixture} error(s) should mention "{phrase}"; got {[f.message for f in errors]}'


@pytest.mark.parametrize('fixture, phrase', sorted(WARNING_CASES.items()))
def test_warning_fixture(fixture, phrase):
    findings = findings_for(fixture)
    errors = [f for f in findings if f.level == 'error']
    warnings = [f for f in findings if f.level == 'warning']
    assert not errors, f'{fixture} should not produce errors; got {[f.message for f in errors]}'
    assert any(phrase in f.message for f in warnings), \
        f'{fixture} warning(s) should mention "{phrase}"; got {[f.message for f in warnings]}'


def test_main_exit_code_nonzero_on_error():
    assert validate_dbc.main(['prog', str(FIXTURES / 'error_overlap.dbc')]) == 1


def test_main_exit_code_zero_on_warning_only():
    assert validate_dbc.main(['prog', str(FIXTURES / 'warning_signal_range.dbc')]) == 0

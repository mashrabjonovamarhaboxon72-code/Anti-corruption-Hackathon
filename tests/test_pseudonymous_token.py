import os
import sys
from pathlib import Path

os.environ.setdefault("PT_SALT", "test-salt-please-rotate")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.pseudonymous_token import generate_pseudonymous_token


def test_token_is_deterministic():
    a = generate_pseudonymous_token("AA1234567")
    b = generate_pseudonymous_token("AA1234567")
    assert a == b
    assert len(a) == 64


def test_token_changes_with_id():
    a = generate_pseudonymous_token("AA1234567")
    b = generate_pseudonymous_token("AA1234568")
    assert a != b


def test_token_normalizes_whitespace():
    a = generate_pseudonymous_token("AA1234567")
    b = generate_pseudonymous_token("  AA1234567  ")
    assert a == b


def test_empty_id_rejected():
    import pytest

    with pytest.raises(ValueError):
        generate_pseudonymous_token("   ")


def test_token_is_hex():
    t = generate_pseudonymous_token("AA1234567")
    int(t, 16)  # must parse as hex


if __name__ == "__main__":
    test_token_is_deterministic()
    test_token_changes_with_id()
    test_token_normalizes_whitespace()
    test_token_is_hex()
    try:
        test_empty_id_rejected()
    except ImportError:
        pass
    print("PT tests passed")

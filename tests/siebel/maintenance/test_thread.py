from siebel.maintenance.crash import fix_thread_id
from siebel.maintenance.crash import dec2bin, dec2bin_backport
import pytest


@pytest.fixture
def fdr_thread():
    return 2658139040  # always read as text


def test_fix_thread_id(fdr_thread):
    assert fix_thread_id(str(fdr_thread)) == '-1636828256'


def test_dec2bin(fdr_thread):
    assert dec2bin(fdr_thread) == '10011110011011111111101110100000'


def test_dec2bin_backport(fdr_thread):
    assert dec2bin_backport(fdr_thread) == '10011110011011111111101110100000'

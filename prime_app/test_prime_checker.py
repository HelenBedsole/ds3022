"""
Test suite proving prime_checker's results are correct.

Three independent lines of evidence:
  1. Hand-checked known values and edge cases.
  2. Exhaustive agreement with a sieve of Eratosthenes for every n in [-10, 50_000].
  3. Agreement with sympy.isprime on large / adversarial inputs (Carmichael
     numbers, Mersenne primes, semiprimes) that naive tests get wrong.
"""

import pytest
from sympy import isprime as sympy_isprime

from prime_checker import (
    InvalidIntegerError,
    check,
    describe,
    is_prime,
    main,
    parse_integer,
    smallest_factor,
)

SIEVE_LIMIT = 50_000


def sieve(limit: int) -> set[int]:
    """Independent oracle: all primes <= limit via sieve of Eratosthenes."""
    flags = bytearray([1]) * (limit + 1)
    flags[0:2] = b"\x00\x00"
    for i in range(2, int(limit**0.5) + 1):
        if flags[i]:
            flags[i * i :: i] = bytearray(len(flags[i * i :: i]))
    return {i for i, f in enumerate(flags) if f}


PRIME_SET = sieve(SIEVE_LIMIT)


# --- input validation -------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("7", 7), ("  7  ", 7), ("-13", -13), ("+13", 13),
        ("0", 0), ("007", 7), ("\t42\n", 42),
        ("123456789012345678901234567890", 123456789012345678901234567890),
    ],
)
def test_parse_accepts_integers(raw, expected):
    assert parse_integer(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "3.0", "3.5", ".5", "1e5", "abc", "7a", "a7", "1_7", "0x11",
     "0b101", "--5", "+-5", "5-", "inf", "nan", "None", "7 7", "٧", "½", None],
)
def test_parse_rejects_non_integers(raw):
    """Anything that is not a plain integer must raise, never silently coerce."""
    with pytest.raises(InvalidIntegerError):
        parse_integer(raw)


# --- known values -----------------------------------------------------------


@pytest.mark.parametrize(
    "n", [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 97, 101,
          7919, 104729, 1_000_003, 2_147_483_647],
)
def test_known_primes(n):
    assert is_prime(n) is True


@pytest.mark.parametrize(
    "n", [0, 1, 4, 6, 8, 9, 10, 15, 21, 25, 27, 49, 100, 1001, 7917,
          104730, 1_000_001, 2_147_483_649],
)
def test_known_composites(n):
    assert is_prime(n) is False


@pytest.mark.parametrize("n", [-1, -2, -3, -7, -97, -100])
def test_negatives_are_not_prime(n):
    """Primality is defined on integers > 1; negatives are always False."""
    assert is_prime(n) is False


def test_zero_and_one_are_not_prime():
    assert is_prime(0) is False
    assert is_prime(1) is False


def test_two_is_the_only_even_prime():
    assert is_prime(2) is True
    assert all(not is_prime(n) for n in range(4, 1000, 2))


# --- exhaustive cross-check against a sieve ---------------------------------


def test_exhaustive_agreement_with_sieve():
    """Every integer in [-10, SIEVE_LIMIT] must match the sieve exactly."""
    mismatches = [n for n in range(-10, SIEVE_LIMIT + 1)
                  if is_prime(n) != (n in PRIME_SET)]
    assert mismatches == []


def test_prime_count_below_100000_is_correct():
    """pi(50_000) = 5133 — a published value, so the sieve itself is validated."""
    assert sum(1 for n in range(SIEVE_LIMIT + 1) if is_prime(n)) == 5133


# --- adversarial / large inputs vs. sympy -----------------------------------


CARMICHAEL = [561, 1105, 1729, 2465, 2821, 6601, 8911, 10585, 15841, 29341,
              41041, 62745, 63973, 75361, 101101, 825265, 321197185]


@pytest.mark.parametrize("n", CARMICHAEL)
def test_carmichael_numbers_are_composite(n):
    """Fermat-style tests call these prime; Miller-Rabin must not."""
    assert is_prime(n) is False


@pytest.mark.parametrize("p", [61, 89, 107, 127, 521, 607])
def test_mersenne_primes(p):
    """2^p - 1 for these p are known primes — large, and all-ones in binary."""
    assert is_prime(2**p - 1) is True


@pytest.mark.parametrize(
    "n",
    [2**61 - 1, 2**64 + 13, 10**18 + 9, 10**30 + 57,
     (10**15 + 37) * (10**15 + 61),   # semiprime of two large primes
     99194853094755497, 67280421310721],
)
def test_large_values_match_sympy(n):
    assert is_prime(n) == sympy_isprime(n)


def test_strong_pseudoprime_to_base_2():
    """2047 = 23 * 89 passes a base-2-only Miller-Rabin; the full base set catches it."""
    assert is_prime(2047) is False


def test_random_large_sample_matches_sympy():
    """Randomised differential test against an independent implementation."""
    import random

    rng = random.Random(3022)  # seeded: failures are reproducible
    for _ in range(300):
        n = rng.randrange(2, 10**12)
        assert is_prime(n) == sympy_isprime(n), f"disagreement on {n}"


# --- factor helper and messaging --------------------------------------------


@pytest.mark.parametrize("n,f", [(4, 2), (9, 3), (15, 3), (25, 5), (1001, 7), (100, 2)])
def test_smallest_factor(n, f):
    assert smallest_factor(n) == f


def test_smallest_factor_none_for_primes():
    assert smallest_factor(97) is None


def test_describe_messages():
    assert "PRIME" in describe(97) and "NOT" not in describe(97)
    assert "NOT prime" in describe(98)
    assert "greater than 1" in describe(1)
    assert "positive" in describe(-5)


def test_check_end_to_end():
    assert "PRIME" in check(" 97 ")
    assert "NOT prime" in check("98")
    with pytest.raises(InvalidIntegerError):
        check("ninety-seven")


# --- CLI --------------------------------------------------------------------


def test_main_exit_codes(capsys):
    assert main(["97"]) == 0
    assert main(["98"]) == 0
    assert main(["abc"]) == 1          # bad input -> nonzero
    assert main(["97", "abc"]) == 1    # any bad input -> nonzero
    out = capsys.readouterr().out
    assert "PRIME" in out

"""
prime_checker.py — prompt for an integer and report whether it is prime.

Rejects any input that is not an integer. Primality uses a deterministic
Miller-Rabin test, so results are exact (not probabilistic) for every input
a user can realistically type.

Usage:
    python prime_checker.py            # interactive prompt loop
    python prime_checker.py 97 1001    # check values from the command line
"""

import logging
import random
import re
import sys
from pathlib import Path

# Log to a file beside this script so runs are auditable after the fact.
LOG_PATH = Path(__file__).with_name("prime_checker.log")

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# An integer and nothing else: optional sign, then ASCII digits. This deliberately
# rejects "3.0", "1e5", "1_7", "0x11" and anything else int() would be lax about.
# re.ASCII matters: without it \d also matches Unicode digits like "٧", which
# int() would happily convert to 7.
INTEGER_RE = re.compile(r"^[+-]?[0-9]+$", re.ASCII)

# Witness bases that make Miller-Rabin *deterministic* for all n < 3.317e24
# (Sorenson & Webster, 2015). Below that bound the test is a proof, not a guess.
DETERMINISTIC_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
DETERMINISTIC_BOUND = 3_317_044_064_679_887_385_961_981

# Small primes used to strip the easy composites before any heavy work.
SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


class InvalidIntegerError(ValueError):
    """Raised when user input does not parse as a plain integer."""


def parse_integer(raw: str) -> int:
    """Convert user text to an int, rejecting everything that is not an integer.

    Surrounding whitespace is forgiven; decimals, exponents and words are not.
    """
    if raw is None:
        raise InvalidIntegerError("No input provided.")
    text = raw.strip()
    if not text:
        raise InvalidIntegerError("No input provided.")
    if not INTEGER_RE.match(text):
        raise InvalidIntegerError(f"{text!r} is not an integer.")
    return int(text)


def _miller_rabin_round(n: int, base: int, d: int, s: int) -> bool:
    """One Miller-Rabin round. True means `base` is not a witness to n being composite."""
    x = pow(base, d, n)
    if x == 1 or x == n - 1:
        return True
    for _ in range(s - 1):
        x = x * x % n
        if x == n - 1:
            return True
    return False


def is_prime(n: int) -> bool:
    """Return True iff n is prime.

    Negatives, 0 and 1 are not prime by definition. Composites are rejected by
    small-prime division first; the rest goes to Miller-Rabin with a fixed base
    set that is proven exhaustive below DETERMINISTIC_BOUND. Above that bound we
    add random bases, leaving an error probability below 4^-40.
    """
    if n < 2:
        return False
    for p in SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False

    # Write n - 1 as d * 2^s with d odd, the form Miller-Rabin needs.
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1

    bases = list(DETERMINISTIC_BASES)
    if n >= DETERMINISTIC_BOUND:
        bases += [random.randrange(2, n - 1) for _ in range(40)]

    return all(_miller_rabin_round(n, b, d, s) for b in bases)


def smallest_factor(n: int, limit: int = 1_000_000) -> int | None:
    """Smallest prime factor of composite n, or None if not found under `limit`.

    Used only to make the "not prime" message more useful; never affects the verdict.
    """
    if n < 2:
        return None
    if n % 2 == 0:
        return 2
    f = 3
    while f <= limit and f * f <= n:
        if n % f == 0:
            return f
        f += 2
    return None


def describe(n: int) -> str:
    """Human-readable verdict for n, with a reason for the common edge cases."""
    if n < 0:
        return f"{n} is NOT prime (primes are positive)."
    if n == 0 or n == 1:
        return f"{n} is NOT prime (primes must be greater than 1)."
    if is_prime(n):
        return f"{n} is PRIME."
    factor = smallest_factor(n)
    if factor is not None:
        return f"{n} is NOT prime (divisible by {factor})."
    return f"{n} is NOT prime (composite)."


def check(raw: str) -> str:
    """Parse then evaluate one piece of input, logging both the request and verdict."""
    n = parse_integer(raw)
    verdict = describe(n)
    log.info("checked %s -> %s", n, "prime" if is_prime(n) else "not prime")
    return verdict


def run_once(raw: str) -> int:
    """Check a single value, printing the result. Returns a process exit code."""
    try:
        print(check(raw))
        return 0
    except InvalidIntegerError as e:
        print(f"Invalid input: {e}", file=sys.stderr)
        log.warning("rejected input %r: %s", raw, e)
        return 1


def interactive() -> int:
    """Prompt repeatedly until the user quits, re-prompting on bad input."""
    print("Prime checker. Enter an integer, or 'q' to quit.")
    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            log.info("session ended by user")
            return 0
        if raw.strip().lower() in {"q", "quit", "exit"}:
            log.info("session ended by user")
            return 0
        try:
            print(check(raw))
        except InvalidIntegerError as e:
            print(f"Invalid input: {e} Please enter a whole number.")
            log.warning("rejected input %r: %s", raw, e)
        except Exception as e:  # unexpected: log it, keep the session alive
            print(f"Unexpected error: {e}")
            log.exception("unexpected failure on input %r", raw)


def main(argv: list[str] | None = None) -> int:
    """Entry point: command-line values if given, otherwise the interactive loop."""
    args = sys.argv[1:] if argv is None else argv
    if not args:
        return interactive()
    return max(run_once(a) for a in args)


if __name__ == "__main__":
    sys.exit(main())

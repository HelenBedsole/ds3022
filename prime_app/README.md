# Prime Checker

Prompts for an integer and reports whether it is prime. Non-integer input is
rejected rather than coerced, and the primality answer is exact — not an estimate.

## Setup

The virtualenv lives at the **repository root**, not in this directory. From the
root of `ds3022`:

```bash
pipenv install --dev   # installs project deps plus pytest
pipenv shell           # activate (or prefix each command with `pipenv run`)
```

Dependencies used here: `sympy` (tests only, as an independent cross-check) and
`pytest` (dev). Both are already in the root `Pipfile`.

## Usage

Interactive — prompts until you quit with `q`, `quit`, `exit`, or Ctrl-D:

```bash
cd prime_app
pipenv run python prime_checker.py
```

```
Prime checker. Enter an integer, or 'q' to quit.
> 97
97 is PRIME.
> 98
98 is NOT prime (divisible by 2).
> 3.5
Invalid input: '3.5' is not an integer. Please enter a whole number.
> q
```

One-shot — pass values as arguments (exit code `0` if all parsed, `1` if any did not):

```bash
pipenv run python prime_checker.py 97 2147483647 561
```

## Input rules

| Accepted | Rejected |
|---|---|
| `7`, `  7  `, `+13`, `-13`, `007` | `3.0`, `3.5`, `1e5`, `1_7`, `0x11` |
| arbitrarily large integers, e.g. `10**30 + 57` | `abc`, `7a`, `inf`, `nan`, empty input |
| | non-ASCII digits such as `٧` |

Bad input re-prompts in interactive mode; it never crashes the session.

By definition, `0`, `1`, and all negative integers are **not** prime, and the
program says why rather than just "no".

## How the answer is guaranteed correct

1. Divide out the first twelve small primes to clear easy composites.
2. Run **Miller-Rabin** against the fixed base set `{2,3,5,...,37}`. That base
   set is *proven* to have no false positives for every `n < 3.317 × 10^24`
   (Sorenson & Webster, 2015), so below that bound the test is a proof, not a
   probability.
3. Above that bound, 40 additional random bases are added, leaving an error
   probability under `4^-40`.

A trial-division fallback (`smallest_factor`) only enriches the "not prime"
message; it never influences the verdict.

## Tests

```bash
cd prime_app
pipenv run pytest -q        # 121 tests
pipenv run pytest -v        # per-test detail
```

The suite proves correctness three independent ways:

- **Exhaustive** — every integer in `[-10, 50_000]` is compared against a sieve
  of Eratosthenes, and the resulting prime count is checked against the
  published value `pi(50_000) = 5133`, which validates the oracle itself.
- **Differential** — large and randomly sampled values (seeded, so failures
  reproduce) are compared against `sympy.isprime`, a separate implementation.
- **Adversarial** — Carmichael numbers (`561`, `1729`, …) that fool Fermat
  tests, the base-2 strong pseudoprime `2047`, Mersenne primes up to `2^607 - 1`,
  and semiprimes built from two 15-digit primes.

Plus edge cases: `0`, `1`, negatives, `2` as the only even prime, every rejected
input form in the table above, and CLI exit codes.

## Logging

Every check and every rejected input is appended to `prime_app/prime_checker.log`
(gitignored via the root `*.log` rule). Unexpected errors are logged with a full
traceback while the interactive session stays alive.

## Files

| File | Purpose |
|---|---|
| `prime_checker.py` | The application — parsing, primality, CLI. Single file. |
| `test_prime_checker.py` | Test suite. |
| `prime_checker.log` | Run log, created on first use. |

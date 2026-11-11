# Corpus data card

Two corpora of original synthetic Python pairs. No case comes from professional code, and
neither corpus is a held-out benchmark: both are public with this repository. They are
built to exercise the harness and probe review failure modes, not sampled from natural
defects. Domain boundaries are explicit; no real tax, medical or regulatory rule is used as
implicit truth, and the rounding and quota examples are toy software contracts.

## Contents of a case

Each folder holds metadata.json, before.py, correct.py, faulty.py, test_public.py and
test_oracle.py. The whole corpus is reserved for the builder and the assessor; reviewers
see only anonymized exports. "correct" means conforming to the stated contract and the
supplied checks, not free of every possible defect. Executable assertions do not replace
an independent audit of contracts and counterexamples.

Validate a corpus with `python -m rbs verify-fixtures` (v1) or
`python -m rbs verify-fixtures --corpus fixtures-v2`: the control passes the public and
witness tests, the faulty variant passes the public tests and fails a witness by
assertion, and the base passes the public tests.

## Corpus v1 (`fixtures/`, c01–c15) — development, October 2026

Short functions with classic boundary defects and explicit constraints. Pilot A showed
that current mid-size open models identify all of them; keep that observation rather than
obscuring the contracts.

### c01 — Expiration boundary

Implement active(now, expires_at) for integer timestamps. A token is active strictly before expires_at and inactive at or after it. Inputs are integers; no clock access is needed.

Assessor target: The candidate accepts a token at the exact expiration timestamp.

### c02 — Zero-sized suffix

Implement recent(items, limit). Return a new list containing at most the last limit items, in input order. limit is a non-negative integer. Zero returns an empty list. Do not modify items.

Assessor target: A zero limit returns the entire input because -0 is zero in the slice.

### c03 — Tenant-scoped cache

Implement lookup(cache, tenant, record_id, load). Cache results separately for each (tenant, record_id). Call load(tenant, record_id) only on a miss. The cache is a mutable dictionary initially empty; both identifiers are strings. Return the cached or loaded value.

Assessor target: The cache key omits tenant, so equal record identifiers collide across tenants.

### c04 — Integer half-up rounding

Implement cents(mills) converting non-negative integer thousandths of a unit to integer hundredths. Round to nearest cent, with exact half-cent ties rounded upward. Inputs are at most 100000000.

Assessor target: Exact half-cent ties are rounded downward rather than upward.

### c05 — Numeric event versions

Implement ordered(events) returning a new list sorted by ascending numeric version. Each event is a dictionary with version as a non-negative base-10 integer string. Equal numeric versions retain input order. Do not modify input.

Assessor target: Text ordering is used instead of numeric ordering, including numeric ties.

### c06 — Idempotency identity

Implement record(events, request_id, payload). request_id and payload are strings. events is a list of (request_id, payload) tuples with unique request IDs. Append and return True only when request_id is new. Existing IDs return False without mutation even if payload differs. Different IDs may have identical payloads.

Assessor target: Idempotency is keyed by payload instead of request identity.

### c07 — Atomic batch validation

Implement append_batch(store, values). Both arguments are lists of integers. Accept only non-negative values. If any value is negative, raise ValueError and leave store exactly unchanged; otherwise append all values in order. Validation and mutation are single-threaded.

Assessor target: An invalid later value leaves earlier values already appended.

### c08 — Missing versus explicit value

Implement setting(options, key, default). Return the stored value when key exists, including None, False, zero and empty strings. Use default only when key is absent. options is a dictionary with string keys.

Assessor target: Explicit falsey values are replaced by the default despite key presence.

### c09 — Return-value isolation

Implement labels(record). record contains a labels list of strings. Return a separate list with the same strings; caller modifications to the returned list must not change record. Nested objects are out of scope.

Assessor target: The returned list aliases the stored list and allows mutation of the record.

### c10 — UTC calendar date

Implement utc_day(timestamp). timestamp is an ISO 8601 datetime string with an explicit numeric UTC offset, accepted by datetime.fromisoformat. Return the UTC calendar date as YYYY-MM-DD, not the date in the input offset. Naive datetimes are outside the contract.

Assessor target: The function extracts the local-offset date before converting to UTC.

### c11 — Half-open intervals

Implement overlaps(a, b), where a and b are non-empty half-open integer intervals [start, end) with start < end. Return True exactly when their intersection is non-empty. Touching endpoints do not overlap.

Assessor target: Touching half-open endpoints are incorrectly treated as an intersection.

### c12 — Repeated order lines

Implement totals(lines), where lines is a list of (product_id, quantity), product_id is a string and quantity is a non-negative integer. Return a dictionary summing all quantities per product, including repeated products. Empty input returns an empty dictionary.

Assessor target: Repeated product quantities overwrite one another instead of being added.

### c13 — Signed integer division

Implement divide(n, d) for arbitrary-size signed integer n and positive integer d. Return the quotient truncated toward zero. Do not use floating point conversion.

Assessor target: Floor division rounds negative non-integral quotients away from zero.

### c14 — Explicit unknown tier policy

Implement quota(tier) for a string tier. Return 10 for basic and 100 for premium. For every other string, raise ValueError. Matching is exact and case-sensitive.

Assessor target: Unknown tiers silently receive a quota rather than raising ValueError.

### c15 — Strict version advancement

Implement advance(state, version, value). state is a dictionary with integer version, value and writes. Apply the update only when version is strictly greater than state[version]; then increment writes by one and return True. Equal or older versions return False and must leave the entire state unchanged.

Assessor target: Equal versions are reapplied, changing value and incrementing writes.

## Corpus v2 (`fixtures-v2/`, h01–h10) — November 2026

Written by the repository's AI engineering agent right after pilot A reached its ceiling,
before any model reviewed it, then frozen with the plan
[PILOT_2026-11-B.md](PILOT_2026-11-B.md). Categories chosen before any score: an omission
(missing cache invalidation), a one-shot iterator, signed rounding symmetry, an effect
across functions with atomicity, stable descending sorting, Unicode case folding, retry
without a trailing sleep, business days from a weekend start, path containment by prefix,
and first-versus-last deduplication. Every rule a witness checks is written in the contract.

Pilot B found two sentences of h01 ambiguous (constructor validation; whether failed
lookups count as reads). They are kept unchanged in v2 and documented as a corpus finding;
a fix belongs in a later version.

### h01 — Cache invalidation on price update

Catalog(prices) holds non-negative integer prices in cents keyed by SKU strings. price(sku) returns the current price and raises KeyError for an unknown SKU. quote(order) returns the sum of price times quantity for a list of (sku, quantity) pairs. update_price(sku, cents) sets a new price, raising ValueError when cents is negative; every later price() or quote() call must reflect the new price. This change adds caching: the counter reads counts accesses to the underlying price table, and each SKU must be read from the table at most once between two updates of that SKU.

Assessor target: update_price does not invalidate the cached entry, so later price() and quote() calls return the old price.

### h02 — One-shot iterator allocation

Implement allocate(records, budget). records is any iterable of (name, weight) pairs with unique string names and non-negative integer weights; it may be a one-shot iterator such as a generator and must be consumed only once. budget is a non-negative integer. Return a dictionary mapping every name to budget * weight // total, where total is the sum of all weights. When total is zero, every name maps to 0.

Assessor target: records is iterated twice, so a generator input yields an empty result after the total is computed.

### h03 — Refund rounding symmetry

Implement percent_of(amount_cents, percent). amount_cents is an integer that is negative for refunds and positive for charges; percent is an integer from 0 to 100. Return amount_cents * percent / 100 rounded to the nearest integer, with exact halves rounded away from zero, so that a refund mirrors its charge: percent_of(-x, p) == -percent_of(x, p) for every valid x and p. Use integer arithmetic only.

Assessor target: Negative amounts are rounded with floor arithmetic, so refund halves round toward zero and refunds do not mirror charges.

### h04 — Ledger validation and atomic transfer

accounts maps account names to integer balances. Ledger.record(src, dst, amount, memo) appends one (src, dst, amount, memo) entry to Ledger.entries; this change makes it raise ValueError for memos longer than 40 characters. transfer(accounts, ledger, src, dst, amount, memo='') moves a positive integer amount from src to dst and returns the new src balance. It raises ValueError, leaving both accounts and the ledger entirely unchanged, when amount is not positive, src equals dst, either account is unknown, src has insufficient funds, or the ledger rejects the entry. On success it records exactly one ledger entry.

Assessor target: Balances are changed before the ledger rejects a long memo, so a failed transfer leaves accounts modified.

### h05 — Stable descending priority order

Implement queue_order(tickets). tickets is a list of (ticket_id, priority) pairs. Priorities are mutually comparable values, for example integers or tuples, and need not be numeric. Return the list of ticket IDs ordered from highest to lowest priority; tickets with equal priority keep their original relative order (earlier submissions first). Do not modify tickets.

Assessor target: Reversing an ascending sort also reverses the order of tickets with equal priority.

### h06 — Unicode case-insensitive lookup

Implement find_user(users, query). users is a list of display-name strings. Ignore leading and trailing whitespace in query, then return the first name in users that equals the query under full Unicode case folding, that is, name.casefold() == stripped_query.casefold(). Return None when nothing matches. Do not modify users.

Assessor target: Matching uses str.lower() instead of str.casefold(), so names that differ only under full case folding do not match.

### h07 — Exponential backoff without trailing sleep

Implement call_with_retry(operation, attempts, sleep, base_delay). attempts is an integer of at least 1: the total number of calls to operation, including the first. When a call raises TransientError, wait by calling sleep(base_delay * 2 ** k), where k is the number of failed calls so far minus one, so the delays are base_delay, 2 * base_delay, 4 * base_delay and so on; then call again. Never sleep after the final failed call: re-raise that last TransientError immediately. Any other exception propagates immediately without retry. Return the result of the first successful call.

Assessor target: After the final failed attempt the function still sleeps once before re-raising.

### h08 — Business days from a weekend start

Implement add_business_days(start, n) for a datetime.date start and an integer n of at least 0. Business days are Monday to Friday; there are no holidays. If start falls on a Saturday or Sunday, first move forward to the following Monday. Then move forward n business days. Consequently n == 0 returns start itself on a weekday and the following Monday on a weekend, and Friday plus one business day is the next Monday.

Assessor target: An early return for n == 0 skips the weekend adjustment, so a weekend start with n == 0 returns the weekend date.

### h09 — Upload path containment

Implement resolve_upload(base, name) for POSIX-style path strings, without touching the filesystem. base is an absolute, normalized directory path without a trailing slash, such as /srv/uploads. name is a relative path supplied by a user; an absolute name raises ValueError. Join base and name, normalize the result with posixpath.normpath, and return it only when it equals base or lies inside base, meaning it starts with base followed by a slash. Any other result raises ValueError.

Assessor target: The containment check is a plain string prefix test, so a sibling directory such as /srv/uploads-old is accepted.

### h10 — Keep the first item per key

Implement unique_by(items, key). items is a list and key is a function returning hashable values. Return a new list with exactly one item for each distinct key(item): the first item in items having that key, placed in the order in which keys first appear. Do not modify items.

Assessor target: A dictionary comprehension keeps the first position of each key but the last item with that key.

## Limits and enrichment

Functions are short, defects often classic and constraints explicit. The same author wrote
the cases and judged the pilots, and no independent reviewer checked the cases before use.
Names and contracts resemble each other across repetitions, so every job needs a fresh
session. Do not select only the cases where a model fails.

To enrich the corpus: define the target categories, origin and selection rules first; add
multi-file scenarios and business state where needed; keep close variants in one family;
separate development and test before any tuning; plan an external audit and diverse
sources. Witnesses must derive from the contract, never from a hidden rule.

For an external source, record license, URL, base revision, patch, selection rationale,
contract, public test, witness, corrected version and limits. The bundled runner is not a
sandbox: add that security boundary before executing such cases.

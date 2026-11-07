# B2 Adversarial input engineering

## Aim and local scope
Compare unsafe SQL concatenation against parameter binding, and challenge the full bus-pass decoder with deliberately malformed text. All SQL runs against a database created only for this assignment and a synthetic user fixture, not a real account or third-party system.

## Constructed login inputs

| ID | Password | Unsafe query | Prepared query |
|---|---|---|---|
| student | demo-only-password | Valid fixture | Valid fixture |
| student | wrong | Reject | Reject |
| ' OR '1'='1' -- followed by space | wrong | Accepts a returned row | Rejects |

The last input closes the original string literal and inserts a true OR predicate; the MySQL comment suppresses the remaining password condition. The PreparedStatement sends the exact same ID as data and finds no matching account. This distinguishes input meaning from SQL control structure. The fixture stores a plain demo password solely to match the assignment; production authentication needs a password-hash design.

## Damaged file
B2/inputs/damaged-passes.txt contains five physical lines: a valid escaped-name pass, a checksummed payload with too few fields, a checksummed payload with NaN as amount, an empty line, and a valid later pass P1003. Checksums are valid for the intentionally malformed nonempty payloads so the test actually reaches field-count and numeric validation instead of only exercising checksum mismatch.

The full store rejects three lines with line numbers/reasons, retains two valid records and successfully finds P1003 after the bad lines. The supplied five-field scaffold only checks token count: a five-token row containing a nonnumeric amount could pass its find method. That limitation motivates the separate semantic validator and is not hidden by the supplied successful example.

## Escaping or regex alternative
```text
IF ID does not match allowed business format THEN reject
BUILD SQL by manually replacing quotes with a chosen escape representation
```
A business-format allowlist can be useful but does not replace parameter binding. Manual escaping is tied to SQL dialect, connection character set, SQL mode and every future code path. An ID-only regex says nothing about another concatenated field. A missed site can reintroduce injection; overly broad regexes can also be vulnerable to expensive backtracking. Correct binding keeps query structure independent of value characters. Linear validation/escaping scans input length L in O(L) time and may allocate O(L) output; binding also encodes/transfers O(L) data. Prepared execution does not make input processing O(1), and server-side preparation/caching behaviour depends on the driver. Prefer business validation plus parameter binding, not hand-built SQL based on escaping alone.

## Reproduction and evidence

From the repository root run `python tools/compile.py`, then `python tools/run.py B2` with the local database configured for JDBC tasks. Actual full output, checks, CSV repetitions and compiler logs are in results; each screenshot is a real terminal capture. Bulk fixtures are generated deterministically rather than checked into GitHub.

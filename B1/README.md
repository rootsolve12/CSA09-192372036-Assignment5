# B1 Instrumented bus pass file store

## Aim and implementations
Implement the seven-field A1 file contract and the A2 counter, then test correctness and growth. BusPass is the validated immutable record; PassCodec performs escaping/checksum/type work; BusPassStore performs single-writer append, lookup and route selection. The supplied PassStore.java is preserved as a separate five-field CSV teaching program; only its TODO region is completed. It does not include boarding stop/date, escaping or full numeric validation and must not be mistaken for the full transport format.

## Validation cases

| Input or interaction | Expected | What it verifies |
|---|---|---|
| Missing file lookup | Empty result | Clear missing-store policy |
| Add P1 and P2, find P2 | Exact immutable record | Save/load field agreement |
| Find P999 | Empty result | Missing ID is not a damaged-record error |
| List route 2 | Only P1 | Route selection is independent of file position |
| Add existing P1 | Duplicate rejected | ID uniqueness within the single writer |
| Append PARTIAL then add P3 | P3 found, tail reported | Partial tail does not swallow next valid record |
| Supplied P1003 lookup | [P1003, 192311003, Divya, 7, 3800.0] | Exact expected TODO output |
| Supplied damaged P1002 lookup | null | Incorrect field count skipped and scanning continues |

## Comparison with Part A
The implementation follows the Part A field order, escaping, checksum, reader loop and synchronous append protocol. A2 uses a byte array rather than character decoding because counting LF does not need all line strings. FIND skips bad records; SCAN additionally exposes line numbers/reasons for reporting. ADD scans for duplicates, so its total cost includes O(n) lookup, then O(new-record bytes) append. No multi-process safety or universal crash-atomic commit is claimed. The supplied TODO remains intentionally narrower: splitting on commas and requiring exactly five fields is all that scaffold guarantees. The separate full store handles the richer requirements.

## Measurement procedure
Create deterministic LF-only files of exactly 1000000, 10000000 and 50000000 bytes. Each contains 100-byte lines. Warm the buffered path once to establish a warm-cache experiment, then alternate unbuffered and 64 KiB block reads for three timed repetitions. System.nanoTime encloses stream open, scan and close. File generation is excluded. The counters retain lines and Java read-call counts. Both methods must match byteSize / 100 lines. Cache state, fixed order, JIT, storage and runtime scheduling limit extrapolation; results do not measure cold disks or syscall traces.

For growth, generate 1000, 10000 and 100000 valid full records, warm one lookup, and time three searches for the final pass. This deliberately exercises the complete scan. Generation is excluded; decoding, checksums, validation and I/O are included. A few repetitions do not prove a precise linear timing ratio; the loop structure establishes O(n) work.

## HashMap alternative
```text
ON STARTUP
    OPEN file and DECODE every valid record
    STORE map[passId] = record
ON QUERY
    RETURN map.get(requestedId)
```
For q searches over n bounded records, repeated scans cost O(q*n); building the map once costs O(n) plus expected O(q) hash lookups. The scan uses O(one record + buffer), while the map retains O(n) records/keys/buckets. Hash lookup is expected O(1), not a universal worst-case bound. Define a duplicate-ID policy rather than silently overwriting damaged input; the validated file writer rejects duplicates, but externally edited files still need audit. An in-memory index can become stale when another process edits the file; coordinate writes and update/rebuild the index. The measured index build and twenty successful lookups are recorded separately, with assertion printing outside the timed lookup region.

## Interpretation
A larger buffer greatly reduces tiny read calls, while final-record lookup must decode more rows as the file grows. The exact measured tables below support those observations without asserting a universal speed multiplier. Whole-file caching is justified only when repeated queries and memory budget outweigh startup and consistency costs.

## Reproduction and evidence

From the repository root run `python tools/compile.py`, then `python tools/run.py B1` with the local database configured for JDBC tasks. Actual full output, checks, CSV repetitions and compiler logs are in results; each screenshot is a real terminal capture. Bulk fixtures are generated deterministically rather than checked into GitHub.

## Observed buffering results

| Bytes | Method | Mean ms of three runs | Lines | Read calls |
|---:|---|---:|---:|---:|
| 1000000 | Single byte | 377.491 | 10000 | 1000001 |
| 1000000 | 64 KiB blocks | 1.350 | 10000 | 17 |
| 10000000 | Single byte | 3167.149 | 100000 | 10000001 |
| 10000000 | 64 KiB blocks | 5.267 | 100000 | 154 |
| 50000000 | Single byte | 16897.887 | 500000 | 50000001 |
| 50000000 | 64 KiB blocks | 30.227 | 500000 | 764 |

| Records | Mean last-record find ms |
|---:|---:|
| 1000 | 40.968 |
| 10000 | 58.364 |
| 100000 | 288.241 |

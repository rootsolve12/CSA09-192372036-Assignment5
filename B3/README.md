# B3 JDBC insertion and transaction experiments

## Aim and schema
Compare Statement, reusable PreparedStatement and 1000-row PreparedStatement batches in the dedicated MySQL assignment database. schema.sql uses InnoDB, a primary key on pass_id, a route index, typed decimal amount and route/amount checks. The full table has seven transport columns. The supplied PassLoader deliberately inserts its five named columns; boarding_stop defaults to empty and validity_date to NULL for this teaching fixture. B4 uses its own seven-parameter statement to preserve full records during migration.

## Small-data correctness and metadata
Each approach first inserts ten generated rows into a fresh table state. SELECT traverses the ResultSet and verifies each ID, nine-digit register, name, exact route, amount, and the two scaffold-default columns. ResultSetMetaData verifies all seven column names and JDBC types; metadata-verification.txt records this strengthened check for every method. Generated fixtures contain only deterministic safe text; the literal Statement comparison is not used for untrusted incoming records. PreparedStatement is the application choice.

## Measurement procedure
Generate the List<String[]> before timing and delete prior benchmark rows before each run. Connection creation and post-run SELECT validation are excluded; statement setup, parameter work, insert execution and the final commit are included. Use three timed repetitions per method/size after the small-data correctness exercise. No additional per-case JMH-style warmup is claimed. All three main methods use one transaction, making their comparison independent of per-row durable-commit frequency. Batch uses at most 1000 queued rows per executeBatch. Separately run the batch with auto-commit TRUE, also three repetitions at every size.

Connection settings enable useServerPrepStmts=true and rewriteBatchedStatements=true. Connector/J may rewrite batched INSERTs into multi-value requests; the measured gain includes that protocol/SQL rewrite and cannot be attributed solely to the addBatch API. Commit behaviour, server cache, indexes, filesystem durability, JVM effects and fixed method order affect timing.

## Supplied Complete the Code
PassLoader.java changes only TODO regions: it binds the five fields, parses route and amount, rejects non-finite/negative amounts, queues each row, executes/clears every 1000 rows, executes the remainder, commits and returns the count. On SQLException or RuntimeException it rolls back, preserves a rollback error as suppressed, rethrows, then restores the original auto-commit state. The program is called with 1000, 10000 and 100000 generated passes and verifies counts and restored auto-commit.

Use a connection with no pending caller transaction. Because the supplied scaffold always commits and rolls back that connection, merely restoring an initial FALSE auto-commit flag does not preserve an unrelated caller transaction. A reusable nested transaction API would need caller ownership or savepoints and a different contract. The assignment requires preserving the supplied scaffold outside TODOs, so the calling contract is explicit.

## Halfway failure evidence
In a fresh 10000-row case, make zero-based row 5000 contain an invalid numeric amount. The first five 1000-row chunks have executed. With auto-commit TRUE they remain committed: 5000 rows. With one transaction the failure rolls back all chunks: zero rows. The supplied loader also leaves zero rows and restores auto-commit. A separate duplicate-key failure exercises SQLException rollback, again leaving zero rows. transaction-verification.txt records the exact final halfway case; the original timed-run output is retained separately.

The database can make one SQL statement atomic without making a sequence of independently auto-committed statements atomic. For duplicate failures, Connector/J batch rewriting and partial execution can affect which statements succeeded; the key invariant for the single transaction is that all successful work is rolled back.

## Alternatives and complexity
```text
MULTI_ROW_INSERT
    FOR EACH chunk of b validated rows
        BUILD placeholders for b complete tuples
        BIND values; EXECUTE once
    END FOR
    COMMIT one transaction

LOAD_DATA
    VALIDATE and export a controlled staging text file
    LOAD DATA [LOCAL] INFILE into a staging table with explicit field rules
    CHECK rejected counts and constraints
    PROMOTE validated rows within the chosen transaction strategy
```
All designs must process at least O(n) row data. Separate Statement/Prepared execution commonly uses n client execute requests, while batches or multi-row chunks can reduce effective request count toward ceil(n/b), depending on driver settings. Both batch and multi-row builders retain O(b*record size) queued values/SQL, in addition to any input list. The supplied loader retains an O(n) caller list; the streaming B4 migrator avoids that input-list cost. Index maintenance, constraints and log writes remain database work and can approach O(n log N) as an indexed table grows. LOAD DATA can reduce parsing/protocol overhead, but file privileges, LOCAL configuration, validation and transactional semantics require server-specific review. It was not benchmarked or enabled here, so no measured speed superiority is claimed.

The batch-rewrite results provide evidence for grouped transfer, not an independent measurement of every multi-row SQL construction or LOAD DATA. For a nightly 100000-pass import, use validated streaming batches within an explicit transaction or clearly designed staging/checkpoint strategy. For one pass issued at a counter, use one parameterized INSERT with primary-key validation and an appropriate transaction boundary; buffering a single counter action into a huge batch adds latency without useful amortization.

## Reproduction and evidence

From the repository root run `python tools/compile.py`, then `python tools/run.py B3` with the local database configured for JDBC tasks. Actual full output, checks, CSV repetitions and compiler logs are in results; each screenshot is a real terminal capture. Bulk fixtures are generated deterministically rather than checked into GitHub.

## Observed insertion results

| Rows | Statement one transaction ms | Prepared one transaction ms | Batch one transaction ms | Batch auto commit ms |
|---:|---:|---:|---:|---:|
| 1000 | 318.245 | 265.337 | 61.215 | 50.915 |
| 10000 | 2162.866 | 1711.980 | 338.060 | 345.186 |
| 100000 | 20224.075 | 17628.007 | 3158.355 | 4180.552 |

PreparedStatement is selected for parameter safety and reusable binding, even when individual timing rows do not rank it fastest. Batch benefits reflect both grouping and the enabled Connector/J rewrite. Compare auto-commit and transaction costs using the actual table; do not assume one always wins at every size.

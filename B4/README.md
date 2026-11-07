# B4 Migration and production decision

## Aim and implemented migration
Migration reads the existing seven-field UTF-8 format one physical line at a time, validates checksum and fields, binds all seven columns and executes 1000-row batches in one owned JDBC transaction. Valid rows are committed together; invalid input lines are skipped and written to a rejection CSV with physical line number, reason and original line. A non-validation SQL/I/O failure before commit rolls back all newly inserted valid rows. This deliberate validation policy is not silently described as all-input acceptance.

```text
ALGORITHM MIGRATE
INPUT sourceFile, rejectionReport
OUTPUT imported count, rejected count and committed valid rows
BEGIN
    OPEN owned connection; SET autoCommit FALSE
    OPEN UTF8 reader and temporary rejection writer
    PREPARE seven-column INSERT
    FOR EACH physical line with lineNumber DO
        TRY decode and validate full record
        IF validation fails THEN
            WRITE lineNumber, reason and raw line to rejection report
            INCREMENT rejected; CONTINUE
        END IF
        BIND full record; ADD batch
        IF batch contains 1000 rows THEN EXECUTE and CLEAR batch END IF
    END FOR
    EXECUTE remaining batch; FLUSH rejection report
    COMMIT database transaction
    CLOSE resources; PUBLISH rejection report
    RETURN imported and rejected counts
ON precommit SQL or I/O failure
    ROLLBACK; PRESERVE original failure; CLOSE resources
END
```
Database commit and publishing a local file are not one distributed atomic action. If report publication fails after commit, the code explicitly reports that data committed and warns against a blind import retry. The temporary report is cleaned up. A production system could retain an import/rejection audit table in the same database transaction and export it later. The current error is not falsely reported as a rolled-back import.

## Demonstrated cases
The mixed fixture commits two valid records and reports three invalid lines. A SELECT confirms boarding stop and validity date are preserved. Repeating the same import produces a primary-key error and leaves the pre-existing two rows unchanged. A separate fresh-table scale check streams all 100000 generated full records, expects zero validation rejects and verifies the final database count. Its elapsed time includes read/decode/validation, batching, commit and rejection-report publication, so it is not directly comparable to B3 timings that start from an already constructed input list.

## Database metadata
DatabaseMetaData reports product/version, driver name/version, transaction support, current isolation and all base tables in the active catalog. This distinguishes it from ResultSetMetaData in B3, which describes query columns. Product/driver capabilities, table naming/case, URL, privileges and isolation can differ after moving servers; inspect them rather than assuming JDBC makes every SQL dialect interchangeable. Metadata is diagnostic evidence, not a substitute for migration/version checks.

## Decision for twelve campuses
At 100 times the original 8000 annual passes, interpret the new total as about 800000 passes per year across the twelve-campus service unless the requirement later specifies 100 times per campus. Several counters need authoritative uniqueness, indexed lookup and transactional writes. Use one logically shared relational database with centrally enforced primary keys, route indexes, constraints, authenticated application access, backups and an operational recovery plan. B1 shows scans grow with record count; B3 shows grouped transfer is useful for import; the transaction tests show why independently committed partial work is unsafe. Do not extrapolate a 100000-row time linearly into a production latency promise for twelve sites.

A single very large transaction can create locks/log pressure; the assignment demonstrates one transaction as required. For production, use staging tables and an idempotent import identifier, then promote verified data with a defined atomicity boundary, or commit documented chunks with restart/checkpoint semantics. Concurrent counters use separate connections, short transactions, database uniqueness and retry policies for deadlocks or uncertain commits. File backups and serialization may supplement archives, but should not be the shared concurrent system of record.

## Separate serialized campus files alternative
```text
FOR EACH of 12 campuses
    ACQUIRE the one writer lock for that campus snapshot
    LOAD or maintain its local object graph
    APPLY change and WRITE replacement snapshot
    RELEASE writer lock
END FOR
GLOBAL SEARCH queries every campus and merges results
```
Searching all serialized snapshots costs O(total records) loading/scanning if no indexes are retained; persistent per-campus in-memory hash indexes can improve expected key lookup after O(total records) startup but require coordinated updates and O(total records) memory. Twelve files still retain O(total data) storage plus snapshot/backup overhead. Object handles have no global identity across files. A file lock can serialize local writers, but cross-process/network locking, crash-safe replacement, global pass-ID uniqueness, cross-campus reports, backups and recovery become application responsibilities. Whole-snapshot updates typically cost O(campus data) I/O, while indexed database queries and row writes avoid rewriting every resident/pass. A shared database also has deployment, availability and network costs; choose it for the concrete concurrency and safety requirements, not because files never have a valid use.

## Reproduction and evidence

From the repository root run `python tools/compile.py`, then `python tools/run.py B4` with the local database configured for JDBC tasks. Actual full output, checks, CSV repetitions and compiler logs are in results; each screenshot is a real terminal capture. Bulk fixtures are generated deterministically rather than checked into GitHub.

## Observed streaming scale result

100000 full records, 0 rejects, 4906.136 ms total pipeline time. This single scale check establishes completion and count, not a stable performance distribution.

from pathlib import Path
import csv,statistics,json,datetime
R=Path(__file__).resolve().parents[1]
notes={
'A1':r'''# A1 Bus pass record formats and file operations

## Aim and theory
Represent all seven required fields without losing delimiters or silently accepting damaged records. Text is inspectable and portable; typed binary encoding avoids decimal parsing but needs an explicit versioned schema. The full store below is separate from the supplied five-field teaching example in B1.

## Two record layouts

| Order | Field | Text payload | DataOutputStream binary version 1 |
|---|---|---|---|
| Header | Format version | Defined as version 1 by this file contract | writeInt(1), four bytes |
| 1 | Pass ID | P followed by digits, max 32 characters | writeUTF, two-byte length then modified UTF-8 |
| 2 | Register number | Exactly nine ASCII digits, leading zeros retained | writeUTF |
| 3 | Name | Nonblank, max 80 UTF-16 code units | writeUTF |
| 4 | Route number | Positive base-10 integer | writeInt, four bytes |
| 5 | Boarding stop | Nonblank, max 80 UTF-16 code units | writeUTF |
| 6 | Validity date | ISO date YYYY-MM-DD | writeLong(epochDay), eight bytes |
| 7 | Amount paid | Nonnegative decimal with two places | writeLong(integer cents), eight bytes |
| Trailer | Corruption check | Eight lowercase CRC32 hex digits | No checksum in this basic binary demonstration |

Text is UTF-8, one physical record per line. The delimiter is a pipe. Escape a backslash as two backslashes and a pipe as backslash-pipe; reject CR/LF inside name and stop, rather than ambiguously permitting multiline records. Compute CRC32 over the exact escaped seven-field payload bytes and append pipe plus checksum. CRC detects accidental corruption; it is not authentication against an attacker who can recompute it. Binary uses Java modified UTF-8 for writeUTF, not ordinary UTF-8. Each string is length-prefixed and limited to 65535 encoded bytes; the bounded fields fit. A reader must mirror field order and reject an unknown version.

## Add a pass pseudocode
```text
ALGORITHM ADD_PASS
INPUT filePath, newPass
OUTPUT stored pass or explicit validation/write error
BEGIN
    VALIDATE all seven fields and reject CR or LF in text fields
    IF FIND_PASS(filePath, newPass.id) exists THEN REPORT duplicate; RETURN END IF
    IF file has a nonempty incomplete final line THEN
        SET separateTail TO TRUE
    ELSE SET separateTail TO FALSE
    END IF
    OPEN FileOutputStream(filePath, append TRUE)
    WRAP with OutputStreamWriter UTF8 and BufferedWriter
    IF separateTail THEN WRITE newline END IF
    WRITE escaped payload, separator and checksum
    WRITE newline; FLUSH writer; SYNC file descriptor
    CLOSE writer and underlying stream
END
```
The duplicate scan makes add O(n) in the current single-writer store, even though writing the new bytes is O(record length). Buffering coalesces small writes; flushing moves characters to the stream, and sync requests stable file storage. FileReader/FileWriter with an explicit UTF-8 charset could also be used on a recent JDK; the chosen bridge exposes the descriptor needed for sync.

## Find by ID pseudocode
```text
ALGORITHM FIND_PASS
INPUT filePath, requestedId
OUTPUT matching record or NOT_FOUND
BEGIN
    IF file is missing THEN RETURN NOT_FOUND END IF
    OPEN BufferedReader using UTF8
    WHILE a physical line can be read DO
        VERIFY checksum and escaped field count
        PARSE and VALIDATE types and domain rules
        IF damaged THEN RECORD reason and CONTINUE END IF
        IF record.id equals requestedId THEN CLOSE reader; RETURN record END IF
    END WHILE
    CLOSE reader
    RETURN NOT_FOUND
END
```
The implementation find method silently skips invalid records for lookup; the separate scan method exposes line numbers and reasons for an audit. Fatal I/O/UTF-8 decoding errors propagate instead of being misreported as a successful search.

## List by route pseudocode
```text
ALGORITHM LIST_ROUTE
INPUT filePath, requestedRoute
OUTPUT list of valid matching passes and optional rejection audit
BEGIN
    CREATE empty result
    IF file is missing THEN RETURN result END IF
    OPEN BufferedReader using UTF8
    FOR EACH physical line DO
        TRY decode and validate record
        IF decoding failed THEN REPORT line number and reason; CONTINUE END IF
        IF record.route equals requestedRoute THEN ADD record TO result END IF
    END FOR
    CLOSE reader
    RETURN result
END
```
Find and route selection scan O(n) records, plus their total byte length. Find retains O(one record + buffer); list retains O(r) matching records. Bounded field lengths make the shorthand O(n) appropriate.

## Damaged data and power failure
A missing file is an empty store for lookup/list and is created on first add. Wrong field counts, numeric/date failures and checksum failures are rejected; an unreadable file is an I/O error. A torn final append cannot be assumed complete. Validate checksum and fields on restart, report the bad tail, and insert a newline before a later append so the next complete record is not joined to it. sync reduces acknowledged-data loss, but this append protocol is not a universally crash-atomic filesystem transaction; a crash before sync can lose or truncate the new row. Existing rejected lines are retained for audit. A stricter alternative writes a complete replacement to a sibling temporary file, forces it, atomically renames it when supported and addresses directory durability; that costs O(file size) per rewrite. Backups remain necessary.

The synchronized add method serializes calls on one store instance only. It does not protect multiple JVMs or different instances; operate with one writer, or coordinate writers with one shared lock protocol. B4 replaces this assumption with database transactions and primary-key enforcement for concurrent counters.

## RandomAccessFile alternative
Use a fixed 512-byte big-endian record: version int 4; pass ID 32 writeChar positions 64; register 9 positions 18; name 80 positions 160; route int 4; stop 80 positions 160; epochDay long 8; cents long 8; reserved padding 86. Fields are padded to exact widths and validated before writing; do not use variable-length writeUTF in fixed slots.

```text
INPUT zeroBasedRecordIndex, recordSize 512
SEEK zeroBasedRecordIndex * 512
READ exactly one fixed record
```
One positional seek is O(1) only when the record index is already known. Arbitrary pass IDs require a separate ID-to-index map or a dense validated ID-to-slot rule; fixed length alone does not turn an unknown-ID search into O(1). A scan is still O(n) without that mapping. Padding waste is 512 minus [24 + 2 times total stored string code units] bytes per record, including the always reserved 86 bytes. Eight thousand slots occupy 4096000 bytes. Text avoids fixed-width padding but pays delimiter, escape, checksum and numeric-character overhead.

## Executed illustration
RecordLayouts round-trips a name containing a pipe and a backslash through both designs. This is supporting evidence; the pseudocode above remains the Part A answer. See results/execution.txt for actual byte counts and checks.
''',
'A2':r'''# A2 Buffered attendance log counting

## Prediction and theory
For a 50 decimal MB file, FileInputStream.read() called once per byte performs 50000000 successful Java calls plus one EOF call. If MB means MiB instead, the byte count is 52428800, plus EOF. B1 uses exact decimal byte sizes and records them explicitly. The original loop repeatedly crosses the Java/native boundary and usually requests extremely small operating-system reads. This call overhead dominates simple newline counting even if file data is already in the OS page cache.

## Buffered redesign pseudocode
```text
ALGORITHM COUNT_LINES
INPUT filePath, byte buffer capacity 65536
OUTPUT number of LF-delimited lines
BEGIN
    SET lines TO 0; SET lastByte TO NONE
    OPEN FileInputStream
    WHILE block read returns bytes DO
        FOR EACH byte in the block DO
            IF byte equals LF THEN INCREMENT lines END IF
        END FOR
        SET lastByte TO final byte of the block
    END WHILE
    IF at least one byte was read AND lastByte is not LF THEN INCREMENT lines END IF
    CLOSE stream
    RETURN lines
END
```
A 64 KiB byte-array loop needs about ceil(B/65536) successful reads plus EOF on ordinary full block reads: 764 total calls at 50000000 bytes. Actual counted API calls are logged, rather than presented as a strace measurement of kernel syscalls. BufferedInputStream is another option: its read() loop still makes B character-level Java calls but refills the underlying stream in blocks. Neither design avoids examining O(B) bytes. The block implementation uses O(buffer size) auxiliary memory; the original uses O(1). The line contract is LF with an optional final unterminated line. CRLF is handled through its LF byte; bare-CR files need a different rule.

## When buffering helps little
Adding a BufferedInputStream around code already reading large byte arrays may add copying without reducing operating-system requests. A tiny file dominated by open/close latency is another case; cache and workload details matter. Buffering does not make an O(B) scan sublinear.

## Files readAllLines alternative
```text
lines = Files.readAllLines(filePath, UTF8)
RETURN size(lines)
```
This is simple and suitable when later work needs all text lines. It decodes the whole file, constructs a list and strings, and retains O(B + number of lines) data/metadata, compared with O(65536) scan buffer state. A 50 MB raw file does not imply exactly 50 MB Java heap usage: strings, arrays, list references and encoding representation add overhead. Both approaches take O(B) time, but readAllLines also allocates and decodes. It also accepts Java text-line rules including bare CR, which differ from the stated byte counter; compare equivalent LF datasets. For a count-only large log, streaming avoids keeping text that is not needed.

## Executed checks
LineCounter checks empty data, a terminated line, an unterminated final line and CRLF. BufferExperiments in B1 records three runs per method at 1, 10 and 50 decimal MB, with matching expected counts and actual read-call counters.
''',
'A3':r'''# A3 Generic data access design

## Repeated pattern and varying parts
StudentDB, CourseDB and MarksDB repeat connection acquisition, statement construction, parameter binding, execution, ResultSet traversal, mapping, error propagation and resource closing. Table/column names, key type, domain type, bound values and row-to-object mapping vary. Centralize the boundary behind a generic DAO contract; do not pretend generics automatically generate SQL or transactions.

| Contract | Meaning |
|---|---|
| Dao<T,K>.insert(T) | Persist one object |
| findById(K) to Optional<T> | Find zero or one object by primary key |
| findAll() to List<T> | Map every selected row |
| update(T) | Change one object's non-key fields |
| delete(K) to boolean | Report whether one row was removed |

## Generic design pseudocode
```text
INTERFACE Dao OF ObjectType T AND KeyType K
    INSERT(object T)
    FIND_BY_ID(key K) RETURNS OPTIONAL T
    FIND_ALL() RETURNS LIST OF T
    UPDATE(object T)
    DELETE(key K) RETURNS BOOLEAN
END INTERFACE

CLASS StudentDao IMPLEMENTS Dao OF Student AND String
    INSERT student using bound reg_no, name and email
    FIND_BY_ID using WHERE reg_no = bound key
    FIND_ALL using explicit columns ordered by reg_no
    MAP every row to Student(reg_no, name, email)
    UPDATE name and email using bound primary key
    DELETE using bound primary key
    CLOSE connection statement and result set on every path
    PROPAGATE SQL failures to the service boundary
END CLASS
```

```mermaid
classDiagram
 Dao~T,K~ <|.. StudentDao
 StudentDao --> Student
 StudentDao --> Db
 Service --> Dao~T,K~
```

## Object to table mapping

| Student field | SQL column | SQL type and rule |
|---|---|---|
| register String | reg_no | CHAR(9), primary key; leading zeros retained |
| name String | name | VARCHAR(80), NOT NULL |
| email String | email | VARCHAR(120), NOT NULL |

The primary key identifies the row; it is not inferred from object identity. PreparedStatement binds data, while ResultSet getters use the explicit column names. The executed StudentDao demonstrates all five operations in the dedicated test database.

## SQL inside services or GUI alternative
```text
ON GUI_SAVE
    OPEN connection
    BUILD student INSERT SQL in GUI
    BIND values and EXECUTE
    DISPLAY result
```
If the same query appears at s GUI/service sites, a column rename can require s code-site edits, plus the database migration. With StudentDao, student SQL/mapping is concentrated in one implementation file plus the migration; all affected SQL statements inside that file must still change. Dao<T,K> usually stays stable if the Java model property does not change. Identical SQL has the same database asymptotic time and result-memory requirements in both designs: indexed key lookup is typically O(log n) index work, findAll O(n) row work and O(n) retained output. DAO dispatch adds an ordinary constant method-call cost, not a new database algorithm. The main gain is ownership, testability and reduced scattered coupling, not guaranteed speed. Multi-operation transactions need a shared transaction boundary rather than opening unrelated connections in each DAO call.
''',
'A4':r'''# A4 Serialization scope and evolution

## Persistent and transient fields
Persist the Hostel room list, each Room identifier/list, and each Resident name and register number. Password and live JDBC Connection must be transient. A database connection is an external session/resource, not portable saved state. A plain password should not be copied into a snapshot. If authentication requires persistence, use an appropriately protected password-hash store outside this object graph, rather than simply serializing a password field.

Serialization walks reachable non-transient fields, including ArrayList contents. Hostel, Room and Resident implement Serializable. Shared references and cycles are represented through object handles, preserving identity; the same resident referenced by two room lists remains the same restored object. Every other reachable non-transient object must be serializable or writing fails with NotSerializableException. Transient reference fields read back as null unless explicitly reconstructed. Establish fresh data-access resources in a service when needed; per-resident Connection fields are best removed entirely in a refined design.

## Version change pseudocode
```text
CLASS Resident IMPLEMENTS Serializable
    CONSTANT serialVersionUID = 1
    PERSIST name, register
    TRANSIENT password, liveConnection
    OPTIONAL NEW FIELD phone
END CLASS

ON READING AN OLDER COMPATIBLE FILE
    MATCH class descriptor and serialVersionUID
    RESTORE old fields
    INITIALIZE missing reference field phone TO null
    VALIDATE restored state and apply any migration defaults
END
```
Keeping an explicit matching serialVersionUID allows compatible addition of an ordinary String phone field; old data has null for the missing field. A primitive would receive its default value. This is not a guarantee for every schema change: incompatible type/hierarchy changes still need design care. A different UID causes InvalidClassException. If UID is omitted, Java computes one from class details; a change can alter it unexpectedly. Constructors of serializable classes are not a substitute for validating loaded state. Deserialize only trusted local files with an appropriate ObjectInputFilter; filtering does not make arbitrary hostile serialization safe.

## Executed version experiments
Three separately compiled programs share identical class names. Version v1 writes a two-room graph with one shared resident and a real live JDBC reference excluded by transient. v1 reads it and checks transient defaults and shared identity. v2 adds phone with UID 1 and checks phone is null. The incompatible version changes Resident UID to 2 and is expected to reject the file. SerializationChecks treats that specific child-process failure as a passed negative test.

## CSV or JSON alternative
```text
SAVE each resident as roomId, register, name, optional phone
DO NOT WRITE password or liveConnection
LOAD records into objects
IF phone is absent THEN use null or a validated default
REBUILD room membership and identity links by explicit IDs
```
For n bounded resident records, both save/load designs take O(n + reference count) graph/record work and O(data bytes) I/O. A streaming text implementation can use O(one row) extra memory while reconstructing the final O(n) model; object serialization uses handle tables proportional to distinct objects/references. JSON labels and escaping add text overhead; binary serialization adds class descriptors and object handles, so neither is universally smaller. Text schemas can ignore unknown optional fields or default absent ones when the parser is designed to do so. CSV needs a header/schema version and explicit new-column handling. Text does not automatically preserve Java object identity or cycles; stable resident IDs are needed. The actual small binary graph size is recorded, but no universal size ratio or text performance claim is inferred from it.
''',
'A5':r'''# A5 Transaction correctness and injection safety

## Wallet transfer pseudocode
```text
ALGORITHM TRANSFER_500
INPUT sourceWallet, targetWallet
OUTPUT committed transfer or rollback error
BEGIN
    OPEN owned JDBC connection
    SET autoCommit TO FALSE
    TRY
        LOCK source and target rows in ascending wallet ID order
        DEBIT source by 500 WHERE sufficient balance exists
        IF affected row count differs from 1 THEN RAISE failure END IF
        CREDIT target by 500
        IF affected row count differs from 1 THEN RAISE failure END IF
        COMMIT
    ON any SQL failure
        ROLLBACK; preserve original exception if rollback also fails
        REPORT failure
    FINALLY CLOSE owned connection
END
```
With InnoDB, both row changes commit together or neither does; a failed process before commit cannot leave just the debit committed. Deterministic lock order reduces opposing-transfer deadlocks. Check source sufficiency and affected-row counts, use decimal money, and do not reuse a failed/uncertain transaction blindly. A network loss during commit can leave the client uncertain whether commit succeeded, so production retries need durable transfer identifiers/idempotency; a rollback request cannot undo a transaction already committed on the server.

## Injection analysis and safe redesign
The supplied query concatenates untrusted input inside SQL quotes. In this dedicated local fixture, the ID `' OR '1'='1' -- ` ends the string, adds a true OR condition and comments out the password condition. The comment marker includes a following space for MySQL's syntax. It can therefore return a user row with an invalid password.

```text
sql = SELECT id FROM users WHERE id = ? AND pwd = ?
PREPARE statement
BIND id as parameter 1
BIND password as parameter 2
EXECUTE and test whether a row exists
```
Parameters are values, not executable SQL structure. B2 runs the exact unsafe and parameterized checks only in a database created for this assignment. The plain password column is an isolated teaching fixture, not a production authentication design; a real application queries by ID and verifies a salted password hash through a suitable password library.

## Two independent auto commits alternative
```text
EXECUTE debit with autoCommit TRUE
PROGRAM FAILS HERE
EXECUTE credit with autoCommit TRUE
```
The first update is already permanent; failure before the second leaves 500 missing from the two-wallet total. One transaction performs the same two updates plus transaction coordination, locks and a commit; independent auto-commit performs two durable commit boundaries. For fixed two-row updates both have constant statement counts and similar indexed operation complexity, but latency, log flush policy, network trips and contention determine actual time. A transaction can even reduce commit flush overhead. Any small speed difference does not justify violating the money invariant. The real failure experiment records rollback, successful transfer and the unsafe partial result in results/execution.txt.
'''
}
for task,text in notes.items():(R/task/'README.md').write_text(text+'\n## Reproduction and evidence\n\nCompile with `python tools/compile.py`, then run `python tools/run.py '+task+'` with the configured local database where needed. Supporting Java illustrates the design; the Part A pseudocode above is the design submission. Actual outputs, expected negative tests and compiler records are in results; screenshots show real terminal execution.\n')
print('Prepared Part A design notes')
notes_b={
'B1':r'''# B1 Instrumented bus pass file store

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
''',
'B2':r'''# B2 Adversarial input engineering

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
''',
'B3':r'''# B3 JDBC insertion and transaction experiments

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
''',
'B4':r'''# B4 Migration and production decision

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
'''}
for task,text in notes_b.items():(R/task/'README.md').write_text(text+'\n## Reproduction and evidence\n\nFrom the repository root run `python tools/compile.py`, then `python tools/run.py '+task+'` with the local database configured for JDBC tasks. Actual full output, checks, CSV repetitions and compiler logs are in results; each screenshot is a real terminal capture. Bulk fixtures are generated deterministically rather than checked into GitHub.\n')

def summary_tables():
 p=R/'B1/results/buffering.csv'
 if p.exists():
  data=list(csv.DictReader(p.open()));text='\n## Observed buffering results\n\n| Bytes | Method | Mean ms of three runs | Lines | Read calls |\n|---:|---|---:|---:|---:|\n'
  for n in [1000000,10000000,50000000]:
   for buffered in ['false','true']:
    rows=[r for r in data if int(r['bytes'])==n and r['buffered']==buffered];text+=f"| {n} | {'64 KiB blocks' if buffered=='true' else 'Single byte'} | {statistics.mean(int(r['elapsed_ns'])/1e6 for r in rows):.3f} | {rows[0]['lines']} | {rows[0]['read_calls']} |\n"
  data=list(csv.DictReader((R/'B1/results/growth.csv').open()));text+='\n| Records | Mean last-record find ms |\n|---:|---:|\n'
  for n in [1000,10000,100000]:text+=f"| {n} | {statistics.mean(int(r['elapsed_ns'])/1e6 for r in data if int(r['records'])==n):.3f} |\n"
  with (R/'B1/README.md').open('a') as f:f.write(text)
 p=R/'B3/results/insert-measurements.csv'
 if p.exists():
  data=list(csv.DictReader(p.open()));text='\n## Observed insertion results\n\n| Rows | Statement one transaction ms | Prepared one transaction ms | Batch one transaction ms | Batch auto commit ms |\n|---:|---:|---:|---:|---:|\n'
  for n in [1000,10000,100000]:
   vals=[statistics.mean(int(r['elapsed_ns'])/1e6 for r in data if int(r['rows'])==n and r['method']==method and r['auto_commit']==auto) for method,auto in [('Statement','false'),('Prepared','false'),('Batch','false'),('Batch','true')]];text+='| '+str(n)+' | '+' | '.join(f'{v:.3f}' for v in vals)+' |\n'
  text+='\nPreparedStatement is selected for parameter safety and reusable binding, even when individual timing rows do not rank it fastest. Batch benefits reflect both grouping and the enabled Connector/J rewrite. Compare auto-commit and transaction costs using the actual table; do not assume one always wins at every size.\n'
  with (R/'B3/README.md').open('a') as f:f.write(text)
 p=R/'B4/results/migration-scale.csv'
 if p.exists():
  row=next(csv.DictReader(p.open()));
  with (R/'B4/README.md').open('a') as f:f.write(f"\n## Observed streaming scale result\n\n{row['records']} full records, {row['rejected']} rejects, {int(row['elapsed_ns'])/1e6:.3f} ms total pipeline time. This single scale check establishes completion and count, not a stable performance distribution.\n")
summary_tables()
(R/'README.md').write_text('''# CSA09-192372036-Assignment5

**B Hitesh Roy — Register 192372036**  
Programming in Java — Assignment 5 CO5 — Individual — 50 marks

Part A contains actual design answers, layouts, structured pseudocode and reasoning; Java illustrations do not replace pseudocode. Part B contains the full seven-field file store, the two exact supplied TODO completions, local adversarial tests, MySQL insertion/rollback experiments and a streaming migration. The Word/PDF report follows the code and GitHub stage.

## Environment

OpenJDK 21.0.13 compilation and command-line execution, MySQL Community Server 8.4.13, MySQL Connector/J 9.5.0. A full desktop JRE 21.0.12.1 is used only for real terminal screenshot capture. The source needs Java 17 or later. Python 3 orchestrates compilation and runs. Synthetic test data is confined to the dedicated assignment5 schema. Passwords, database files, dependency binaries and generated bulk files are excluded from Git.

## Setup and reproduce

Create a dedicated MySQL database and run B3/schema.sql. Create an application user with SELECT, INSERT, UPDATE and DELETE only on that database. Place Connector/J in deps/mysql-connector-j.jar. Configure ASSIGNMENT_DB_URL, ASSIGNMENT_DB_USER and ASSIGNMENT_DB_PASSWORD in your local environment, never in source. The default URL is jdbc:mysql://127.0.0.1:3307/assignment5?rewriteBatchedStatements=true&useServerPrepStmts=true; use your own port and preserve/disclose these measurement settings.

```sh
java -version
python tools/compile.py
python tools/run.py
# Or run one task (some require generated data from B1):
python tools/run.py B3
```

A1/RecordLayouts illustrates both text and binary layouts. A2/LineCounter is used by B1. A3 executes the generic StudentDao. A4 separately compiles three same-named serialization versions; keep their build directories isolated. A5 runs synthetic wallet transaction tests. B1 executes both the supplied PassStore and the full BusPassStore. B2 challenges only the dedicated local test database. B3 runs the supplied PassLoader plus insertion comparisons. B4 migrates the mixed fixture and a generated 100000-record file. MigrationScale can be run separately after B1 creates its file. Raw bulk inputs are recreated from code, not uploaded.

## Task map

| Task | Marks | Evidence |
|---|---:|---|
| [A1](A1/README.md) | 7 | Seven-field text/binary layouts, three algorithms, damage and seek analysis |
| [A2](A2/README.md) | 5 | Read-call prediction, buffer algorithm and memory trade-off |
| [A3](A3/README.md) | 5 | Generic DAO pseudocode, class diagram and object/table mapping |
| [A4](A4/README.md) | 4 | Transient graph fields, compatible phone addition and expected UID rejection |
| [A5](A5/README.md) | 4 | Atomic wallet algorithm and local injection analysis |
| [B1](B1/README.md) | 7 | File checks, exact supplied output, buffering and growth CSVs |
| [B2](B2/README.md) | 5 | Unsafe/safe query outcomes and three damaged-line reasons |
| [B3](B3/README.md) | 8 | Metadata, 36 measured insertion cases, loader counts and rollback checks |
| [B4](B4/README.md) | 5 | Mixed/large migration, rejection CSV, metadata and production decision |

## Interpretation and provenance

Every output and screenshot comes from actual workspace execution, not claimed personal execution on the student device. Personally execute and understand all required programs for verification. Negative tests are intentional: incompatible serialization UID, local unsafe SQL bypass, independently committed wallet loss and partial auto-commit batch inserts demonstrate the defects being investigated. The safe variants check the required invariants. Progressive commits correspond to task work in this session; no prior-day history is fabricated.

B1 uses exact decimal MB, three timed repetitions and a warm-cache design. B3 measures three repetitions per method/size including commit but excluding generation/cleanup/connection creation. Batch rewriting is enabled and disclosed. No timing is treated as a universal guarantee. The five-field supplied programs remain separate from full seven-field persistence so boarding stop/date are not silently discarded. The exact GCR report filename and deadline must come from the classroom description.
''')
print('Prepared Part B notes and measured result tables')

# A1 Bus pass record formats and file operations

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

## Reproduction and evidence

Compile with `python tools/compile.py`, then run `python tools/run.py A1` with the configured local database where needed. Supporting Java illustrates the design; the Part A pseudocode above is the design submission. Actual outputs, expected negative tests and compiler records are in results; screenshots show real terminal execution.

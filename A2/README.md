# A2 Buffered attendance log counting

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

## Reproduction and evidence

Compile with `python tools/compile.py`, then run `python tools/run.py A2` with the configured local database where needed. Supporting Java illustrates the design; the Part A pseudocode above is the design submission. Actual outputs, expected negative tests and compiler records are in results; screenshots show real terminal execution.

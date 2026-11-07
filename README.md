# CSA09-192372036-Assignment5

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

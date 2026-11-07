# A4 Serialization scope and evolution

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

## Reproduction and evidence

Compile with `python tools/compile.py`, then run `python tools/run.py A4` with the configured local database where needed. Supporting Java illustrates the design; the Part A pseudocode above is the design submission. Actual outputs, expected negative tests and compiler records are in results; screenshots show real terminal execution.

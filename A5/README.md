# A5 Transaction correctness and injection safety

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

## Reproduction and evidence

Compile with `python tools/compile.py`, then run `python tools/run.py A5` with the configured local database where needed. Supporting Java illustrates the design; the Part A pseudocode above is the design submission. Actual outputs, expected negative tests and compiler records are in results; screenshots show real terminal execution.

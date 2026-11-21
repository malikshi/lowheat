# Comment debt ledger

Every Excuse-category comment removed by a comment audit leaves one row here, so
the hacky implementation it was excusing is tracked instead of forgotten. Delete a
row in the commit that fixes the hack; delete this file once the table is empty.

A comment is an **Excuse** when its only job is to justify a shortcut the code
should not have taken — a workaround, a disabled check, a second source of truth,
or a "temporary" branch that outlived the reason.

| id | file:line | hack the comment excused | fix | owner |
|---|---|---|---|---|

No open entries: every comment in this repository is a mandated CodeDNA
annotation, and no CodeDNA annotation was judged an Excuse at the last audit.

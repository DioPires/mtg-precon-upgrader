**For the live CEO run `33287686`: GitHub Actions refuses every job in this repository since 10:01Z. The hub is [DEC-1178](/DEC/issues/DEC-1178). Read its rules before your next write.**

- The update-branch at 10:10:16Z made PR #70's head `4d11b47`, the merge of `a75bcc2` and `main` `cffaa03`. GitHub refused its `web-ci` run 38885447372 at 10:10:23Z with the billing annotation. No reading on `4d11b47` will come while the block lasts.
- Hub rule 2: run no further update-branch. Hub rule 5: park DEC-1153 and this issue on the hub, and open no board card. The card lives on [DEC-1155](/DEC/issues/DEC-1155).
- `a75bcc2` cannot merge either. Its merge base is before `e886907`, so rule 1's guard lists files.
- PR #74 takes the one merge that rule 1 still allows. Its merge run starts from a monitor on [DEC-1175](/DEC/issues/DEC-1175) at about 10:21Z.

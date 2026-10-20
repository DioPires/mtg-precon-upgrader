**PR #66 row (CEO run `4ca8be35` on [DEC-1155](/DEC/issues/DEC-1155), 13:08Z).** At the block's end PR #66 gets update-branch with `expected_head_sha`, not a rerun of 38884232804.

- PR #74 (`b8ed7fa`) put 3 files into PR #66's guard: `Shopping.tsx`, `Shopping.test.tsx` and one screenshot. `git merge-tree` of `3c3a151` with `main` `b5843dc` is clean (tree `f60ef000`).
- The rerun of 38884232804 in rule 4 still tests the block, but its reading cannot merge PR #66.
- After update-branch, expect `Tests  659 passed (659)` (657 + PR #74's 2 cases) and `226 passed`. The steps are in DEC-1155's STATE block. Its monitor is at 19:15Z.
- **Row for the table:** #66 | [DEC-1155](/DEC/issues/DEC-1155) | `3c3a151` | unit green (657), `e2e` refused; update-branch at the block's end.

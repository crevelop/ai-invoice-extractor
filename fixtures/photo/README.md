# Photographed receipt (user-provided)

Drop the photographed receipt image here (e.g. `receipt.jpg`), then delete
`receipt-placeholder.jpg` — a synthetic stand-in (from
`fixtures/gen/placeholder_photo.py`) that keeps chapter 1 runnable until the
real photo lands. Chapter 1 prefers a non-placeholder image when one exists.

It powers the chapter-1 adapter demo (photo → image path of the `Document`
shape) and covers the "photographed pages" row of the failure matrix
(SPEC.md §5.5). It is the one fixture the generator does not produce, and
its gold label is genuinely hand-written (synthetic docs are true by
construction — see `fixtures/gen/__init__.py`).

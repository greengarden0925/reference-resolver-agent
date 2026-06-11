---
name: reference-resolver-agent
description: resolve plain-text, apa, mla, or incomplete reference lists into endnote-ready import files. use when the user asks to convert citations or references into .ris, .enw, or .bib; recover missing doi, pmid, journal, volume, issue, pages, or authors; search by title using crossref, pubmed, semantic scholar, openalex, or google scholar fallback; deduplicate references; or build a citation-to-endnote workflow or agent.
---

# Reference Resolver Agent

## Core workflow

Use this skill to turn messy citation text into a validated EndNote import file. Prefer reliable bibliographic APIs before Google Scholar.

1. Parse each raw reference into probable fields: title, first author, year, doi, journal/book, volume, issue, pages, url, and publication type.
2. Search in this order unless the user specifies otherwise:
   - exact DOI if present
   - Crossref for journal articles, books, preprints, and conference papers
   - PubMed for biomedical literature
   - Semantic Scholar or OpenAlex for broad scholarly matching and citation metadata
   - Google Scholar only as low-frequency/manual fallback because it has no official public API and may trigger CAPTCHA
3. Match candidates using title similarity first, then author/year/doi/journal agreement.
4. Mark uncertain matches as `needs_review` instead of guessing.
5. Export one or more import files: `.ris` for EndNote/Reference Manager, `.enw` for EndNote tagged format, and `.bib` when BibTeX is requested.
6. Provide a short unresolved-items report listing references that need manual review.

## Matching rules

Use conservative matching.

- Accept automatically when title similarity is at least 0.90 and year or first author agrees.
- Accept DOI matches even when casing differs.
- Flag for review when title similarity is 0.75-0.89, author/year conflict, or multiple candidates are close.
- Reject when title similarity is below 0.75 unless DOI exactly matches.
- Preserve original user-provided fields when API results are missing or obviously incomplete.

For books, Crossref and Google Scholar records may disagree on edition, publisher, or year. Keep edition statements from the user's original reference when the API result omits them.

## Output requirements

When producing import text directly in chat:

- Prefer RIS for EndNote unless the user asks for `.enw`.
- Separate records with `ER  -` in RIS and a blank line in ENW.
- Put each author on a separate `AU  -` line in RIS or `%A` line in ENW.
- Include `DO  -` for DOI without `https://doi.org/`.
- Include `UR  -` for URL.
- Use suitable RIS types: `JOUR`, `BOOK`, `CHAP`, `CONF`, `THES`, `RPRT`, `ELEC`, `GEN`, or `PREPRINT` only if the target importer supports it; otherwise use `GEN` with `T2  - arXiv` for preprints.

## Scripted batch conversion

For batch processing, use `scripts/reference_resolver.py`. It can parse a text file, resolve records through public APIs when internet access is available, and export RIS/ENW/BibTeX.

Typical commands:

```bash
python scripts/reference_resolver.py input.txt --format ris --output references.ris
python scripts/reference_resolver.py input.txt --format enw --output references.enw
python scripts/reference_resolver.py input.txt --format bib --output references.bib
python scripts/reference_resolver.py input.txt --format ris --output references.ris --no-network
```

Use `--no-network` when the environment lacks internet or the user only wants a best-effort conversion from provided text.

## Google Scholar fallback

Do not claim full automation through Google Scholar unless the user accepts the operational risk. Explain that Scholar has no official public API, can rate-limit or require CAPTCHA, and is best used as:

- a manual verification step,
- a low-frequency fallback,
- or through a user-provided downloaded citation file.

If the user asks specifically for Scholar-driven retrieval, design the agent so Scholar is isolated behind a fallback module and always caches results.

## Quality checklist

Before returning final files or import text:

- Validate that every record has a title and year when available.
- Check author line splitting.
- Confirm DOI normalization.
- Deduplicate by DOI first, then normalized title plus year.
- List unresolved or low-confidence references separately.

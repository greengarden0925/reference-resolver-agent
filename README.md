# Reference Resolver Agent

A Claude Code skill that converts messy plain-text citations (APA, MLA, or incomplete) into clean EndNote-ready import files (`.ris`, `.enw`, `.bib`).

## Features

- Parses plain-text references into structured fields (title, authors, year, DOI, journal, volume, issue, pages)
- Enriches records via public bibliographic APIs: **Crossref → PubMed → Semantic Scholar / OpenAlex → Google Scholar fallback**
- Exports to `.ris` (EndNote / Reference Manager), `.enw` (EndNote tagged), and `.bib` (BibTeX)
- Conservative matching — uncertain records are flagged as `needs_review` instead of silently guessed
- Deduplicates by DOI, then by normalized title + year
- Generates a JSON report listing unresolved and low-confidence references

## File Structure

```
reference-resolver-agent/
├── pyproject.toml            # Python package metadata (pip install)
├── SKILL.md                  # Claude Code skill definition
├── agents/
│   └── openai.yaml           # Agent interface configuration
├── assets/
│   └── icon.svg              # Skill icon
├── references/
│   └── field_mapping.md      # RIS / ENW field reference
└── scripts/
    └── reference_resolver.py # Batch conversion script (pure Python, stdlib only)
```

## Quick Start

### Install (recommended)

```bash
pip install .
```

Then run from anywhere:

```bash
reference-resolver input.txt --format ris --output references.ris
reference-resolver input.txt --format enw --output references.enw
reference-resolver input.txt --format bib --output references.bib

# Offline mode — parse only, skip API lookups
reference-resolver input.txt --format ris --output references.ris --no-network
```

### In Claude Code (skill mode)

Just describe your references or paste a reference list and ask Claude to convert them to EndNote format. The skill handles parsing, API lookups, and export automatically.

### Run without installing

```bash
python scripts/reference_resolver.py input.txt --format ris --output references.ris
python scripts/reference_resolver.py input.txt --format enw --output references.enw
python scripts/reference_resolver.py input.txt --format bib --output references.bib
python scripts/reference_resolver.py input.txt --format ris --output references.ris --no-network
```

A JSON resolution report is written alongside the output file (e.g. `references.ris.report.json`). Use `--report <path>` to specify a custom path.

**Requirements:** Python 3.8+, no third-party packages needed.

## Input Format

The script accepts a plain-text file where references are separated by blank lines, or a continuous APA-style list. Example:

```
Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N.,
Kaiser, L., & Polosukhin, I. (2017). Attention is all you need. Advances in
Neural Information Processing Systems, 30, 5998–6008.

LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553),
436–444. https://doi.org/10.1038/nature14539
```

## Matching Confidence

| Score | Status | Behaviour |
|-------|--------|----------|
| ≥ 0.90 or exact DOI | `resolved` | Accepted automatically |
| 0.75 – 0.89 | `needs_review` | Kept but flagged |
| < 0.75 | `needs_review` | Not replaced; original fields preserved |

## Supported Reference Types

| RIS type | ENW type | Description |
|----------|----------|-------------|
| `JOUR` | Journal Article | Journal papers |
| `BOOK` | Book | Monographs, edited books |
| `CONF` | Conference Paper | Proceedings |
| `THES` | Thesis | Dissertations |
| `RPRT` | Report | Technical reports |
| `GEN` | Generic | arXiv preprints and fallback |

## Notes on Google Scholar

Google Scholar has no official public API and may rate-limit or require CAPTCHA. It is used only as a manual fallback — not for automated batch resolution. If Scholar-based retrieval is needed, results should be cached and the module isolated behind the other API sources.

## License

MIT

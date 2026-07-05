# Log template

Copy for `pkf/log.md`. Newest-first, grouped under `## YYYY-MM-DD` date headings — the date
lives on the heading, not repeated per entry. Convention words: Initialization, Creation,
Update, Removal, Fix, Deprecation. Historical links may dangle — that's expected, never rewrite
them. Rotate to `log-YYYY.md` once this file passes ~500 entries.

```markdown
# Log

<!-- Chronological history, NEWEST FIRST. Group entries under a `## YYYY-MM-DD` heading.
     Each entry:  * **Action**: prose with [links](relative/path.md).
     Convention words: Initialization, Creation, Update, Removal, Fix, Deprecation.
     Historical links may dangle (exempt from the link check). Rotate at 500 entries -> log-YYYY.md. -->

## 2026-07-04
* **Creation**: Filed [transcript-timestamp-toggle](issues/transcript-timestamp-toggle.md).
* **Update**: Synced [docs/transcription/transcribe-audio](docs/transcription/transcribe-audio.md)
  after resolving it.
```

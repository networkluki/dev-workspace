# Changelog

Alla noterbara ändringar i `exa` dokumenteras i denna fil.

Formatet följer [Keep a Changelog](https://keepachangelog.com/sv/1.1.0/)
och projektet använder [Semantisk versionshantering](https://semver.org/lang/sv/).

## [1.0.1] - 2026-09-03

### Tillagt

- `-version` (ett bindestreck) som alias för `-V`/`--version`.

## [1.0.0] - 2026-09-03

### Tillagt

- Grundläggande `exa`-kommando i Python (endast standardbibliotek) som ersätter `ls`.
- Rutnätsvy (kolumner) som fyller terminalbredden — standardläge.
- Långt format (`-l`/`--long`): rättigheter, länkantal, ägare, grupp, storlek, datum, namn.
- En-post-per-rad (`-1`/`--oneline`).
- Trädvy (`-T`/`--tree`) med djupbegränsning (`-L`/`--level`).
- JSON-utdata (`-j`/`--json`) med `--indent`.
- Filter: dolda poster (`-a`/`--all`, `-A`/`--almost-all`) och katalogposter (`-d`/`--dirs`).
- Sortering (`-s`/`--sort`) på name, size, modified, type, extension eller none, med `-r`/`--reverse` och `--dirs-first`.
- Typindikatorer (`-F`/`--classify`): `/`, `@`, `*`.
- Kolumnrubrik i långt format (`-H`/`--header`).
- Storleksformat: människoläsbart (standard), råa byte (`--bytes`) och SI-enheter (`--si`).
- Färgläggning per filtyp och för rättighetsbitar, storlek, ägare och datum, med `--color {auto,always,never}`.
- `ls`-liknande argumenthantering: filer samlas i en listning, kataloger listas var för sig med rubrik.
- Säker hantering av symlänkar, inklusive trasiga länkar och visning av länkmål.
- Sanering av kontrolltecken i filnamn för att förhindra terminal-escape-injektion.
- Säker degradering till `?`/`N/A` när metadata inte går att läsa.
- Tyst hantering av `BrokenPipeError` (t.ex. `exa | head`) och Ctrl-C.
- Flaggan `-V`/`--version`.
- `README.md` med installations- och användningsexempel samt denna `CHANGELOG.md`.

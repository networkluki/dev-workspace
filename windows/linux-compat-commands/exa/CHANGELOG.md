# Ändringslogg

## Versionsregler

Formatet är `STOR.MEDEL.LITEN`. I exemplet `1.2.3` betyder positionerna:

- `1`: stora ändringar. Höj första talet och nollställ resten: `1.2.3` → `2.0.0`.
- `2`: medelstora ändringar. Höj andra talet och nollställ tredje: `1.2.3` → `1.3.0`.
- `3`: små ändringar. Höj tredje talet: `1.2.3` → `1.2.4`.

Höj versionen en gång per sammanhängande färdig ändring, även för dokumentation.
Vid flera ändringar samtidigt styr den största ändringens nivå.
Lägg till version, datum och beskrivning här, senast först.
Visa aktuell version med `exa -v` eller `exa --version`.

## 1.3.2 — 2026-09-08

- Dokumenterade Windows-installation och användning utan WSL.
- Förberedde exa för `windows/linux-compat-commands/exa/` i `dev-workspace`.
- Förtydligade att verktyget är en egen Linux-inspirerad Python-implementation för Windows.

## 1.3.1 — 2026-09-08

- Lade till `exa -v` som alias för `exa --version`. Båda visar `exa-python 1.3.1`.
- Lade till denna ändringslogg och dokumenterade versionsreglerna.
- Lade till tester för båda versionsflaggorna, även med felaktig konfiguration.

Ändringsloggen börjar här. Föregående version i koden var `1.3.0`.

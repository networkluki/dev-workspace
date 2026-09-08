# Changelog

Alla noterbara ändringar i `systeminfo` dokumenteras i denna fil.

Formatet följer [Keep a Changelog](https://keepachangelog.com/sv/1.1.0/)
och projektet använder [Semantisk versionshantering](https://semver.org/lang/sv/).

## [1.1.0] - 2026-09-02

### Tillagt

- `README.md` med installations- och användningsexempel.
- Denna `CHANGELOG.md`.

## [1.0.0] - 2026-09-02

### Tillagt

- Grundläggande `systeminfo`-kommando i Python (endast standardbibliotek).
- Insamling av OS, kärna och plattform från `/etc/os-release` och `platform`.
- CPU-information: modell, arkitektur, logiska kärnor och load average.
- Minnesinformation inklusive swap från `/proc/meminfo`.
- Diskanvändning för `/` via `shutil.disk_usage`.
- Nätverk: värdnamn och primär utgående IP (UDP-`connect` utan att skicka trafik).
- Upptid, användare och Python-version.
- Temperaturavläsning från `/sys/class/thermal/*` och `/sys/class/hwmon/*`.
- Nätverksinterface-lista med state, MAC, MTU, IPv4/IPv6 och RX/TX-byte.
- Flaggan `-j`/`--json` för maskinläsbar utdata, med `--indent`.
- Flaggan `--iface` för att filtrera på ett eller flera interface.
- Flaggan `--temp-unit {c,f}` för Celsius eller Fahrenheit.
- Flaggan `-V`/`--version` för att visa versionsnummer.
- Säker degradering till `N/A` när en datakälla saknas eller är åtkomstnekad.

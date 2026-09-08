# systeminfo

Ett kommando i Python som samlar in och visar information om OS, hårdvara och nätverk. Använder **endast Pythons standardbibliotek** — inga externa beroenden.

## Krav

- Python 3.9 eller senare (testat på 3.13)
- Linux (läser från `/proc` och `/sys`). Fungerar även i Termux/Android, men vissa källor kan vara åtkomstnekade och visas då som `N/A`.

## Installation

Skriptet är körbart och kan symlänkas till en katalog i din `PATH`:

```bash
chmod +x systeminfo
ln -sf "$PWD/systeminfo" "$PREFIX/bin/systeminfo"   # Termux
# eller på vanlig Linux:
# sudo ln -sf "$PWD/systeminfo" /usr/local/bin/systeminfo
```

Därefter kan du köra `systeminfo` var som helst.

## Användning

```
systeminfo [-h] [-V] [-j] [--iface NAMN] [--temp-unit {c,f}] [--indent INDENT]
```

### Flaggor

| Flagga | Beskrivning |
| --- | --- |
| `-h`, `--help` | Visa hjälp och avsluta. |
| `-V`, `--version` | Visa versionsnummer och avsluta. |
| `-j`, `--json` | Skriv ut som JSON istället för text. |
| `--iface NAMN` | Visa endast angivet interface. Kan upprepas. |
| `--temp-unit {c,f}` | Temperaturenhet: `c`=Celsius (standard), `f`=Fahrenheit. |
| `--indent INDENT` | JSON-indentering (endast med `--json`). Standard: `2`. |

## Exempel

Visa all systeminformation som text:

```bash
systeminfo
```

Skriv ut som JSON (maskinläsbart):

```bash
systeminfo --json
```

Temperaturer i Fahrenheit:

```bash
systeminfo --temp-unit f
```

Visa endast ett specifikt interface:

```bash
systeminfo --iface eth0
```

Flera interfaces samtidigt:

```bash
systeminfo --iface eth0 --iface wlan0
```

Kombinera flaggor — JSON, Fahrenheit och ett interface:

```bash
systeminfo --json --temp-unit f --iface eth0
```

Kompakt JSON (ingen indentering) och vidare till `jq`:

```bash
systeminfo --json --indent 0 | jq '.memory.used_bytes'
```

## Exempelutdata (text)

```
===== SYSTEMINFO =====
Tid          : 2026-09-02 12:15:56 CEST

[ OS ]
  Namn       : Debian GNU/Linux 12 (bookworm)
  Version    : 12
  Kärna      : 6.1.0-18-amd64
  Plattform  : Linux-6.1.0-18-amd64-x86_64-with-glibc2.36

[ CPU ]
  Modell     : Intel(R) Xeon(R) CPU
  Arkitektur : x86_64
  Kärnor     : 4
  Load avg   : 0.15 / 0.10 / 0.05

[ MINNE ]
  Totalt     : 7.8 GiB
  Använt     : 2.1 GiB (27%)
  Tillgängl. : 5.7 GiB
  Swap       : 2.0 GiB fritt / 2.0 GiB

[ DISK / ]
  Totalt     : 40.0 GiB
  Använt     : 12.3 GiB (31%)
  Fritt      : 27.7 GiB

[ NÄTVERK ]
  Värdnamn   : srv01
  Primär IP  : 10.0.0.5

[ TEMPERATUR ]
  cpu-thermal       : 45.0 °C
  battery           : 30.5 °C

[ INTERFACES ]
  eth0       up     MTU=1500 RX=4.8 MiB TX=1.9 MiB
             MAC=aa:bb:cc:dd:ee:ff  addr=10.0.0.5
  lo         unknown MTU=65536 RX=1.0 KiB TX=1.0 KiB
             MAC=00:00:00:00:00:00  addr=127.0.0.1, ::1

[ SYSTEM ]
  Upptid     : 3d 4h 12m
  Användare  : root (uid=0)
  Python     : 3.13.13 (CPython)
======================
```

## Insamlade fält

- **OS**: namn, version, kärna, plattform (från `/etc/os-release` och `platform`)
- **CPU**: modell, arkitektur, logiska kärnor, load average
- **Minne**: totalt, använt, tillgängligt, swap (från `/proc/meminfo`)
- **Disk**: total/använd/fri storlek för `/` (från `shutil.disk_usage`)
- **Nätverk**: värdnamn, primär utgående IP
- **Temperatur**: från `/sys/class/thermal/*` och `/sys/class/hwmon/*`
- **Interfaces**: state, MAC, MTU, IPv4/IPv6, RX/TX-byte (från `/proc/net/*` och `/sys/class/net/*`)
- **System**: upptid, användare, Python-version

## Datakällor och säkerhet

- Samtliga källor läses via en skyddad wrapper — om en källa saknas eller är åtkomstnekad degraderar utdata till `N/A` istället för att krascha.
- Primär IP bestäms via en UDP-`connect` som endast binder socketen; **ingen trafik skickas** och ingen DNS-uppslagning görs.
- Inga externa kommandon anropas, vilket eliminerar risk för command injection.

## Exit-koder

| Kod | Betydelse |
| --- | --- |
| `0` | OK. |
| `1` | Oväntat fel under insamling. |
| `2` | Ogiltigt argument, eller okänt interface angivet med `--iface`. |

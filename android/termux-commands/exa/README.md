# exa

En modern ersättare för `ls` skriven i Python. Listar filer och kataloger med färg, långt format, rutnät och trädvy. Använder **endast Pythons standardbibliotek** — inga externa beroenden.

## Krav

- Python 3.9 eller senare (testat på 3.13)
- Linux/Unix. Fungerar även i Termux/Android, men vissa metadata kan sakna namnuppslag (uid/gid) och visas då som siffror.

## Installation

Skriptet är körbart och kan symlänkas till en katalog i din `PATH`:

```bash
chmod +x exa
ln -sf "$PWD/exa" "$PREFIX/bin/exa"   # Termux
# eller på vanlig Linux:
# sudo ln -sf "$PWD/exa" /usr/local/bin/exa
```

Därefter kan du köra `exa` var som helst.

> Obs: om det riktiga `exa`/`eza` (Rust) redan finns i din `PATH` kan namnkonflikt uppstå. Välj annat namn vid behov, t.ex. `ln -sf "$PWD/exa" "$PREFIX/bin/pexa"`.

## Användning

```
exa [SÖKVÄG ...] [flaggor]
```

Utan argument listas aktuell katalog i rutnät.

### Flaggor

| Flagga | Beskrivning |
| --- | --- |
| `-h`, `--help` | Visa hjälp och avsluta. |
| `-V`, `--version` | Visa versionsnummer och avsluta. |
| `-l`, `--long` | Långt format: rättigheter, länkar, ägare, grupp, storlek, datum, namn. |
| `-1`, `--oneline` | En post per rad. |
| `-T`, `--tree` | Visa som ett träd. |
| `-L`, `--level DJUP` | Maximalt rekursionsdjup för trädvy (`-T`). |
| `-j`, `--json` | Skriv ut som JSON istället för text. |
| `-a`, `--all` | Visa även dolda poster (som börjar med punkt). |
| `-A`, `--almost-all` | Som `--all` men utan `.` och `..`. |
| `-d`, `--dirs` | Lista kataloger själva, inte deras innehåll. |
| `-s`, `--sort NYCKEL` | Sortera: `name`, `size`, `modified`, `type`, `extension`, `none`. Standard: `name`. |
| `-r`, `--reverse` | Omvänd sorteringsordning. |
| `--dirs-first` | Visa kataloger före filer. |
| `-F`, `--classify` | Lägg till typindikator (`/`, `@`, `*`) efter namn. |
| `-H`, `--header` | Visa kolumnrubrik i långt format (`-l`). |
| `--bytes` | Visa storlek i råa byte istället för människoläsbart. |
| `--si` | Använd SI-enheter (1000) istället för binära (1024). |
| `--color {auto,always,never}` | När färg ska användas. Standard: `auto` (endast i terminal). |
| `--indent INDENT` | JSON-indentering (endast med `--json`). Standard: `2`. |

## Exempel

Lista aktuell katalog i rutnät:

```bash
exa
```

Långt format med rubrik och typindikatorer:

```bash
exa -lHF
```

Visa alla poster (inkl. dolda), sorterade på storlek, största först:

```bash
exa -la -s size -r
```

Trädvy två nivåer djupt:

```bash
exa -T -L 2
```

Kataloger före filer, långt format:

```bash
exa -l --dirs-first
```

Maskinläsbar JSON vidare till `jq`:

```bash
exa -j /etc | jq '.[] | select(.is_dir) | .name'
```

Endast katalogerna själva (som `ls -d`):

```bash
exa -d */
```

## Exempelutdata (långt format)

```
Permissions Links User    Group    Size Modified     Name
drwxr-xr-x  2 alice   alice   4.0Ki 02 Sep 12:18 __pycache__/
-rw-r--r--  1 alice   alice   1.3Ki 02 Sep 12:22 CHANGELOG.md
-rw-r--r--  1 alice   alice   4.0Ki 02 Sep 12:21 README.md
-rwxr-xr-x  1 alice   alice  16.5Ki 02 Sep 12:21 systeminfo
```

## Färgläggning

| Typ | Färg |
| --- | --- |
| Katalog | Fet blå |
| Symlänk | Fet cyan |
| Trasig symlänk | Fet röd |
| Körbar fil | Fet grön |
| Setuid/setgid | Vit på röd |
| Socket | Fet magenta |
| Named pipe (FIFO) | Gul |
| Block-/teckenenhet | Fet gul |

I långt format färgläggs även rättighetsbitar (`r` gul, `w` röd, `x` grön), storlek (grön), ägare (gul) och datum (blå). Färg används endast när utdata går till en terminal, om inte `--color=always` anges.

## Argumenthantering (som `ls`)

- Flera **filargument** samlas i en gemensam listning.
- Flera **katalogargument** listas var för sig med en rubrik (`sökväg:`).
- Blandas filer och kataloger visas filerna först, därefter varje katalog med rubrik.

## Säkerhet

- **Filnamn behandlas som otillförlitlig indata.** Kontrolltecken (C0/C1 samt DEL), inklusive ANSI-escapesekvenser, ersätts med `?` innan de skrivs ut. Detta förhindrar terminal-escape-injektion via manipulerade filnamn.
- **Inga externa kommandon anropas** — ingen risk för command injection.
- Metadata läses via en skyddad wrapper; om `lstat`/`stat` misslyckas degraderar utdata till `?`/`N/A` istället för att krascha.
- `BrokenPipeError` (t.ex. `exa | head`) hanteras tyst med exit-kod `0`.

## Exit-koder

| Kod | Betydelse |
| --- | --- |
| `0` | OK. |
| `2` | Minst en sökväg kunde inte läsas (saknas eller åtkomst nekad). Övriga listas ändå. |
| `130` | Avbruten med Ctrl-C. |

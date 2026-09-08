# exa för Windows

Ett Linux-inspirerat kommando för Windows som listar filer med ikoner och färger.
Detta är en egen Python-implementation inspirerad av exa. Kräver Python 3.9 eller senare via
`py -3`. Git behövs bara när `--git` används. Visa aktuell version med `exa -v`
eller `exa --version`. Versionsformatet är `STOR.MEDEL.LITEN`: första talet för
stora ändringar, andra för medelstora och tredje för små.
Se [CHANGELOG.md](CHANGELOG.md) för ändringar och regler för versionshöjning.

## Installation på Windows

Installera Python 3.9 eller senare med Python-startaren `py` och kontrollera med
`py -3 --version`. Kör följande från repots rot i PowerShell:

```powershell
cd windows\linux-compat-commands\exa
.\exa.cmd --version
```

Lägg katalogen som innehåller `exa.cmd`, `exa.py` och `config.json` i din användares
`Path` via Windows miljövariabler. Öppna sedan en ny terminal för att använda
`exa` från valfri katalog i PowerShell eller Kommandotolken.
För enbart den aktuella PowerShell-sessionen kan du i exa-katalogen köra:

```powershell
$env:Path = (Get-Location).Path + ';' + $env:Path
exa --version
```

Kommandot körs direkt i Windows och kräver inte WSL.

## Exempel

```powershell
exa
exa -la
exa -T --depth 2
exa --git
exa --ext py,lua
exa --only-dirs
exa -T --ext py,lua --summary
exa -l -s size -r --summary
exa --help
```

Trädets rot har djup 0. Utan `--depth` visas hela trädet. Symboliska länkar,
junctions och andra Windows-reparse-points följs inte i trädvyn. Dolda filer
och mappar kräver `-a`, även i trädvyn. Läsfel rapporteras och övriga poster visas.

`--ext` tar filändelser utan hänsyn till stora/små bokstäver, med eller utan punkt.
Även sammansatta ändelser som `tar.gz` fungerar. I vanlig listning visas bara
matchande filer. I trädvyn behålls katalogerna som struktur, även tomma kataloger.
`--only-dirs` visar bara kataloger och har företräde framför `--ext`.

`--summary` räknar visade filer, mappar, länkar och eventuella andra posttyper.
Storleken är summan av visade vanliga filers storlek, inte upptaget diskutrymme
eller en rekursiv storlek för kollapsade mappar. Trädets rot räknas inte bland
barnen. Summeringen gäller separat för varje angiven sökväg och markeras som
ofullständig om något läsfel eller Git-fel inträffat.

## Git-status

`--git` läser status från Git-repot som innehåller den angivna sökvägen.
Varje repo läses en gång per körning, med en tidsgräns på 10 sekunder per Git-anrop.
En misslyckad Git-fråga ger ett felmeddelande, markeringen `[ER]` och exitkod 1;
själva fillistningen fortsätter. `--no-git` stänger av funktionen.

- `[--]`: ren post, utan rapporterade ändringar.
- `[ M]`: ändrad i arbetskatalogen; `[M ]`: ändringen finns i index.
- `[A ]`: tillagd i index; `[ D]` eller `[D ]`: borttagen.
- `[??]`: ny fil som inte spåras av Git.
- `[!!]`: ignorerad av Git.
- `[**]`: katalog med flera olika statusar bland sina barn.

Git använder två positioner: index respektive arbetskatalog. Övriga Git-koder,
exempelvis konfliktstatus, visas oförändrade. Kataloger summerar barnens status.
En borttagen fil finns inte i fillistningen men kan påverka katalogens status.
Namnbyten visas som borttagning och tillägg. Inbäddade repon/submoduler visas
enligt det yttre repots status; ange dem som egen sökväg för deras interna status.
Git-status kan omfatta dolda eller filtrerade barn som inte visas i listningen.

## Sparade standardinställningar

Redigera `config.json` bredvid `exa.py`. Exempel på egna standardval:

```json
{
  "icons": "always",
  "color": "auto",
  "sort": "name",
  "group_directories_first": true,
  "summary": true
}
```

Kommandoradsflaggor har företräde. Exempelvis `exa --no-summary` stänger av en
sparad summering och `exa --ext=` tar bort ett sparat filfilter.
`exa --config "C:\sökväg\egna-val.json"` läser en annan fil.
`exa --no-config` använder inbyggda standardvärden. Inställningar skrivs aldrig
om av programmet och ändringar läses in nästa gång kommandot körs.

Tillåtna booleska nycklar: `all`, `long`, `oneline`, `directory`, `reverse`,
`classify`, `group_directories_first`, `tree`, `git`, `only_dirs`, `summary`.
Varje motsvarande lång flagga kan stängas av med `--no-`, t.ex. `--no-tree`.
Övriga nycklar: `sort` (`name`, `size`, `modified`, `extension`), `icons` och
`color` (`always`, `auto`, `never`), `ext` (text), `depth` (heltal minst 0).
Utelämna `depth` för obegränsat djup. `depth` påverkar bara trädvyn.
Inställningsfilen måste vara ett JSON-objekt på högst 64 KiB. Felaktiga värden,
okända nycklar och oläsbara filer ger tydliga fel; hjälp och version fungerar ändå.

Kodfiler visas i gult, bilder/video i lila, arkiv i rött, körbara filer i grönt,
inställningsfiler i cyan och ljud i ljuslila. Kataloger är blå. Färger används
automatiskt i terminalen; `NO_COLOR` stänger av automatisk färg.
`--color=always` tvingar färg och `--color=never` stänger av den.
Ikonernas bredd och utseende beror på terminalens typsnitt.

## Kontroller

```powershell
# Kör i katalogen som innehåller exa.py.
py -3 -m ruff format --check .
py -3 -m ruff check .
py -3 -m mypy exa.py
py -3 -m unittest discover -v
exa -v
exa --version
```

Ruff och mypy är valfria utvecklingsverktyg och behövs inte för att köra exa.
För att återgå till inbyggda standardinställningar, använd `--no-config`.

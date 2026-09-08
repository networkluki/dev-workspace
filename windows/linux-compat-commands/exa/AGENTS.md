# Versionshantering för exa

- Versionsnumret finns i konstanten `VERSION` i `exa.py` och visas med `exa -v` eller `exa --version`.
- Formatet är `STOR.MEDEL.LITEN`. Utgångsversionen är `1.2.0`.
- Höj versionen vid varje färdig ändring av detta projekt, även dokumentationsändringar.
- Höj en gång per sammanhängande ändring, inte vid varje filsparning.
- Stor ändring: höj första talet och nollställ de två andra, exempelvis `1.2.0` → `2.0.0`.
- Medelstor ändring: höj andra talet och nollställ tredje, exempelvis `1.2.0` → `1.3.0`.
- Liten ändring: höj tredje talet, exempelvis `1.2.0` → `1.2.1`.
- Vid flera ändringar samtidigt styr den största ändringens nivå.
- Dokumentera varje färdig ändring i `CHANGELOG.md` med version, datum och en kort beskrivning, senast först.
- Ange den nya versionen i sammanfattningen och verifiera både `exa -v` och `exa --version`.

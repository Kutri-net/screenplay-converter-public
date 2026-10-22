# Käsikirjoitusmuunnin

*In English: [README.md](README.md)*

Muunnin siirtää käsikirjoituksen Movie Magic Screenwriterin, Fountainin, Final Draftin ja PDF:n välillä omalla koneellasi. Movie Magicia tai Final Draftia ei tarvita. Pyydät Claude Codea tai Codexia tekemään muunnoksen VS Codessa, tai ajat yhden komennon itse.

| Mistä | Mihin |
| --- | --- |
| Movie Magic `.mmsw`, `.BK`-varmuuskopiot, `.mmx` | Fountain `.fountain` |
| Final Draft `.fdx` | Final Draft `.fdx` |
| Fountain `.fountain` | PDF `.pdf` (A4 tai US Letter) |
| | Movie Magic `.mmsw` / `.mmx` (uusi, ks. alla) |

Muunnin toimii kokonaan omalla koneellasi. Käsikirjoitusta ei lähetetä minnekään.

## Mitä tarvitset

- VS Coden, jossa on Claude Code- tai Codex-laajennus.
- Pythonin, versio 3.8 tai uudempi. Tarkista VS Coden terminaalissa: `python3 --version` (Windowsissa `py -3 --version`).
  - Mac: jos Python puuttuu, aja `xcode-select --install`.
  - Windows: asenna Python osoitteesta [python.org](https://www.python.org/downloads/) ja rastita asennuksessa "Add python.exe to PATH".

Muita asennuksia ei tarvita.

## Asennus

1. Lataa koodi: valitse sivulla [github.com/Kutri-net/screenplay-converter-public](https://github.com/Kutri-net/screenplay-converter-public) **Code → Download ZIP** ja pura tiedosto. Voit myös pyytää Claude Codea tai Codexia: "Lataa https://github.com/Kutri-net/screenplay-converter-public ja asenna sieltä käsikirjoitusmuunnin."
2. Avaa purettu kansio VS Codessa tai Clauden tai ChatGPT:n työpöytäsovelluksessa.
3. Pyydä Claude Codelta tai Codexilta: "Aja tämän kansion install.py". Voit myös ajaa sen itse terminaalissa: `python3 install.py` (Windowsissa `py -3 install.py`).
4. Aloita uusi keskustelu Claude Codessa tai Codexissa.

`install.py` kopioi skillin kansioihin `~/.claude/skills/` (Claude Code) ja `~/.agents/skills/` (Codex). Lisäämällä `--claude` tai `--codex` asennat sen vain toiselle, ja `--uninstall` poistaa sen. Kun ajat skriptin uudelleen, aiempi asennus päivittyy.

Jos käytät Claude Codea komentorivillä, voit asentaa muuntimen myös pluginina: `/plugin marketplace add Kutri-net/screenplay-converter-public` ja `/plugin install screenplay-converter@kutri-screenplay`.

## Käyttö

Pyydä omin sanoin, esimerkiksi:

- "Muunna `jakso1.mmsw` Fountainiksi."
- "Tee tästä käsikirjoituksesta PDF." (A4; sano "US Letter", jos tarvitset sen)
- "Muunna kaikki tämän kansion Movie Magic -tiedostot Final Draftiksi."
- "Tee `luonnos.fountain`-tiedostosta Movie Magic -tiedosto."
- "Mitä tässä .BK-tiedostossa on?"

Muunnin ei koskaan kirjoita olemassa olevan tiedoston tai alkuperäisen tiedoston päälle.

### Komentorivillä

```
python3 scripts/convert.py jakso1.mmsw jakso1.fountain
python3 scripts/convert.py jakso1.fountain jakso1.pdf --paper letter
python3 scripts/convert.py *.mmsw --to fdx --out-dir muunnetut
python3 scripts/convert.py jakso1.BK --info
```

`scripts/convert.py` on asennetun skillin kansiossa (`~/.claude/skills/screenplay-convert/` tai `~/.agents/skills/screenplay-convert/`).

## Hyvä tietää

- **Movie Magic -tiedostojen kirjoittaminen on uutta.** Movie Magic -tiedostojen lukemista on testattu yli 1 500 oikealla tiedostolla, ja tulos vastasi Movie Magicin omia Final Draft -vientejä 99,6–100-prosenttisesti. Myös `.mmsw`-tiedoston kirjoittaminen läpäisee samat testit, mutta tiedostoa ei ole vielä avattu itse Movie Magicissa. Avaa tiedosto kerran Movie Magicissa ennen kuin luotat siihen. `.mmsw` toimii Movie Magicin Windows- ja Mac-versiossa, `.mmx` vain Mac-versiossa.
- Movie Magic lisää kohtausnumerot sekä (MORE)- ja (CONT'D)-merkinnät vasta tulostaessa, joten niitä ei ole sen tiedostoissa. PDF:ään muunnin lisää omat (MORE)- ja (CONT'D)-merkinnät.
- Fountain ei pysty esittämään kaikkea. Hahmon nimi ilman repliikkiä muuttuu toimintariviksi, ja kuva (shot) muuttuu toiminnaksi.
- Muistiinpanot säilyvät Fountainissa ja Movie Magic -tiedostoissa. PDF:stä ja Final Draftista ne jäävät pois.
- Keskitetty teksti, sivunvaihdot ja kaksoisrepliikki säilyvät Fountainissa ja Final Draftissa, mutta eivät Movie Magic -tiedostoissa.
- Vanhempia Screenwriter 4 -tiedostoja (`.scw`) muunnin ei vielä osaa lukea. Avaa ne Movie Magic 6:ssa ja tallenna `.mmsw`-muotoon, tai käytä Final Draft- tai RTF-vientiä.
- PDF käyttää Courier-perusfonttia. Se tuntee länsieurooppalaiset kirjaimet (ä, ö, å, é …), ajatusviivat ja kaarevat lainausmerkit. Muut merkit tulostuvat kysymysmerkkeinä, ja muunnin varoittaa niistä.

## Kehittäjille

- `plugin/skills/screenplay-convert/` – itse skill: `SKILL.md`, `scripts/convert.py` ja `screenplay_convert`-paketti (vain Pythonin vakiokirjasto)
- `tests/` – `python3 -m unittest discover tests`. `tests/validate_archive.py ARKISTO` tarkistaa paikallisen Movie Magic -arkiston ja tulostaa vain lukumääriä.
- `scripts/build-zip.sh` – rakentaa ladattavan zip-paketin kansioon `dist/`
- `mms-testi/` – testitiedostot ja ohje Movie Magic -tiedostojen tarkistamiseen Movie Magicissa ja Final Draftissa

Movie Magicin tiedostomuoto selvitettiin vertaamalla oikeita tiedostoja niiden FDX-, RTF- ja PDF-vienteihin. Muodon kuvaus on tiedoston `screenplay_convert/mmsw.py` alussa.

Tekijä: Katri Manninen, [kutri.net](https://kutri.net). MIT-lisenssi, katso [LICENSE](LICENSE).

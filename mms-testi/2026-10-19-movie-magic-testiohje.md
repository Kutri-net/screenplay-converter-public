# Movie Magic -testi: avautuuko muuntimen tekemä .mmsw?

Muunnin kirjoittaa Movie Magic -tiedostoja ilman Movie Magicia. Lukupuoli on testattu 1 559 oikealla tiedostolla, mutta kirjoitettua tiedostoa ei ole vielä avattu itse ohjelmassa. Tämä testi ratkaisee, voiko .mmsw-muunnokseen luottaa.

Testiaineisto on keksitty lyhyt käsikirjoitus, jossa on ääkkösiä, korostuksia ja kaikki tavalliset elementit.

## Tiedostot

- `2026-10-19-testikasikirjoitus.mmsw` – Movie Magic 6:n tavallinen tiedosto (Windows ja Mac)
- `2026-10-19-testikasikirjoitus.mmx` – Movie Magicin Mac-version XML-muoto
- `2026-10-19-testikasikirjoitus.fdx` – Final Draft
- `2026-10-19-testikasikirjoitus.pdf` – vertailukopio: tältä käsikirjoituksen pitäisi näyttää
- `2026-10-19-testikasikirjoitus.fountain` – alkuperäinen teksti

## Testi Movie Magicissa

1. Avaa `.mmsw` Movie Magicissa (File > Open).
2. Vertaa PDF:ään ja käy läpi:
   - Aukeaako tiedosto ilman virheilmoitusta?
   - Ovatko kohtausotsikot, toiminta, hahmot, repliikit, sulkurepliikit ja siirtymät oikeina elementteinä? Näet elementin nimen, kun viet kursorin kappaleeseen.
   - Näkyvätkö ä, ö ja ajatusviiva (–) oikein?
   - Näkyvätkö kursiivi (*varovasti*), lihavointi (**ÖRKKI**) ja alleviivaus (vanha valokuva)?
   - Onko nimiösivulla otsikko ja yhteystiedot? Nimiösivu löytyy Movie Magicin Title Page -näkymästä.
   - Onko muistiinpano "tarkista saunan sijainti" näkyvissä muistiinpanona?
3. Tallenna tiedosto Movie Magicissa uudella nimellä, sulje ja avaa uudelleen. Aukeaako se edelleen?
4. Jos käytössä on Mac-versio, tee sama `.mmx`-tiedostolle.

Kohtausnumerot, keskitetty "LOPPU"-teksti ja kaksoisrepliikki (BRICK ja STEEL rinnakkain) eivät siirry Movie Magic -tiedostoon. Ne puuttuvat tiedostosta tarkoituksella.

## Testi Final Draftissa

1. Avaa `.fdx` Final Draftissa.
2. Tarkista samat asiat kuin yllä. Nimiösivu löytyy Final Draftin Title Page -näkymästä.

## Palaute

Kirjoita jokaisesta kohdasta "toimii" tai mitä näit. Kuvakaappaus virheilmoituksesta tai väärästä kohdasta auttaa eniten. Kerro myös Movie Magicin versio (Help > About) ja onko käytössä Windows vai Mac.

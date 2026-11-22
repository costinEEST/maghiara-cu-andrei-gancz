# Literata în Nebuló

Fonturi copiate din `assets/fonts/literata/` al proiectului părinte, fără modificarea
fișierelor binare. Autori: TypeTogether / The Literata Project Authors.
Licență: SIL Open Font License 1.1, inclusă în `OFL.txt`.

- Normal: `literata-latin-roman.e42c54d5.woff2`, 183.064 octeți.
- Italic: `literata-latin-italic.85368b48.woff2`, 184.924 octeți.

Variantele păstrează greutățile variabile 400–700 și axa optică 7–72.
Subsetul include literele românești și maghiare, diacriticele combinante și
semnele de punctuație. Nu este un font IPA complet; rămâne fallback-ul serif.

Surse originale:
https://github.com/google/fonts/tree/main/ofl/literata
https://github.com/googlefonts/literata

`assets/site.css` declară ambele variante cu `font-display: swap`, ajustare de
x-height 0.507 și dimensionare optică automată. Nu sunt cereri la Google Fonts.
Ambele WOFF2 sunt incluse în inventarul offline și în interfața precache-uită.

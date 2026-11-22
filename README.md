# Nebuló — Maghiară, pas cu pas

Lecții de limba maghiară pentru vorbitori de română, într-o ediție de studiu adaptată
după [Nebuló.ro](https://www.nebulo.ro/). Site-ul este accesibil, adaptat telefoanelor
și poate fi instalat pentru învățare offline.

**[Deschide cursul](https://costineest.github.io/maghiara-cu-andrei-gancz/)**

## Cuprins

- [Ce găsești în curs](#ce-găsești-în-curs)
- [Cum îl folosești](#cum-îl-folosești)
- [Instalare și acces offline](#instalare-și-acces-offline)
- [Ce am schimbat](#ce-am-schimbat)
- [Autori și atribuire](#autori-și-atribuire)
- [Licențe](#licențe)
- [Contribuții și întreținere](#contribuții-și-întreținere)

## Ce găsești în curs

- **50 de lecții:** 11 introductive și 39 din „Maghiara cu András”.
- **76 de pagini de referință:** gramatică, vocabular, comunicare, alfabet și pronunție.
- **371 de exerciții și lecturi suplimentare**.
- **131 de înregistrări MP3**, ilustrații didactice și **87 de arhive suplimentare**
  disponibile local pentru descărcare.

[Pagina principală](https://costineest.github.io/maghiara-cu-andrei-gancz/) reunește
lecțiile și resursele și permite căutarea lor. Forumul și celelalte secțiuni comunitare
ale sursei nu sunt incluse.

## Cum îl folosești

Începe cu lecțiile introductive sau urmează cursul „Maghiara cu András”. Referințele și
exercițiile asociate se deschid din fiecare lecție.

Lecțiile au numere cu trei cifre în cadrul fiecărui curs (de exemplu, **Lecția 001**).
Cele 371 de activități au un index separat, **001–371**, în ordinea lecțiilor și apoi
a temelor de referință. Sub fiecare titlu apar toate lecțiile sau temele asociate.
Numărul activității este un reper în cuprins, nu numărul lecției; adresele paginilor
au fost păstrate.

Poți vedea răspunsurile fără să completezi mai întâi exercițiul. Pentru corectarea
automată, completează câmpurile și apasă **„Verifică răspunsurile”**. Accentele maghiare
contează: `o`, `ö` și `ő` sunt litere diferite.

Pentru folosire locală, din directorul proiectului:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Deschide apoi [http://127.0.0.1:8765/](http://127.0.0.1:8765/). Lectura funcționează și
prin deschiderea fișierului `index.html`; instalarea și salvarea offline necesită însă
un server local sau HTTPS.

## Instalare și acces offline

Pe pagina principală, secțiunea **„Învață și fără internet”** oferă două opțiuni:

1. **Adaugă site-ul pe ecranul principal**, dacă browserul permite acest lucru. Poți folosi și opțiunea
   de instalare sau adăugare pe ecranul principal din meniul browserului.
2. **Salvează cursul offline** și așteaptă confirmarea descărcării. Pachetul are
   aproximativ **22 MB** și include lecțiile, exercițiile, imaginile, fonturile și
   înregistrările MP3.

Instalarea și salvarea cursului sunt acțiuni separate. Poți opri și relua salvarea.
Arhivele RAR/ZIP, videoclipurile și serviciile externe nu sunt incluse în pachetul
offline. Jocurile din arhive necesită dezarhivare, iar compatibilitatea lor cu
browserele actuale poate varia. Vezi [ghidul pentru arhive](referinte/cum-deschizi-arhivele.html).

Browserul poate elimina datele salvate la curățarea stocării sau când spațiul este
insuficient. Verifică starea salvării înainte de a rămâne fără internet. Când apare
**„Actualizează site-ul”**, termină exercițiul curent înainte de actualizare și
verifică din nou salvarea offline.

## Ce am schimbat

- Am reorganizat materialele într-un site fără framework-uri, cu un cuprins, căutare și
  navigare comună între lecții.
- Am revizuit îndrumări și explicații în română, păstrând exemplele maghiare și
  atribuirea surselor.
- Am adaptat exercițiile pentru tastatură, am recuperat răspunsurile lipsă și am adăugat
  feedback de corectare.
- Am transcris capturile cu text în HTML, cu etichete de limbă pentru română și
  maghiară, și am păstrat materialele audio și vizuale utile.
- Am adăugat fontul Literata, text mai mare, o identitate vizuală cu măr SVG și afișare
  adaptată telefoanelor.
- Am adăugat instalare, acces offline și metadate pentru distribuirea paginilor.

Detalii despre proveniența materialelor:
[Despre ediție și surse](https://costineest.github.io/maghiara-cu-andrei-gancz/referinte/despre-editie.html).

## Autori și atribuire

Materialele originale sunt atribuite autorilor indicați de
[Nebuló.ro](https://www.nebulo.ro/faq.html#autori), un proiect
[Lkozma.net](https://www.lkozma.net/):

- **László Kozma:** site-ul, materialele și prima serie de lecții.
- **András (Andrei) Gancz:** cursul, vocabularul, comunicarea și corectura lecțiilor.
- **Judit Kozma (Vass):** materiale, ilustrații și înregistrări audio.
- **Ágnes Kozma:** înregistrări audio.

Cursul pentru vorbitori de română adaptează
[Le hongrois avec András](https://hongroisavecandras.blog4ever.com/).
[Prezentarea lui Andrei Gancz](https://costineest.github.io/maghiara-cu-andrei-gancz/referinte/despre-autor.html)
este păstrată în ediție.

Ediția este inițiată și întreținută de **Constantin Câmpean
([costinEEST](https://github.com/costinEEST))**, cu asistență tehnică OpenAI Codex. Este
o adaptare independentă; nu implică aprobarea autorilor originali.

## Licențe

Site-ul oficial [declară](https://www.nebulo.ro/faq.html#licenta) licența **Creative
Commons Atribuire–Distribuire în Condiții Identice 3.0 România (CC BY-SA 3.0 RO)**.
Materialele adaptate și contribuțiile de adaptare din această ediție păstrează aceeași
licență. Redistribuirea și adaptarea, inclusiv comercială, impun respectarea atribuirii
și a condițiilor licenței.

Vezi [LICENSE.txt](LICENSE.txt) și
[textul licenței](https://creativecommons.org/licenses/by-sa/3.0/ro/). Materialele
terților își păstrează propriile drepturi și condiții.

Fontul **Literata**, realizat de TypeTogether / The Literata Project Authors, este
inclus separat sub [SIL Open Font License 1.1](assets/fonts/literata/OFL.txt).

## Contribuții și întreținere

Sunt binevenite corecturile de conținut, îmbunătățirile de accesibilitate și sesizările
despre linkuri sau exerciții. Include pagina și un exemplu concret; conținutul nu a
trecut printr-o revizie lingvistică integrală.

Site-ul folosește HTML, CSS și JavaScript simplu, fără un pas de build pentru lectură.
Fișierele HTML sunt sursele întreținute. Fonturile și resursele necesare lecturii sunt
locale.

După modificări, formatează sursele și actualizează pachetul offline:

```sh
npx -y @biomejs/biome@2.6.8 format --write .
node tools/build-offline.mjs
npx -y @biomejs/biome@2.6.8 format --write offline-assets.js
node tools/build-offline.mjs --check
```

Instrucțiunile detaliate și comenzile de verificare sunt în [AGENTS.md](AGENTS.md) și în
skillurile locale:

- [Formatare cu Biome](.agents/skills/nebulo-biome-format/SKILL.md).
- [Unelte Python, audituri și teste](.agents/skills/nebulo-python-tools/SKILL.md).

Biome este folosit pentru formatare, Ruff pentru formatarea și lintingul Python, iar ty
pentru verificarea tipurilor. Uneltele, testele și rapoartele de audit nu sunt incluse
în cache-ul PWA.

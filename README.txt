NEBULÓ — CURS DE LIMBA MAGHIARĂ PENTRU VORBITORI DE ROMÂNĂ

Nebuló este o ediție de lectură și studiu realizată pornind de la materialele
educative de pe Nebuló.ro. Reunește lecțiile și resursele într-un site static,
accesibil și adaptat telefoanelor, cu instalare ca aplicație și salvare offline.

CUPRINS
  1. Ce conține proiectul
  2. Utilizare și instalare
  3. Acces offline
  4. Autorii sursei și ai ediției Nebuló
  5. Licența site-ului oficial și licența ediției
  6. Ce am schimbat față de sursă
  7. Structura proiectului
  8. Publicare și metadate SEO
     8.1. Tipografie și fonturi locale
  9. Formatare cu Biome și Ruff
 10. Verificarea implementării Python
     10.1. Răspunsuri și exerciții de completare
 11. Verificarea PWA și actualizarea pachetului offline
     11.1. Verificarea finală înainte de commit
 12. Competențe Codex și întreținere
 13. Limite și resurse externe

1. CE CONȚINE PROIECTUL

- 50 de lecții: 11 introductive și 39 din cursul „Maghiara cu András”.
- 75 de pagini de referință: gramatică, vocabular, comunicare, alfabet,
  pronunție, îndrumări, prezentarea autorului și linkuri utile.
- 371 de exerciții și lecturi suplimentare asociate materialelor păstrate.
- 498 de pagini în inventarul principal, inclusiv cuprinsul și pagina ediției.
- O pagină tehnică separată, offline.html, pentru paginile nesalvate.
- 131 de înregistrări MP3 locale și imagini didactice.
- 87 de arhive suplimentare locale verificate: 86 RAR și un ZIP, în
  assets/original/leckek/fajlok/.

Forumul, știrile, întrebările generale despre site și jocurile independente
nu fac parte din această ediție. Nu sunt necesare un cont sau un cadru de
lucru JavaScript. HTML-ul este sursa întreținută a lecțiilor.

2. UTILIZARE ȘI INSTALARE

Repository:
https://github.com/costinEEST/maghiara-cu-andrei-gancz

Adresa publică prevăzută în configurație:
https://costineest.github.io/maghiara-cu-andrei-gancz/

Poți deschide index.html direct pentru lectură locală. Instalarea și salvarea
prin service worker necesită însă HTTPS sau un server local; file:// nu este
suficient pentru aceste funcții. Pentru testare, din rădăcina proiectului:

  python3 -m http.server 8765 --bind 127.0.0.1

Apoi deschide http://127.0.0.1:8765/ în browser.

Pe pagina principală, secțiunea „Învață și fără internet” oferă instalarea
atunci când browserul permite afișarea unui buton funcțional. Instalarea
folosește confirmarea browserului; nu se face automat. Dacă butonul nu apare,
poți folosi opțiunea de instalare sau de adăugare pe ecranul principal din
meniul browserului, dacă aceasta este disponibilă. Site-ul funcționează și
ca pagină obișnuită, fără instalare.

3. ACCES OFFLINE

Pagina principală și interfața de bază sunt salvate după activarea service
workerului. Paginile și resursele locale vizitate se salvează pe parcurs.

Pentru întregul curs, apasă „Salvează cursul offline” și așteaptă confirmarea.
Pachetul include paginile, ilustrațiile și MP3-urile locale. Dimensiunea este
afișată în interfață și este de aproximativ 21 MB, în funcție de ediție.
Instalarea aplicației și salvarea întregului curs sunt acțiuni separate.

Poți opri descărcarea și o poți relua. Fișierele deja salvate rămân disponibile.
Dacă un fișier nu se poate salva, aplicația nu anunță în mod fals finalizarea.
Pentru o pagină nesalvată, afișează explicația offline și un link la cuprins.
Înregistrările salvate permit redare și navigare în timp fără internet.

Arhivele RAR/ZIP, videoclipurile și serviciile externe nu intră în pachet.
Spațiul de stocare este administrat de browser: datele pot fi eliminate la
curățarea istoricului sau când dispozitivul rămâne fără spațiu. Verifică starea
salvării înainte să te bazezi pe accesul offline.

O versiune nouă se activează la închiderea paginilor vechi sau prin butonul
„Actualizează aplicația”. Actualizarea explicită reîncarcă pagina; termină
exercițiul curent înainte să o alegi. După actualizare, verifică din nou salvarea
cursului. Cache-urile sunt separate după calea proiectului, inclusiv pe GitHub
Pages; aplicația nu șterge cache-urile altor proiecte de pe același domeniu.

4. AUTORII SURSEI ȘI AI EDIȚIEI NEBULÓ

Autorii materialelor originale, conform paginii oficiale de atribuire:
https://www.nebulo.ro/faq.html#autori

- László Kozma: dezvoltarea site-ului Nebuló.ro, materiale și prima serie de lecții.
- András (Andrei) Gancz: cursul „Maghiara cu András”, vocabular, comunicare
  și corectura lecțiilor. Cursul pentru vorbitori de română adaptează
  „Le hongrois avec András”, destinat inițial francofonilor.
- Judit Kozma (Vass): materiale, ilustrații și înregistrări audio.
- Ágnes Kozma: înregistrări audio.

Prezentarea lui Andrei Gancz se păstrează în referinte/despre-autor.html.
Nebuló.ro este un proiect Lkozma.net: https://www.lkozma.net/

Ediția Nebuló este inițiată și întreținută de Constantin Câmpean (costinEEST):
selectarea și reunirea materialelor, coordonarea adaptării și întreținerea
proiectului. Implementarea și verificările tehnice au fost asistate de
OpenAI Codex. Materialele educative rămân atribuite autorilor originali;
asistența AI nu reprezintă autoratul cursului sau o validare lingvistică integrală.

5. LICENȚA SITE-ULUI OFICIAL ȘI LICENȚA EDIȚIEI

Site-ul oficial Nebuló.ro declară pentru conținutul său licența Creative
Commons Atribuire–Distribuire în Condiții Identice 3.0 România,
abreviată CC BY-SA 3.0 RO. Declarația și legătura la licență sunt publicate aici:
https://www.nebulo.ro/faq.html#licenta

Licența și textul său juridic:
https://creativecommons.org/licenses/by-sa/3.0/ro/
https://creativecommons.org/licenses/by-sa/3.0/ro/legalcode

Este o licență de conținut deschis care permite distribuirea și adaptarea,
inclusiv în scop comercial, cu respectarea atribuirii, indicarea modificărilor
și distribuirea adaptărilor în aceleași condiții. Nu este o licență de tip
„doar pentru uz personal” și nu este o licență non-comercială.

Ediția Nebuló păstrează CC BY-SA 3.0 RO pentru materialele adaptate și
contribuțiile de adaptare, conform LICENSE.txt. Fiecare pagină educativă include
un link la sursa originală. Autorii Nebuló.ro nu sunt prezentați ca susținători
sau aprobatori ai acestei ediții. Operele, mărcile și materialele terților își
păstrează drepturile și condițiile proprii; o legătură externă nu le relicențiază.

Fonturile Literata sunt distribuite separat sub SIL Open Font License 1.1,
cu atribuirea The Literata Project Authors / TypeTogether. Licența completă
se află în assets/fonts/literata/OFL.txt; nu sunt relicențiate sub CC BY-SA.

6. CE AM SCHIMBAT FAȚĂ DE SURSĂ

- Am reunit lecțiile, resursele, exercițiile și lecturile suplimentare
  într-o ediție de studiu cu navigare și prezentare comune.
- Am creat o interfață comună în HTML, CSS și JavaScript simplu, cu un index,
  căutare, nume descriptive de fișiere și navigare între lecții.
- Am reorganizat titlurile, formulările de îndrumare și unele explicații în
  română. Exemplele maghiare și traducerile provin din materialele originale.
- Am înlocuit mecanismele vechi de exerciții: asocierea folosește liste de
  selectare, iar rebusurile au și o prezentare accesibilă prin răspuns scris.
- Am adăugat controale audio native, etichete pentru câmpuri, feedback accesibil,
  focus vizibil, link de salt la conținut și tabele derulabile de la tastatură.
- Am păstrat româna ca limbă a documentului și am etichetat pasaje identificabile
  în maghiară cu lang="hu". Formele o, ö și ő rămân distincte la verificare.
- Am salvat local înregistrările MP3 și am recuperat imagini didactice lipsă.
  Am eliminat elemente decorative și mecanismele vechi de comentarii.
- Am reparat două legături malformate și 15 trimiteri externe confirmate ca
  indisponibile: nouă au fost înlocuite cu pagini de bibliotecă verificate,
  iar șase resurse vechi au devenit texte marcate ca indisponibile.
- Am adăugat metadate SEO, date structurate, sitemap și imagine pentru distribuire.
- Am redesenat mărul roșu în SVG pentru identitatea ediției Nebuló, inspirat
  de simbolul Nebuló.ro. Este folosit în antet, favicon, pictogramele aplicației
  și imaginea de distribuire; nu este o reproducere a siglei oficiale.
- Am adăugat manifest PWA, pictograme, instalare, salvare offline, progres,
  întreruperea descărcării și gestionarea actualizărilor.
- Am introdus unelte locale pentru linkuri, metadate, limbă, formatare,
  verificare de tipuri și teste de regresie.

Arhivele inițiale și generatorul dependent de ele au fost eliminate la cererea
proprietarului. assets/inventory.json păstrează inventarul și URL-urile sursă.

7. STRUCTURA PROIECTULUI

  index.html                 Cuprinsul și comenzile PWA/offline
  lectii/, andras/            Cele două parcursuri de lecții
  gramatica/, vocabular/      Referințe gramaticale și tematice
  comunicare/, referinte/     Expresii, pronunție, surse și atribuire
  exercitii/                 Exerciții și lecturi suplimentare
  assets/                    Stiluri, scripturi, înregistrări și imagini
  manifest.webmanifest       Identitatea și aspectul aplicației instalate
  sw.js                      Salvare offline și actualizări
  offline-assets.js           Lista generată și versiunea pachetului offline
  offline.html               Pagina de rezervă pentru resurse nesalvate
  tools/                     Unelte de întreținere și teste
  .agents/skills/             Competențe Codex locale
  LICENSE.txt                Licență și atribuire

8. PUBLICARE ȘI METADATE SEO

Acest director este rădăcina unui repository Git local independent. Comenzile
Git și uneltele de întreținere se rulează de aici. Repository-ul local nu
activează publicarea; pentru GitHub Pages publică acest conținut ca site static.
Fișierele text sunt versionate cu finaluri de linie LF, iar .gitattributes
protejează fișierele binare de conversii. Astfel se păstrează arhivele intacte
și amprentele folosite la verificarea inventarului offline între platforme.
.nojekyll permite servirea fișierelor statice pe GitHub Pages. Pentru PWA,
publică prin HTTPS și păstrează manifestul, sw.js și offline-assets.js la
rădăcina proiectului. Configurarea adresei nu activează singură publicarea.

site-config.json conține URL-ul public, numele ediției și imaginea de distribuire.
Metadatele includ titluri și descrieri distincte, canonical, Open Graph,
Twitter și JSON-LD. sitemap.xml acoperă paginile din inventarul principal;
offline.html este o pagină tehnică noindex.

Dacă schimbi domeniul sau numele repository-ului, actualizează site-config.json
și rulează tools/prepare_seo.py. Manifestul și service workerul folosesc căi
relative și se adaptează căii proiectului. După modificări, refă pachetul offline.
Nu inventăm o pagină alternativă în maghiară pentru hreflang. Un robots.txt
într-o subcale GitHub Pages nu stabilește regulile întregului domeniu github.io.

8.1. TIPOGRAFIE ȘI FONTURI LOCALE

Literata normal și italic sunt copiate fără modificări din proiectul părinte,
în assets/fonts/literata/. Variantele variabile includ greutăți 400–700,
dimensionare optică 7–72 și diacriticele românești și maghiare. Site-ul nu
încarcă fonturi de la terți; cele două fișiere WOFF2 sunt incluse în interfața
salvată de service worker, iar licența este inclusă și în pachetul offline.

assets/site.css folosește range mapping cu progress(), după articolul:
https://blog.master.dev/fluid-typography-with-progress/

Dimensiunile cresc între 400 și 1200 px lățime, cu ieșiri în rem: textul de bază
este 1.125–1.25rem (18–20 px la setarea implicită de 16 px). Dimensiunea rădăcinii
nu este fixată; preferința utilizatorului pentru font mai mare se păstrează.
@supports activează progress() numai când expresia este acceptată. Restul
browserelor folosesc dimensiuni rem lizibile. Titlurile folosesc aceeași scară,
paragrafele de lecție sunt limitate la 70ch și spațierea liniilor rămâne relativă.

Verifică paginile la 320/390 px, desktop și cu text mărit la 200%. După schimbări,
regenerează inventarul offline. Detalii despre fonturi: assets/fonts/literata/README.md.

9. FORMATARE CU BIOME ȘI RUFF

Toate comenzile se execută din rădăcina acestui proiect, unde se află index.html.
Pentru fișierele web, cu Node.js și npx:

  npx -y @biomejs/biome@2.6.8 format --write .
  npx -y @biomejs/biome@2.6.8 format .

biome.json folosește două spații, lățime de 100 de coloane și tratare CSS a
spațiilor HTML. Regiunile de dialog afectate de o instabilitate Biome au
comentarii de păstrare a formatării. Nu elimina aceste protecții fără o verificare.

Pentru Python, cu uv și Ruff:

  uv tool run --from ruff==0.14.4 ruff format --no-cache tools
  uv tool run --from ruff==0.14.4 ruff format --no-cache --check tools
  uv tool run --from ruff==0.14.4 ruff check --no-cache tools

Biome este configurat numai pentru formatare: linterul și assist sunt
dezactivate. Comanda biome format nu reprezintă linting JavaScript/CSS.
Ruff verifică stilul și implementarea Python, iar ty verifică tipurile.
Formatarea nu înlocuiește lintingul, verificarea de tipuri sau testele.

10. VERIFICAREA IMPLEMENTĂRII PYTHON

  uv tool run --from ty==0.0.107 --with-requirements tools/requirements.txt ty check tools --error-on-warning
  uv run --no-project --with-requirements tools/requirements.txt python -B -W error -m unittest discover -s tools -p 'test_*.py'
  uv run --no-project --with-requirements tools/requirements.txt python -B tools/validate.py
  python3 tools/check_links.py

Testele sunt offline și folosesc site-uri temporare. Importul modulelor nu
citește sau rescrie lecțiile. Generatoarele acceptă --root pentru o copie de test.

Pentru verificarea opțională a resurselor externe:

  python3 tools/check_links.py --external --json link-report.json

Checkerul raportează separat răspunsurile 404/410 și solicitările blocate sau
expirate. Coduri de ieșire: 0 fără erori confirmate, 1 linkuri defecte, 2 verificări
externe neconcludente. O verificare locală nu dovedește disponibilitatea surselor.

Fără uv, se poate folosi un mediu virtual:

  python3 -m venv .venv
  .venv/bin/python -m pip install -r tools/requirements.txt ruff==0.14.4 ty==0.0.107

Pe Windows, executabilul echivalent este .venv\Scripts\python.exe.
ruff.toml și ty.toml vizează Python 3.10+. Citește și scrie textele explicit UTF-8.

10.1. RĂSPUNSURI ȘI EXERCIȚII DE COMPLETARE

Răspunsurile sunt incluse în HTML, în details.solutions, și pot fi consultate
imediat, fără completarea câmpurilor și fără JavaScript. Verificarea automată
folosește data-answers și controalele comune din assets/site.js. Validatorul
respinge secțiunile goale și câmpurile Gap fără chei de corectare.

63 de exerciții aveau liste goale și 707 câmpuri fără chei. Cheile au fost
recuperate din sursele originale, fără executarea JavaScriptului acestora.
Escape-urile Unicode defecte au fost reconciliate cu opțiunile existente;
răspunsul „kellemes”, confirmat în sursă, a fost adăugat meniului unde lipsea.

Pentru recuperarea viitoare din copii HTML originale, păstrate în afara site-ului
și denumite la fel ca paginile locale afectate:

  uv run --no-project --with-requirements tools/requirements.txt python -B tools/repair_answers.py --sources /cale/catre/surse

Adaugă --write doar pentru aplicare. Scriptul verifică toate paginile înainte de
a modifica vreuna și păstrează HTML-ul în afara controalelor reparate. Citește
codificarea declarată de sursă, inclusiv ISO-8859-1. După aplicare, rulează
validatorul și Biome, apoi regenerează pachetul offline.

11. VERIFICAREA PWA ȘI ACTUALIZAREA PACHETULUI OFFLINE

Inventarul include paginile educative, interfața, fonturile, imaginile, MP3-urile,
manifestul, pagina de rezervă, README-ul și licențele. assets/site.js și
assets/pwa.js sunt necesare funcționării site-ului și intră în cache.
tools/, .agents/, scripturile Python, testele, configurațiile uneltelor și
rapoartele de audit nu sunt incluse. Nici arhivele RAR/ZIP sau resursele externe
nu sunt preîncărcate. sw.js și offline-assets.js sunt scripturi ale service
workerului, administrate de browser, nu intrări obișnuite din inventar.

După modificarea paginilor, stilurilor, scripturilor, imaginilor sau README-ului,
formatează mai întâi fișierele și regenerează lista de fișiere/versionarea:

  node tools/build-offline.mjs
  npx -y @biomejs/biome@2.6.8 format --write offline-assets.js
  node tools/build-offline.mjs --check
  node --test tools/test_pwa.mjs

Builderul calculează versiunea din conținutul fișierelor, nu din data curentă.
Nu edita manual offline-assets.js. Păstrează și sursa SVG a pictogramelor.
Dacă un fișier declarat lipsește, verificarea trebuie să eșueze, nu să producă
un pachet incomplet anunțat ca fiind disponibil offline.

În browser, testează cu un server local: înregistrarea workerului, descărcarea
integrală, o lecție nevizitată înainte, imaginile și audio după deconectare,
pagina de rezervă și apariția opțiunii de actualizare după o versiune nouă.
Instalarea efectivă se confirmă în interfața sistemului/browserului.

11.1. VERIFICAREA FINALĂ ÎNAINTE DE COMMIT

Rulează verificările pe starea finală a fișierelor. Orice editare ulterioară,
inclusiv salvarea din editor cu un alt formatter, poate invalida rezultatul.
Ordinea de mai jos formatează sursele înainte de calcularea versiunii offline:

  npx -y @biomejs/biome@2.6.8 format --write .
  uv tool run --from ruff==0.14.4 ruff format --no-cache tools
  uv tool run --from ruff==0.14.4 ruff check --no-cache tools
  uv tool run --from ruff==0.14.4 ruff format --no-cache --check tools
  uv tool run --from ty==0.0.107 --with-requirements tools/requirements.txt ty check tools --error-on-warning
  uv run --no-project --with-requirements tools/requirements.txt python -B -W error -m unittest discover -s tools -p 'test_*.py'
  uv run --no-project --with-requirements tools/requirements.txt python -B tools/validate.py
  python3 -B tools/check_links.py
  python3 -B tools/audit_archives.py
  node tools/build-offline.mjs
  npx -y @biomejs/biome@2.6.8 format --write offline-assets.js
  npx -y @biomejs/biome@2.6.8 format .
  node tools/build-offline.mjs --check
  node --test tools/test_pwa.mjs

Oprește-te la orice eroare și corectează cauza înainte de commit. Nu rula
prepare_seo.py sau label_languages.py doar pentru formatare: rescriu conținut.
Dacă verifici numai documentație, nu sunt necesare teste noi; o modificare în
README.txt necesită însă regenerarea și verificarea inventarului offline.
Înainte de commit inspectează git diff --cached, iar după commit verifică
git status --short. Un commit local nu publică site-ul și nu face push.

12. COMPETENȚE CODEX ȘI ÎNTREȚINERE

AGENTS.md introduce competențele locale:
  .agents/skills/nebulo-biome-format/SKILL.md
  .agents/skills/nebulo-python-tools/SKILL.md

Pot fi invocate ca $nebulo-biome-format și $nebulo-python-tools când sunt
descoperite de Codex. Uneori este necesară o sesiune nouă; fișierele pot fi
citite și direct. Rulează generatoarele de metadate și limbă doar pentru o
modificare intenționată, apoi reformatează și revalidează rezultatul.

13. LIMITE ȘI RESURSE EXTERNE

Arhive suplimentare

Cele 87 de arhive sunt păstrate local în assets/original/leckek/fajlok/:
86 RAR și un ZIP. Au fost descărcate din nou ca date binare și au trecut toate
verificarea integrității; cele 90 de trimiteri folosesc acum fișierele locale.
ZIP-ul a fost mutat din assets/external/ pentru a evita o copie duplicată.
Arhivele se pot descărca din site, dar nu sunt preîncărcate de service worker.

Sursele se reconstruiesc din căile originale și din maparea explicită a ZIP-ului
în tools/audit_archives.py. Rapoartele JSON cu verificări și SHA-256 sunt rezultate
regenerabile, nu fișiere de configurare și nu sunt necesare site-ului. Rapoartele
generate la rădăcină sunt ignorate de Git și pot fi șterse după verificare.

Pentru redescărcarea și verificarea tuturor arhivelor, cu actualizarea linkurilor:

  python3 -B tools/restore_archives.py --report archive-restoration-latest.json

Scriptul descarcă întâi într-un director temporar. Publică fișierele doar după
ce toate descărcările trec verificarea, le copiază binar cu verificare SHA-256
și actualizează apoi linkurile. Nu folosi read_text/write_text pentru arhive.
Nu extrage automat jocurile vechi în site-ul publicat.

Pentru auditul local, fără modificări și fără rețea:

  python3 -B tools/audit_archives.py

Pentru reverificarea inclusiv a arhivelor externe, fără păstrarea descărcărilor:

  python3 -B tools/audit_archives.py --check-remote --report archive-audit-latest.json

Alternativ, dacă alegi explicit să renunți la copiile locale deteriorate
și să revii la linkuri externe verificate:

  python3 -B tools/audit_archives.py --check-remote --replace-broken --report archive-audit-latest.json

Scriptul folosește zipfile din Python pentru CRC-ul fișierelor ZIP și bsdtar
(libarchive, disponibil pe macOS) pentru decomprimarea RAR. Nu extrage fișierele
în site; descărcările de audit sunt în directoare temporare șterse automat. Dacă bsdtar
lipsește, formatul nu este suportat sau sursa nu poate fi verificată, raportează
„unverified” și nu șterge copia locală. Coduri de ieșire: 0 fără probleme
constatate, 1 arhivă deteriorată, 2 verificare neconcludentă. Un audit fără
--check-remote nu dovedește disponibilitatea descărcărilor externe.

Pe termen lung, activitățile utile din aceste arhive pot fi refăcute ca pagini
HTML accesibile, după revizuirea conținutului și a licențelor. Integritatea arhivelor
nu garantează că jocurile vechi sunt compatibile cu browserele actuale.
Arhivele nu fac parte din pachetul offline.

Imaginile din același director

Directorul păstrează 22 de imagini: 20 de fotografii/ilustrații și două diagrame.
Cele opt capturi cu text au fost transcrise direct în lecțiile 9, 18, 20 și 35:
formularele festivalului și rezervării de avion, specificațiile mașinii de spălat,
traducerea anunțului imobiliar și lectura despre Lacul Roșu. Originalele maghiare
au lang="hu", iar traducerile și îndrumările românești au lang="ro". Tabelele au
antete și titluri, iar formularele sunt exemple de lectură, fără colectare de date.
Capturile au fost șterse după înlocuire. Datele istorice și diferențele între
versiunile sursă au fost păstrate și explicate în lecții.

Etichetarea lingvistică este conservatoare și nu reprezintă o revizie integrală
făcută de un lingvist. Modificările de explicații nu garantează că fiecare regulă
sau răspuns original este fără greșeală. Auditul din tools/language-audit.json
ajută la revizuirea pasajelor mixte.

Auditul extern inițial a lăsat 26 de URL-uri neverificate din cauza blocării,
limitării cererilor sau expirării. Lista se află în tools/external-link-audit.json
și trebuie reverificată la nevoie. Unele înregistrări Wikimedia, videoclipuri,
Google Translate și alte servicii externe necesită internet și depind de terți.

Surse pentru instalare și funcționare offline:
https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable
https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation

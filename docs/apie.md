#### Kaip veikia tikrintuvas

1. **Pavadinimų atpažinimas.** Įvestas tekstas išvalomas (dozės, vaisto formos), tada ieškoma
   tikslaus atitikmens tarp angliškų (INN), lietuviškų, prekinių ir buitinių pavadinimų
   („žuvų taukai“, „magnis“). Jei tikslaus atitikmens nėra, lietuviška galūnė nuimama
   (*varfarinas → warfarin*), o galiausiai taikomas neraiškusis palyginimas su rašybos klaidomis.
   Apytiksliai atpažinti įrašai pažymimi 🟡, neaiškūs – ❓ su pasiūlymais.
2. **Sąveikų paieška.** Kiekviena medžiagų pora tikrinama kuruotoje **DDInter** duomenų bazėje
   (~235 tūkst. porų, 1 971 medžiaga, įskaitant vitaminus, mineralus ir augalinius preparatus).
3. **Taisyklės.** Farmakologinės rizikos klasės (antikoaguliantai, NVNU, serotoninerginiai,
   QT ilginantys, CNS slopinantys, kalį didinantys, CYP3A4 inhibitoriai/induktoriai, mineralai)
   paaiškina **galimą šalutinį poveikį ir mechanizmą**, o kai DDInter poros neturi – sugeneruoja
   atsargumo įspėjimą. Tikrinami ir sąrašo lygmens pavojai: ta pati veiklioji medžiaga keliuose
   preparatuose bei „trigubas smūgis“ inkstams (NVNU + AKFI/sartanas + diuretikas).
4. **AI modelis.** ~42 tūkst. DDInter porų sunkumas nenurodytas – jį prognozuoja LightGBM
   modelis, o SHAP reikšmės parodo, kodėl.

#### Kada rodomas įspėjimas „naudoti atsargiai“

| Situacija | Ką rodo programėlė |
|---|---|
| Pavadinimas neatpažintas arba medžiagos DDInter nėra | ❌ / ⛔ ir pranešimas, kad sąveikos netikrintos |
| Pavadinimas atpažintas apytiksliai | 🟡 ir prašymas patikrinti |
| Sunkumas prognozuotas AI modelio | ⚠️ „PROGNOZUOTA – naudokite atsargiai“, tikimybės, SHAP |
| AI modelis nėra tikras (< 60 %) | ⚠️ papildomas įspėjimas |
| Sąveika nustatyta tik taisyklėmis | ⚠️ „GALIMA, o ne patvirtinta sąveika“ |
| Taisyklės ir DDInter vertina skirtingai | ⚠️ nurodomas griežtesnis vertinimas |
| Nėra mechanizmo aprašymo | ⚠️ siūloma pasitikslinti pakuotės lapelyje ar pas vaistininką |
| Dalyvauja papildas | ⚠️ įrodymai dažnai riboti, sudėtis skiriasi |
| Poros duomenų nėra | ⚪ „tai NEREIŠKIA, kad derinys saugus“ |

#### Duomenų šaltiniai

- **DDInter** – Xiong G. ir kt. *DDInter: an online drug–drug interaction database towards improving
  clinical decision-making and patient safety.* Nucleic Acids Research, 2022, 50(D1):D1200–D1207.
  Duomenys atsisiųsti iš viešos kopijos (Hugging Face `amulyakh/drug-interactions-data`, failai
  `ddinter/ddinter_<ATC>.csv`), kurios formatas atitinka DDInter v1 atsisiuntimus.
- **Greipfrutų sultys** – Bailey D.G. ir kt. *Grapefruit–medication interactions: forbidden fruit or
  avoidable consequences?* CMAJ, 2013, 185(4):309–316; FDA vartotojų informacija.
- **Kofermentas Q10** – NCCIH informacinis lapas.
- Rizikos klasės sudarytos remiantis bendrosiomis farmakologijos žiniomis, CredibleMeds (QT),
  FDA CYP3A4 inhibitorių/induktorių lentelėmis ir Phansalkar S. ir kt. (JAMIA, 2012) didelės
  svarbos sąveikų sąrašu.

#### Ribotumai

- DDInter v1 rinkinyje **nėra mechanizmų aprašymų ir rekomendacijų tekstų** – juos iš dalies
  pakeičia taisyklės.
- Neįtraukta: dozės, vartojimo trukmė, amžius, inkstų ir kepenų funkcija, nėštumas, alergijos.
- Kai kurių Lietuvoje populiarių medžiagų DDInter neturi (metamizolas, nimesulidas, drotaverinas,
  gliklazidas, dabigatranas ir kt.) – jos pažymimos ⛔.
- Prekinių pavadinimų sąrašas – pavyzdinis ir nepilnas.
- AI modelis prastai veikia su vaistais, kurių nematė mokymo metu (macro F1 ≈ 0,58).
- Atskirų vaistų šalutiniai poveikiai (pvz., SIDER) neįtraukti – rodomi tik **derinių** galimi
  šalutiniai poveikiai.

#### Etika ir privatumas

Programėlė **nerenka ir nesaugo** jokių asmens duomenų: įvestas sąrašas apdorojamas tik
naršyklės sesijoje. Naudojami tik vieši, anonimiški duomenų rinkiniai. Sprendimo kritiškumas –
**informacinis**: programėlė tik informuoja ir pataria kreiptis į specialistą, bet nepriima
sprendimų už vartotoją.

"""Rankiniu būdu sudaryta žinių bazė.

Turinys:
  * RISK_CLASSES  – farmakologinės rizikos klasės (kraujavimas, serotoninas, QT ...)
  * RULES         – taisyklės „klasė + klasė -> galimas šalutinis poveikis“
  * LT_NAMES      – DDInter (angliškas) pavadinimas -> lietuviškas pavadinimas
  * BRANDS        – Lietuvoje paplitę prekiniai pavadinimai -> veikliosios medžiagos
  * GENERIC_ALIASES – buitiniai pavadinimai („žuvų taukai“, „magnis“, „kava“ ...)
  * NOT_IN_DB     – populiarios LT medžiagos, kurių DDInter neturi
  * CURATED_PAIRS – papildomi literatūros įrašai (greipfrutų sultys, kofermentas Q10)

Visi vaistų pavadinimai rašomi TIKSLIAI taip, kaip DDInter (patikrinama testais).
Taisyklės yra supaprastintos ir skirtos PAAIŠKINTI galimą mechanizmą – jos
nepakeičia klinikinės duomenų bazės ir specialisto vertinimo.
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# 1. Rizikos klasės
# --------------------------------------------------------------------------
_CALCIUM = ["Calcium acetate", "Calcium carbonate", "Calcium citrate", "Calcium gluconate",
            "Calcium lactate", "Calcium Phosphate", "Calcium glubionate anhydrous",
            "Calcium glucoheptonate", "Calcium glycerophosphate"]
_MAGNESIUM = ["Magnesium carbonate", "Magnesium chloride", "Magnesium citrate",
              "Magnesium gluconate", "Magnesium glycinate", "Magnesium hydroxide",
              "Magnesium oxide", "Magaldrate"]
_IRON = ["Iron", "Ferrous sulfate anhydrous", "Ferrous fumarate", "Ferrous gluconate",
         "Iron protein succinylate", "Tetraferric tricitrate decahydrate"]
_ZINC = ["Zinc acetate", "Zinc gluconate", "Zinc sulfate", "Zinc chloride"]

RISK_CLASSES: dict[str, dict] = {
    "anticoagulant": {
        "lt": "antikoaguliantai",
        "members": ["Warfarin", "Acenocoumarol", "Dicoumarol", "Anisindione", "Apixaban",
                    "Rivaroxaban", "Edoxaban", "Betrixaban", "Heparin", "Enoxaparin",
                    "Dalteparin", "Tinzaparin", "Fondaparinux", "Argatroban", "Bivalirudin",
                    "Desirudin", "Lepirudin", "Danaparoid", "Ardeparin"],
    },
    "antiplatelet": {
        "lt": "antiagregantai",
        "members": ["Acetylsalicylic acid", "Clopidogrel", "Prasugrel", "Ticagrelor",
                    "Ticlopidine", "Cilostazol", "Dipyridamole", "Vorapaxar", "Cangrelor",
                    "Eptifibatide", "Tirofiban", "Abciximab"],
    },
    "nsaid": {
        "lt": "NVNU (nesteroidiniai vaistai nuo uždegimo)",
        "members": ["Ibuprofen", "Naproxen", "Diclofenac", "Ketoprofen", "Ketorolac",
                    "Indomethacin", "Meloxicam", "Piroxicam", "Celecoxib", "Etodolac",
                    "Nabumetone", "Flurbiprofen", "Fenoprofen", "Mefenamic acid",
                    "Meclofenamic acid", "Sulindac", "Tolmetin", "Oxaprozin", "Diflunisal",
                    "Salsalate", "Rofecoxib", "Valdecoxib", "Phenylbutazone"],
    },
    "bleeding_supplement": {
        "lt": "papildai, galintys didinti kraujavimą",
        "members": ["Ginkgo biloba", "Garlic", "Omega-3 fatty acids", "Icosapent",
                    "Vitamin E", "Turmeric", "Ginger"],
    },
    "ssri_snri": {
        "lt": "SSRI/SNRI antidepresantai",
        "members": ["Citalopram", "Escitalopram", "Fluoxetine", "Fluvoxamine", "Paroxetine",
                    "Sertraline", "Venlafaxine", "Desvenlafaxine", "Duloxetine",
                    "Milnacipran", "Levomilnacipran", "Vilazodone", "Vortioxetine"],
    },
    "maoi": {
        "lt": "MAO inhibitoriai",
        "members": ["Phenelzine", "Tranylcypromine", "Isocarboxazid", "Selegiline",
                    "Rasagiline", "Linezolid", "Methylene blue", "Safinamide"],
    },
    "serotonergic": {
        "lt": "serotoninerginiai vaistai",
        "members": ["Citalopram", "Escitalopram", "Fluoxetine", "Fluvoxamine", "Paroxetine",
                    "Sertraline", "Venlafaxine", "Desvenlafaxine", "Duloxetine",
                    "Milnacipran", "Levomilnacipran", "Vilazodone", "Vortioxetine",
                    "Clomipramine", "Imipramine", "Amitriptyline", "Phenelzine",
                    "Tranylcypromine", "Isocarboxazid", "Selegiline", "Rasagiline",
                    "Linezolid", "Methylene blue", "Tramadol", "Tapentadol", "Meperidine",
                    "Methadone", "Fentanyl", "Dextromethorphan", "Sumatriptan", "Rizatriptan",
                    "Zolmitriptan", "Naratriptan", "Almotriptan", "Eletriptan", "Frovatriptan",
                    "Lasmiditan", "Lithium carbonate", "Buspirone", "Trazodone", "Nefazodone",
                    "Mirtazapine", "St. John's Wort", "Tryptophan", "Oxitriptan"],
    },
    "qt": {
        "lt": "QT intervalą ilginantys vaistai",
        "members": ["Amiodarone", "Dronedarone", "Sotalol", "Dofetilide", "Ibutilide",
                    "Quinidine", "Procainamide", "Disopyramide", "Haloperidol", "Droperidol",
                    "Thioridazine", "Pimozide", "Chlorpromazine", "Ziprasidone", "Citalopram",
                    "Escitalopram", "Methadone", "Clarithromycin", "Erythromycin",
                    "Azithromycin", "Levofloxacin", "Moxifloxacin", "Ciprofloxacin",
                    "Ondansetron", "Hydroxychloroquine", "Chloroquine", "Quinine",
                    "Halofantrine", "Arsenic trioxide", "Vandetanib", "Cisapride",
                    "Astemizole", "Terfenadine", "Bedaquiline", "Fluconazole", "Pentamidine"],
    },
    "opioid": {
        "lt": "opioidai",
        "members": ["Morphine", "Oxycodone", "Hydrocodone", "Hydromorphone", "Codeine",
                    "Fentanyl", "Tramadol", "Tapentadol", "Methadone", "Buprenorphine",
                    "Oxymorphone", "Meperidine", "Dihydrocodeine", "Diamorphine", "Sufentanil",
                    "Remifentanil", "Alfentanil", "Levorphanol", "Pentazocine", "Butorphanol",
                    "Nalbuphine", "Opium"],
    },
    "benzodiazepine": {
        "lt": "benzodiazepinai ir Z-vaistai",
        "members": ["Alprazolam", "Diazepam", "Lorazepam", "Clonazepam", "Midazolam",
                    "Triazolam", "Temazepam", "Oxazepam", "Chlordiazepoxide", "Clorazepic acid",
                    "Estazolam", "Flurazepam", "Nitrazepam", "Quazepam", "Halazepam",
                    "Clobazam", "Zolpidem", "Zopiclone", "Eszopiclone", "Zaleplon"],
    },
    "cns_depressant": {
        "lt": "CNS slopinančios medžiagos",
        "members": ["Phenobarbital", "Pentobarbital", "Secobarbital", "Butalbital",
                    "Amobarbital", "Butabarbital", "Gabapentin", "Pregabalin",
                    "Diphenhydramine", "Doxylamine", "Hydroxyzine", "Promethazine",
                    "Clemastine", "Baclofen", "Tizanidine", "Carisoprodol", "Cyclobenzaprine",
                    "Methocarbamol", "Ethanol", "Sodium oxybate", "Chloral hydrate",
                    "Meprobamate", "Quetiapine", "Olanzapine", "Mirtazapine", "Trazodone",
                    "Valerian", "Kava", "Dexmedetomidine", "Propofol"],
    },
    "hyperkalemia": {
        "lt": "kalio kiekį kraujyje didinančios medžiagos",
        "members": ["Captopril", "Enalapril", "Lisinopril", "Ramipril", "Perindopril",
                    "Quinapril", "Benazepril", "Fosinopril", "Moexipril", "Trandolapril",
                    "Losartan", "Valsartan", "Irbesartan", "Olmesartan", "Telmisartan",
                    "Eprosartan", "Azilsartan medoxomil", "Aliskiren", "Spironolactone",
                    "Eplerenone", "Amiloride", "Triamterene", "Potassium chloride",
                    "Potassium citrate", "Potassium bicarbonate", "Potassium gluconate",
                    "Potassium acetate", "Trimethoprim", "Cyclosporine", "Tacrolimus"],
    },
    "acei_arb": {
        "lt": "AKF inhibitoriai / sartanai",
        "members": ["Captopril", "Enalapril", "Lisinopril", "Ramipril", "Perindopril",
                    "Quinapril", "Benazepril", "Fosinopril", "Moexipril", "Trandolapril",
                    "Losartan", "Valsartan", "Irbesartan", "Olmesartan", "Telmisartan",
                    "Eprosartan", "Azilsartan medoxomil", "Aliskiren"],
    },
    "diuretic": {
        "lt": "diuretikai",
        "members": ["Furosemide", "Torasemide", "Bumetanide", "Etacrynic acid",
                    "Hydrochlorothiazide", "Chlorthalidone", "Indapamide", "Metolazone",
                    "Chlorothiazide", "Bendroflumethiazide", "Spironolactone", "Eplerenone",
                    "Amiloride", "Triamterene"],
    },
    "cyp3a4_inhibitor": {
        "lt": "CYP3A4 fermento inhibitoriai",
        "members": ["Clarithromycin", "Telithromycin", "Erythromycin", "Ketoconazole",
                    "Itraconazole", "Posaconazole", "Voriconazole", "Fluconazole",
                    "Ritonavir", "Cobicistat", "Indinavir", "Nelfinavir", "Saquinavir",
                    "Boceprevir", "Telaprevir", "Nefazodone", "Conivaptan", "Troleandomycin",
                    "Idelalisib", "Diltiazem", "Verapamil", "Grapefruit juice"],
    },
    "cyp3a4_inducer": {
        "lt": "CYP3A4 fermento induktoriai",
        "members": ["Rifampicin", "Rifabutin", "Rifapentine", "Carbamazepine", "Phenytoin",
                    "Fosphenytoin", "Phenobarbital", "Primidone", "St. John's Wort",
                    "Enzalutamide", "Apalutamide", "Mitotane", "Efavirenz", "Bosentan"],
    },
    "cyp3a4_substrate": {
        "lt": "per CYP3A4 metabolizuojami jautrūs vaistai",
        "members": ["Simvastatin", "Lovastatin", "Atorvastatin", "Midazolam", "Triazolam",
                    "Alprazolam", "Cyclosporine", "Tacrolimus", "Sirolimus", "Everolimus",
                    "Quetiapine", "Colchicine", "Ivabradine", "Ticagrelor", "Apixaban",
                    "Rivaroxaban", "Fentanyl", "Oxycodone", "Felodipine", "Nifedipine",
                    "Amlodipine", "Sildenafil", "Tadalafil", "Ibrutinib", "Lurasidone",
                    "Pimozide", "Ergotamine", "Dihydroergotamine", "Buspirone", "Eplerenone"],
    },
    "hormonal_contraceptive": {
        "lt": "hormoniniai kontraceptikai",
        "members": ["Ethinylestradiol", "Levonorgestrel", "Norethisterone", "Desogestrel",
                    "Drospirenone", "Etonogestrel", "Norgestimate", "Dienogest",
                    "Norelgestromin", "Norgestrel"],
    },
    "chelation_target": {
        "lt": "vaistai, kurių įsisavinimą mažina mineralai",
        "members": ["Levothyroxine", "Ciprofloxacin", "Levofloxacin", "Moxifloxacin",
                    "Ofloxacin", "Norfloxacin", "Gemifloxacin", "Delafloxacin", "Tetracycline",
                    "Doxycycline", "Minocycline", "Demeclocycline", "Omadacycline",
                    "Sarecycline", "Alendronic acid", "Risedronic acid", "Ibandronate",
                    "Etidronic acid", "Dolutegravir", "Bictegravir", "Raltegravir",
                    "Elvitegravir", "Penicillamine", "Eltrombopag", "Levodopa"],
    },
    "polyvalent_cation": {
        "lt": "kalcio, magnio, geležies, cinko, aliuminio preparatai",
        "members": _CALCIUM + _MAGNESIUM + _IRON + _ZINC + [
            "Aluminum hydroxide", "Sucralfate", "Lanthanum carbonate", "Sevelamer",
            "Bismuth subsalicylate"],
    },
    "pde5": {
        "lt": "PDE5 inhibitoriai",
        "members": ["Sildenafil", "Tadalafil", "Vardenafil", "Avanafil"],
    },
    "nitrate": {
        "lt": "nitratai",
        "members": ["Nitroglycerin", "Isosorbide mononitrate", "Isosorbide dinitrate",
                    "Isosorbide", "Amyl Nitrite", "Nitroprusside"],
    },
}

# --------------------------------------------------------------------------
# 2. Taisyklės (porinės). level – numatytas sunkumas, jei DDInter įrašo nėra.
# --------------------------------------------------------------------------
RULES: list[dict] = [
    {"id": "bleeding_major", "a": ["anticoagulant"],
     "b": ["anticoagulant", "antiplatelet", "nsaid"], "level": "Major",
     "effect": "Padidėjusi kraujavimo rizika (įskaitant virškinamojo trakto ir vidinį kraujavimą).",
     "mechanism": "Abi medžiagos veikia kraujo krešėjimą skirtingais keliais – poveikis sumuojasi.",
     "advice": "Venkite derinio be gydytojo nurodymo; stebėkite kraujavimo požymius (mėlynės, juodos išmatos)."},
    {"id": "bleeding_moderate", "a": ["antiplatelet", "nsaid"], "b": ["antiplatelet", "nsaid"],
     "level": "Moderate",
     "effect": "Didesnė kraujavimo ir skrandžio gleivinės pažeidimo rizika.",
     "mechanism": "Trombocitų funkcijos slopinimas ir skrandžio gleivinės pažeidimas sumuojasi.",
     "advice": "Nevartokite dviejų NVNU kartu; jei skirta, aptarkite skrandžio apsaugą su gydytoju."},
    {"id": "bleeding_supp", "a": ["anticoagulant", "antiplatelet", "nsaid"],
     "b": ["bleeding_supplement", "ssri_snri"], "level": "Moderate",
     "effect": "Galimai padidėjusi kraujavimo rizika.",
     "mechanism": "Medžiaga gali silpninti trombocitų funkciją (papildams įrodymai riboti).",
     "advice": "Pasakykite gydytojui apie vartojamus papildus, ypač prieš operacijas."},
    {"id": "serotonin_major", "a": ["maoi"], "b": ["serotonergic"], "level": "Major",
     "effect": "Serotonino sindromas: sujaudinimas, karščiavimas, raumenų trūkčiojimas, tachikardija.",
     "mechanism": "MAO inhibitorius slopina serotonino skaidymą, kita medžiaga didina jo kiekį.",
     "advice": "Paprastai derinys draudžiamas – būtina gydytojo konsultacija."},
    {"id": "serotonin", "a": ["serotonergic"], "b": ["serotonergic"], "level": "Moderate",
     "effect": "Serotonino sindromo rizika (prakaitavimas, drebulys, sumišimas, karščiavimas).",
     "mechanism": "Abi medžiagos didina serotonino aktyvumą centrinėje nervų sistemoje.",
     "advice": "Pajutę minėtus simptomus, nedelsdami kreipkitės į gydytoją."},
    {"id": "qt", "a": ["qt"], "b": ["qt"], "level": "Moderate",
     "effect": "QT intervalo pailgėjimas, pavojingų širdies ritmo sutrikimų (torsades de pointes) rizika.",
     "mechanism": "Abi medžiagos lėtina širdies repoliarizaciją – poveikis sumuojasi.",
     "advice": "Gali reikėti EKG stebėsenos; ypač atsargiai esant mažam kalio ar magnio kiekiui."},
    {"id": "opioid_benzo", "a": ["opioid"], "b": ["benzodiazepine"], "level": "Major",
     "effect": "Stiprus mieguistumas, kvėpavimo slopinimas, koma, mirties rizika.",
     "mechanism": "Abi grupės slopina centrinę nervų sistemą ir kvėpavimo centrą.",
     "advice": "Derinti tik griežtai prižiūrint gydytojui; nevartoti alkoholio."},
    {"id": "cns", "a": ["opioid", "benzodiazepine", "cns_depressant"],
     "b": ["opioid", "benzodiazepine", "cns_depressant"], "level": "Moderate",
     "effect": "Padidėjęs mieguistumas, galvos svaigimas, sutrikusi koordinacija, griuvimų rizika.",
     "mechanism": "Centrinės nervų sistemos slopinimas sumuojasi.",
     "advice": "Nevairuokite, kol nežinote, kaip derinys veikia; venkite alkoholio."},
    {"id": "hyperkalemia", "a": ["hyperkalemia"], "b": ["hyperkalemia"], "level": "Moderate",
     "effect": "Hiperkalemija (per didelis kalio kiekis) – raumenų silpnumas, širdies ritmo sutrikimai.",
     "mechanism": "Abi medžiagos mažina kalio išsiskyrimą arba jį papildo.",
     "advice": "Reguliariai tikrinkite kalio kiekį kraujyje; nevartokite kalio papildų savavališkai."},
    {"id": "cyp_inhib", "a": ["cyp3a4_inhibitor"], "b": ["cyp3a4_substrate"], "level": "Moderate",
     "effect": "Padidėjusi vaisto koncentracija ir šalutinis poveikis (pvz., statinams – raumenų pažeidimas).",
     "mechanism": "CYP3A4 inhibitorius lėtina kito vaisto metabolizmą kepenyse.",
     "advice": "Gali reikėti keisti dozę ar vaistą – pasitarkite su gydytoju."},
    {"id": "cyp_induc", "a": ["cyp3a4_inducer"], "b": ["cyp3a4_substrate", "hormonal_contraceptive"],
     "level": "Moderate",
     "effect": "Sumažėjęs vaisto veiksmingumas (pvz., kontracepcijos nesėkmė, atmetimo reakcija).",
     "mechanism": "CYP3A4 induktorius pagreitina kito vaisto skaidymą.",
     "advice": "Gali reikėti papildomos kontracepcijos ar dozės keitimo – pasitarkite su gydytoju."},
    {"id": "chelation", "a": ["polyvalent_cation"], "b": ["chelation_target"], "level": "Moderate",
     "effect": "Sumažėjęs vaisto įsisavinimas ir poveikis.",
     "mechanism": "Mineralai virškinamajame trakte suriša vaistą į sunkiai įsisavinamus junginius.",
     "advice": "Vartokite atskirai – dažniausiai su 2–4 val. pertrauka (tiksliai – pakuotės lapelyje)."},
    {"id": "pde5_nitrate", "a": ["pde5"], "b": ["nitrate"], "level": "Major",
     "effect": "Staigus ir pavojingas kraujospūdžio kritimas, alpimas.",
     "mechanism": "Abi grupės plečia kraujagysles per cGMP kelią – poveikis stipriai sustiprėja.",
     "advice": "Derinys draudžiamas."},
]

# Daugiavaistė taisyklė: „trigubas smūgis“ inkstams.
TRIPLE_WHAMMY = {
    "id": "triple_whammy", "classes": ["nsaid", "acei_arb", "diuretic"], "level": "Major",
    "effect": "Ūminio inkstų pažeidimo rizika („trigubas smūgis“).",
    "mechanism": "NVNU, AKF inhibitorius/sartanas ir diuretikas kartu sumažina inkstų kraujotaką.",
    "advice": "Venkite NVNU vartojant šiuos vaistus; jei būtina – stebėkite inkstų funkciją.",
}

# --------------------------------------------------------------------------
# 3. Papildomi literatūros įrašai (medžiagos, kurių DDInter v1 neturi)
# --------------------------------------------------------------------------
EXTRA_SUBSTANCES = {
    "Grapefruit juice": {"lt": "Greipfrutų sultys", "kind": "maistas"},
    "Coenzyme Q10": {"lt": "Kofermentas Q10", "kind": "papildas"},
}
CURATED_SOURCE_GRAPEFRUIT = ("Bailey DG ir kt. Grapefruit–medication interactions. CMAJ 2013;185(4):309–316; "
                             "FDA: Grapefruit Juice and Some Drugs Don't Mix")
CURATED_PAIRS: list[dict] = [
    *[{"a": "Grapefruit juice", "b": d, "level": lvl, "source": CURATED_SOURCE_GRAPEFRUIT,
       "effect": "Padidėjusi vaisto koncentracija kraujyje ir šalutinis poveikis.",
       "mechanism": "Greipfrutų furanokumarinai slopina žarnyno CYP3A4."}
      for d, lvl in [("Simvastatin", "Major"), ("Lovastatin", "Major"), ("Atorvastatin", "Moderate"),
                     ("Felodipine", "Moderate"), ("Nifedipine", "Moderate"), ("Cyclosporine", "Moderate"),
                     ("Tacrolimus", "Moderate"), ("Amiodarone", "Moderate"), ("Midazolam", "Moderate"),
                     ("Triazolam", "Moderate"), ("Buspirone", "Moderate")]],
    {"a": "Coenzyme Q10", "b": "Warfarin", "level": "Moderate",
     "source": "NCCIH: Coenzyme Q10 (informacinis lapas)",
     "effect": "Galimai susilpnėjęs antikoaguliacinis poveikis (INR pokyčiai).",
     "mechanism": "Struktūriškai panašus į vitaminą K; tikslus mechanizmas neaiškus."},
]

# --------------------------------------------------------------------------
# 4. Lietuviški pavadinimai (DDInter pavadinimas -> LT)
# --------------------------------------------------------------------------
LT_NAMES: dict[str, str] = {
    # Skausmas, uždegimas
    "Acetaminophen": "Paracetamolis", "Acetylsalicylic acid": "Acetilsalicilo rūgštis",
    "Ibuprofen": "Ibuprofenas", "Naproxen": "Naproksenas", "Diclofenac": "Diklofenakas",
    "Ketoprofen": "Ketoprofenas", "Meloxicam": "Meloksikamas", "Celecoxib": "Celekoksibas",
    "Indomethacin": "Indometacinas", "Ketorolac": "Ketorolakas",
    "Tramadol": "Tramadolis", "Morphine": "Morfinas", "Oxycodone": "Oksikodonas",
    "Codeine": "Kodeinas", "Fentanyl": "Fentanilis", "Methadone": "Metadonas",
    "Buprenorphine": "Buprenorfinas", "Tapentadol": "Tapentadolis", "Naloxone": "Naloksonas",
    # Kraujo krešėjimas
    "Warfarin": "Varfarinas", "Acenocoumarol": "Acenokumarolis", "Apixaban": "Apiksabanas",
    "Rivaroxaban": "Rivaroksabanas", "Edoxaban": "Edoksabanas", "Heparin": "Heparinas",
    "Enoxaparin": "Enoksaparinas", "Clopidogrel": "Klopidogrelis", "Ticagrelor": "Tikagreloras",
    "Prasugrel": "Prasugrelis",
    # Širdis, kraujagyslės
    "Amlodipine": "Amlodipinas", "Nifedipine": "Nifedipinas", "Felodipine": "Felodipinas",
    "Diltiazem": "Diltiazemas", "Verapamil": "Verapamilis", "Metoprolol": "Metoprololis",
    "Bisoprolol": "Bisoprololis", "Nebivolol": "Nebivololis", "Carvedilol": "Karvedilolis",
    "Atenolol": "Atenololis", "Propranolol": "Propranololis", "Enalapril": "Enalaprilis",
    "Lisinopril": "Lizinoprilis", "Ramipril": "Ramiprilis", "Perindopril": "Perindoprilis",
    "Captopril": "Kaptoprilis", "Quinapril": "Kvinaprilis", "Losartan": "Losartanas",
    "Valsartan": "Valsartanas", "Telmisartan": "Telmisartanas", "Irbesartan": "Irbesartanas",
    "Olmesartan": "Olmesartanas", "Hydrochlorothiazide": "Hidrochlorotiazidas",
    "Indapamide": "Indapamidas", "Furosemide": "Furozemidas", "Torasemide": "Torasemidas",
    "Spironolactone": "Spironolaktonas", "Eplerenone": "Eplerenonas", "Digoxin": "Digoksinas",
    "Amiodarone": "Amiodaronas", "Sotalol": "Sotalolis", "Nitroglycerin": "Nitroglicerinas",
    "Isosorbide mononitrate": "Izosorbido mononitratas", "Ivabradine": "Ivabradinas",
    "Atorvastatin": "Atorvastatinas", "Rosuvastatin": "Rosuvastatinas",
    "Simvastatin": "Simvastatinas", "Pravastatin": "Pravastatinas", "Lovastatin": "Lovastatinas",
    "Fenofibrate": "Fenofibratas", "Gemfibrozil": "Gemfibrozilis", "Ezetimibe": "Ezetimibas",
    # Diabetas, hormonai
    "Metformin": "Metforminas", "Glimepiride": "Glimepiridas", "Sitagliptin": "Sitagliptinas",
    "Empagliflozin": "Empagliflozinas", "Dapagliflozin": "Dapagliflozinas",
    "Semaglutide": "Semaglutidas", "Insulin glargine": "Insulinas glarginas",
    "Levothyroxine": "Levotiroksinas", "Methimazole": "Tiamazolas",
    "Prednisolone": "Prednizolonas", "Prednisone": "Prednizonas",
    "Methylprednisolone": "Metilprednizolonas", "Dexamethasone": "Deksametazonas",
    "Hydrocortisone": "Hidrokortizonas", "Ethinylestradiol": "Etinilestradiolis",
    "Levonorgestrel": "Levonorgestrelis", "Estradiol": "Estradiolis",
    "Drospirenone": "Drospirenonas", "Desogestrel": "Dezogestrelis",
    # Virškinimas
    "Omeprazole": "Omeprazolas", "Pantoprazole": "Pantoprazolas", "Esomeprazole": "Esomeprazolas",
    "Lansoprazole": "Lansoprazolas", "Rabeprazole": "Rabeprazolas", "Famotidine": "Famotidinas",
    "Metoclopramide": "Metoklopramidas", "Loperamide": "Loperamidas", "Ondansetron": "Ondansetronas",
    "Lactulose": "Laktuliozė", "Bisacodyl": "Bisakodilis", "Simethicone": "Simetikonas",
    "Activated charcoal": "Aktyvuota anglis",
    # Infekcijos
    "Amoxicillin": "Amoksicilinas", "Clavulanic acid": "Klavulano rūgštis",
    "Azithromycin": "Azitromicinas", "Clarithromycin": "Klaritromicinas",
    "Erythromycin": "Eritromicinas", "Ciprofloxacin": "Ciprofloksacinas",
    "Levofloxacin": "Levofloksacinas", "Moxifloxacin": "Moksifloksacinas",
    "Doxycycline": "Doksiciklinas", "Tetracycline": "Tetraciklinas", "Metronidazole": "Metronidazolas",
    "Sulfamethoxazole": "Sulfametoksazolas", "Trimethoprim": "Trimetoprimas",
    "Nitrofurantoin": "Nitrofurantoinas", "Cefuroxime": "Cefuroksimas", "Cephalexin": "Cefaleksinas",
    "Clindamycin": "Klindamicinas", "Fluconazole": "Flukonazolas", "Ketoconazole": "Ketokonazolas",
    "Itraconazole": "Itrakonazolas", "Terbinafine": "Terbinafinas", "Acyclovir": "Acikloviras",
    "Valaciclovir": "Valacikloviras", "Rifampicin": "Rifampicinas", "Linezolid": "Linezolidas",
    # Psichika, nervų sistema
    "Sertraline": "Sertralinas", "Citalopram": "Citalopramas", "Escitalopram": "Escitalopramas",
    "Fluoxetine": "Fluoksetinas", "Paroxetine": "Paroksetinas", "Fluvoxamine": "Fluvoksaminas",
    "Venlafaxine": "Venlafaksinas", "Duloxetine": "Duloksetinas", "Mirtazapine": "Mirtazapinas",
    "Trazodone": "Trazodonas", "Amitriptyline": "Amitriptilinas", "Bupropion": "Bupropionas",
    "Vortioxetine": "Vortioksetinas", "Lithium carbonate": "Ličio karbonatas",
    "Quetiapine": "Kvetiapinas", "Olanzapine": "Olanzapinas", "Risperidone": "Risperidonas",
    "Aripiprazole": "Aripiprazolas", "Haloperidol": "Haloperidolis", "Clozapine": "Klozapinas",
    "Chlorpromazine": "Chlorpromazinas", "Alprazolam": "Alprazolamas", "Diazepam": "Diazepamas",
    "Lorazepam": "Lorazepamas", "Clonazepam": "Klonazepamas", "Midazolam": "Midazolamas",
    "Oxazepam": "Oksazepamas", "Zolpidem": "Zolpidemas", "Zopiclone": "Zopiklonas",
    "Hydroxyzine": "Hidroksizinas", "Gabapentin": "Gabapentinas", "Pregabalin": "Pregabalinas",
    "Carbamazepine": "Karbamazepinas", "Oxcarbazepine": "Okskarbazepinas",
    "Valproic acid": "Valproinė rūgštis", "Lamotrigine": "Lamotriginas",
    "Levetiracetam": "Levetiracetamas", "Phenytoin": "Fenitoinas", "Phenobarbital": "Fenobarbitalis",
    "Topiramate": "Topiramatas", "Sumatriptan": "Sumatriptanas", "Donepezil": "Donepezilis",
    "Memantine": "Memantinas", "Levodopa": "Levodopa",
    # Kiti
    "Allopurinol": "Alopurinolis", "Febuxostat": "Febuksostatas", "Colchicine": "Kolchicinas",
    "Methotrexate": "Metotreksatas", "Sildenafil": "Sildenafilis", "Tadalafil": "Tadalafilis",
    "Tamsulosin": "Tamsulozinas", "Finasteride": "Finasteridas", "Cetirizine": "Cetirizinas",
    "Levocetirizine": "Levocetirizinas", "Loratadine": "Loratadinas",
    "Desloratadine": "Desloratadinas", "Fexofenadine": "Feksofenadinas",
    "Montelukast": "Montelukastas", "Salbutamol": "Salbutamolis",
    "Diphenhydramine": "Difenhidraminas", "Cyclosporine": "Ciklosporinas",
    "Tacrolimus": "Takrolimuzas", "Pseudoephedrine": "Pseudoefedrinas",
    "Phenylephrine": "Fenilefrinas", "Xylometazoline (nasal)": "Ksilometazolinas (nosies)",
    "Dextromethorphan": "Dekstrometorfanas", "Acetylcysteine": "Acetilcisteinas",
    "Pentoxifylline": "Pentoksifilinas", "Nicotine": "Nikotinas",
    # Papildai, vitaminai, mineralai, maistas
    "St. John's Wort": "Jonažolė", "Ginkgo biloba": "Ginkmedis (Ginkgo biloba)",
    "Garlic": "Česnakas", "Ginseng": "Ženšenis",
    "Omega-3 fatty acids": "Omega-3 riebalų rūgštys (žuvų taukai)", "Melatonin": "Melatoninas",
    "Valerian": "Valerijonas", "Turmeric": "Ciberžolė", "Echinacea": "Ežiuolė",
    "Ginger": "Imbieras", "Chamomile": "Ramunėlė", "Milk thistle": "Margainis",
    "Cranberry": "Spanguolė", "Licorice": "Saldymedis", "Kava": "Kava kava (Piper methysticum)",
    "Saw palmetto": "Serenoja (saw palmetto)", "Flax seed": "Sėmenys",
    "Glucosamine": "Gliukozaminas", "Chondroitin sulfate": "Chondroitino sulfatas",
    "Creatine": "Kreatinas", "Caffeine": "Kofeinas", "Ethanol": "Alkoholis (etanolis)",
    "Vitamin A": "Vitaminas A", "Vitamin D": "Vitaminas D",
    "Cholecalciferol": "Vitaminas D3 (cholekalciferolis)",
    "Ergocalciferol": "Vitaminas D2 (ergokalciferolis)", "Vitamin E": "Vitaminas E",
    "Phylloquinone": "Vitaminas K1 (filochinonas)", "Ascorbic acid": "Vitaminas C (askorbo rūgštis)",
    "Cyanocobalamin": "Vitaminas B12 (cianokobalaminas)", "Pyridoxine": "Vitaminas B6 (piridoksinas)",
    "Folic acid": "Folio rūgštis", "Niacin": "Vitaminas B3 (niacinas)",
    "Beta carotene": "Beta karotenas", "Calcium carbonate": "Kalcio karbonatas",
    "Calcium citrate": "Kalcio citratas", "Magnesium oxide": "Magnio oksidas",
    "Magnesium citrate": "Magnio citratas", "Magnesium glycinate": "Magnio glicinatas",
    "Ferrous sulfate anhydrous": "Geležies sulfatas", "Ferrous fumarate": "Geležies fumaratas",
    "Iron": "Geležis", "Zinc gluconate": "Cinko gliukonatas", "Zinc sulfate": "Cinko sulfatas",
    "Selenium": "Selenas", "Potassium chloride": "Kalio chloridas", "Iodine": "Jodas",
    "Lactobacillus acidophilus": "Probiotikai (Lactobacillus acidophilus)",
    "Lutein": "Liuteinas", "Lipoic acid": "Alfa lipoinė rūgštis",
    "Grapefruit juice": "Greipfrutų sultys", "Coenzyme Q10": "Kofermentas Q10",
}

# Kurie įrašai laikomi papildais / maistu (UI žymėjimui)
SUPPLEMENTS = {
    "St. John's Wort", "Ginkgo biloba", "Garlic", "Ginseng", "Omega-3 fatty acids", "Melatonin",
    "Valerian", "Turmeric", "Echinacea", "Ginger", "Chamomile", "Milk thistle", "Cranberry",
    "Licorice", "Kava", "Saw palmetto", "Flax seed", "Glucosamine", "Chondroitin sulfate",
    "Creatine", "Caffeine", "Ethanol", "Vitamin A", "Vitamin D", "Cholecalciferol",
    "Ergocalciferol", "Vitamin E", "Phylloquinone", "Ascorbic acid", "Cyanocobalamin",
    "Pyridoxine", "Folic acid", "Niacin", "Beta carotene", "Calcium carbonate", "Calcium citrate",
    "Magnesium oxide", "Magnesium citrate", "Magnesium glycinate", "Ferrous sulfate anhydrous",
    "Ferrous fumarate", "Iron", "Zinc gluconate", "Zinc sulfate", "Selenium", "Potassium chloride",
    "Lactobacillus acidophilus", "Lutein", "Lipoic acid", "Grapefruit juice", "Coenzyme Q10",
    "Goldenseal", "Capsicum", "Clove", "Papaya", "Chromium picolinate", "Plantago seed",
}

# --------------------------------------------------------------------------
# 5. Buitiniai / bendriniai pavadinimai -> atstovaujanti DDInter medžiaga
# --------------------------------------------------------------------------
GENERIC_ALIASES: dict[str, tuple[list[str], str | None]] = {
    # raktas (be lietuviškų raidžių): ([medžiagos], pastaba)
    "zuvu taukai": (["Omega-3 fatty acids"], None),
    "zuvies taukai": (["Omega-3 fatty acids"], None),
    "fish oil": (["Omega-3 fatty acids"], None),
    "omega 3": (["Omega-3 fatty acids"], None),
    "magnis": (["Magnesium oxide"], "Bendras magnio įrašas – naudojamas magnio oksidas kaip atstovas."),
    "magnesium": (["Magnesium oxide"], "Bendras magnio įrašas – naudojamas magnio oksidas kaip atstovas."),
    "kalcis": (["Calcium carbonate"], "Bendras kalcio įrašas – naudojamas kalcio karbonatas kaip atstovas."),
    "calcium": (["Calcium carbonate"], "Bendras kalcio įrašas – naudojamas kalcio karbonatas kaip atstovas."),
    "gelezis": (["Ferrous sulfate anhydrous"], "Bendras geležies įrašas – naudojamas geležies sulfatas kaip atstovas."),
    "cinkas": (["Zinc gluconate"], "Bendras cinko įrašas – naudojamas cinko gliukonatas kaip atstovas."),
    "zinc": (["Zinc gluconate"], "Bendras cinko įrašas – naudojamas cinko gliukonatas kaip atstovas."),
    "kalis": (["Potassium chloride"], "Bendras kalio įrašas – naudojamas kalio chloridas kaip atstovas."),
    "vitaminas d": (["Cholecalciferol"], None), "vitaminas d3": (["Cholecalciferol"], None),
    "vitamin d3": (["Cholecalciferol"], None), "d3": (["Cholecalciferol"], None),
    "vitaminas k": (["Phylloquinone"], None), "vitamin k": (["Phylloquinone"], None),
    "vitaminas c": (["Ascorbic acid"], None), "vitamin c": (["Ascorbic acid"], None),
    "vitaminas e": (["Vitamin E"], None), "vitaminas a": (["Vitamin A"], None),
    "vitaminas b12": (["Cyanocobalamin"], None), "b12": (["Cyanocobalamin"], None),
    "vitaminas b6": (["Pyridoxine"], None),
    "alkoholis": (["Ethanol"], None), "alcohol": (["Ethanol"], None),
    "kava": (["Caffeine"], "„Kava“ suprasta kaip gėrimas (kofeinas). Augalui rinkitės „Kava kava“."),
    "coffee": (["Caffeine"], None),
    "kava kava": (["Kava"], None),
    "greipfrutas": (["Grapefruit juice"], None), "greipfrutai": (["Grapefruit juice"], None),
    "grapefruit": (["Grapefruit juice"], None),
    "q10": (["Coenzyme Q10"], None), "koenzimas q10": (["Coenzyme Q10"], None),
    "probiotikai": (["Lactobacillus acidophilus"], "Naudojamas Lactobacillus acidophilus kaip atstovas."),
    "aspirinas": (["Acetylsalicylic acid"], None),
}

# --------------------------------------------------------------------------
# 6. Prekiniai pavadinimai (pavyzdinis, NEPILNAS sąrašas)
# --------------------------------------------------------------------------
BRANDS: dict[str, list[str]] = {
    "Nurofen": ["Ibuprofen"], "Ibumetin": ["Ibuprofen"], "Ibuprom": ["Ibuprofen"],
    "Panadol": ["Acetaminophen"], "Aspirin": ["Acetylsalicylic acid"],
    "Cardiomagnyl": ["Acetylsalicylic acid", "Magnesium hydroxide"],
    "Voltaren": ["Diclofenac"], "Diclac": ["Diclofenac"], "Naklofen": ["Diclofenac"],
    "Ketonal": ["Ketoprofen"], "Movalis": ["Meloxicam"], "Celebrex": ["Celecoxib"],
    "Nalgesin": ["Naproxen"], "Tramal": ["Tramadol"],
    "Zaldiar": ["Tramadol", "Acetaminophen"],
    "Xarelto": ["Rivaroxaban"], "Eliquis": ["Apixaban"], "Lixiana": ["Edoxaban"],
    "Warfarin Orion": ["Warfarin"], "Plavix": ["Clopidogrel"], "Brilique": ["Ticagrelor"],
    "Concor": ["Bisoprolol"], "Betaloc": ["Metoprolol"], "Egilok": ["Metoprolol"],
    "Nebilet": ["Nebivolol"], "Norvasc": ["Amlodipine"], "Prestarium": ["Perindopril"],
    "Noliprel": ["Perindopril", "Indapamide"], "Tritace": ["Ramipril"], "Enap": ["Enalapril"],
    "Lorista": ["Losartan"], "Cozaar": ["Losartan"], "Diovan": ["Valsartan"],
    "Micardis": ["Telmisartan"], "Arifon": ["Indapamide"], "Trifas": ["Torasemide"],
    "Verospiron": ["Spironolactone"], "Cordarone": ["Amiodarone"],
    "Atoris": ["Atorvastatin"], "Lipitor": ["Atorvastatin"], "Sortis": ["Atorvastatin"],
    "Crestor": ["Rosuvastatin"], "Roxera": ["Rosuvastatin"], "Zocor": ["Simvastatin"],
    "Euthyrox": ["Levothyroxine"], "Letrox": ["Levothyroxine"], "L-Thyroxin": ["Levothyroxine"],
    "Glucophage": ["Metformin"], "Siofor": ["Metformin"], "Amaryl": ["Glimepiride"],
    "Januvia": ["Sitagliptin"], "Jardiance": ["Empagliflozin"], "Forxiga": ["Dapagliflozin"],
    "Ozempic": ["Semaglutide"],
    "Controloc": ["Pantoprazole"], "Nolpaza": ["Pantoprazole"], "Losec": ["Omeprazole"],
    "Nexium": ["Esomeprazole"], "Emanera": ["Esomeprazole"], "Quamatel": ["Famotidine"],
    "Imodium": ["Loperamide"], "Cerucal": ["Metoclopramide"],
    "Augmentin": ["Amoxicillin", "Clavulanic acid"], "Amoksiklav": ["Amoxicillin", "Clavulanic acid"],
    "Ospamox": ["Amoxicillin"], "Sumamed": ["Azithromycin"], "Klacid": ["Clarithromycin"],
    "Fromilid": ["Clarithromycin"], "Ciprinol": ["Ciprofloxacin"], "Tavanic": ["Levofloxacin"],
    "Biseptol": ["Sulfamethoxazole", "Trimethoprim"], "Diflucan": ["Fluconazole"],
    "Zoloft": ["Sertraline"], "Asentra": ["Sertraline"], "Cipralex": ["Escitalopram"],
    "Prozac": ["Fluoxetine"], "Paxil": ["Paroxetine"], "Velaxin": ["Venlafaxine"],
    "Cymbalta": ["Duloxetine"], "Remeron": ["Mirtazapine"], "Trittico": ["Trazodone"],
    "Xanax": ["Alprazolam"], "Valium": ["Diazepam"], "Relanium": ["Diazepam"],
    "Lorafen": ["Lorazepam"], "Rivotril": ["Clonazepam"], "Stilnox": ["Zolpidem"],
    "Imovane": ["Zopiclone"], "Atarax": ["Hydroxyzine"], "Seroquel": ["Quetiapine"],
    "Zyprexa": ["Olanzapine"], "Rispolept": ["Risperidone"], "Abilify": ["Aripiprazole"],
    "Lyrica": ["Pregabalin"], "Neurontin": ["Gabapentin"], "Tegretol": ["Carbamazepine"],
    "Finlepsin": ["Carbamazepine"], "Depakine": ["Valproic acid"], "Lamictal": ["Lamotrigine"],
    "Keppra": ["Levetiracetam"], "Medrol": ["Methylprednisolone"],
    "Milurit": ["Allopurinol"], "Zyloric": ["Allopurinol"], "Viagra": ["Sildenafil"],
    "Cialis": ["Tadalafil"], "Omnic": ["Tamsulosin"], "Zyrtec": ["Cetirizine"],
    "Zodac": ["Cetirizine"], "Xyzal": ["Levocetirizine"], "Claritine": ["Loratadine"],
    "Aerius": ["Desloratadine"], "Telfast": ["Fexofenadine"], "Singulair": ["Montelukast"],
    "Ventolin": ["Salbutamol"], "Otrivin": ["Xylometazoline (nasal)"],
    "ACC": ["Acetylcysteine"], "Fluimucil": ["Acetylcysteine"], "Trental": ["Pentoxifylline"],
    "Magne B6": ["Magnesium oxide", "Pyridoxine"],
    "Calcium-D3 Nycomed": ["Calcium carbonate", "Cholecalciferol"],
    "Tardyferon": ["Ferrous sulfate anhydrous"],
    "Sorbifer Durules": ["Ferrous sulfate anhydrous", "Ascorbic acid"],
    "Vigantol": ["Cholecalciferol"], "Vigantoletten": ["Cholecalciferol"],
    "Detrimax": ["Cholecalciferol"], "Persen": ["Valerian"],
    "Valocordin": ["Phenobarbital"], "Corvalol": ["Phenobarbital"],
}
BRAND_NOTES = {
    "Magne B6": "Preparate yra magnio laktatas; naudojamas magnio oksidas kaip atstovas.",
    "Persen": "Sudėtyje yra ir melisos bei mėtų ekstraktų – jų sąveikos netikrinamos.",
    "Valocordin": "Sudėtyje yra ir etilo bromizovalerato – jo sąveikos netikrinamos.",
    "Corvalol": "Sudėtyje yra ir etilo bromizovalerato – jo sąveikos netikrinamos.",
}

# --------------------------------------------------------------------------
# 7. Populiarios medžiagos, kurių DDInter v1 NETURI (svarbu įspėti vartotoją)
# --------------------------------------------------------------------------
NOT_IN_DB: dict[str, str] = {
    "metamizolas": "Metamizolas (Analginas)", "metamizole": "Metamizolas (Analginas)",
    "analginas": "Metamizolas (Analginas)", "analgin": "Metamizolas (Analginas)",
    "nimesulidas": "Nimesulidas (Nimesil)", "nimesil": "Nimesulidas (Nimesil)",
    "drotaverinas": "Drotaverinas (No-Spa)", "no-spa": "Drotaverinas (No-Spa)",
    "nospa": "Drotaverinas (No-Spa)",
    "meldonis": "Meldonis (Mildronate)", "mildronate": "Meldonis (Mildronate)",
    "gliklazidas": "Gliklazidas (Diaprel)", "diaprel": "Gliklazidas (Diaprel)",
    "dabigatranas": "Dabigatranas (Pradaxa)", "pradaxa": "Dabigatranas (Pradaxa)",
    "kandesartanas": "Kandesartanas", "lerkanidipinas": "Lerkanidipinas",
    "betahistinas": "Betahistinas (Betaserc)", "betaserc": "Betahistinas (Betaserc)",
    "trimetazidinas": "Trimetazidinas (Preductal)", "preductal": "Trimetazidinas (Preductal)",
    "piracetamas": "Piracetamas (Nootropil)", "nootropil": "Piracetamas (Nootropil)",
    "ambroksolis": "Ambroksolis (Lazolvan)", "lazolvan": "Ambroksolis (Lazolvan)",
    "validolis": "Validolis",
}

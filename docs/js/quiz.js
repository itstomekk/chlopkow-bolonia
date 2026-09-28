/* Quiz o Chłopkowie — ABCD questions, each bound to a real place on the map (13 village facts + wayside shrines + the jazz barn).
   Source: Polish Wikipedia, "Chłopków (województwo mazowieckie)" (CC BY-SA 4.0).
   `spot` = where the question signboard stands (see osm/place_items.py -> items.json "boards");
   `halina` = asked by Pani Halina herself. `ok` = index of the correct answer (0..3).
   Answers are shuffled at display time, so `ok` always refers to the original order. */
'use strict';
window.QUIZ = [
  {
    id: 'king', spot: 'halina', ok: 0,
    pl: {
      q: 'Około 1450 roku król nadał wieś (wtedy zwaną Chłopowo) Mleczce herbu Korczak. Który to był król?',
      a: ['Kazimierz IV Jagiellończyk', 'Bolesław Chrobry', 'Jan III Sobieski', 'Stefan Batory'],
      fact: 'Kazimierz IV Jagiellończyk był królem Polski i wielkim księciem litewskim. Chłopków ma ponad 570 lat!',
    },
    en: {
      q: 'Around 1450 a king granted the village (then called Chłopowo) to Mleczko of the Korczak clan. Which king?',
      a: ['Casimir IV Jagiellon', 'Bolesław the Brave', 'John III Sobieski', 'Stephen Báthory'],
      fact: 'Casimir IV Jagiellon was King of Poland and Grand Duke of Lithuania. Chłopków is over 570 years old!',
    },
  },
  {
    id: 'name', spot: 'shop', ok: 1,
    pl: {
      q: 'Pani ze sklepu pyta: „A wiesz, jak dawniej nazywała się nasza wieś?”',
      a: ['Chłopkowice', 'Chłopowo', 'Chłapów', 'Chłopiec Wielki'],
      fact: 'W XV wieku wieś nazywała się Chłopowo. Dopiero później przyjęła się nazwa Chłopków.',
    },
    en: {
      q: 'The shop lady asks: "Do you know what our village used to be called?"',
      a: ['Chłopkowice', 'Chłopowo', 'Chłapów', 'Great Chłopiec'],
      fact: 'In the 15th century the village was called Chłopowo. The name Chłopków came later.',
    },
  },
  {
    id: 'church', spot: 'church', ok: 2,
    pl: {
      q: 'Murowany kościół w Chłopkowie zbudowano w 1890 roku. Czym był pierwotnie?',
      a: ['Synagogą', 'Zborem ewangelickim', 'Cerkwią prawosławną', 'Kaplicą zamkową'],
      fact: 'Zbudowano go w stylu bizantyjsko-rosyjskim jako cerkiew. W 1918 r. przejęli go katolicy, a w 1920 r. wznowiono parafię.',
    },
    en: {
      q: 'The brick church in Chłopków was built in 1890. What was it originally?',
      a: ['A synagogue', 'A Protestant church', 'An Orthodox church', 'A castle chapel'],
      fact: 'It was built in Byzantine-Russian style as an Orthodox church. Catholics took it over in 1918 and the parish was restored in 1920.',
    },
  },
  {
    id: 'lightning', spot: 'river', ok: 1,
    pl: {
      q: 'Z nad Melioranki widać wieżę kościoła. A co w 1702 roku zniszczyło pierwszą cerkiew w Chłopkowie?',
      a: ['Powódź', 'Uderzenie pioruna', 'Wojsko szwedzkie', 'Trąba powietrzna'],
      fact: 'Cerkiew spłonęła od pioruna w 1702 r. Już dwa lata później, w 1704 r., stanęła nowa świątynia.',
    },
    en: {
      q: 'You can see the church tower from the Melioranka. What destroyed the first church in Chłopków in 1702?',
      a: ['A flood', 'A lightning strike', 'The Swedish army', 'A tornado'],
      fact: 'It burned down after a lightning strike in 1702. A new church stood just two years later, in 1704.',
    },
  },
  {
    id: 'cerkwisko', spot: 'rectory', ok: 1,
    pl: {
      q: 'Plebania stoi w miejscu, które mieszkańcy nazywają „cerkwiskiem”. Co tam było w średniowieczu?',
      a: ['Cmentarz', 'Gród otoczony wałami', 'Młyn wodny', 'Karczma'],
      fact: 'Wały wczesnośredniowiecznego grodziska miały u podstawy nawet 8 m szerokości. W XIX w. piasek i kamienie z wałów zużyto do budowy cerkwi, plebanii i drogi.',
    },
    en: {
      q: 'The rectory stands on a spot locals call the "cerkwisko". What was here in the Middle Ages?',
      a: ['A cemetery', 'A fortified settlement with ramparts', 'A water mill', 'An inn'],
      fact: 'The ramparts of the early medieval hillfort were up to 8 m wide at the base. In the 19th century their sand and stones were used to build the church, the rectory and the road.',
    },
  },
  {
    id: 'windmill', spot: 'windmill', ok: 0,
    pl: {
      q: 'Stary wiatrak w Chłopkowie to „koźlak”. Co jest w nim wyjątkowego?',
      a: ['Cały budynek obraca się na słupie do wiatru', 'Ma murowaną wieżę', 'Napędza go woda', 'Ma sześć skrzydeł'],
      fact: 'W koźlaku cały drewniany budynek młyna obraca się na pionowym słupie. Młynarz obracał go dyszlem, żeby skrzydła łapały wiatr.',
    },
    en: {
      q: 'The old windmill in Chłopków is a "koźlak" (post mill). What is special about it?',
      a: ['The whole building turns on a post to face the wind', 'It has a brick tower', 'It is driven by water', 'It has six sails'],
      fact: 'In a post mill the whole wooden mill house turns on a vertical post. The miller pushed the tail pole to point the sails into the wind.',
    },
  },
  {
    id: 'voivodeship', spot: 'bus1', ok: 3,
    pl: {
      q: 'W latach 1975–1998 Chłopków należał do innego województwa niż dziś. Do którego?',
      a: ['Siedleckiego', 'Lubelskiego', 'Podlaskiego', 'Bialskopodlaskiego'],
      fact: 'Do 1998 r. było to województwo bialskopodlaskie. Dziś Chłopków leży w województwie mazowieckim, w powiecie łosickim, w gminie Platerów.',
    },
    en: {
      q: 'From 1975 to 1998 Chłopków belonged to a different voivodeship. Which one?',
      a: ['Siedlce', 'Lublin', 'Podlaskie', 'Biała Podlaska'],
      fact: 'Until 1998 it was the Biała Podlaska voivodeship. Today Chłopków is in Masovia, Łosice county, Platerów commune.',
    },
  },
  {
    id: 'lindens', spot: 'bus2', ok: 2,
    pl: {
      q: 'Jeden z odcinków drogi w Chłopkowie to lokalna atrakcja. Czym jest obsadzony?',
      a: ['Topolami', 'Kasztanowcami', 'Starymi lipami', 'Wierzbami płaczącymi'],
      fact: 'Odcinek drogi obsadzony starymi lipami to jedno z miejsc wartych odwiedzenia we wsi, obok kościoła, cmentarza i wiatraka.',
    },
    en: {
      q: "One stretch of road in Chłopków is a local sight. What is it lined with?",
      a: ['Poplars', 'Horse chestnuts', 'Old linden trees', 'Weeping willows'],
      fact: 'The road lined with old lindens is one of the sights of the village, alongside the church, the cemetery and the windmill.',
    },
  },
  {
    id: 'lampart', spot: 'cemetery', ok: 0,
    pl: {
      q: 'W maju 1952 r. koło Chłopkowa po 7-godzinnej walce rozbito patrol podziemia niepodległościowego. Jaki pseudonim miał jego dowódca, Adam Ratyniec?',
      a: ['„Lampart”', '„Ryś”', '„Orzeł”', '„Wilk”'],
      fact: 'Patrol „Lamparta” z 6. Brygady Wileńskiej AK otoczyło ok. 400 żołnierzy KBW i funkcjonariuszy UB. Dowódca poległ w walce.',
    },
    en: {
      q: 'In May 1952, after a 7-hour fight near Chłopków, an anti-communist resistance patrol was crushed. What was the codename of its commander, Adam Ratyniec?',
      a: ['"Lampart" (Leopard)', '"Ryś" (Lynx)', '"Orzeł" (Eagle)', '"Wilk" (Wolf)'],
      fact: 'The "Lampart" patrol of the 6th Vilnius Brigade of the Home Army was surrounded by about 400 security troops. The commander was killed in the fight.',
    },
  },
  {
    id: 'club', spot: 'pitch', ok: 1,
    pl: {
      q: 'Na boisku w Chłopkowie grał kiedyś klub sportowy. Jak się nazywał?',
      a: ['KS „Orzeł”', 'KS „Sokół”', 'LKS „Traktor”', 'KS „Wiatrak”'],
      fact: 'Boisko do piłki nożnej należało niegdyś do KS „Sokół”. Damian twierdzi, że gra lepiej niż cały „Sokół”.',
    },
    en: {
      q: 'A sports club used to play on the Chłopków pitch. What was it called?',
      a: ['KS "Eagle"', 'KS "Falcon" (Sokół)', 'LKS "Tractor"', 'KS "Windmill"'],
      fact: 'The football pitch once belonged to KS "Sokół". Damian claims he plays better than the whole "Sokół" team.',
    },
  },
  {
    id: 'parts', spot: 'orchard', ok: 3,
    pl: {
      q: 'Sady rosną w różnych częściach wsi. Która z tych nazw to naprawdę część Chłopkowa?',
      a: ['Podlipie', 'Nowa Wola', 'Chłopskie Pole', 'Peryczówka'],
      fact: 'Części wsi to m.in. Peryczówka, Wapnica, Adamowo, Chłopków przy drodze i Chłopków-Kolonia (od lasu i od Szpak).',
    },
    en: {
      q: 'Orchards grow in several parts of the village. Which of these is really a part of Chłopków?',
      a: ['Podlipie', 'Nowa Wola', 'Chłopskie Pole', 'Peryczówka'],
      fact: 'Parts of the village include Peryczówka, Wapnica, Adamowo, Chłopków-by-the-road and Chłopków-Kolonia.',
    },
  },
  {
    id: 'forest', spot: 'woods', ok: 2,
    pl: {
      q: 'Wokół wsi są trzy lasy: Sułów, Bagno i... jak nazywa się ten trzeci?',
      a: ['Borek', 'Zielony Gaj', 'Wisielec', 'Knieja'],
      fact: 'Las „Wisielec”, obok Sułowa i Bagna. Lepiej nie pytać, skąd ta nazwa... a najlepiej zapytać babcię.',
    },
    en: {
      q: 'There are three woods around the village: Sułów, Bagno and... what is the third called?',
      a: ['Borek', 'Green Grove', 'Wisielec (the Hanged Man)', 'Knieja'],
      fact: 'The "Wisielec" (Hanged Man) wood, next to Sułów and Bagno. Better not ask where the name comes from... or ask Grandma.',
    },
  },
  {
    id: 'neighbour', spot: 'eastroad', ok: 0,
    pl: {
      q: 'Ta droga prowadzi na wschód, do sąsiedniej wsi. Do której?',
      a: ['Stare Litewniki', 'Ostromęczyn', 'Grzybów', 'Hruszniew'],
      fact: 'Na wschodzie są Stare Litewniki, na zachodzie Ostromęczyn, na północy Grzybów, a na południowym zachodzie Hruszniew.',
    },
    en: {
      q: 'This road leads east to the neighbouring village. Which one?',
      a: ['Stare Litewniki', 'Ostromęczyn', 'Grzybów', 'Hruszniew'],
      fact: 'Stare Litewniki lies to the east, Ostromęczyn to the west, Grzybów to the north and Hruszniew to the south-west.',
    },
  },
  /* Wayside figures (osm/render_map.py GENERATED_SHRINES + the Kapliczka) and the JAZZ W STODOLE barn.
     General Polish folk-religious customs, not claims about these particular figures. */
  {
    id: 'crossroads', spot: 'shrine1', ok: 0,
    pl: {
      q: 'Przydrożne krzyże na polskiej wsi najczęściej stawiano...',
      a: ['na rozstajach dróg i na skraju wsi', 'tylko na szczytach gór', 'wyłącznie przy dworcach kolejowych', 'na środku stawów'],
      fact: 'Krzyże stawiano na rozstajach i granicach wsi: z wdzięczności, jako wotum lub by chroniły mieszkańców i pola.',
    },
    en: {
      q: 'Roadside crosses in Polish villages were most often put up...',
      a: ['at crossroads and at the edge of the village', 'only on mountain tops', 'only at railway stations', 'in the middle of ponds'],
      fact: 'Crosses stood at crossroads and village boundaries: as thanksgiving, as a votive offering or to protect the people and fields.',
    },
  },
  {
    id: 'majowka', spot: 'shrine2', ok: 1,
    pl: {
      q: 'W maju mieszkańcy wsi zbierają się przy kapliczkach na nabożeństwo majowe ("majówkę"). Komu jest ono poświęcone?',
      a: ['Świętemu Mikołajowi', 'Matce Bożej', 'Świętemu Florianowi', 'Świętemu Janowi Chrzcicielowi'],
      fact: 'Nabożeństwa majowe to modlitwy do Maryi, m.in. Litania Loretańska, śpiewane wieczorem przy przystrojonej kapliczce.',
    },
    en: {
      q: 'In May villagers gather at wayside shrines for the May devotion ("majówka"). To whom is it dedicated?',
      a: ['Saint Nicholas', 'the Virgin Mary', 'Saint Florian', 'Saint John the Baptist'],
      fact: 'May devotions are prayers to Mary, such as the Litany of Loreto, sung in the evening at a decorated shrine.',
    },
  },
  {
    id: 'bozecialo', spot: 'shrine3', ok: 2,
    pl: {
      q: 'W Boże Ciało procesja idzie przez wieś i zatrzymuje się przy ołtarzach. Ile ich jest tradycyjnie?',
      a: ['Dwa', 'Trzy', 'Cztery', 'Siedem'],
      fact: 'Tradycyjnie są cztery ołtarze, przy każdym czyta się fragment innej Ewangelii. Ołtarze często stają przy kapliczkach.',
    },
    en: {
      q: 'On Corpus Christi the procession walks through the village and stops at altars. How many are there traditionally?',
      a: ['Two', 'Three', 'Four', 'Seven'],
      fact: 'Traditionally there are four altars, each with a reading from a different Gospel. They are often set up at wayside shrines.',
    },
  },
  {
    id: 'nepomucen', spot: 'shrine4', ok: 3,
    pl: {
      q: 'Figury którego świętego, patrona od powodzi, stawiano często przy mostach i rzekach?',
      a: ['Św. Floriana', 'Św. Huberta', 'Św. Izydora', 'Św. Jana Nepomucena'],
      fact: 'Św. Jan Nepomucen chroni przed powodzią, dlatego jego figury stoją przy mostach. Św. Florian to patron strażaków.',
    },
    en: {
      q: 'Statues of which saint, the patron against floods, were often put up by bridges and rivers?',
      a: ['St Florian', 'St Hubert', 'St Isidore', 'St John of Nepomuk'],
      fact: 'St John of Nepomuk protects from floods, so his statues stand by bridges. St Florian is the patron of firefighters.',
    },
  },
  {
    id: 'frasobliwy', spot: 'shrine5', ok: 0,
    pl: {
      q: 'Jak nazywa się ludowa figurka Chrystusa siedzącego w zadumie z głową opartą na dłoni, częsta w wiejskich kapliczkach?',
      a: ['Chrystus Frasobliwy', 'Chrystus Pantokrator', 'Dobry Pasterz', 'Chrystus Król'],
      fact: 'Chrystus Frasobliwy (Smętek) to jeden z najczęstszych motywów polskiej rzeźby ludowej w przydrożnych kapliczkach.',
    },
    en: {
      q: 'What is the folk figure of Christ sitting deep in thought with his head resting on his hand, common in village shrines?',
      a: ['Christ the Pensive (Frasobliwy)', 'Christ Pantocrator', 'The Good Shepherd', 'Christ the King'],
      fact: 'The Pensive Christ (Frasobliwy) is one of the most common motifs of Polish folk carving in wayside shrines.',
    },
  },
  {
    id: 'discopolak', spot: 'jazz', ok: 2,
    pl: {
      q: 'Tu w stodole gra jazz, ale na wiejskiej zabawie tańczy się "discopolaka". Przy jakiej muzyce?',
      a: ['Przy jazzie tradycyjnym', 'Przy muzyce klasycznej', 'Przy disco polo', 'Przy death metalu'],
      fact: 'Disco polo wyrosło pod koniec lat 80. z muzyki granej na weselach i wiejskich zabawach. Najlepiej smakuje z parkietem pod chmurką!',
    },
    en: {
      q: 'The barn plays jazz tonight, but at a village party people dance the "discopolak". To what music?',
      a: ['Trad jazz', 'Classical music', 'Disco polo', 'Death metal'],
      fact: 'Disco polo grew out of music played at weddings and village dances in the late 1980s. Best enjoyed on an open-air dance floor!',
    },
  },
];

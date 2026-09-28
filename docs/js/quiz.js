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
  {
    id: 'niemira-grant', spot: 'house01', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 1,
    pl: {
      q: 'W 1512 roku Zygmunt I Stary nadał Chłopków kolejnej rodzinie. Komu?',
      a: ['Kiszkóm', 'Niemirom', 'Sedlnickim', 'Kuczyńskim'],
      fact: 'Mikołaj Niemira herbu Gozdawa został właścicielem wsi w 1512 roku.',
    },
    en: {
      q: 'In 1512, Sigismund I the Old granted Chłopków to another family. Which one?',
      a: ['The Kiszkas', 'The Niemiras', 'The Sedlnickis', 'The Kuczyńskis'],
      fact: 'Mikołaj Niemira of the Gozdawa coat of arms became the village owner in 1512.',
    },
  },
  {
    id: 'niemira-coat', spot: 'house02', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 3,
    pl: {
      q: 'Mikołaj Niemira, właściciel Chłopkowa od 1512 roku, nosił herb...',
      a: ['Korczak', 'Dąbrowa', 'Odrowąż', 'Gozdawa'],
      fact: 'Niemirowie z Chłopkowa należeli do herbu Gozdawa.',
    },
    en: {
      q: 'Mikołaj Niemira, owner of Chłopków from 1512, bore which coat of arms?',
      a: ['Korczak', 'Dąbrowa', 'Odrowąż', 'Gozdawa'],
      fact: 'The Niemira family of Chłopków belonged to the Gozdawa coat of arms.',
    },
  },
  {
    id: 'kiszka-founder', spot: 'house03', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 0,
    pl: {
      q: 'Według części przekazów fundatorem pierwszej cerkwi w Chłopkowie był...',
      a: ['Mikołaj Kiszka', 'Mikołaj Niemira', 'Karol Sedlnicki', 'Kajetan Kuczyński'],
      fact: 'To przypuszczenie, nie pewnik: źródło diecezjalne pisze, że „niektórzy twierdzą”, iż fundatorem był Mikołaj Kiszka herbu Dąbrowa.',
    },
    en: {
      q: 'According to some accounts, who founded Chłopków’s first Orthodox church?',
      a: ['Mikołaj Kiszka', 'Mikołaj Niemira', 'Karol Sedlnicki', 'Kajetan Kuczyński'],
      fact: 'This is not certain: the diocesan history says that some accounts name Mikołaj Kiszka of the Dąbrowa coat of arms as founder.',
    },
  },
  {
    id: 'kiszka-era', spot: 'house04', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 2,
    pl: {
      q: 'Pierwsza cerkiew w Chłopkowie mogła powstać na przełomie których wieków?',
      a: ['XIII i XIV', 'XV i XVI', 'XVI i XVII', 'XVIII i XIX'],
      fact: 'Źródło diecezjalne wskazuje przełom XVI i XVII wieku, z zastrzeżeniem, że fundator i okoliczności nie są całkiem pewne.',
    },
    en: {
      q: 'Around the turn of which centuries may Chłopków’s first Orthodox church have been founded?',
      a: ['13th and 14th', '15th and 16th', '16th and 17th', '18th and 19th'],
      fact: 'The diocesan history places it around the turn of the 16th and 17th centuries, while noting that the details are uncertain.',
    },
  },
  {
    id: '1704-dedication', spot: 'house05', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 1,
    pl: {
      q: 'Unicka świątynia wzniesiona w Chłopkowie w 1704 roku była pod wezwaniem...',
      a: ['Świętego Mikołaja', 'Wniebowzięcia Najświętszej Maryi Panny', 'Świętego Jana Nepomucena', 'Narodzenia Pańskiego'],
      fact: 'Kolejna unicka świątynia pw. Wniebowzięcia NMP powstała w 1704 roku.',
    },
    en: {
      q: 'The Uniate church built in Chłopków in 1704 was dedicated to...',
      a: ['Saint Nicholas', 'the Assumption of the Virgin Mary', 'Saint John of Nepomuk', 'the Nativity of Christ'],
      fact: 'The next Uniate church, dedicated to the Assumption of the Virgin Mary, was built in 1704.',
    },
  },
  {
    id: '1786-church', spot: 'house06', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 3,
    pl: {
      q: 'W którym roku w Chłopkowie wzniesiono następną unicką świątynię po tej z 1704 roku?',
      a: ['1726', '1775', '1787', '1786'],
      fact: 'Świątynię wzniesiono w 1786 roku; poświęcono ją rok później, w 1787.',
    },
    en: {
      q: 'In what year was the next Uniate church built in Chłopków after the one from 1704?',
      a: ['1726', '1775', '1787', '1786'],
      fact: 'It was built in 1786 and consecrated the following year, in 1787.',
    },
  },
  {
    id: 'parish-1875', spot: 'house07', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 2,
    pl: {
      q: 'Co stało się z greckokatolicką parafią w Chłopkowie po kasacie unii w 1875 roku?',
      a: ['Została przeniesiona do Sarnak', 'Zmieniono ją w klasztor', 'Zamieniono ją na prawosławną', 'Zamknięto ją na zawsze'],
      fact: 'W 1875 roku parafia greckokatolicka została zamieniona na prawosławną.',
    },
    en: {
      q: 'What happened to Chłopków’s Greek Catholic parish after the Union was abolished in 1875?',
      a: ['It moved to Sarnaki', 'It became a monastery', 'It became Orthodox', 'It closed permanently'],
      fact: 'In 1875 the Greek Catholic parish was converted into an Orthodox parish.',
    },
  },
  {
    id: 'church-1890-order', spot: 'house08', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 0,
    pl: {
      q: 'Co stało się w 1890 roku ze starą, drewnianą świątynią w Chłopkowie?',
      a: ['Rozebrano ją na rozkaz władz carskich', 'Przeniesiono ją do Łosic', 'Zamieniono ją w szkołę', 'Spłonęła od pioruna'],
      fact: 'Władze carskie nakazały rozebrać drewnianą świątynię; na jej miejscu powstała murowana cerkiew.',
    },
    en: {
      q: 'What happened to the old wooden church in Chłopków in 1890?',
      a: ['It was dismantled by order of the tsarist authorities', 'It was moved to Łosice', 'It became a school', 'It burned down after a lightning strike'],
      fact: 'The tsarist authorities ordered the wooden church dismantled; a brick Orthodox church was built in its place.',
    },
  },
  {
    id: 'church-style', spot: 'house09', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 3,
    pl: {
      q: 'W jakim stylu wzniesiono murowaną cerkiew w Chłopkowie w 1890 roku?',
      a: ['Gotyckim', 'Klasycystycznym', 'Zakopiańskim', 'Bizantyjskim'],
      fact: 'Murowaną cerkiew wzniesiono w stylu bizantyjskim.',
    },
    en: {
      q: 'In which style was Chłopków’s brick Orthodox church built in 1890?',
      a: ['Gothic', 'Neoclassical', 'Zakopane style', 'Byzantine'],
      fact: 'The brick Orthodox church was built in the Byzantine style.',
    },
  },
  {
    id: 'przezdziecki', spot: 'house10', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 1,
    pl: {
      q: 'Który biskup wydał w 1918 roku rozporządzenie o rewindykacji świątyni dla katolików?',
      a: ['Józef Kocięcki', 'Henryk Przeździecki', 'Zygmunt Urban', 'Andrzej Jakubowicz'],
      fact: 'Rozporządzenie nr 65 wydał 11 grudnia 1918 roku biskup Henryk Przeździecki.',
    },
    en: {
      q: 'Which bishop issued the 1918 order returning the church to Catholics?',
      a: ['Józef Kocięcki', 'Henryk Przeździecki', 'Zygmunt Urban', 'Andrzej Jakubowicz'],
      fact: 'Bishop Henryk Przeździecki issued decree no. 65 on 11 December 1918.',
    },
  },
  {
    id: 'parish-restored', spot: 'house11', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 2,
    pl: {
      q: 'W którym roku wznowiono w Chłopkowie parafię katolicką obrządku łacińskiego?',
      a: ['1875', '1890', '1920', '1945'],
      fact: 'Parafię wznowiono w 1920 roku; dekret wydano 27 marca, a jej istnienie rozpoczęło się 15 kwietnia.',
    },
    en: {
      q: 'In what year was the Latin-rite Catholic parish in Chłopków re-established?',
      a: ['1875', '1890', '1920', '1945'],
      fact: 'The parish was re-established in 1920; the decree was issued on 27 March and it began on 15 April.',
    },
  },
  {
    id: 'parish-territory', spot: 'house12', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 0,
    pl: {
      q: 'W 1775 roku część wsi z parafii chłopkowskiej przyłączono do parafii w...',
      a: ['Sarnakach', 'Łosicach', 'Mielniku', 'Drohiczynie'],
      fact: 'W 1775 roku obszar parafii chłopkowskiej zmalał; kilka wsi przyłączono do parafii Sarnaki.',
    },
    en: {
      q: 'In 1775, some villages from Chłopków parish were transferred to the parish in...',
      a: ['Sarnaki', 'Łosice', 'Mielnik', 'Drohiczyn'],
      fact: 'In 1775 Chłopków parish became smaller; several villages were transferred to Sarnaki parish.',
    },
  },
  {
    id: 'parish-1797', spot: 'house13', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 3,
    pl: {
      q: 'Jakie dwie wsie dołączono do parafii chłopkowskiej w 1797 roku?',
      a: ['Grzybów i Chlebczyn', 'Lipno i Płosków', 'Mierzwice i Hołowczyce', 'Terlików i Binduga'],
      fact: 'W 1797 roku z parafii mielnickiej dołączono Mierzwice i Hołowczyce.',
    },
    en: {
      q: 'Which two villages were added to Chłopków parish in 1797?',
      a: ['Grzybów and Chlebczyn', 'Lipno and Płosków', 'Mierzwice and Hołowczyce', 'Terlików and Binduga'],
      fact: 'Mierzwice and Hołowczyce were transferred from Mielnik parish in 1797.',
    },
  },
  {
    id: 'sedlnicki', spot: 'house14', optional: true, source: 'Diecezja Drohiczyńska, rys historyczny: https://drohiczynska.pl/parafie/chlopkow-parafia-narodzenia-nmp/', ok: 1,
    pl: {
      q: 'Kto był kolatorem unickiej świątyni w Chłopkowie w 1726 roku?',
      a: ['Mikołaj Kiszka', 'Karol Józef Hiacynt Sedlnicki', 'Mikołaj Niemira', 'Kajetan Antoni Kuczyński'],
      fact: 'W 1726 roku kolatorem był Karol Józef Hiacynt Sedlnicki herbu Odrowąż.',
    },
    en: {
      q: 'Who was the patron of the Uniate church in Chłopków in 1726?',
      a: ['Mikołaj Kiszka', 'Karol Józef Hiacynt Sedlnicki', 'Mikołaj Niemira', 'Kajetan Antoni Kuczyński'],
      fact: 'In 1726 the church patron was Karol Józef Hiacynt Sedlnicki of the Odrowąż coat of arms.',
    },
  },
  {
    id: 'hillfort-height', spot: 'house15', optional: true, source: 'Polinow, Chłopków – grodzisko: https://www.polinow.pl/losice_i_okolice-chlopkow', ok: 2,
    pl: {
      q: 'Jak wysoko nad doliną strumienia wznosi się wzgórze dawnego grodziska?',
      a: ['Około 3 metrów', 'Około 6 metrów', 'Około 9 metrów', 'Około 20 metrów'],
      fact: 'Wzgórze ma około 9 metrów wysokości nad doliną pobliskiego strumienia.',
    },
    en: {
      q: 'How high does the old hillfort mound rise above the stream valley?',
      a: ['About 3 metres', 'About 6 metres', 'About 9 metres', 'About 20 metres'],
      fact: 'The mound rises about 9 metres above the nearby stream valley.',
    },
  },
  {
    id: 'hillfort-platform', spot: 'house16', optional: true, source: 'Polinow, Chłopków – grodzisko: https://www.polinow.pl/losice_i_okolice-chlopkow', ok: 0,
    pl: {
      q: 'Jakie wymiary ma w przybliżeniu spłaszczona górna platforma grodziska?',
      a: ['30 × 28 metrów', '56 × 44 metry', '80 × 60 metrów', '12 × 9 metrów'],
      fact: 'Górna platforma ma około 30 × 28 metrów; podstawa wzgórza jest większa.',
    },
    en: {
      q: 'What are the approximate dimensions of the hillfort’s flattened upper platform?',
      a: ['30 × 28 metres', '56 × 44 metres', '80 × 60 metres', '12 × 9 metres'],
      fact: 'The upper platform is about 30 × 28 metres; the mound’s base is larger.',
    },
  },
  {
    id: 'hillfort-base', spot: 'house17', optional: true, source: 'Polinow, Chłopków – grodzisko: https://www.polinow.pl/losice_i_okolice-chlopkow', ok: 1,
    pl: {
      q: 'Ile mniej więcej mierzy podstawa wzgórza dawnego grodziska?',
      a: ['30 × 28 metrów', '56 × 44 metry', '12 × 9 metrów', '100 × 80 metrów'],
      fact: 'Według opisu grodziska podstawa ma około 56 × 44 metry.',
    },
    en: {
      q: 'What are the approximate dimensions of the old hillfort mound’s base?',
      a: ['30 × 28 metres', '56 × 44 metres', '12 × 9 metres', '100 × 80 metres'],
      fact: 'The hillfort description gives the base as about 56 × 44 metres.',
    },
  },
  {
    id: 'hillfort-findings', spot: 'house18', optional: true, source: 'Polinow, Chłopków – grodzisko: https://www.polinow.pl/losice_i_okolice-chlopkow', ok: 3,
    pl: {
      q: 'Co znajdowano na terenie chłopkowskiego grodziska?',
      a: ['Monety rzymskie i szkło', 'Żelazne miecze', 'Kamienne młyny', 'Skorupy naczyń glinianych i węgiel drzewny'],
      fact: 'Opis wymienia liczne skorupy naczyń glinianych i węgle drzewne.',
    },
    en: {
      q: 'What was found at the Chłopków hillfort site?',
      a: ['Roman coins and glass', 'Iron swords', 'Stone mills', 'Pottery shards and charcoal'],
      fact: 'The site description mentions many pottery fragments and pieces of charcoal.',
    },
  },
  {
    id: 'hillfort-reuse', spot: 'house19', optional: true, source: 'Polinow, Chłopków – grodzisko: https://www.polinow.pl/losice_i_okolice-chlopkow', ok: 2,
    pl: {
      q: 'Do budowy czego wykorzystano w XIX wieku piasek i kamienie z wałów grodziska?',
      a: ['Dworu i stodoły', 'Wiatraka i mostu', 'Cerkwi, plebanii i później drogi', 'Cmentarza i szkoły'],
      fact: 'Materiał z obwarowań wywożono pod budowę cerkwi i plebanii, a później także drogi.',
    },
    en: {
      q: 'What were sand and fieldstones from the hillfort ramparts reused to build in the 19th century?',
      a: ['A manor and a barn', 'A windmill and a bridge', 'The church, rectory and later the road', 'The cemetery and a school'],
      fact: 'Material from the ramparts was taken for the church and rectory, and later for the road.',
    },
  },
  {
    id: 'hillfort-garden', spot: 'house20', optional: true, source: 'Polinow, Chłopków – grodzisko: https://www.polinow.pl/losice_i_okolice-chlopkow', ok: 0,
    pl: {
      q: 'Jak obecnie użytkowane jest wzgórze po dawnym grodzisku?',
      a: ['Jako ogród', 'Jako boisko', 'Jako parking', 'Jako kamieniołom'],
      fact: 'Opis podaje, że wzgórze jest obecnie użytkowane jako ogród.',
    },
    en: {
      q: 'How is the old hillfort mound used today?',
      a: ['As a garden', 'As a sports field', 'As a car park', 'As a quarry'],
      fact: 'The site description says the mound is now used as a garden.',
    },
  },
  {
    id: 'hillfort-location', spot: 'house21', optional: true, source: 'Polinow, Chłopków – grodzisko: https://www.polinow.pl/losice_i_okolice-chlopkow', ok: 1,
    pl: {
      q: 'Po której stronie strumienia znajdują się ślady wczesnośredniowiecznego grodziska?',
      a: ['Na prawym brzegu', 'Na lewym brzegu', 'Na wyspie pośrodku', 'Na drugim końcu wsi, przy lesie'],
      fact: 'Ślady grodziska opisano w pobliżu kościoła, na lewym brzegu strumienia.',
    },
    en: {
      q: 'On which side of the stream are the remains of the early-medieval hillfort?',
      a: ['On the right bank', 'On the left bank', 'On an island in the middle', 'At the far end of the village by the forest'],
      fact: 'The hillfort remains are described near the church, on the stream’s left bank.',
    },
  },
];

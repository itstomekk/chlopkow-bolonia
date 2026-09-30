/* AREK W CHŁOPKOWIE — top-down adventure on a map generated from real OpenStreetMap data.
   World units = art pixels of map_ground.png (2 px per metre). Pure JS, no libraries.
   Quests: Kasia (10 apples), Damian (lost cap), Marcin (orangeade from the shop) -> Grandpa's tractor keys. */
'use strict';
(() => {
  const cvs = document.getElementById('game');
  const ctx = cvs.getContext('2d');
  // Silkscreen has no 'Ć'. Measure it as 'C' and draw 'C' plus a tiny acute accent.
  const _fill = ctx.fillText.bind(ctx), _measure = ctx.measureText.bind(ctx);
  ctx.measureText = t => _measure(String(t).replace(/Ć/g, 'C'));
  ctx.fillText = (t, x, y, mw) => {
    t = String(t);
    if (!t.includes('Ć')) return _fill(t, x, y, mw);
    const plain = t.replace(/Ć/g, 'C'), w = _measure(plain).width, al = ctx.textAlign;
    let cx = al === 'center' ? x - w / 2 : al === 'right' || al === 'end' ? x - w : x;
    const fs = parseFloat((ctx.font.match(/([\d.]+)px/) || [0, 16])[1]);
    ctx.textAlign = 'left';
    for (const part of t.split(/(Ć)/)) {
      if (!part) continue;
      const seg = part === 'Ć' ? 'C' : part; _fill(seg, cx, y);
      if (part === 'Ć') { const cw = _measure('C').width, u = fs / 8; ctx.fillRect(cx + cw * .45, y - fs * .78, u * 1.4, u); ctx.fillRect(cx + cw * .45 + u, y - fs * .78 - u, u * 1.4, u); }
      cx += _measure(seg).width;
    }
    ctx.textAlign = al;
  };
  const params = new URLSearchParams(location.search);
  const LANG = params.get('lang') === 'en' ? 'en' : 'pl';
  const DEBUG = params.get('debug') === '1';
  const SAVE_KEY = 'arek-chlopkow-save-v1';
  const CHARACTER_KEY = 'arek-chlopkow-character-v1';
  const APPLES_NEEDED = 10, MUSHROOMS_TOTAL = 15, MUSHROOMS_NEEDED = 10, TRASH_TOTAL = 5;
  const PLAYABLE_CHARACTERS = ['arek', 'marcin', 'damian', 'edytka', 'renik'];
  let selectedCharacter = localStorage.getItem(CHARACTER_KEY) || 'arek';
  if (!PLAYABLE_CHARACTERS.includes(selectedCharacter)) selectedCharacter = 'arek';

  /* ---------- text ---------- */
  const T = {
    pl: {
      title: 'CHŁOPKÓW BOLONIA', start: 'NACIŚNIJ ENTER / DOTKNIJ', cont: 'KONTYNUUJ: ENTER · NOWA GRA: N',
      help: 'STRZAŁKI / WASD — CHODZENIE · SHIFT — BIEG · SPACJA — ROZMOWA / SKOK · M — MAPA · K — MUZYKA',
      names: { arek: 'BOHATER', kasia: 'KASIA', marcin: 'MARCIN', damian: 'DAMIAN', grandpa: 'DZIADEK ZDZISIEK', halina: 'BABCIA IRENKA', kuba: 'KUBA', soltys: 'SOŁTYS', michal: 'BUKAŁA', mateusz: 'MATEUSZ', patryk: 'PATRYK', edytka: 'EDYTKA', wesoly_swiat: 'WESOŁYCH ŚWIĄT', renik: 'DJ RENIK' },
      edytka0: ['Frodo! Tęskniłam za nim! Przyprowadzisz go do mnie?', 'Tylko on nigdy nie wytrzyma długo. Po paru chwilach i tak ucieka do ciebie.', 'Przyprowadź mi go trzy razy, dobrze?'],
      edytkaNoDog: ['A gdzie Frodo? Przyprowadź go tu, blisko mnie.'],
      edytkaVisit: n => [`Frodo! Chodź tu, piesku! (${n}/3)`],
      edytkaWait: ['Ciii... Frodo jest teraz u mnie.'],
      edytkaDone: ['Trzy razy! Frodo chyba jednak woli ciebie. Ale i tak go kocham.', 'Dziękuję, Arek.'],
      edytkaAfter: ['Pozdrów Frodo. I podrap go za uchem ode mnie.'],
      edytkaBack: 'AREK, FRODO WRÓCIŁ DO CIEBIE!',
      edytkaQuest: 'Przyprowadź Frodo do Edytki',
      wesoly0: ['Ho ho... spokojnie, to nie kolęda, tylko mój marsz przez las.', 'Widziałeś gdzieś renifera? Albo chociaż żabę w czapce?', 'Idę dalej. Jak się zgubię, będę udawał, że to plan.'],
      renik: [
        ['Siema! DJ Renik, do usług. Dziś na boisku gram tylko disco polo.', 'Techno? Techno jest dla ludzi, którzy nie umieją tańczyć w parach.'],
        ['Wiesz, co jest najpiękniejsze w disco polo? Refren. Słyszysz raz i nosisz go w głowie do niedzieli.', 'A potem śpiewa go cała wieś. Nawet ksiądz. Po cichu.'],
        ['Mam na pendrive 4000 kawałków. Wszystkie o miłości, oczach i wakacjach.', 'Każdy inny. Tak mi się przynajmniej wydaje.'],
        ['Syntezator, stopa na raz, klaskanie na dwa. Tyle potrzeba do szczęścia.', 'Reszta to tylko dodatki. Jak sól do ogórków.'],
        ['Kiedyś grałem na weselu do piątej rano. Wujek Zdzisiek tańczył z krzesłem.', 'Krzesło do dziś go wspomina.'],
        ['Jak zrobię remizę pod gwiazdami, to będziesz pierwszy na parkiecie. Obiecuję.', 'Tylko załóż coś błyszczącego. Disco polo lubi cekiny.'],
      ],
      church: ['Kościół pw. Narodzenia NMP. Dzwony biją w południe. Arek, jak zwykle, spóźniony.'],
      rectory: ['Plebania. Ksiądz macha z okna. Arek udaje, że poprawia okulary.'],
      cemetery: ['Cmentarz parafialny. Arek zdejmuje okulary. Na chwilę.'],
      windmill: ['Wiatrak „Koźlak”. Stoi tu dłużej niż ktokolwiek pamięta. Skrzypi, jakby coś mówił.'],
      shop: ['Sklep spożywczo-przemysłowy. Półki są ciasne, ale pełne: oranżada, chleb, konserwy, nabiał i słodycze.', 'Pani sklepowa zna ceny na pamięć. I wie, kto kupił ostatniego pączka.'],
      shopBuy: ['Pani ze sklepu: „Oranżada? Ostatnia butelka, dla Marcina.”', 'Arek dostaje oranżadę!'],
      bus: ['Przystanek. Autobus był... albo będzie. W Chłopkowie to jedno i to samo.'],
      river: ['Rzeka Melioranka. Woda zimna, żaby głośne, a lato jeszcze długie.'],
      kasia0: ['Arek! Piekę szarlotkę na dożynki, ale brakuje mi grzybów do farszu.', 'Przynieś mi 10 pieczarek. Rosną na zielonej trawie w całej wsi. Jabłka zbieraj osobno, przydadzą się do ciasta.'],
      kasia1: n => [`Masz dopiero ${n}/10 pieczarek. Farsz sam się nie zrobi!`],
      kasia2: ['10 pieczarek! Jesteś niezastąpiony. No, prawie.', 'Szarlotka będzie gotowa wieczorem. Zostawię ci kawałek.'],
      kasia3: ['Szarlotka w piekarniku. Pachnie całą wsią!'],
      damian0: ['Stary, zgubiłem czapkę! Biegałem po polach niedaleko stąd...', 'Znajdziesz ją? Bez czapki nie gram.'],
      damian1: ['Nadal nic? Szukaj w żółtym zbożu, kilka minut drogi stąd.'],
      damian2: ['MOJA CZAPKA! Arek, jesteś legendą.', 'Stawiam ci kanapkę. No, pół kanapki.'],
      damian3: ['Z czapką gram jak Lewandowski. Prawie.'],
      marcin0: ['Czekam na autobus od godziny. Umieram z pragnienia.', 'Skoczysz do sklepu po oranżadę? Ja pilnuję przystanku.'],
      marcin1: ['Oranżada. Sklep. Szybko. Proszę.'],
      marcin2: ['Oranżada! Ratujesz mi życie.', 'Autobus i tak nie przyjechał. Ale kto by się przejmował.'],
      marcin3: ['Jeszcze tylko jeden łyk... i idę po traktor. Żartuję. Chyba.'],
      grandpa0: ['Czego tu szukasz, młody? Wiatrak nie jest na sprzedaż.', 'Chcesz czegoś więcej niż spacer? Pomóż najpierw Kasi, Damianowi i Marcinowi.'],
      grandpa1: n => [`Pomogłeś ${n} z 3 przyjaciół. Wracaj, jak skończysz.`],
      grandpa2: ['Pomogłeś całej ekipie. Dobra robota, Arek.', 'Masz tu kluczyki do mojego Ursusa. Tylko w niedzielę i tylko do wzgórza.', 'I nie mów babci Irenki.'],
      apple: 'JABŁKO', mushroom: 'PIECZARKA', trash: 'WOREK ŚMIECI', cap: 'CZAPKA DAMIANA', gotCap: ['Czapka Damiana! Trochę zakurzona, ale cała.'],
      quests: ['10 pieczarek dla Kasi', 'Czapka Damiana', 'Oranżada dla Marcina', 'Pogadaj z dziadkiem Zdziśkiem'],
      churchIn: ['Wnętrze kościoła. Chłodno, cicho, pachnie woskiem i kwiatami.'],
      altar: ['Ołtarz w białym obrusie z koronką. Arek niczego nie dotyka. Tym razem.'],
      mary: ['Matka Boża w marmurowej niszy. Ktoś zostawił świeże kwiaty i wieniec z kłosów.'],
      glass: ['Witraże świecą jak ekran telefonu. Tylko ładniej.'],
      flowers: ['Kwiaty ułożone w złote „100”. Sto lat parafii w Chłopkowie!'],
      confession: ['Konfesjonał. Arek szybko idzie dalej. Nie dziś.'],
      pew: ['Drewniane ławki. Babcia Irenka zawsze siada w trzecim rzędzie, po lewej.'],
      soltys0: ['Dzień dobry, Arek. Chleb na dożynki już jest, poświęcony.', 'Teraz czekamy tylko na szarlotkę Kasi. Pomożesz jej, prawda?', 'A ja dopilnuję porządku. Po pracy należy się zimne piwo i pięć minut ciszy.'],
      soltys1: ['Szarlotka Kasi będzie? To dożynki mamy uratowane.', 'Sołtys wszystko widzi, Arek. Dobra robota.', 'Za taką pomoc wznoszę toast. Tylko nie każ mi przemawiać przed orkiestrą.'],
      soltysSecret: ['Sołtys musi wiedzieć, co dzieje się w każdym zakątku wsi. Nawet w tym.'],
      churchLabel: 'KOŚCIÓŁ', exitHint: '↓ WYJŚCIE', musicOn: 'KAPELA GRA!', musicOff: 'KAPELA CICHO',
      end1: 'MASZ KLUCZYKI DO URSUSA', end2: 'CIĄG DALSZY: GRAND THEFT TRACTOR', end3: 'CZAS',
      memoryTitle: 'ARCHIWUM CMENTARZA', memoryNext: 'ENTER — NASTĘPNE ZDJĘCIE · ESC — POMIŃ', memoryReturn: 'ENTER — WRÓĆ DO WSI',
      memoryNames: ['PROCESJA', 'PAMIĘĆ O ZMARŁYCH', 'DREWNIANY KRZYŻ'],
      memoryFacts: [
        'NA STARYM ZDJĘCIU MIESZKAŃCY NIOSĄ TRUMNĘ W PROCESJI.',
        'PRZY GROBIE WIDAĆ KRZYŻ I WIENIEC, A WOKÓŁ STOJĄ ŻAŁOBNICY.',
        'PROSTY, RĘCZNIE ZROBIONY KRZYŻ Z TABLICZKĄ OZNACZA MOGIŁĘ.',
      ],
    },
    en: {
      title: 'CHŁOPKÓW BOLONIA', start: 'PRESS ENTER / TAP', cont: 'CONTINUE: ENTER · NEW GAME: N',
      help: 'ARROWS / WASD — WALK · SHIFT — RUN · SPACE — TALK / JUMP · M — MAP · K — MUSIC',
      names: { arek: 'PLAYER', kasia: 'KASIA', marcin: 'MARCIN', damian: 'DAMIAN', grandpa: 'GRANDPA ZDZISIEK', halina: 'GRANNY IRENKA', kuba: 'KUBA', soltys: 'SOŁTYS (VILLAGE HEAD)', michal: 'BUKAŁA', mateusz: 'MATEUSZ', patryk: 'PATRYK', edytka: 'EDYTKA', wesoly_swiat: 'WESOŁYCH ŚWIĄT', renik: 'DJ RENIK' },
      edytka0: ['Frodo! I missed him so much! Will you bring him to me?', "He never stays long, though. After a little while he runs back to you anyway.", 'Bring him to me three times, okay?'],
      edytkaNoDog: ["Where's Frodo? Bring him here, close to me."],
      edytkaVisit: n => [`Frodo! Come here, doggy! (${n}/3)`],
      edytkaWait: ['Shh... Frodo is with me right now.'],
      edytkaDone: ['Three times! I think Frodo likes you better. I still love him, though.', 'Thank you, Arek.'],
      edytkaAfter: ['Say hi to Frodo. And scratch him behind the ear from me.'],
      edytkaBack: 'FRODO RAN BACK TO AREK!',
      edytkaQuest: 'Bring Frodo to Edytka',
      wesoly0: ['Ho ho... easy, this is not a carol, just my walk through the woods.', 'Have you seen a reindeer? Or at least a frog in a hat?', 'I am moving on. If I get lost, I will call it a plan.'],
      renik: [
        ['Hey! DJ Renik at your service. Tonight at the pitch it is disco polo only.', 'Techno? Techno is for people who cannot dance in pairs.'],
        ['The best thing about disco polo? The chorus. Hear it once and it stays in your head till Sunday.', 'Then the whole village sings it. Even the priest. Quietly.'],
        ['I have 4000 tracks on my USB stick. All about love, eyes and holidays.', 'Every one is different. At least I think so.'],
        ['A synth, a kick on one, a clap on two. That is all you need for happiness.', 'The rest is extras. Like salt on cucumbers.'],
        ['Once I played a wedding till five in the morning. Uncle Zdzisiek danced with a chair.', 'The chair still remembers him.'],
        ['When I throw a party under the stars, you are first on the dance floor. Promise.', 'Just wear something shiny. Disco polo loves sequins.'],
      ],
      church: ['Church of the Nativity of the Virgin Mary. Bells at noon. Arek is late, as usual.'],
      rectory: ['The rectory. The priest waves from a window. Arek pretends to fix his sunglasses.'],
      cemetery: ['The parish cemetery. Arek takes his sunglasses off. For a moment.'],
      windmill: ['The "Koźlak" windmill. Older than anyone remembers. It creaks like it wants to talk.'],
      shop: ['The village shop. Tight aisles, full shelves: orangeade, bread, tins, dairy and sweets.', 'The shopkeeper knows every price by heart. And who bought the last doughnut.'],
      shopBuy: ['Shop lady: "Orangeade? Last bottle. For Marcin."', 'Arek got an ORANGEADE!'],
      bus: ['Bus stop. The bus has been... or will be. In Chłopków that is the same thing.'],
      river: ['The Melioranka river. Cold water, loud frogs, and summer is still long.'],
      kasia0: ["Arek! I'm baking the harvest-festival pie, but I need mushrooms for the filling.", 'Bring me 10 champignon mushrooms. They grow on green grass all around the village. Keep collecting apples separately - they are for the pie.'],
      kasia1: n => [`Only ${n}/10 mushrooms. The filling won't make itself!`],
      kasia2: ['10 mushrooms! You are irreplaceable. Well, almost.', "The pie will be ready tonight. I'll save you a slice."],
      kasia3: ['Pie is in the oven. The whole village smells of it!'],
      damian0: ['Dude, I lost my cap! I was running around the fields near here...', "Can you find it? I don't play without it."],
      damian1: ['Still nothing? Look in the yellow wheat, a few minutes from here.'],
      damian2: ['MY CAP! Arek, you legend.', "I owe you a sandwich. Well, half a sandwich."],
      damian3: ['With the cap on I play like Lewandowski. Almost.'],
      marcin0: ["I've been waiting for the bus for an hour. I'm dying of thirst.", "Could you run to the shop for an orangeade? I'll guard the bus stop."],
      marcin1: ['Orangeade. Shop. Quick. Please.'],
      marcin2: ["Orangeade! You're a lifesaver.", "The bus never came anyway. Who cares."],
      marcin3: ["One more sip... then I'm going for the tractor. Kidding. Probably."],
      grandpa0: ["What are you after, young man? The windmill isn't for sale.", 'Want to prove yourself? Help Kasia, Damian and Marcin first.'],
      grandpa1: n => [`You've helped ${n} of 3 friends. Come back when you're done.`],
      grandpa2: ['You helped the whole crew. Good job, Arek.', 'Here are the keys to my Ursus. Sundays only, and only to the hill.', "And don't tell Granny Irenka."],
      apple: 'APPLE', mushroom: 'MUSHROOM', trash: 'TRASH BAG', cap: "DAMIAN'S CAP", gotCap: ["Damian's cap! A bit dusty, but in one piece."],
      quests: ['10 mushrooms for Kasia', "Damian's cap", 'Orangeade for Marcin', 'Talk to Grandpa Zdzisiek'],
      churchIn: ['Inside the church. Cool, quiet, it smells of wax and flowers.'],
      altar: ['The altar in its white lace cloth. Arek touches nothing. This time.'],
      mary: ['Our Lady in a marble niche. Someone left fresh flowers and a wreath of wheat.'],
      glass: ['The stained glass glows like a phone screen. Only prettier.'],
      flowers: ['Flowers around a golden "100". The parish of Chłopków turns one hundred!'],
      confession: ['The confessional. Arek walks on quickly. Not today.'],
      pew: ['Wooden pews. Granny Irenka always sits in the third row, on the left.'],
      soltys0: ['Good morning, Arek. The harvest bread is ready, and blessed.', "Now we're only waiting for Kasia's apple pie. You'll help her, right?", 'I will keep order. After work, a cold beer and five minutes of quiet.'],
      soltys1: ["Kasia's pie is coming? Then the harvest festival is saved.", 'The sołtys sees everything, Arek. Good job.', 'For that kind of help, I raise a toast. Just do not make me speak before the band.'],
      soltysSecret: ['A village head must know what is happening in every corner of the village. Even this one.'],
      churchLabel: 'CHURCH', exitHint: '↓ EXIT', musicOn: 'BAND PLAYS!', musicOff: 'BAND QUIET',
      end1: 'YOU GOT THE URSUS KEYS', end2: 'TO BE CONTINUED: GRAND THEFT TRACTOR', end3: 'TIME',
      memoryTitle: 'CEMETERY ARCHIVE', memoryNext: 'ENTER — NEXT PHOTO · ESC — SKIP', memoryReturn: 'ENTER — RETURN TO THE VILLAGE',
      memoryNames: ['THE PROCESSION', 'REMEMBERING THE DEAD', 'A WOODEN CROSS'],
      memoryFacts: [
        'IN THE OLD PHOTO, VILLAGERS CARRY A COFFIN IN PROCESSION.',
        'A CROSS AND WREATH MARK THE GRAVE, SURROUNDED BY MOURNERS.',
        'A HANDMADE WOODEN CROSS WITH A PLAQUE MARKS THE GRAVE.',
      ],
    },
  }[LANG];
  const SPOT_R = { church: 90, rectory: 60, cemetery: 90, windmill: 60, shop: 60, bus: 40, river: 70 };
  const NPC_IDX = { kasia: 0, marcin: 1, damian: 2, grandpa: 3, halina: 4, kuba: 5, michal: 6, mateusz: 7, patryk: 8, wesoly_swiat: 10, edytka: 11, renik: 12 };   // 9 zbyszek (gen/build_npcs.py ORDER)
  // Walking speed follows the ground everywhere outdoors: asphalt is quickest, crops and the forest floor slow Arek down.
  // docs/img/map_terrain.png (1/4 scale, from osm/render_map.py): 0 grass, 60 paved, 100 dirt road, 160 field, 220 forest.
  const TERRAIN_CLASS = { 0: 'grass', 60: 'road', 100: 'track', 160: 'field', 220: 'forest' };
  const TERRAIN_SPEED = { grass: 1, road: 1.2, track: 1.1, field: .8, forest: .85 };
  let TERRAIN = null;
  function terrainAt(x, y) {
    if (!TERRAIN || ROOM) return 'grass';
    const gx = Math.max(0, Math.min(TERRAIN.w - 1, Math.floor(x / TERRAIN.k))), gy = Math.max(0, Math.min(TERRAIN.h - 1, Math.floor(y / TERRAIN.k)));
    return TERRAIN_CLASS[TERRAIN.v[gy * TERRAIN.w + gx]] || 'grass';
  }
  /* Extension hooks used by features.js (quiz, minigames). Each list holds callbacks:
     near(P) -> [{x,y,r,label,onInteract}]   extra things Arek can interact with
     npcTalk(id) -> true if handled           dialogue for NPCs defined outside this file
     update(dt)                               per-frame logic (runs while scene === 'play')
     world(push, S, inView)                   add y-sorted drawables: push(baseY, drawFn)
     hud(U, W, H)                             draw on top of the HUD
     key(e) / pointer(px, py) -> true if consumed (modal UIs)
     questLog(lines)                          push [text, done] rows into the quest log
     minimap(dot)                             draw markers: dot(x, y, colour)
     blocksPlayer() -> true to freeze normal movement (e.g. countdowns)
     speed(x, y) -> multiplier for Arek's walking speed at (x, y) (e.g. off-track slowdown in the race)
     busy() -> true while a quiz/minigame runs (the church door stays shut) */
  const HOOKS = { near: [], npcTalk: [], update: [], world: [], hud: [], key: [], pointer: [], questLog: [], minimap: [], blocksPlayer: [], busy: [], speed: [] };

  /* ---------- assets ---------- */
  const load = src => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error(src)); i.src = src; });
  const MEMORY_PATHS = ['img/memories/procession.png', 'img/memories/memorial.png', 'img/memories/wooden_cross.png'];
  let MAP, GROUND, OBJ, SOLID, SPR, PLAYER_SHEETS = {}, MINI, NPCIMG, DOGIMG, FRODO_IDLE = null, TRASH_IMG = null, ITEMS, SPLASH = null, MEMORY_ART = [], FOREST_STATS = null;
  let ROOM = null, OUT = null, trans = null, shopGame = null;   // OUT: the village to return to

  /* ---------- state ---------- */
  const P = { x: 0, y: 0, dir: 'down', moving: false, step: 0, z: 0, air: false, jt: 0, jx: 0, jy: 0, ox: 0, oy: 0, land: 1 };
  const FRODO = { x: 0, y: 0, dir: 'down', moving: false, step: 0, stuck: 0, idleAnim: 0, action: 'idle', wander: 0, wanderX: 0, wanderY: 0, wanderWait: 4, returning: false, returningT: 0, trailI: -1, chase: null };
  const BALES = [];
  const BALE_ACTORS = [P, FRODO];
  const trail = [];   // Arek's recent footsteps: Frodo walks them when the direct way is blocked (he never teleports in view)
  const JUMP_T = .48, JUMP_H = 15, DIRV = { up: [0, -1], up_right: [.707, -.707], right: [1, 0], down_right: [.707, .707], down: [0, 1], down_left: [-.707, .707], left: [-1, 0], up_left: [-.707, -.707] };
  const DIR8 = ['right', 'down_right', 'down', 'down_left', 'left', 'up_left', 'up', 'up_right'];
  const DIR4 = { down: 'down', down_right: 'right', right: 'right', up_right: 'up', up: 'up', up_left: 'left', left: 'left', down_left: 'down' };
  const direction8 = (x, y) => DIR8[(Math.round(Math.atan2(y, x) / (Math.PI / 4)) + 8) % 8];
  const cardinalDir = d => DIR4[d] || d || 'down';
  const CLOUDS = Array.from({ length: 7 }, (_, i) => ({ x: (i * 733 + 260) % 4675, y: 220 + (i * 907) % 5800, speed: 3 + (i % 3) * 1.4, scale: .75 + (i % 4) * .12, alpha: .07 + (i % 3) * .018 }));
  const CHAR_H = 40, SPEED = 110, HIT = { w: 14, h: 6 };
  let scene = 'title', talkClosedAt = -9, talk = null, talkT = 0, time = 0, dust = [], showMap = false, fx = [], toast = null;
  // Q.kasia/damian/marcin: 0 not met, 1 active, 2 done. Q.grandpa: 0/1 met, 2 got keys.
  const freshQ = () => ({ playerName: '', kasia: 0, damian: 0, marcin: 0, grandpa: 0, halina: 0, edytka: 0, edytkaN: 0, quiz: {}, mg: {}, apples: [], mushroomSpots: [], mushrooms: [], trashSpots: [], trash: [], cap: false, orange: false, playTime: 0 });
  function sanitizePlayerName(value) {
    return Array.from(String(value || '').normalize('NFC').replace(/[^\p{L}\p{N} _'-]/gu, '').replace(/\s+/g, ' ').trim()).slice(0, 20).join('');
  }
  let Q = freshQ();
  let hasSave = false, memoryIndex = 0, savedDog = null;
  const keys = new Set();
  const joy = { active: false, id: null, cx: 0, cy: 0, x: 0, y: 0 };
  const pointer = { x: 0, y: 0, seen: false, kind: null };   // last pointer position in canvas px + its type ('mouse'/'touch'/'pen'); the world hover label shows only for a real mouse
  const clickTarget = { active: false, x: 0, y: 0 };
  const mapCursor = { seen: false, x: 0, y: 0 };

  function npcSavePositions() {
    return ITEMS && ITEMS.npcs ? ITEMS.npcs.filter(n => !n.secret).map(n => ({ id: n.id, x: n.x, y: n.y })) : [];
  }
  function save() { try { localStorage.setItem(SAVE_KEY, JSON.stringify({ Q, x: ROOM ? OUT.x : P.x, y: ROOM ? OUT.y : P.y, dog: ROOM ? OUT.dog : { x: FRODO.x, y: FRODO.y }, npcs: npcSavePositions() })); } catch (e) { } }
  function loadSave() {
    try {
      const s = JSON.parse(localStorage.getItem(SAVE_KEY) || 'null');
      if (s && s.Q) {
        Q = Object.assign(Q, s.Q);
        Q.playerName = sanitizePlayerName(Q.playerName);
        if (Q.playerName.toUpperCase() === 'AREK') Q.playerName = '';
        if (!Q.playerName) return false;
        P.x = s.x; P.y = s.y;
        if (s.dog && Number.isFinite(s.dog.x) && Number.isFinite(s.dog.y)) savedDog = { x: s.dog.x, y: s.dog.y };
        if (Array.isArray(s.npcs) && ITEMS && ITEMS.npcs) for (const saved of s.npcs) {
          const n = ITEMS.npcs.find(v => v.id === saved.id && !v.secret && !NPC_FIXED.has(v.id));
          if (n && Number.isFinite(saved.x) && Number.isFinite(saved.y)) { n.x = saved.x; n.y = saved.y; }
        }
        return true;
      }
    } catch (e) { }
    return false;
  }
  const appleCount = () => Q.apples.length;
  const mushroomCount = () => Array.isArray(Q.mushrooms) ? Q.mushrooms.length : 0;
  const trashCount = () => Array.isArray(Q.trash) ? Q.trash.length : 0;
  const questsDone = () => (Q.kasia === 2) + (Q.damian === 2) + (Q.marcin === 2);

  // Keep quest roles in their useful parts of the map while varying the exact spot.
  // Homes are captured from items.json after loading, so this remains correct when the map grows.
  const NPC_ZONE_RADIUS = { kasia: 520, marcin: 420, damian: 500, grandpa: 300, halina: 420, edytka: 99999 };   // Edytka: anywhere on the map
  let NPC_HOME = {};
  let reachableMask = null, reachableStep = 12, reachableW = 0;
  function npcWalkable(x, y) {
    const l = x - HIT.w / 2, r = x + HIT.w / 2, t = y - HIT.h;
    return ![solidAt(l, y), solidAt(r, y), solidAt(l, t), solidAt(r, t), solidAt(x, y), solidAt(x, t)].some(Boolean);
  }
  function buildReachableMask() {
    reachableW = Math.ceil(MAP.w / reachableStep);
    const h = Math.ceil(MAP.h / reachableStep), total = reachableW * h;
    reachableMask = new Uint8Array(total);
    const walk = (gx, gy) => {
      if (gx < 0 || gy < 0 || gx >= reachableW || gy >= h) return false;
      const cx = gx * reachableStep + reachableStep / 2, cy = gy * reachableStep + reachableStep / 2;
      for (const dx of [-4, 0, 4]) for (const dy of [-4, 0, 4]) if (npcWalkable(cx + dx, cy + dy)) return true;
      return false;
    };
    let sx = Math.floor(MAP.spawn.x / reachableStep), sy = Math.floor(MAP.spawn.y / reachableStep);
    for (let r = 0; r < 20 && !walk(sx, sy); r++) { sx += r % 2 ? 1 : -1; sy += r % 3 ? 0 : 1; }
    if (!walk(sx, sy)) return;
    const q = new Int32Array(total), start = sy * reachableW + sx; let head = 0, tail = 0;
    q[tail++] = start; reachableMask[start] = 1;
    while (head < tail) {
      const at = q[head++], x = at % reachableW, y = (at / reachableW) | 0;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy, ni = ny * reachableW + nx;
        if (walk(nx, ny) && !reachableMask[ni]) { reachableMask[ni] = 1; q[tail++] = ni; }
      }
    }
  }
  function samplePlayerSpawn() {
    buildReachableMask();
    if (!reachableMask) return { x: MAP.spawn.x, y: MAP.spawn.y };
    const candidates = [];
    for (let i = 0; i < reachableMask.length; i++) {
      if (!reachableMask[i]) continue;
      const x = (i % reachableW) * reachableStep + reachableStep / 2;
      const y = Math.floor(i / reachableW) * reachableStep + reachableStep / 2;
      if (npcWalkable(x, y)) candidates.push({ x, y });
    }
    return candidates.length ? candidates[(Math.random() * candidates.length) | 0] : { x: MAP.spawn.x, y: MAP.spawn.y };
  }
  function ensureMushrooms() {
    const old = Array.isArray(Q.mushroomSpots) && Q.mushroomSpots.length === MUSHROOMS_TOTAL && Q.mushroomSpots.every(p => p && Number.isFinite(p.x) && Number.isFinite(p.y));
    if (!old) {
      buildReachableMask();
      const spots = [], near = (x, y, r) => spots.some(p => Math.hypot(x - p.x, y - p.y) < r);
      const accept = (x, y, strict) => {
        const gx = Math.floor(x / reachableStep), gy = Math.floor(y / reachableStep);
        if (!reachableMask || !reachableMask[gy * reachableW + gx] || !npcWalkable(x, y)) return false;
        if (!['grass', 'forest'].includes(terrainAt(x, y))) return false;
        if (Math.hypot(x - P.x, y - P.y) < 120 || near(x, y, strict ? 120 : 48)) return false;
        if ((ITEMS.apples || []).some(a => Math.hypot(x - a.x, y - a.y) < 36)) return false;
        if ((ITEMS.npcs || []).some(n => Math.hypot(x - n.x, y - n.y) < 48)) return false;
        return true;
      };
      for (const strict of [true, false]) {
        for (let tries = 0; tries < 60000 && spots.length < MUSHROOMS_TOTAL; tries++) {
          const i = (Math.random() * reachableMask.length) | 0;
          if (!reachableMask[i]) continue;
          const x = (i % reachableW) * reachableStep + reachableStep / 2, y = Math.floor(i / reachableW) * reachableStep + reachableStep / 2;
          if (accept(x, y, strict)) spots.push({ x, y });
        }
      }
      // The generated map has ample green reachable terrain; this fallback only
      // handles a future map revision where the strict terrain filter is sparse.
      if (spots.length < MUSHROOMS_TOTAL) for (let i = 0; i < reachableMask.length && spots.length < MUSHROOMS_TOTAL; i++) {
        if (!reachableMask[i]) continue;
        const x = (i % reachableW) * reachableStep + reachableStep / 2, y = Math.floor(i / reachableW) * reachableStep + reachableStep / 2;
        if (npcWalkable(x, y) && !near(x, y, 32)) spots.push({ x, y });
      }
      Q.mushroomSpots = spots.slice(0, MUSHROOMS_TOTAL);
      Q.mushrooms = [];
      return true;
    }
    Q.mushrooms = Array.isArray(Q.mushrooms) ? Q.mushrooms.filter(i => Number.isInteger(i) && i >= 0 && i < MUSHROOMS_TOTAL).filter((i, n, a) => a.indexOf(i) === n) : [];
    return false;
  }
  // Trash bags: a plain collectible like apples and mushrooms. The fixed litter spots from items.json
  // (by the cemetery and the southern shop) come first, the rest are scattered by roads and on grass.
  function ensureTrash() {
    if (Array.isArray(Q.trashSpots) && Q.trashSpots.length > TRASH_TOTAL) Q.trashSpots = Q.trashSpots.slice(0, TRASH_TOTAL);   // old saves had 12 bags
    const ok = Array.isArray(Q.trashSpots) && Q.trashSpots.length === TRASH_TOTAL && Q.trashSpots.every(p => p && Number.isFinite(p.x) && Number.isFinite(p.y));
    if (ok) {
      Q.trash = Array.isArray(Q.trash) ? Q.trash.filter(i => Number.isInteger(i) && i >= 0 && i < TRASH_TOTAL).filter((i, n, a) => a.indexOf(i) === n) : [];
      return false;
    }
    buildReachableMask();
    const spots = (ITEMS.trash || []).map(t => ({ x: t.x, y: t.y })).slice(0, TRASH_TOTAL);
    const near = (x, y, r) => spots.some(p => Math.hypot(x - p.x, y - p.y) < r)
      || (Q.mushroomSpots || []).some(p => Math.hypot(x - p.x, y - p.y) < 40)
      || (ITEMS.apples || []).some(a => Math.hypot(x - a.x, y - a.y) < 36)
      || (ITEMS.npcs || []).some(n => Math.hypot(x - n.x, y - n.y) < 48);
    for (const strict of [true, false]) {
      for (let tries = 0; tries < 60000 && spots.length < TRASH_TOTAL; tries++) {
        const i = (Math.random() * reachableMask.length) | 0;
        if (!reachableMask[i]) continue;
        const x = (i % reachableW) * reachableStep + reachableStep / 2, y = Math.floor(i / reachableW) * reachableStep + reachableStep / 2;
        if (!npcWalkable(x, y) || !['grass', 'road', 'track'].includes(terrainAt(x, y))) continue;
        if (Math.hypot(x - P.x, y - P.y) < 120 || near(x, y, strict ? 180 : 60)) continue;
        spots.push({ x, y });
      }
    }
    Q.trashSpots = spots.slice(0, TRASH_TOTAL);
    Q.trash = [];
    return true;
  }
  function npcPositionAllowed(x, y, occupied, requireReachable = true) {
    if (!npcWalkable(x, y)) return false;
    const gx = Math.floor(x / reachableStep), gy = Math.floor(y / reachableStep);
    if (requireReachable && reachableMask && !reachableMask[gy * reachableW + gx]) return false;
    if (Math.hypot(x - P.x, y - P.y) < 90) return false;
    for (const n of occupied) if (Math.hypot(x - n.x, y - n.y) < 90) return false;
    for (const p of MAP.pois || []) if (Math.hypot(x - p.x, y - p.y) < (SPOT_R[p.key] || 50) + 35) return false;
    for (const b of ITEMS.boards || []) if (Math.hypot(x - b.x, y - b.y) < 45) return false;
    for (const l of ITEMS.landmarks || []) if (Math.hypot(x - l.x, y - l.y) < 55) return false;
    for (const a of ITEMS.apples || []) if (Math.hypot(x - a.x, y - a.y) < 28) return false;
    if (ITEMS.cap && Math.hypot(x - ITEMS.cap.x, y - ITEMS.cap.y) < 28) return false;
    return true;
  }
  function sampleNpcPosition(npc, occupied) {
    const home = NPC_HOME[npc.id] || npc, poi = npc.id === 'grandpa' ? MAP.pois.find(p => p.key === 'windmill') : npc.id === 'halina' ? MAP.pois.find(p => p.key === 'church') : null;
    const anchor = poi || home, radius = NPC_ZONE_RADIUS[npc.id] || 500;
    const z = { x0: Math.max(40, anchor.x - radius), y0: Math.max((MAP.top || 40) + 30, anchor.y - radius), x1: Math.min(MAP.w - 40, anchor.x + radius), y1: Math.min(MAP.h - 40, anchor.y + radius) };
    for (let i = 0; i < 1600; i++) {
      const x = z.x0 + Math.random() * (z.x1 - z.x0), y = z.y0 + Math.random() * (z.y1 - z.y0);
      if (npcPositionAllowed(x, y, occupied)) return { x, y };
    }
    // Some narrow rural paths disappear on the coarse reachability grid. Keep the
    // collision/marker/player checks, but do not strand a role at its old fixed point.
    for (let i = 0; i < 1600; i++) {
      const x = z.x0 + Math.random() * (z.x1 - z.x0), y = z.y0 + Math.random() * (z.y1 - z.y0);
      if (npcPositionAllowed(x, y, occupied, false)) return { x, y };
    }
    for (let y = z.y0; y <= z.y1; y += 18) for (let x = z.x0; x <= z.x1; x += 18) if (npcPositionAllowed(x, y, occupied)) return { x, y };
    return { x: npc.x, y: npc.y };
  }
  // These roles live at a fixed spot of the level (items.json) and are never shuffled; old saves are pulled back to it.
  const NPC_FIXED = new Set(['damian', 'marcin', 'kuba', 'michal', 'mateusz', 'patryk', 'wesoly_swiat', 'edytka', 'renik', 'soltys']);
  function randomizeNpcPositions() {
    if (!MAP || !ITEMS || !SOLID) return;
    buildReachableMask();
    const occupied = ITEMS.npcs.filter(n => n.secret || NPC_FIXED.has(n.id)).map(n => ({ x: n.x, y: n.y }));
    for (const n of ITEMS.npcs) {
      if (n.secret || NPC_FIXED.has(n.id)) continue; // Sołtys is hidden; fixed roles keep their level spot.
      const p = sampleNpcPosition(n, occupied); n.x = p.x; n.y = p.y; occupied.push(n);
    }
  }
  // Marcin loiters ("kręci się") around the bus stop: slow random strolls inside a small radius, paused while talking.
  const WANDER = {
    kasia: { r: 42, speed: 20 }, marcin: { r: 60, speed: 26 }, damian: { r: 48, speed: 22 },
    grandpa: { r: 34, speed: 16 }, halina: { r: 42, speed: 18 }, edytka: { r: 54, speed: 24 },
    kuba: { r: 36, speed: 18 }, michal: { r: 38, speed: 20 }, mateusz: { r: 44, speed: 20 }, patryk: { r: 44, speed: 20 },
    wesoly_swiat: { r: 72, speed: 20 }, renik: { r: 56, speed: 24 },
  };
  const wanderState = {};
  function updateWanderers(dt) {
    if (!ITEMS || ROOM) return;
    for (const n of ITEMS.npcs) {
      const cfg = WANDER[n.id], home = NPC_HOME[n.id]; if (!cfg || !home) continue;
      const w = wanderState[n.id] || (wanderState[n.id] = { tx: n.x, ty: n.y, wait: 1 + Math.random() * 2, moving: false });
      if (n.id === 'edytka' && Q.edytka === 1) continue; // keep the quest anchor stable while Frodo visits
      if (talk && Math.hypot(P.x - n.x, P.y - n.y) < 70) { w.moving = false; continue; }
      if (Math.hypot(P.x - n.x, P.y - n.y) < 30) { w.moving = false; continue; }   // stand still when Arek walks up
      if (!w.moving) {
        w.wait -= dt; if (w.wait > 0) continue;
        for (let i = 0; i < 12; i++) {
          const a = Math.random() * Math.PI * 2, d = Math.random() * cfg.r, tx = home.x + Math.cos(a) * d, ty = home.y + Math.sin(a) * d;
          if (npcWalkable(tx, ty)) { w.tx = tx; w.ty = ty; w.moving = true; break; }
        }
        w.wait = 1.5 + Math.random() * 3; continue;
      }
      const dx = w.tx - n.x, dy = w.ty - n.y, d = Math.hypot(dx, dy);
      if (d < 2) { w.moving = false; continue; }
      const st = Math.min(d, cfg.speed * dt), nx = n.x + dx / d * st, ny = n.y + dy / d * st;
      if (npcWalkable(nx, ny) && Math.hypot(nx - P.x, ny - P.y) > 18) { n.x = nx; n.y = ny; n.face = Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? 'left' : 'right') : (dy < 0 ? 'up' : 'down'); }
      else w.moving = false;
    }
  }

  /* ---------- input ---------- */
  function cancelClickMove() { clickTarget.active = false; }
  let namePrompt = null;
  function requestPlayerName(fresh = true) {
    if (namePrompt || scene !== 'title') return;
    const overlay = document.createElement('div'); overlay.id = 'player-name-overlay';
    Object.assign(overlay.style, { position: 'fixed', inset: '0', zIndex: '20', display: 'grid', placeItems: 'center', padding: '20px', boxSizing: 'border-box', background: 'rgba(5,8,25,.78)', fontFamily: 'sans-serif', touchAction: 'auto' });
    const form = document.createElement('form');
    Object.assign(form.style, { width: 'min(420px, 100%)', boxSizing: 'border-box', padding: '24px', border: '3px solid #ffd21f', background: '#10163a', color: '#f5f0e0', textAlign: 'center', display: 'grid', gap: '16px' });
    const label = document.createElement('label'); label.htmlFor = 'player-name-input'; label.textContent = LANG === 'pl' ? 'JAK MASZ NA IMIĘ?' : 'WHAT IS YOUR NAME?';
    const input = document.createElement('input'); input.id = 'player-name-input'; input.name = 'playerName'; input.type = 'text'; input.maxLength = 80; input.autocomplete = 'nickname'; input.placeholder = LANG === 'pl' ? 'Wpisz imię' : 'Enter a name'; input.value = fresh ? '' : heroName(); input.required = true;
    Object.assign(input.style, { width: '100%', boxSizing: 'border-box', padding: '14px', fontSize: '18px', border: '2px solid #c8cee0', borderRadius: '4px' });
    const submit = document.createElement('button'); submit.id = 'player-name-submit'; submit.type = 'submit'; submit.textContent = LANG === 'pl' ? 'ZACZNIJ GRĘ' : 'START GAME';
    Object.assign(submit.style, { padding: '14px', border: '0', borderRadius: '4px', background: '#ffd21f', color: '#10163a', fontWeight: 'bold', fontSize: '16px', touchAction: 'manipulation' });
    const error = document.createElement('div'); error.setAttribute('aria-live', 'polite'); error.style.color = '#ff9b8f';
    form.append(label, input, submit, error); overlay.appendChild(form);
    overlay.addEventListener('pointerdown', e => e.stopPropagation());
    form.addEventListener('submit', e => {
      e.preventDefault();
      const playerName = sanitizePlayerName(input.value);
      if (!playerName) { error.textContent = LANG === 'pl' ? 'Wpisz niepuste imię.' : 'Please enter a non-blank name.'; input.focus(); return; }
      overlay.remove(); namePrompt = null;
      if (fresh) startGame(true, playerName);
      else { Q.playerName = playerName; save(); }
    });
    document.body.appendChild(overlay); namePrompt = overlay; input.focus();
  }
  function characterButtonBounds() {
    const W = cvs.width, H = cvs.height, U = Math.min(W, H * 1.6) / 100;
    const scale = W / Math.max(1, innerWidth);
    const size = Math.max(U * 7, 48 * scale), gap = U * 1.5;
    const n = PLAYABLE_CHARACTERS.length, rows = Math.ceil(n / 2);
    // keep every row above the bottom prompt strip (H - 9.5U) on short landscape screens
    const gridW = size * 2 + gap, gridX = (W - gridW) / 2, gridY = Math.min(H * .45, H - U * 10.3 - rows * size - (rows - 1) * gap);
    return PLAYABLE_CHARACTERS.map((id, i) => ({   // 2 columns; a lone last button is centred on its own row
      id, x: i === n - 1 && n % 2 ? (W - size) / 2 : gridX + (i % 2) * (size + gap), y: gridY + Math.floor(i / 2) * (size + gap), w: size, h: size,
    }));
  }
  function selectCharacter(char) {
    if (!PLAYABLE_CHARACTERS.includes(char)) return;
    selectedCharacter = char;
    try { localStorage.setItem(CHARACTER_KEY, char); } catch (e) { }
    if (PLAYER_SHEETS[char]) SPR = PLAYER_SHEETS[char];
  }
  function startGame(fresh, playerName) {
    if (fresh) {
      if (!playerName) { requestPlayerName(true); return; }
      try { localStorage.removeItem(SAVE_KEY); } catch (e) { }
      Q = freshQ(); Q.playerName = sanitizePlayerName(playerName);
      const debugX = params.has('x') && params.has('y') ? Number(params.get('x')) : NaN, debugY = params.has('x') && params.has('y') ? Number(params.get('y')) : NaN;
      const spawn = Number.isFinite(debugX) && Number.isFinite(debugY) ? { x: debugX, y: debugY } : samplePlayerSpawn();
      P.x = spawn.x; P.y = spawn.y; randomizeNpcPositions(); ensureMushrooms(); ensureTrash(); unstick(); placeFrodoNearArek(); camX = P.x; camY = P.y; hasSave = true; save();
    }
    if (!fresh && !Q.playerName) { requestPlayerName(false); return; }
    scene = 'play';
  }
  addEventListener('keydown', e => {
    if (namePrompt) return;
    keys.add(e.code);
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(e.code)) e.preventDefault();
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'KeyW', 'KeyA', 'KeyS', 'KeyD'].includes(e.code)) cancelClickMove();
    if (scene === 'title') {
      if (e.code === 'KeyN') hasSave ? requestPlayerName(false) : startGame(true);
      else if (e.code === 'KeyR') startGame(true);
      else if (e.code === 'Enter' || e.code === 'Space') startGame(!hasSave);
      return;
    }
    if (scene === 'end') {
      if (e.code === 'Escape') scene = 'play';
      else if (e.code === 'Enter' || e.code === 'Space') {
        if (memoryIndex < T.memoryFacts.length - 1) memoryIndex++;
        else scene = 'play';
      }
      return;
    }
    if (!talk && HOOKS.key.some(f => f(e))) return;
    if (e.code === 'Escape' && scene === 'play' && !talk && !shopGame) { save(); showMap = false; mapCursor.seen = false; keys.clear(); scene = 'title'; return; }
    if (e.code === 'KeyX' || e.code === 'KeyJ') jump();
    else if (e.code === 'Space') { if (talk || nearThing()) interact(); else jump(); }
    else if (e.code === 'KeyE' || e.code === 'Enter') interact();
    if (e.code === 'KeyM') { showMap = !showMap; cancelClickMove(); if (!showMap) mapCursor.seen = false; }
  });
  addEventListener('keyup', e => keys.delete(e.code));
  const toCanvas = e => { const r = cvs.getBoundingClientRect(); return [(e.clientX - r.left) / r.width * cvs.width, (e.clientY - r.top) / r.height * cvs.height]; };
  function mapLayout() {
    const W = cvs.width, H = cvs.height, U = Math.min(W, H * 1.6) / 100;
    const mw = Math.min(W * .8, H * .8 * MAP.w / MAP.h), mh = mw * MAP.h / MAP.w;
    return { mx: (W - mw) / 2, my: (H - mh) / 2, mw, mh, U };
  }
  function mapPoint(px, py) {
    if (!showMap) return null;
    const { mx, my, mw, mh } = mapLayout();
    if (px < mx || px > mx + mw || py < my || py > my + mh) return null;
    return { x: Math.max(0, Math.min(MAP.w, (px - mx) / mw * MAP.w)), y: Math.max(0, Math.min(MAP.h, (py - my) / mh * MAP.h)) };
  }
  const MAP_PLACE_NAMES = {
    shop: 'SKLEP', windmill: 'WIATRAK KOŹLAK', cemetery: 'CMENTARZ', rectory: 'PLEBANIA', church: 'KOŚCIÓŁ', river: 'RZEKA MELIORANKA',
    corral: 'ŚWINKA PEPA', track: 'TOR WYŚCIGOWY', meadow: 'PASTWISKO', range: 'PPM STRZELECTWO', football_pitch: 'BOISKO', jazz: 'JAZZ W STODOLE', gravel: 'WAPNICA',
  };
  function mapPlaceCandidates() {
    if (!MAP) return [];
    const out = [];
    for (const l of MAP.landmarks || []) if (l.name && Number.isFinite(l.x) && Number.isFinite(l.y)) out.push({ name: String(l.name).toUpperCase(), x: l.x, y: l.y });
    for (const p of MAP.pois || []) {
      const name = p.name || MAP_PLACE_NAMES[p.key];
      if (name && Number.isFinite(p.x) && Number.isFinite(p.y)) out.push({ name: String(name).toUpperCase(), x: p.x, y: p.y });
    }
    const named = [
      ['corral', MAP.corral && MAP.corral.cx, MAP.corral && MAP.corral.cy],
      ['track', MAP.track && MAP.track.cx, MAP.track && MAP.track.cy],
      ['meadow', MAP.meadow && (MAP.meadow.x0 + MAP.meadow.x1) / 2, MAP.meadow && (MAP.meadow.y0 + MAP.meadow.y1) / 2],
      ['range', MAP.range && MAP.range.x, MAP.range && MAP.range.y],
      ['football_pitch', MAP.football_pitch && MAP.football_pitch.cx, MAP.football_pitch && MAP.football_pitch.cy],
      ['jazz', MAP.jazz && MAP.jazz.x, MAP.jazz && MAP.jazz.y],
      ['gravel', MAP.gravel && MAP.gravel.x, MAP.gravel && MAP.gravel.y],
    ];
    for (const [key, x, y] of named) if (Number.isFinite(x) && Number.isFinite(y)) out.push({ name: MAP_PLACE_NAMES[key], x, y });
    for (const s of MAP.shrines || []) if (Number.isFinite(s.x) && Number.isFinite(s.y)) out.push({ name: 'KAPLICZKA', x: s.x, y: s.y });
    return out;
  }
  function mapPlaceAt(x, y) {
    let best = null, bd = Infinity;
    for (const place of mapPlaceCandidates()) {
      const d = Math.hypot(x - place.x, y - place.y);
      if (d < bd) { bd = d; best = place; }
    }
    return best && bd <= Math.max(180, Math.min(MAP.w, MAP.h) * .045) ? best : null;
  }
  const mapPlaceName = (x, y) => { const p = mapPlaceAt(Number(x), Number(y)); return p ? p.name : null; };
  const TERRAIN_NAMES = LANG === 'pl'
    ? { grass: 'ŁĄKA', road: 'DROGA', track: 'DROGA POLNA', field: 'POLE', forest: 'LAS' }
    : { grass: 'MEADOW', road: 'ROAD', track: 'DIRT TRACK', field: 'FIELD', forest: 'FOREST' };
  // Hover label for the big map: the player, Frodo, people, then named places, then the ground type.
  function mapHoverLabel(x, y, pickR) {
    const near = (px, py) => Math.hypot(x - px, y - py) <= pickR;
    if (near(P.x, P.y)) return heroName().toUpperCase();
    if (near(FRODO.x, FRODO.y)) return 'FRODO';
    let best = null, bd = pickR;
    for (const n of ITEMS.npcs || []) if (!n.secret && T.names[n.id]) { const d = Math.hypot(x - n.x, y - n.y); if (d <= bd) { bd = d; best = T.names[n.id]; } }
    if (best) return String(best).toUpperCase();
    const place = mapPlaceAt(x, y);
    if (place) return place.name;
    const t = terrainAt(x, y);
    return TERRAIN_NAMES[t] || null;
  }
  /* ---------- world hover picker (A02) ----------
     Side-effect-free read-only query: which small hover label belongs to the
     world point (wx, wy)? Unlike mapHoverLabel() (big M-map floating box), it
     works in the normal world and mirrors the y-sorted render: among all
     objects whose draw extent (map px, unzoomed) contains the point, the
     front-most wins - highest baseline, ties go to the layer drawn last.
     Types owned by world-life.js (cars, tractors, animals) are read through
     its read-only hitShapes() adapter, never duplicated here. */
  const WORLD_HOVER = LANG === 'pl'
    ? { building: 'BUDYNEK', tree: 'DRZEWO', bale: 'BELA', car: 'SAMOCHÓD', tractor: 'TRAKTOR',
        animal: { mouse: 'MYSZ', bird: 'PTAK', chicken: 'KURA', dog: 'PIES', boar: 'DZIK', hare: 'ZAJĄC', pig: 'ŚWINIA', fox: 'LIS', stork: 'BOCIAN', butterfly: 'MOTYL' } }
    : { building: 'BUILDING', tree: 'TREE', bale: 'BALE', car: 'CAR', tractor: 'TRACTOR',
        animal: { mouse: 'MOUSE', bird: 'BIRD', chicken: 'CHICKEN', dog: 'DOG', boar: 'BOAR', hare: 'HARE', pig: 'PIG', fox: 'FOX', stork: 'STORK', butterfly: 'BUTTERFLY' } };
  const worldAnimalLabel = kind => (WORLD_HOVER.animal[kind] || String(kind).toUpperCase());
  // Hit boxes in map pixels, mirroring the draw functions' sprite sizes / art offsets.
  const EXTENT_HERO = { halfW: 10, top: 40, bottom: 5 };   // drawArek: CHAR_H 40, ~20 px wide
  const EXTENT_FRODO = { halfW: 13, top: 27, bottom: 1 };  // drawFrodo: 27 px box
  const EXTENT_NPC = { halfW: 18, top: 46, bottom: 2 };    // drawNpc: atlas cell scaled to ~40 px
  const EXTENT_BALE = { halfW: 12, top: 16, bottom: 1 };  // drawBale: 24x16 art
  const EXTENT_PICKUP = { halfW: 7, top: 13, bottom: 1 };  // drawApple/drawMushroom: 13x12 art
  const EXTENT_TRASH = { halfW: 9, top: 17, bottom: 2 };   // drawTrashBag: 16 px bag above the ground
  function worldPickAt(wx, wy) {
    if (!MAP || !ITEMS || ROOM) return null;   // rooms (church/shop) keep the coordinates-only HUD
    const hit = e => Math.abs(wx - e.x) <= e.halfW && wy >= e.y - e.top && wy <= e.y + e.bottom;
    let best = null;
    const take = cand => { if (!best || cand.base >= best.base) best = cand; };   // drawn-last wins ties
    // Iterate in the render() push order (back-most first); with the >= rule
    // above, every equal-baseline tie goes to the front-most layer that is
    // actually drawn on top - the mirror image of the y-sort at render().
    for (const o of MAP.objects || []) {
      // Static scenery: wide sprites are buildings, tall-narrow sprites are trees; other props stay anonymous.
      // Wayside-shrine sprites sit at MAP.shrines positions - label them with the same
      // KAPLICZKA name the big map uses instead of mislabelling them as trees.
      const cx = o.x + o.w / 2;
      const shrine = (MAP.shrines || []).find(s => Math.abs(s.x - cx) <= 24 && s.y >= o.base - o.h && s.y <= o.base + 2);
      if (shrine) {
        if (hit({ x: shrine.x, y: shrine.y, halfW: 16, top: 64, bottom: 1 })) take({ label: 'KAPLICZKA', kind: 'shrine', x: shrine.x, y: shrine.y, base: shrine.y });
        continue;
      }
      const box = { x: cx, y: o.base, halfW: o.w / 2, top: o.h, bottom: 1 };
            // C06: generated trees carry kind:'tree' - never classify a tree by sprite
            // dims (broad oak crowns w >= 40/h >= 30 used to read as BUILDING and the
            // remaining trees fell through to the anonymous ground label).
            if (o.kind === 'tree') { if (hit(box)) take({ label: WORLD_HOVER.tree, kind: 'tree', x: o.x, y: o.y, base: o.base }); continue; }
            if (o.w >= 40 && o.h >= 30 && o.w <= 200) { if (hit(box)) take({ label: WORLD_HOVER.building, kind: 'building', x: o.x, y: o.y, base: o.base }); }
            else if (o.w < 40 && o.h >= 40) { if (hit(box)) take({ label: WORLD_HOVER.tree, kind: 'tree', x: o.x, y: o.y, base: o.base }); }
    }
    ITEMS.apples.forEach((a, i) => {
      if (Q.apples.includes(i)) return;   // picked-up apples are no longer drawn
      if (hit(Object.assign({ x: a.x, y: a.y }, EXTENT_PICKUP))) take({ label: T.apple, kind: 'apple', x: a.x, y: a.y, base: a.y });
    });
    (Q.mushroomSpots || []).forEach((m, i) => {
      if ((Q.mushrooms || []).includes(i)) return;
      if (hit(Object.assign({ x: m.x, y: m.y }, EXTENT_PICKUP))) take({ label: T.mushroom, kind: 'mushroom', x: m.x, y: m.y, base: m.y });
    });
    (Q.trashSpots || []).forEach((t, i) => {
      if ((Q.trash || []).includes(i)) return;
      if (hit(Object.assign({ x: t.x, y: t.y }, EXTENT_TRASH))) take({ label: T.trash, kind: 'trash', x: t.x, y: t.y, base: t.y });
    });
    // cap is pushed after the pickups in render(), so it draws on top - keep it last here too.
    if (!Q.cap && hit(Object.assign({ x: ITEMS.cap.x, y: ITEMS.cap.y }, EXTENT_PICKUP))) take({ label: T.cap, kind: 'cap', x: ITEMS.cap.x, y: ITEMS.cap.y, base: ITEMS.cap.y });
    for (const b of BALES) if (hit(Object.assign({ x: b.x, y: b.y }, EXTENT_BALE))) take({ label: WORLD_HOVER.bale, kind: 'bale', x: b.x, y: b.y, base: b.y });
    for (const n of ITEMS.npcs || []) {
      if (n.secret || !T.names[n.id]) continue;   // private people stay anonymous
      if (hit(Object.assign({ x: n.x, y: n.y }, EXTENT_NPC))) take({ label: String(T.names[n.id]).toUpperCase(), kind: 'npc', x: n.x, y: n.y, base: n.y });
    }
    if (hit(Object.assign({ x: P.x, y: P.y }, EXTENT_HERO))) take({ label: heroName().toUpperCase(), kind: 'hero', x: P.x, y: P.y, base: P.y });
    if (hit(Object.assign({ x: FRODO.x, y: FRODO.y }, EXTENT_FRODO))) take({ label: 'FRODO', kind: 'frodo', x: FRODO.x, y: FRODO.y, base: FRODO.y });
    if (window.__worldLife && typeof window.__worldLife.hitShapes === 'function') {
      for (const s of window.__worldLife.hitShapes()) {
        if (!hit(s)) continue;
        take({ label: s.kind === 'car' ? WORLD_HOVER.car : s.kind === 'tractor' ? WORLD_HOVER.tractor : worldAnimalLabel(s.kind), kind: s.kind, x: s.x, y: s.y, base: s.base });
      }
    }
    if (best) return best;
    const t = terrainAt(wx, wy);
    return { label: TERRAIN_NAMES[t] || null, kind: 'ground', x: wx, y: wy, base: -Infinity };
  }
  function worldHoverLabel(wx, wy) { const p = worldPickAt(+wx, +wy); return p ? p.label : null; }
  // Screen-space entry point: canvas pixels -> world via the live camera inverse, then pick.
  function worldHoverLabelAtCanvas(px, py) {
    if (!lastCam) return null;
    const [wx, wy] = lastCam.toWorld(+px, +py);
    return worldHoverLabel(wx, wy);
  }
  function mapCoordinateText(x, y) {
    const b = MAP.bbox, s = MAP.scale || 2;
    const lat = b[2] - y / (110574 * s), lon = b[1] + x / (111320 * Math.cos((b[0] + b[2]) / 2 * Math.PI / 180) * s);
    return `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
  }
  function copyMapCoordinates(point) {
    if (!point) return;
    const text = mapCoordinateText(point.x, point.y), fallback = () => {
      try {
        const input = document.createElement('textarea'); input.value = text; input.setAttribute('readonly', ''); input.style.position = 'fixed'; input.style.opacity = '0';
        document.body.appendChild(input); input.select(); document.execCommand('copy'); input.remove();
      } catch (e) { }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).catch(fallback); else fallback();
  }
  cvs.addEventListener('pointerdown', e => {
    cvs.setPointerCapture(e.pointerId);
    if (scene === 'title') {
      // Check for character button click
      const [px, py] = toCanvas(e);
      const button = characterButtonBounds().find(b => px >= b.x && px < b.x + b.w && py >= b.y && py < b.y + b.h);
      if (button) { selectCharacter(button.id); return; }
      startGame(!hasSave);
      return;
    }
    if (scene === 'end') {
      if (memoryIndex < T.memoryFacts.length - 1) memoryIndex++;
      else scene = 'play';
      return;
    }
    const [px, py] = toCanvas(e);
    pointer.x = px; pointer.y = py; pointer.seen = true; pointer.kind = e.pointerType;
    if (!talk && HOOKS.pointer.some(f => f(px, py))) return;
    if (showMap) {
      const point = mapPoint(px, py);
      if (point) { mapCursor.seen = true; mapCursor.x = point.x; mapCursor.y = point.y; copyMapCoordinates(point); }
      else { showMap = false; mapCursor.seen = false; cancelClickMove(); }   // click outside the map closes it
      return;
    }
    if (px > cvs.width * .78 && py > cvs.height * .6) { if (talk || nearThing()) interact(); else jump(); return; }
    if (px > cvs.width * .78 && py < cvs.height * .3) { showMap = !showMap; return; }
    if (talk) { interact(); return; }
    if (e.pointerType === 'mouse') {
      if (lastCam) { const [x, y] = lastCam.toWorld(px, py); clickTarget.active = true; clickTarget.x = x; clickTarget.y = y; }
      return;
    }
    cancelClickMove();
    Object.assign(joy, { active: true, id: e.pointerId, cx: px, cy: py, x: 0, y: 0 });
  });
  cvs.addEventListener('pointermove', e => {
    [pointer.x, pointer.y] = toCanvas(e); pointer.seen = true; pointer.kind = e.pointerType;
    if (showMap && e.pointerType === 'mouse') { const point = mapPoint(pointer.x, pointer.y); if (point) { mapCursor.seen = true; mapCursor.x = point.x; mapCursor.y = point.y; } else mapCursor.seen = false; }
    if (!joy.active || e.pointerId !== joy.id) return;
    const [px, py] = toCanvas(e);
    let dx = px - joy.cx, dy = py - joy.cy; const d = Math.hypot(dx, dy), max = 70;
    if (d > max) { dx *= max / d; dy *= max / d; }
    joy.x = dx / max; joy.y = dy / max; cancelClickMove();
  });
  const endJoy = e => { if (e.pointerId === joy.id) Object.assign(joy, { active: false, x: 0, y: 0 }); };
  cvs.addEventListener('pointerup', endJoy); cvs.addEventListener('pointercancel', endJoy);
  // A mouse leaving the canvas must drop the world hover label (touch/pen have no
  // leave in the same sense, and their aiming is gated by pointer.kind anyway).
  cvs.addEventListener('pointerleave', e => { if (e.pointerType === 'mouse') { pointer.seen = false; pointer.kind = null; } });

  /* ---------- rooms (church interior) ---------- */
  function fade(fn) { if (!trans) trans = { t: 0, fn, done: false }; }
  function enterChurch() {
    fade(() => {
      const c = window.buildChurch();
      OUT = { MAP, GROUND, OBJ, SOLID, x: P.x, y: P.y, dog: { x: FRODO.x, y: FRODO.y } };
      ROOM = c; MAP = { w: c.w, h: c.h, top: c.top, objects: c.objects, pois: c.pois, spawn: c.spawn };
      GROUND = c.ground; OBJ = c.obj; SOLID = c.solid;
      P.x = c.spawn.x; P.y = c.spawn.y; P.dir = 'up'; camX = P.x; camY = P.y; dust = [];
      placeFrodoNearArek();
      if (!Q.churchSeen) { Q.churchSeen = true; save(); say('arek', T.churchIn); }
    });
  }
  function enterShop() {
    if (trans || ROOM) return;
    fade(() => {
      const c = window.buildShop();
      c.kind = 'shop';
      OUT = { MAP, GROUND, OBJ, SOLID, x: P.x, y: P.y, dog: { x: FRODO.x, y: FRODO.y } };
      ROOM = c; MAP = { w: c.w, h: c.h, top: c.top, objects: c.objects, pois: c.pois, spawn: c.spawn };
      GROUND = c.ground; OBJ = c.obj; SOLID = c.solid;
      P.x = c.spawn.x; P.y = c.spawn.y; P.dir = 'up'; camX = P.x; camY = P.y; dust = [];
      placeFrodoNearArek();
    });
  }
  function playShop() {
    if (shopGame) return;
    cancelClickMove(); keys.clear();
    shopGame = window.ShopGame.create({ onComplete: result => {
      Q.shopGames = (Q.shopGames || 0) + 1;
      Q.shopCreditGrosz = (Q.shopCreditGrosz || 0) + result.creditGrosz;
      if (Q.marcin === 1 && !Q.orange) {
        Q.orange = true;
        popToast(LANG === 'pl' ? '+ ORANŻADA DLA MARCINA' : '+ ORANGEADE FOR MARCIN');
      }
      save();
    } });
    const game = shopGame, destroy = game.destroy;
    game.destroy = () => { destroy(); shopGame = null; keys.clear(); };
    game.element.addEventListener('keydown', e => e.stopPropagation());
    game.element.addEventListener('keyup', e => e.stopPropagation());
    document.body.appendChild(game.element);
  }
  function leaveRoom() {
    fade(() => {
      ({ MAP, GROUND, OBJ, SOLID } = OUT); P.x = OUT.x; P.y = OUT.y + 6; P.dir = 'down';
      ROOM = null; unstick(); trail.length = 0;
      if (OUT.dog && !blocked(OUT.dog.x, OUT.dog.y)) { FRODO.x = OUT.dog.x; FRODO.y = OUT.dog.y; } else placeFrodoNearArek();   // he waited by the door
      camX = P.x; camY = P.y; dust = []; save();
    });
  }
  const npcsHere = () => ROOM ? (ROOM.soltys ? [{ id: 'soltys', x: ROOM.soltys.x, y: ROOM.soltys.y }] : []) : ITEMS.npcs;

  /* ---------- dialogue & quests ---------- */
  function heroName() { return sanitizePlayerName(Q.playerName) || (LANG === 'pl' ? 'GRACZ' : 'PLAYER'); }
  // The hero is whoever the player named: every "Arek" in dialogue/toasts (incl. Polish forms Areka/Arkowi/Arkiem/Arku) becomes that name.
  function heroText(value) {
    const name = heroName();
    return String(value).replace(/(?<![\p{L}\-_])(arek|areka|arkowi|arkiem|arku)(?![\p{L}\-_])/giu, m => m === m.toUpperCase() ? name.toUpperCase() : name);
  }
  function say(who, lines, after) { talk = { who, lines: lines.map(heroText), i: 0, after }; talkT = 0; }
  function nearThing() {
    let best = null, bd = 1e9;
    for (const n of npcsHere()) { const d = Math.hypot(P.x - n.x, P.y - n.y); if (d < 42 && d < bd) { bd = d; best = { npc: n.id, x: n.x, y: n.y }; } }
    if (best) return best;
    if (!ROOM) for (const f of HOOKS.near) for (const c of f(P)) { const d = Math.hypot(P.x - c.x, P.y - c.y); if (d < (c.r || 30) && d < bd) { bd = d; best = { feat: c, x: c.x, y: c.y }; } }
    if (best) return best;
    for (const s of MAP.pois) { const r = s.r || SPOT_R[s.key] || 50, d = Math.hypot(P.x - s.x, P.y - s.y); if (d < r && d < bd) { bd = d; best = { poi: s.key, x: s.x, y: s.y }; } }
    return best;
  }
  function talkNpc(id) {
    if (id === 'kasia') {
      if (Q.kasia === 0) { Q.kasia = 1; say(id, T.kasia0); }
      else if (Q.kasia === 1) { if (mushroomCount() >= MUSHROOMS_NEEDED) { Q.kasia = 2; say(id, T.kasia2, () => celebrate()); } else say(id, T.kasia1(mushroomCount())); }
      else say(id, T.kasia3);
    } else if (id === 'damian') {
      if (Q.damian === 0) { Q.damian = 1; say(id, Q.cap ? T.damian2 : T.damian0); if (Q.cap) { Q.damian = 2; celebrate(); } }
      else if (Q.damian === 1) { if (Q.cap) { Q.damian = 2; say(id, T.damian2, () => celebrate()); } else say(id, T.damian1); }
      else say(id, T.damian3);
    } else if (id === 'marcin') {
      if (Q.marcin === 0) { Q.marcin = 1; say(id, T.marcin0); }
      else if (Q.marcin === 1) { if (Q.orange) { Q.marcin = 2; say(id, T.marcin2, () => celebrate()); } else say(id, T.marcin1); }
      else say(id, T.marcin3);
    } else if (id === 'soltys') {
      say(id, ROOM ? (Q.kasia === 2 ? T.soltys1 : T.soltys0) : T.soltysSecret);
    } else if (id === 'grandpa') {
      const n = questsDone();
      if (Q.grandpa === 2) say(id, [T.grandpa2[2]]);
      else if (n >= 3) { say(id, T.grandpa2, () => { Q.grandpa = 2; save(); celebrate(); memoryIndex = 0; scene = 'end'; }); }
      else if (Q.grandpa === 0) { Q.grandpa = 1; say(id, T.grandpa0); }
      else say(id, T.grandpa1(n));
    } else if (id === 'wesoly_swiat') {
      say(id, T.wesoly0);
    } else if (id === 'renik') {
      Q.renikTalks = (Q.renikTalks || 0) + 1;
      say(id, T.renik[(Q.renikTalks - 1) % T.renik.length]);
    } else if (id === 'edytka') {
      talkEdytka();
    } else HOOKS.npcTalk.some(f => f(id));
    save();
  }
  /* ---------- Edytka: bring Frodo to her 3 times. He stays EDYTKA_STAY seconds, then runs back to Arek. ---------- */
  const EDYTKA_NEAR = 70, EDYTKA_STAY = 10, EDYTKA_TIMES = 3;
  const edytkaNpc = () => ITEMS && ITEMS.npcs.find(n => n.id === 'edytka');
  function frodoNearEdytka() {
    const e = edytkaNpc(); return !!e && !ROOM && Math.hypot(FRODO.x - e.x, FRODO.y - e.y) < EDYTKA_NEAR;
  }
  function talkEdytka() {
    const id = 'edytka';
    if (Q.edytka === 2) { say(id, T.edytkaAfter); return; }
    if (Q.edytka === 0) { Q.edytka = 1; say(id, T.edytka0, () => { if (frodoNearEdytka()) startFrodoVisit(); }); return; }
    if (FRODO.visit) { say(id, T.edytkaWait); return; }
    if (frodoNearEdytka() && FRODO.visitReady !== false) startFrodoVisit(); else say(id, T.edytkaNoDog);
  }
  function startFrodoVisit() {
    const e = edytkaNpc(); if (!e || FRODO.visit || Q.edytka !== 1) return;
    FRODO.visitReady = false;
    Q.edytkaN = (Q.edytkaN || 0) + 1;
    FRODO.visit = { t: 0, n: Q.edytkaN };
    say('edytka', T.edytkaVisit(Q.edytkaN)); popToast(`FRODO ${Q.edytkaN}/${EDYTKA_TIMES}`); save();
  }
  // Frodo sits at Edytka's feet during a visit; when it ends he runs back to Arek (the normal follow logic).
  function updateFrodoVisit(dt) {
    const v = FRODO.visit, e = edytkaNpc(); if (!v || !e) return false;
    if (ROOM) { FRODO.visit = null; return false; }
    v.t += dt;
    if (v.t >= EDYTKA_STAY) {
      FRODO.visit = null; FRODO.wander = 0; FRODO.wanderWait = 6; FRODO.returning = true; FRODO.returningT = 0;
      if (Q.edytkaN >= EDYTKA_TIMES) { Q.edytka = 2; say('edytka', T.edytkaDone, () => celebrate()); }
      else popToast(T.edytkaBack);
      save(); return false;
    }
    const tx = e.x + 22, ty = e.y + 6, vx = tx - FRODO.x, vy = ty - FRODO.y, d = Math.hypot(vx, vy);
    if (d > 4) {
      const st = Math.min(d, 120 * dt), nx = FRODO.x + vx / d * st, ny = FRODO.y + vy / d * st;
      FRODO.x = nx; FRODO.y = ny;   // walks through yard clutter instead of popping onto her feet
      FRODO.moving = true; FRODO.step += dt * 9; FRODO.dir = Math.abs(vx) > Math.abs(vy) ? (vx < 0 ? 'left' : 'right') : (vy < 0 ? 'up' : 'down');
    } else {   // happy at her feet: pant / sit / lick
      FRODO.moving = false; FRODO.idleAnim += dt; FRODO.dir = 'left';
      FRODO.action = ['pant', 'sit', 'lick'][Math.floor(v.t / 3.4) % 3];
    }
    return true;
  }
  function interact() {
    if (talk) {
      const line = talk.lines[talk.i];
      if (talkT * 45 < line.length) { talkT = 1e3; return; }
      if (talk.i < talk.lines.length - 1) { talk.i++; talkT = 0; return; }
      const after = talk.after; talk = null; talkClosedAt = time; if (after) after(); return;
    }
    if (P.air) return;
    const s = nearThing(); if (!s) return;
    if (s.npc) { turnTo(s); talkNpc(s.npc); return; }
    if (s.feat) { turnTo(s); s.feat.onInteract(); return; }
    if (s.poi === 'church') { if (!HOOKS.busy.some(f => f())) enterChurch(); return; }
    if (s.poi === 'shop') { if (!HOOKS.busy.some(f => f())) enterShop(); return; }
    if (ROOM && ROOM.kind === 'shop') {
      if (s.poi === 'checkout' || s.poi === 'scale' || s.poi === 'bread' || s.poi === 'produce' || s.poi === 'beer') playShop();
      else say('arek', [LANG === 'pl' ? 'W tym sklepie można płacić bitcoinem.' : 'This shop accepts Bitcoin.']);
      return;
    }
    say('arek', T[s.poi]);
  }
  function turnTo(s) { const dx = s.x - P.x, dy = s.y - P.y; P.dir = Math.abs(dx) > Math.abs(dy) ? (dx < 0 ? 'left' : 'right') : (dy < 0 ? 'up' : 'down'); }
  function popToast(text) { toast = { text: heroText(text), t: 0 }; if (window.MUSIC) MUSIC.ding(); }
  function jump() {
    if (scene !== 'play' || talk || P.air || time - talkClosedAt < .3) return;   // don't jump when mashing Space through dialogue
    cancelClickMove();
    let ix = 0, iy = 0;
    if (keys.has('ArrowLeft') || keys.has('KeyA')) ix -= 1;
    if (keys.has('ArrowRight') || keys.has('KeyD')) ix += 1;
    if (keys.has('ArrowUp') || keys.has('KeyW')) iy -= 1;
    if (keys.has('ArrowDown') || keys.has('KeyS')) iy += 1;
    if (joy.active && Math.hypot(joy.x, joy.y) > .2) { ix = joy.x; iy = joy.y; }
    const m = Math.hypot(ix, iy), moving = m > .01;
    if (!moving) [ix, iy] = DIRV[P.dir]; else { ix /= m; iy /= m; }
    const run = keys.has('ShiftLeft') || keys.has('ShiftRight') ? 1.5 : 1;
    const sp = (moving ? 1.35 : .8) * SPEED * run;   // standing jump still hops forward a little
    Object.assign(P, { air: true, jt: 0, jx: ix * sp, jy: iy * sp, ox: P.x, oy: P.y });
    if (window.MUSIC && MUSIC.hop) MUSIC.hop();
  }
  function updateJump(dt) {
    P.jt += dt;
    const nx = P.x + P.jx * dt, ny = P.y + P.jy * dt;
    if (!blocked(nx, P.y, true)) P.x = nx;
    if (!blocked(P.x, ny, true)) P.y = ny;
    const k = P.jt / JUMP_T;
    if (k < 1) { P.z = Math.sin(Math.PI * k) * JUMP_H; return; }
    // coming down on top of a fence / into the stream: glide a little further, else hop back
    if (blocked(P.x, P.y, false)) {
      P.z = 2;
      if (P.jt > JUMP_T + .35) { P.x = P.ox; P.y = P.oy; land(); }
      return;
    }
    land();
  }
  function land() {
    P.air = false; P.z = 0; P.land = 0;
    for (let k = 0; k < 6; k++) dust.push({ x: P.x + (k - 2.5) * 3, y: P.y + (k % 2), t: k * .03 });
  }
  function celebrate() { if (window.MUSIC) MUSIC.jingle(); for (let i = 0; i < 40; i++) fx.push({ x: P.x, y: P.y - 25, vx: (Math.random() - .5) * 160, vy: -Math.random() * 180 - 40, t: 0, c: ['#ffd21f', '#ff4fa3', '#7cff6b', '#6fd0ff'][i % 4] }); }

  /* ---------- physics ---------- */
  function solidAt(x, y, air) {
    x |= 0; y |= 0;
    if (x < 4 || y < (MAP.top ?? 40) || x >= MAP.w - 4 || y >= MAP.h - 2) return true;
    const v = SOLID[y * MAP.w + x];
    return air ? v === 2 : v !== 0;   // 2 = tall (walls, trees, ponds), 1 = low (fences, streams, hay) — clearable mid-air
  }
  function baleAt(x, y) { return BALES.some(b => Math.hypot(x - b.x, y - b.y) < 22); }
  function updateBales(dt) {
    // Stationary bales need no per-frame physics until a walker gets close; moving bales keep rolling anywhere.
    for (const b of BALES) {
      const nearPlayer = P.moving && Math.abs(P.x - b.x) < 38 && Math.abs(P.y - b.y) < 38;
      const nearFrodo = FRODO.moving && Math.abs(FRODO.x - b.x) < 34 && Math.abs(FRODO.y - b.y) < 34;
      if (Math.abs(b.vx) < .01 && Math.abs(b.vy) < .01 && !nearPlayer && !nearFrodo) continue;
      for (const who of BALE_ACTORS) {
        if (!who.moving || (who === P && P.air)) continue;
        let dx = b.x - who.x, dy = b.y - who.y; const d = Math.hypot(dx, dy), reach = who === P ? 16 : 12;
        if (d >= reach) continue;
        if (d < .01) { const v = DIRV[who.dir] || DIRV.down; dx = v[0]; dy = v[1]; } else { dx /= d; dy /= d; }
        const nx = who.x + dx * reach, ny = who.y + dy * reach;   // shove it out in front of the walker...
        if (!solidAt(nx, ny, false)) { b.x = nx; b.y = ny; }
        const kick = who === P ? 95 : 60; b.vx = dx * kick; b.vy = dy * kick;   // ...and let it roll on a bit
      }
      const sp = Math.hypot(b.vx, b.vy);
      if (sp > 150) { b.vx *= 150 / sp; b.vy *= 150 / sp; }
      const nx = b.x + b.vx * dt, ny = b.y + b.vy * dt;
      if (solidAt(nx - 12, b.y, false) || solidAt(nx + 12, b.y, false) || nx < 30 || nx > MAP.w - 30) b.vx *= -.25; else b.x = nx;
      if (solidAt(b.x, ny - 12, false) || ny < (MAP.top || 40) + 20 || ny > MAP.h - 20) b.vy *= -.25; else b.y = ny;
      b.roll += (Math.abs(b.vx) + Math.abs(b.vy)) * dt * .35;
      b.vx *= Math.max(0, 1 - dt * 3.2); b.vy *= Math.max(0, 1 - dt * 3.2);
    }
  }
  function blocked(x, y, air = false) {
    if (!air && baleAt(x, y)) return false;
    const l = x - HIT.w / 2, r = x + HIT.w / 2, t = y - HIT.h;
    if (solidAt(l, y, air) || solidAt(r, y, air) || solidAt(l, t, air) || solidAt(r, t, air) || solidAt(x, y, air) || solidAt(x, t, air)) return true;
    if (ITEMS) for (const n of npcsHere()) if (Math.abs(x - n.x) < 12 && Math.abs(y - n.y) < 6) return true;
    return false;
  }
  function unstick() {
    if (!blocked(P.x, P.y)) return;
    const ox = P.x, oy = P.y;
    for (let r = 4; r < 300; r += 4) for (let a = 0; a < 6.28; a += .4) { const x = ox + Math.cos(a) * r, y = oy + Math.sin(a) * r; if (!blocked(x, y)) { P.x = x; P.y = y; return; } }
  }
  function placeFrodoNearArek() {
    const [dx, dy] = DIRV[P.dir] || DIRV.down;
    const behind = Math.atan2(-dy, -dx);
    const turns = [0, -.65, .65, -1.3, 1.3, -2, 2, Math.PI];
    for (let r = 26; r <= 68; r += 7) for (const turn of turns) {
      const x = P.x + Math.cos(behind + turn) * r, y = P.y + Math.sin(behind + turn) * r;
      if (!blocked(x, y)) { FRODO.x = x; FRODO.y = y; FRODO.stuck = 0; FRODO.wander = 0; FRODO.wanderWait = 4; return; }
    }
    FRODO.x = P.x; FRODO.y = P.y; FRODO.stuck = 0; FRODO.wander = 0; FRODO.wanderWait = 4;
  }
  function updateFrodo(dt) {
    // Edytka's quest: bringing Frodo close to her starts a visit on its own; he must get away from her before the next one counts
    if (Q.edytka === 1 && !FRODO.visit) {
      const e = edytkaNpc(), d = e ? Math.hypot(FRODO.x - e.x, FRODO.y - e.y) : 1e9;
      if (d > EDYTKA_NEAR * 2) FRODO.visitReady = true;
      else if (FRODO.visitReady !== false && d < EDYTKA_NEAR && !ROOM && !talk) { FRODO.visitReady = false; startFrodoVisit(); }
    }
    if (updateFrodoVisit(dt)) return;
    // footsteps: one crumb every ~14 px of Arek's walk
    const lastCrumb = trail[trail.length - 1];
    if (!lastCrumb || Math.hypot(P.x - lastCrumb.x, P.y - lastCrumb.y) > 14) { trail.push({ x: P.x, y: P.y }); if (trail.length > 240) trail.shift(); }
    const [dx, dy] = DIRV[P.dir] || DIRV.down;
    let tx = P.x - dx * 42, ty = P.y - dy * 42;
    const toArek = Math.hypot(P.x - FRODO.x, P.y - FRODO.y);
    // world-life.js asks him to chase a mouse / hare / fox: FRODO.chase = { x, y, t }; he gives up when Arek gets too far
    const chase = FRODO.chase && FRODO.chase.t > 0 && toArek < 260 && Number.isFinite(FRODO.chase.x) ? FRODO.chase : null;
    if (chase) { tx = chase.x; ty = chase.y; FRODO.wander = 0; FRODO.trailI = -1; }
    // Arek teleported (minigame start, debug): the whole view changed, so the dog can rejoin without anyone seeing a jump
    if (!chase && toArek > 450 && !dogOnScreen() && !FRODO.visit) { placeFrodoNearArek(); FRODO.trailI = -1; trail.length = 0; return; }
    const followDist = Math.hypot(tx - FRODO.x, ty - FRODO.y);
    if (FRODO.returning) { FRODO.returningT += dt; if (followDist < 42) { FRODO.returning = false; FRODO.returningT = 0; } }
    // walking Arek's footsteps (set when he got stuck behind a wall)
    if (FRODO.trailI >= 0 && !chase) {
      if (toArek < 60 || FRODO.trailI >= trail.length) FRODO.trailI = -1;
      else {
        const c = trail[FRODO.trailI], vx = c.x - FRODO.x, vy = c.y - FRODO.y, d = Math.hypot(vx, vy);
        if (d < 6) { FRODO.trailI++; return; }
        const st = Math.min(d, 190 * dt);
        FRODO.x += vx / d * st; FRODO.y += vy / d * st;   // Arek walked (or hopped) here, so the dog can too
        FRODO.moving = true; FRODO.step += dt * 9; FRODO.routine = null; FRODO.action = 'idle'; FRODO.idleAnim = 0; FRODO.stuck = 0;
        FRODO.dir = Math.abs(vx) > Math.abs(vy) ? (vx < 0 ? 'left' : 'right') : (vy < 0 ? 'up' : 'down');
        return;
      }
    }
    if (followDist > 75) FRODO.wander = 0;
    if (!chase && !FRODO.wander && followDist < 68 && (FRODO.wanderWait -= dt) <= 0) {
      for (let i = 0; i < 8; i++) {
        const a = Math.random() * Math.PI * 2, r = 20 + Math.random() * 30, x = P.x + Math.cos(a) * r, y = P.y + Math.sin(a) * r;
        if (!blocked(x, y)) { FRODO.wander = 2.4 + Math.random() * 1.8; FRODO.wanderX = x; FRODO.wanderY = y; break; }
      }
      FRODO.wanderWait = 7 + Math.random() * 6;
    }
    let vx = (FRODO.wander ? FRODO.wanderX : tx) - FRODO.x, vy = (FRODO.wander ? FRODO.wanderY : ty) - FRODO.y;
    const dist = Math.hypot(vx, vy);
    if (FRODO.wander && (FRODO.wander -= dt) <= 0) { FRODO.wander = 0; vx = tx - FRODO.x; vy = ty - FRODO.y; }
    FRODO.moving = dist > (chase ? 4 : 18);
    if (!FRODO.moving) {
      FRODO.stuck = 0; FRODO.idleAnim += dt;
      // random idle routine while Arek stands still: sit / pant, lick himself, scratch, sniff around, lie down
      if (!FRODO.routine || (FRODO.routineT -= dt) <= 0) {
        const opts = ['sit', 'pant', 'lick', 'lick', 'scratch', 'sniff', 'lie'].filter(a => a !== FRODO.routine);
        FRODO.routine = opts[(Math.random() * opts.length) | 0];
        FRODO.routineT = { sit: 2.5, pant: 3, lick: 3.2, scratch: 2.2, sniff: 2.6, lie: 4.5 }[FRODO.routine] * (.8 + Math.random() * .5);
        if (FRODO.dir === 'up' || FRODO.dir === 'down') FRODO.dir = Math.random() < .5 ? 'left' : 'right';
      }
      FRODO.action = FRODO.idleAnim < .6 ? 'idle' : FRODO.routine;
      return;
    }
    FRODO.routine = null;
    FRODO.dir = Math.abs(vx) > Math.abs(vy) ? (vx < 0 ? 'left' : 'right') : (vy < 0 ? 'up' : 'down');
    const speed = chase ? 215 : FRODO.wander ? 28 : Math.min(190, 110 + Math.max(0, dist - 28) * 1.2);
    const step = Math.min(dist - (chase ? 0 : 18), speed * dt);
    vx = vx / dist * step; vy = vy / dist * step;
    let moved = false;
    if (!blocked(FRODO.x + vx, FRODO.y + vy)) { FRODO.x += vx; FRODO.y += vy; moved = true; }
    else {
      if (Math.abs(vx) > .01 && !blocked(FRODO.x + vx, FRODO.y)) { FRODO.x += vx; moved = true; }
      if (Math.abs(vy) > .01 && !blocked(FRODO.x, FRODO.y + vy)) { FRODO.y += vy; moved = true; }
    }
    if (moved) { FRODO.step += dt * (FRODO.wander ? 4 : chase ? 12 : 9); FRODO.stuck = 0; FRODO.idleAnim = 0; FRODO.action = 'idle'; }
    else if ((FRODO.stuck += dt) > (chase ? .6 : FRODO.returning ? 2.5 : dist > 100 ? 1.0 : 2.0)) {
      FRODO.stuck = 0; FRODO.wanderWait = .5;
      if (chase) { FRODO.chase = null; return; }   // the mouse slipped under a fence
      // Continuity: never pop next to Arek. Walk back along his footsteps from the crumb closest to the dog.
      let best = -1, bd = 1e9;
      for (let i = 0; i < trail.length; i++) { const d = Math.hypot(trail[i].x - FRODO.x, trail[i].y - FRODO.y); if (d < bd) { bd = d; best = i; } }
      if (best >= 0 && bd < 90) { FRODO.trailI = best; FRODO.wander = 0; }
      else {
        const side = Math.atan2(ty - FRODO.y, tx - FRODO.x) + (Math.random() < .5 ? 1 : -1) * Math.PI / 2;
        FRODO.wander = .8; FRODO.wanderX = FRODO.x + Math.cos(side) * 55; FRODO.wanderY = FRODO.y + Math.sin(side) * 55;
        // Last resort (e.g. Arek was teleported by a minigame): only relocate while the dog is off-screen, so nobody sees a jump.
        if (dist > 100 && !dogOnScreen()) placeFrodoNearArek();
      }
    }
  }
  function dogOnScreen() {
    if (!lastCam) return false;
    const [x, y] = lastCam.S(FRODO.x, FRODO.y);
    return x > -40 && y > -40 && x < cvs.width + 40 && y < cvs.height + 40;
  }
  function update(dt) {
    time += dt;
    dust = dust.filter(d => (d.t += dt) < .5);
    fx = fx.filter(f => { f.t += dt; f.x += f.vx * dt; f.y += f.vy * dt; f.vy += 320 * dt; return f.t < 1.2; });
    if (toast && (toast.t += dt) > 1.6) toast = null;
    if (trans) { trans.t += dt; if (!trans.done && trans.t >= .25) { trans.done = true; trans.fn(); } if (trans.t >= .5) trans = null; else return; }
    if (scene !== 'play') return;
    Q.playTime += dt;
    if (shopGame) { P.moving = false; return; }
    if (talk) { talkT += dt; P.moving = false; return; }
    HOOKS.update.forEach(f => f(dt));
    updateWanderers(dt);
    if (HOOKS.blocksPlayer.some(f => f())) { P.moving = false; return; }
    P.land = Math.min(1, P.land + dt * 6);
    if (P.air) { updateJump(dt); P.moving = true; P.step += dt * 3; } else {
    let ix = 0, iy = 0;
    const manual = keys.has('ArrowLeft') || keys.has('KeyA') || keys.has('ArrowRight') || keys.has('KeyD') || keys.has('ArrowUp') || keys.has('KeyW') || keys.has('ArrowDown') || keys.has('KeyS');
    if (keys.has('ArrowLeft') || keys.has('KeyA')) ix -= 1;
    if (keys.has('ArrowRight') || keys.has('KeyD')) ix += 1;
    if (keys.has('ArrowUp') || keys.has('KeyW')) iy -= 1;
    if (keys.has('ArrowDown') || keys.has('KeyS')) iy += 1;
    if (joy.active && Math.hypot(joy.x, joy.y) > .2) { ix = joy.x; iy = joy.y; cancelClickMove(); }
    if (manual) cancelClickMove();
    if (!manual && !joy.active && clickTarget.active) {
      ix = clickTarget.x - P.x; iy = clickTarget.y - P.y;
    }
    const m = Math.hypot(ix, iy);
    if (clickTarget.active && !manual && !joy.active && m < 8) clickTarget.active = false;
    P.moving = m > .01;
    if (P.moving) {
      ix /= Math.max(1, m); iy /= Math.max(1, m);
      P.dir = direction8(ix, iy);
      const clickMove = !manual && !joy.active && clickTarget.active;
      const run = clickMove ? 1 : keys.has('ShiftLeft') || keys.has('ShiftRight') || (joy.active && m > .95) ? 1.8 : 1;
      const terrain = HOOKS.speed.reduce((k, f) => k * f(P.x, P.y), 1) * (TERRAIN_SPEED[terrainAt(P.x, P.y)] || 1);
      const step = clickMove ? Math.min(m, SPEED * terrain * dt) : SPEED * run * terrain * dt;
      const nx = P.x + ix * step, ny = P.y + iy * step;
      let moved = false;
      if (!blocked(nx, P.y)) { P.x = nx; moved = true; }
      if (!blocked(P.x, ny)) { P.y = ny; moved = true; }
      if (clickMove && (m < 8 || !moved)) clickTarget.active = false;
      if (moved) {
        const prev = Math.floor(P.step);
        P.step += dt * 7 * run;
        if (Math.floor(P.step) !== prev && Math.floor(P.step) % 2 === 0) dust.push({ x: P.x, y: P.y, t: 0 });
      }
    }
    }
    updateBales(dt);
    updateFrodo(dt);
    if (ROOM) { const e = ROOM.exit; if (P.y > e.y && P.x > e.x0 && P.x < e.x1) leaveRoom(); return; }
    // pickups
    ITEMS.apples.forEach((a, i) => {
      if (Q.apples.includes(i) || Math.hypot(P.x - a.x, P.y - a.y) > 14) return;
      Q.apples.push(i); save();
      popToast(`+1 ${T.apple}  ${appleCount()}/${APPLES_NEEDED}`);
      for (let k = 0; k < 14; k++) fx.push({ x: a.x, y: a.y - 6, vx: (Math.random() - .5) * 90, vy: -Math.random() * 120, t: 0, c: k % 2 ? '#ffd21f' : '#ff5a4e' });
    });
    (Q.mushroomSpots || []).forEach((m, i) => {
      if ((Q.mushrooms || []).includes(i) || Math.hypot(P.x - m.x, P.y - m.y) > 16) return;
      Q.mushrooms.push(i); save();
      popToast(`+1 ${T.mushroom}  ${mushroomCount()}/${MUSHROOMS_NEEDED}`);
      for (let k = 0; k < 14; k++) fx.push({ x: m.x, y: m.y - 6, vx: (Math.random() - .5) * 90, vy: -Math.random() * 120, t: 0, c: k % 2 ? '#fff0ba' : '#8bdc66' });
    });
    (Q.trashSpots || []).forEach((t, i) => {
      if ((Q.trash || []).includes(i) || Math.hypot(P.x - t.x, P.y - t.y) > 16) return;
      Q.trash.push(i); save();
      popToast(`+1 ${T.trash}  ${trashCount()}/${TRASH_TOTAL}`);
      for (let k = 0; k < 14; k++) fx.push({ x: t.x, y: t.y - 6, vx: (Math.random() - .5) * 90, vy: -Math.random() * 120, t: 0, c: k % 2 ? '#c8cee0' : '#2b2f3a' });
    });
    if (!Q.cap && Math.hypot(P.x - ITEMS.cap.x, P.y - ITEMS.cap.y) < 16) {
      Q.cap = true; save(); popToast('+ ' + T.cap); say('arek', T.gotCap);
      for (let k = 0; k < 20; k++) fx.push({ x: ITEMS.cap.x, y: ITEMS.cap.y - 6, vx: (Math.random() - .5) * 110, vy: -Math.random() * 140, t: 0, c: '#ffd21f' });
    }
  }

  /* ---------- render helpers ---------- */
  let zoom = 3, camX = 0, camY = 0, lastCam = null;
  function resize() {
    const dpr = Math.min(2, devicePixelRatio || 1);
    cvs.width = Math.round(innerWidth * dpr); cvs.height = Math.round(innerHeight * dpr);
    zoom = Math.max(cvs.height / 330, cvs.width / 640);
  }
  addEventListener('resize', resize);

  function shadow(sx, sy, s, w = 8.5) { ctx.fillStyle = 'rgba(20,34,12,0.38)'; ctx.beginPath(); ctx.ellipse(sx, sy, w * s, 3 * s, 0, 0, Math.PI * 2); ctx.fill(); }
  // Cemetery zone: the OSM landuse rectangle around the cemetery POI (same as music.js), with hysteresis at the edge.
  // Inside it Arek takes his sunglasses off (img/arek_sheet_noglasses.png, same layout as arek_sheet.png).
  const CEM_HALF = [112, 97];
  let inCemetery = false;
  function cemeteryZone() {
    const c = !ROOM && MAP && MAP.pois.find(p => p.key === 'cemetery');
    if (!c) return (inCemetery = false);
    const m = inCemetery ? 70 : 25;
    return (inCemetery = Math.abs(P.x - c.x) < CEM_HALF[0] + m && Math.abs(P.y - c.y) < CEM_HALF[1] + m);
  }
  function spriteAnim(meta, prefix, dir) {
    return meta.anims[prefix + dir] || meta.anims[prefix + cardinalDir(dir)] || meta.anims[prefix + 'down'];
  }
  function drawArek(sx, sy, s) {
    const h = CHAR_H * s, zk = 1 - P.z / JUMP_H * .45;
    ctx.globalAlpha = zk; shadow(sx, sy, s * zk); ctx.globalAlpha = 1;
    sy -= P.z * s;
    const { meta } = SPR, sheet = (inCemetery && selectedCharacter === 'arek' && SPR.bare) || SPR.sheet;   // no-glasses sheet exists only for Arek
    const anim = spriteAnim(meta, P.moving || P.air ? 'walk_' : 'idle_', P.dir) || spriteAnim(meta, 'walk_', P.dir);
    const f = anim.frames[P.air ? 2 % anim.frames.length : P.moving ? Math.floor(P.step) % anim.frames.length : 0];
    const scale = h / (f.h - meta.foot - 14), w = f.w * scale, hh = f.h * scale;
    ctx.save(); ctx.translate(sx, sy + meta.foot * scale);
    if (anim.flip) ctx.scale(-1, 1);
    const sq = P.land < 1 ? 1 - Math.sin(P.land * Math.PI) * .14 : 1;   // landing squash
    ctx.scale(2 - sq, sq);
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(sheet, f.x, f.y, f.w, f.h, -w / 2, -hh, w, hh);
    ctx.restore(); ctx.imageSmoothingEnabled = false;
  }
  function drawArekPose(sx, sy, s, dir, step, alpha = 1) {   // used for the race ghost
    const { meta, sheet } = SPR, anim = spriteAnim(meta, 'walk_', dir), f = anim.frames[Math.floor(step) % anim.frames.length];
    const h = CHAR_H * s, scale = h / (f.h - meta.foot - 14), w = f.w * scale, hh = f.h * scale;
    ctx.save(); ctx.globalAlpha = alpha; ctx.translate(sx, sy + meta.foot * scale); if (anim.flip) ctx.scale(-1, 1);
    ctx.imageSmoothingEnabled = true; ctx.drawImage(sheet, f.x, f.y, f.w, f.h, -w / 2, -hh, w, hh); ctx.restore(); ctx.imageSmoothingEnabled = false;
  }
  // Round straw bale lying on its side (24x16 art px), end face with rings on the right. Mirrored every few px of
  // rolling so it visibly tumbles when pushed.
  const BALE_PX = [[9, 0, 5, "q"], [7, 1, 2, "q"], [9, 1, 3, "y"], [12, 1, 2, "n"], [14, 1, 2, "q"], [5, 2, 2, "q"], [7, 2, 5, "y"], [12, 2, 2, "n"], [14, 2, 4, "q"], [3, 3, 2, "q"], [5, 3, 4, "Y"], [9, 3, 2, "y"], [11, 3, 1, "Y"], [12, 3, 2, "n"], [14, 3, 6, "q"], [2, 4, 1, "q"], [3, 4, 4, "Y"], [7, 4, 1, "n"], [8, 4, 1, "Y"], [9, 4, 1, "y"], [10, 4, 2, "Y"], [12, 4, 2, "n"], [14, 4, 1, "q"], [15, 4, 2, "x"], [17, 4, 3, "y"], [20, 4, 1, "x"], [1, 5, 1, "q"], [2, 5, 1, "y"], [3, 5, 4, "Y"], [7, 5, 1, "n"], [8, 5, 1, "Y"], [9, 5, 1, "y"], [10, 5, 2, "Y"], [12, 5, 2, "n"], [14, 5, 1, "x"], [15, 5, 1, "y"], [16, 5, 5, "N"], [21, 5, 1, "y"], [0, 6, 1, "q"], [1, 6, 1, "Y"], [2, 6, 1, "y"], [3, 6, 4, "Y"], [7, 6, 1, "n"], [8, 6, 1, "Y"], [9, 6, 1, "y"], [10, 6, 2, "Y"], [12, 6, 1, "n"], [13, 6, 1, "x"], [14, 6, 1, "n"], [15, 6, 1, "N"], [16, 6, 1, "y"], [17, 6, 2, "N"], [19, 6, 2, "y"], [21, 6, 1, "N"], [22, 6, 1, "x"], [0, 7, 1, "q"], [1, 7, 1, "Y"], [2, 7, 1, "y"], [3, 7, 4, "Y"], [7, 7, 1, "n"], [8, 7, 1, "Y"], [9, 7, 1, "y"], [10, 7, 2, "Y"], [12, 7, 1, "n"], [13, 7, 1, "x"], [14, 7, 1, "N"], [15, 7, 1, "y"], [16, 7, 1, "N"], [17, 7, 2, "Y"], [19, 7, 1, "N"], [20, 7, 1, "y"], [21, 7, 1, "N"], [22, 7, 1, "y"], [23, 7, 1, "q"], [0, 8, 1, "q"], [1, 8, 2, "Y"], [3, 8, 1, "y"], [4, 8, 1, "Y"], [5, 8, 1, "y"], [6, 8, 2, "n"], [8, 8, 1, "y"], [9, 8, 2, "Y"], [11, 8, 1, "y"], [12, 8, 1, "n"], [13, 8, 1, "x"], [14, 8, 3, "N"], [17, 8, 2, "Y"], [19, 8, 1, "N"], [20, 8, 1, "y"], [21, 8, 1, "N"], [22, 8, 1, "y"], [23, 8, 1, "q"], [0, 9, 1, "q"], [1, 9, 2, "Y"], [3, 9, 1, "y"], [4, 9, 1, "Y"], [5, 9, 1, "y"], [6, 9, 2, "n"], [8, 9, 1, "y"], [9, 9, 2, "Y"], [11, 9, 1, "y"], [12, 9, 1, "n"], [13, 9, 1, "x"], [14, 9, 1, "n"], [15, 9, 1, "N"], [16, 9, 4, "y"], [20, 9, 2, "N"], [22, 9, 1, "x"], [1, 10, 1, "q"], [2, 10, 1, "Y"], [3, 10, 1, "y"], [4, 10, 1, "Y"], [5, 10, 1, "y"], [6, 10, 2, "n"], [8, 10, 1, "y"], [9, 10, 2, "Y"], [11, 10, 1, "y"], [12, 10, 2, "n"], [14, 10, 1, "x"], [15, 10, 1, "y"], [16, 10, 5, "N"], [21, 10, 1, "x"], [2, 11, 1, "q"], [3, 11, 3, "Y"], [6, 11, 2, "n"], [8, 11, 4, "Y"], [12, 11, 2, "n"], [14, 11, 2, "q"], [16, 11, 2, "x"], [18, 11, 1, "y"], [19, 11, 2, "x"], [3, 12, 2, "q"], [5, 12, 1, "Y"], [6, 12, 1, "n"], [7, 12, 5, "Y"], [12, 12, 2, "n"], [14, 12, 6, "q"], [5, 13, 2, "q"], [7, 13, 7, "n"], [14, 13, 4, "q"], [7, 14, 2, "q"], [9, 14, 5, "n"], [14, 14, 2, "q"], [9, 15, 5, "q"]];
  // Art-space bounds of BALE_PX, shared by drawBale (offsets), the hover extent and the test hook.
  const BALE_DRAW = (() => {
  let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
    for (const [rx, ry, rw] of BALE_PX) {
    minX = Math.min(minX, rx); minY = Math.min(minY, ry);
    maxX = Math.max(maxX, rx + rw); maxY = Math.max(maxY, ry + 1);
  }
    const w = maxX - minX, h = maxY - minY;
    return { w, h, halfW: w / 2, top: h, minX, minY, maxX, maxY, aspect: Math.round(w / h * 100) / 100, area: w * h };
  })();
  function drawBale(bale, sx, sy, s) {
    shadow(sx, sy, s * 1.15, 14);
    const u = s, flip = Math.floor(bale.roll / 5) % 2;
    ctx.save(); ctx.translate(Math.round(sx), 0); if (flip) ctx.scale(-1, 1);
    drawPixels(BALE_PX, -BALE_DRAW.halfW * u, sy - BALE_DRAW.top * u, u); ctx.restore();
  }
  const DIRECTION_SIGNS = { left: '← DUŃCY', right: 'WIELKIE KSIĘSTWO LITEWSKIE →' };
  function directionSignEdges(W) {   // screen x of the map's west/east edge and how visible each sign is (0..1)
    if (!lastCam || !MAP) return { left: 0, right: 0, leftX: 0, rightX: W };
    const leftX = lastCam.S(0, 0)[0], rightX = lastCam.S(MAP.w, 0)[0];
    const fade = x => Math.max(0, Math.min(1, x));
    // the camera stops at the edge (leftX = 0 / rightX = W); the sign fades in over the last quarter screen before it
    return { leftX: Math.max(0, leftX), rightX: Math.min(W, rightX), left: fade((leftX + W * .25) / (W * .25)), right: fade((W * 1.25 - rightX) / (W * .25)) };
  }
  // Large lumpy clouds (B06): each cloud is one connected, non-uniform silhouette made of
  // overlapping blobs, drawn as a single path so one fill paints the whole layer (no naive
  // per-area fill inflation). Blob coordinates live in 50 px cloud-local units at scale 1
  // (cached geometry); PUFF_BLOBS is the same silhouette shrunk 62% and tucked a touch
  // higher, so the soft white body sits inside the darker multiply shade.
  const CLOUD_UNIT = 50, CLOUD_ALPHA_CAP = .22;   // shadows ~2x darker than before, but capped
  const CLOUD_BLOBS = [
    [0, .9, 7.6, 2.0], [-3.0, -.6, 4.3, 2.7], [3.1, -.4, 4.1, 2.5],
    [-.4, -2.5, 4.7, 2.2], [-4.7, -2.3, 3.0, 1.9], [4.6, -1.9, 2.8, 1.7], [1.7, -3.7, 2.3, 1.4],
  ];
  const PUFF_BLOBS = CLOUD_BLOBS.map(b => [b[0] * .62, b[1] * .62 - .12, b[2] * .62, b[3] * .62]);
  // Culling margins derive from the actual silhouette bounds (x largest cloud), so a cloud
  // renders whenever its shape can reach the screen and is skipped otherwise.
  const CLOUD_GEOM = (() => {
    let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
    for (const [dx, dy, rx, ry] of CLOUD_BLOBS) {
      minX = Math.min(minX, dx - rx); maxX = Math.max(maxX, dx + rx);
      minY = Math.min(minY, dy - ry); maxY = Math.max(maxY, dy + ry);
    }
    const unitW = (maxX - minX) * CLOUD_UNIT, unitH = (maxY - minY) * CLOUD_UNIT;
    const maxScale = Math.max(...CLOUDS.map(c => c.scale));
    return { unitW, unitH, halfW: unitW / 2, halfH: unitH / 2,
             marginX: Math.ceil(unitW / 2 * maxScale) + 8, marginY: Math.ceil(unitH / 2 * maxScale) + 8,
             blobs: CLOUD_BLOBS.length };
  })();
  function drawClouds(ox, oy, zoom, sx0, sy0, sw, sh) {
    // Visual-only weather: drifting translucent cloud shadows and soft puffs. They never touch
    // SOLID or gameplay state, and seven bounded sprites keep the cost low on mobile.
    ctx.save();
    for (const cloud of CLOUDS) {
      const x = (cloud.x + time * cloud.speed) % MAP.w, y = cloud.y;
      if (x < sx0 - CLOUD_GEOM.marginX || x > sx0 + sw + CLOUD_GEOM.marginX ||
          y < sy0 - CLOUD_GEOM.marginY || y > sy0 + sh + CLOUD_GEOM.marginY) continue;
      const sx = ox + x * zoom, sy = oy + y * zoom, k = cloud.scale * zoom * CLOUD_UNIT;
      const shadowA = Math.min(cloud.alpha * 2, CLOUD_ALPHA_CAP);
      ctx.globalCompositeOperation = 'multiply'; ctx.fillStyle = `rgba(90,100,116,${shadowA})`;
      ctx.beginPath();
      for (const [dx, dy, rx, ry] of CLOUD_BLOBS) ctx.ellipse(sx + dx * k, sy + dy * k, rx * k, ry * k, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalCompositeOperation = 'source-over'; ctx.fillStyle = `rgba(255,255,255,${shadowA * .34})`;
      ctx.beginPath();
      for (const [dx, dy, rx, ry] of PUFF_BLOBS) ctx.ellipse(sx + dx * k, sy + dy * k, rx * k, ry * k, 0, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }
function drawFrodo(sx, sy, s) {
    shadow(sx, sy, s * .78, 6);
    const row = { down: 0, up: 1, right: 2, left: 3 }[FRODO.dir] || 0;
    const col = FRODO.moving ? Math.floor(FRODO.step) % 2 : 0;
    const lickScale = FRODO.action === 'lick' ? .8 : 1, size = 27 * s * lickScale, top = sy - size * 29 / 32;
    ctx.imageSmoothingEnabled = false;
    const IDLE_POSE = { sit: [0], pant: [1, 2], scratch: [3, 0], sniff: [4], lie: [5], lick: [6, 7, 8, 7, 8, 9] };
    const poses = FRODO_IDLE && !FRODO.moving && IDLE_POSE[FRODO.action];
    if (poses) {   // idle poses from img/frodo_idle.png (drawn facing right; mirrored for left)
      const rate = FRODO.action === 'lick' ? 5 : FRODO.action === 'scratch' ? 9 : 3, f = poses[Math.floor(FRODO.idleAnim * rate) % poses.length];
      ctx.save(); ctx.translate(sx, 0); if (FRODO.dir === 'left') ctx.scale(-1, 1);
      ctx.drawImage(FRODO_IDLE, f * 32, 0, 32, 32, -size / 2, top, size, size); ctx.restore();
      return;
    }
    ctx.drawImage(DOGIMG, col * 32, row * 32, 32, 32, sx - size / 2, top, size, size);
    if (FRODO.action === 'lick') { ctx.fillStyle = '#ef8b9b'; ctx.fillRect(sx + (FRODO.dir === 'left' ? -7 : 5) * s * lickScale, sy - 10 * s * lickScale, 2 * s * lickScale, 4 * s * lickScale); }
    if (FRODO.action === 'scratch') {
      ctx.fillStyle = '#e6c38a';
      const side = FRODO.dir === 'left' ? -1 : 1, bob = Math.sin(FRODO.idleAnim * 18) * 2;
      ctx.fillRect(sx + side * 7 * s, sy - (12 + bob) * s, 3 * s, 5 * s);
      ctx.fillRect(sx + side * 10 * s, sy - (10 + bob) * s, 2 * s, 2 * s);
    }
  }
  function drawNpc(n, sx, sy, s) {
    shadow(sx, sy, s, 8);
    if (n.id === 'soltys') {
      window.drawSoltysBeer(ctx, sx, sy, s, time);
      ctx.imageSmoothingEnabled = false;
      return;
    }
    // The selected hero takes the matching NPC's place. Keep the original id
    // for dialogue and saves, but render the Arek-style player sprite there.
    if (n.id === selectedCharacter && selectedCharacter !== 'arek' && PLAYER_SHEETS.arek) {
      const player = PLAYER_SHEETS.arek, meta = player.meta;
      const anim = meta.anims['walk_' + (n.face || 'down')] || meta.anims.walk_down;
      const f = anim.frames[Math.floor(time * 3) % anim.frames.length], h = CHAR_H * s;
      const scale = h / (f.h - meta.foot - 14), w = f.w * scale, hh = f.h * scale;
      ctx.save(); ctx.imageSmoothingEnabled = true; ctx.drawImage(player.sheet, f.x, f.y, f.w, f.h, sx - w / 2, sy + meta.foot * scale - hh, w, hh); ctx.restore();
      return;
    }
    const i = NPC_IDX[n.id], h = CHAR_H * s * (n.id === 'grandpa' ? 1.05 : 1);
    if (i == null || NPCIMG.width < (i + 1) * 130) return;   // atlas cell not built yet
    const scale = h / (170 - 6 - 14), w = 130 * scale, hh = 170 * scale;
    const bob = Math.sin(time * 2.4 + i) * .6 * s;
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(NPCIMG, i * 130, 0, 130, 170, sx - w / 2, sy + 6 * scale - hh + bob, w, hh);
    ctx.imageSmoothingEnabled = false;
    // quest marker
    const state = n.id === 'grandpa' ? (Q.grandpa === 2 ? 2 : questsDone() >= 3 ? 'ready' : Q.grandpa) : Q[n.id];
    const ready = (n.id === 'kasia' && Q.kasia === 1 && mushroomCount() >= MUSHROOMS_NEEDED) || (n.id === 'damian' && Q.damian === 1 && Q.cap) || (n.id === 'marcin' && Q.marcin === 1 && Q.orange) || state === 'ready';
    const mark = state === 0 ? '!' : ready ? '?' : null;
    if (mark && !n.rival) {
      const my = sy - h - 12 * s + Math.sin(time * 5 + i) * 1.5 * s;
      ctx.fillStyle = '#10163a'; ctx.fillRect(sx - 5 * s, my - 6 * s, 10 * s, 11 * s);
      ctx.fillStyle = mark === '!' ? '#ffd21f' : '#7cff6b'; ctx.font = `${9 * s}px Silkscreen`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(mark, sx, my);
    }
  }
  // Pickup pixel art (12x12 / 13x12 px), one palette; drawn as merged runs so each sprite is ~50 fillRects.
  const PICK_PAL = {"C": "#e9e1cf", "D": "#bfb39a", "G": "#2f7a33", "R": "#d8262c", "T": "#d6ccb6", "c": "#fffdf5", "g": "#5dbb4a", "h": "#ff7a70", "o": "#3a1216", "r": "#a3161d", "s": "#6b3b1a", "t": "#f3ecdd", "w": "#fff1ea"};
  const APPLE_PX = [[7,0,1,"s"],[8,0,2,"g"],[6,1,1,"s"],[7,1,1,"g"],[8,1,1,"G"],[9,1,1,"g"],[3,2,3,"o"],[6,2,1,"s"],[7,2,4,"o"],[2,3,1,"o"],[3,3,2,"h"],[5,3,5,"R"],[10,3,1,"r"],[11,3,1,"o"],[1,4,1,"o"],[2,4,1,"h"],[3,4,1,"w"],[4,4,1,"h"],[5,4,6,"R"],[11,4,1,"r"],[12,4,1,"o"],[1,5,1,"o"],[2,5,2,"h"],[4,5,7,"R"],[11,5,1,"r"],[12,5,1,"o"],[1,6,1,"o"],[2,6,9,"R"],[11,6,1,"r"],[12,6,1,"o"],[1,7,1,"o"],[2,7,8,"R"],[10,7,2,"r"],[12,7,1,"o"],[2,8,1,"o"],[3,8,6,"R"],[9,8,2,"r"],[11,8,1,"o"],[2,9,1,"o"],[3,9,1,"r"],[4,9,4,"R"],[8,9,3,"r"],[11,9,1,"o"],[3,10,1,"o"],[4,10,6,"r"],[10,10,1,"o"],[4,11,3,"o"],[8,11,2,"o"]];
  const MUSH_PX = [[4,0,5,"o"],[2,1,2,"o"],[4,1,4,"c"],[8,1,1,"C"],[9,1,2,"o"],[1,2,1,"o"],[2,2,8,"c"],[10,2,1,"C"],[11,2,1,"o"],[0,3,1,"o"],[1,3,2,"c"],[3,3,1,"w"],[4,3,5,"c"],[9,3,2,"C"],[11,3,1,"D"],[12,3,1,"o"],[0,4,1,"o"],[1,4,9,"c"],[10,4,1,"C"],[11,4,1,"D"],[12,4,1,"o"],[0,5,1,"o"],[1,5,1,"C"],[2,5,7,"c"],[9,5,2,"C"],[11,5,1,"D"],[12,5,1,"o"],[1,6,1,"o"],[2,6,8,"C"],[10,6,1,"D"],[11,6,1,"o"],[2,7,2,"o"],[4,7,1,"D"],[5,7,3,"T"],[8,7,1,"D"],[9,7,2,"o"],[3,8,1,"o"],[4,8,3,"t"],[7,8,2,"T"],[9,8,1,"o"],[3,9,1,"o"],[4,9,3,"t"],[7,9,2,"T"],[9,9,1,"o"],[3,10,1,"o"],[4,10,3,"t"],[7,10,2,"T"],[9,10,1,"o"],[4,11,5,"o"]];
  Object.assign(PICK_PAL,   // hay bale colours
    {"x": "#c9913c", "n": "#b07b30", "Y": "#dcaa4a", "y": "#f4d27a", "N": "#8a5a22", "q": "#5a3a17"});
  const PIXEL_CACHE = new WeakMap();
  function drawPixels(runs, x, y, u) {   // cache run-based art once per effective zoom; draws one image instead of ~50 fillRects
    let scales = PIXEL_CACHE.get(runs);
    if (!scales) PIXEL_CACHE.set(runs, scales = new Map());
    const key = Math.round(u * 1000) / 1000;
    let sprite = scales.get(key);
    if (!sprite) {
      let width = 0, height = 0;
      for (const [rx, ry, rw] of runs) { width = Math.max(width, rx + rw); height = Math.max(height, ry + 1); }
      sprite = document.createElement('canvas');
      sprite.width = Math.max(1, Math.ceil(width * key)); sprite.height = Math.max(1, Math.ceil(height * key));
      const px = sprite.getContext('2d');
      for (const [rx, ry, rw, c] of runs) { px.fillStyle = PICK_PAL[c]; px.fillRect(Math.round(rx * key), Math.round(ry * key), Math.ceil(rw * key), Math.ceil(key)); }
      scales.set(key, sprite);
    }
    ctx.drawImage(sprite, Math.round(x), Math.round(y));
  }
  function drawApple(sx, sy, s) {
    const b = Math.sin(time * 3 + sx * .1) * s * .45, u = s * .85;
    ctx.fillStyle = 'rgba(20,34,12,.35)'; ctx.fillRect(sx - 4 * s, sy + .5 * s, 8 * s, 1.5 * s);
    drawPixels(APPLE_PX, sx - 6.5 * u, sy - 12 * u - b, u);
  }
  function drawMushroom(sx, sy, s) {
    const b = Math.sin(time * 3 + sx * .1) * s * .45, u = s * .8;
    ctx.fillStyle = 'rgba(20,34,12,.35)'; ctx.fillRect(sx - 3.5 * s, sy + .5 * s, 7 * s, 1.5 * s);
    drawPixels(MUSH_PX, sx - 6.5 * u, sy - 12 * u - b, u);
  }
  function drawTrashBag(sx, sy, s) {   // tied black bag, cell 2 of img/trash.png (32 px); pixel fallback until it loads
    const b = Math.sin(time * 2.4 + sx * .07) * s * .35;
    ctx.fillStyle = 'rgba(20,34,12,.35)'; ctx.fillRect(sx - 5 * s, sy + .5 * s, 10 * s, 1.5 * s);
    if (TRASH_IMG) {
      const d = 16 * s; ctx.imageSmoothingEnabled = false;
      ctx.drawImage(TRASH_IMG, 2 * 32, 0, 32, 32, sx - d / 2, sy - d + 2 * s - b, d, d);
      return;
    }
    const px = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(sx + x * s, sy + y * s - b, w * s, h * s); };
    px(-5, -8, 10, 8, '#1c1f27'); px(-4, -9, 8, 1, '#1c1f27'); px(-1, -11, 2, 2, '#2b2f3a'); px(-3, -7, 2, 3, '#4a5061');
  }
  function drawCap(sx, sy, s) {
    const b = Math.sin(time * 3) * s;
    const px = (x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(sx + x * s, sy + y * s - b, w * s, h * s); };
    px(-4, -5, 7, 4, '#1f5fd1'); px(-3, -6, 5, 1, '#1f5fd1'); px(2, -2, 4, 1.5, '#163f8c'); px(-2, -5, 2, 1, '#6fa3ff');
    if (Math.floor(time * 4) % 2) { ctx.fillStyle = '#fff'; ctx.fillRect(sx + 5 * s, sy - 9 * s, s, s); }
  }
  function box(x, y, w, h, u) {
    ctx.fillStyle = 'rgba(8,12,40,0.94)'; ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = '#f5f0e0'; ctx.lineWidth = Math.max(2, u * .35); ctx.strokeRect(x + u * .8, y + u * .8, w - u * 1.6, h - u * 1.6);
  }
  function wrapText(text, maxW) {
    const words = text.split(' '), out = []; let cur = '';
    for (const w of words) { const t = cur ? cur + ' ' + w : w; if (ctx.measureText(t).width > maxW && cur) { out.push(cur); cur = w; } else cur = t; }
    if (cur) out.push(cur); return out;
  }
  const fmtTime = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  // Position readout: map pixels and real-world lat/lon from map.json's bbox.
  function drawCoords(U, H, big, mx, my, mw, mh) {
    const player = `${heroName()} ${Math.round(P.x)},${Math.round(P.y)}  ${mapCoordinateText(P.x, P.y)}`;
    if (!big) {
      ctx.font = `${U * 1.1}px Silkscreen`; ctx.textAlign = 'left';
      const tw = ctx.measureText(player).width;
      ctx.fillStyle = 'rgba(8,12,40,.55)'; ctx.fillRect(U * 1.2, H - U * 2.4, tw + U * .8, U * 2);
      ctx.fillStyle = 'rgba(255,255,255,.8)'; ctx.fillText(player, U * 1.6, H - U * 1.35);
      // A03: one small world hover label beside the coordinates (state fn above).
      const hl = worldHoverLabelState(U, cvs.width, H);
      if (hl.shown) {
        ctx.font = `${U * 1.1}px Silkscreen`; ctx.textAlign = 'left';
        ctx.fillStyle = 'rgba(8,12,40,.55)'; ctx.fillRect(hl.x, hl.y, hl.w, hl.h);
        ctx.fillStyle = 'rgba(255,255,255,.8)'; ctx.fillText(hl.text, hl.x + U * .4, hl.y + hl.h * .55);
      }
      return;
    }
    const cursor = mapCursor.seen ? `KURSOR ${Math.round(mapCursor.x)},${Math.round(mapCursor.y)}  ${mapCoordinateText(mapCursor.x, mapCursor.y)}` : 'KURSOR / TAP - kliknij mapę';
    ctx.font = `${U * 1.25}px Silkscreen`; ctx.textAlign = 'left';
    const tw = Math.max(ctx.measureText(player).width, ctx.measureText(cursor).width) + U * 2;
    const x = Math.max(U, mx), y = Math.min(H - U * 5.2, my + mh + U);
    ctx.fillStyle = 'rgba(8,12,40,.84)'; ctx.fillRect(x, y, tw, U * 4.2);
    ctx.fillStyle = '#f5f0e0'; ctx.fillText(player, x + U, y + U * 1.25);
    ctx.fillStyle = '#ffd21f'; ctx.fillText(cursor, x + U, y + U * 3);
  }

  /* ---------- A03: small world hover label in the coordinate HUD ----------
     One short strip directly above the bottom-left coordinate readout, painted
     from the A02 picker (worldPickAt) at the live pointer's world position.
     It is deliberately NOT the big M-map floating box (mapHoverLabel keeps its
     own independent draw). Rules: only a real mouse pointer on the canvas (a
     touch tap/pen aiming must never leave a stuck label), no label on ground/
     terrain (the HUD already shows coordinates), none in title/end scenes,
     rooms, dialogue or over the big M-map, none after pointerleave, and the
     measured text is clamped with an ellipsis so the strip never leaves the
     viewport. The same function feeds the draw call and the test accessor
     __game.worldHoverLabelState(), so tests assert exactly what is painted. */
  function worldHoverLabelState(U, W, H) {
    const none = { shown: false, text: '', x: 0, y: 0, w: 0, h: 0 };
    if (scene !== 'play' || ROOM || showMap || talk) return none;
    if (!lastCam || !pointer.seen || pointer.kind !== 'mouse') return none;
    const [wx, wy] = lastCam.toWorld(pointer.x, pointer.y);
    const p = worldPickAt(wx, wy);
    if (!p || !p.label || p.kind === 'ground') return none;   // terrain stays anonymous
    let text = String(p.label);
    ctx.font = `${U * 1.1}px Silkscreen`; ctx.textAlign = 'left';
    const maxW = W - U * 2.0;   // keep the strip fully inside the viewport
    if (ctx.measureText(text).width > maxW) {
      while (text.length > 1 && ctx.measureText(text + '…').width > maxW) text = text.slice(0, -1);
      text += '…';
    }
    const tw = ctx.measureText(text).width, h = U * 1.6, w = tw + U * .8;
    const x = U * 1.2, y = H - U * 2.4 - h;   // sits directly above the coordinate box
    return { shown: true, text, x, y, w, h };
  }

  /* ---------- title / splash screen: pixel-art remake of the "Chłopków" sign + church photo ---------- */
  function outlined(txt, x, y, fill, px) {   // pixel-font text with a hard 8-way dark outline
    ctx.fillStyle = '#10163a';
    for (const [dx, dy] of [[-1, -1], [0, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [0, 1], [1, 1]]) ctx.fillText(txt, x + dx * px, y + dy * px);
    ctx.fillStyle = fill; ctx.fillText(txt, x, y);
  }
  function drawSplash(W, H, U) {
    ctx.fillStyle = '#6fb6ea'; ctx.fillRect(0, 0, W, H);
    if (SPLASH) {   // cover-fit with a slow Ken-Burns drift toward the church
      const k = Math.max(W / SPLASH.width, H / SPLASH.height) * (1.04 + .02 * Math.sin(time * .15));
      const dw = SPLASH.width * k, dh = SPLASH.height * k;
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(SPLASH, (W - dw) / 2 - Math.sin(time * .1) * U * .8, (H - dh) * .55, dw, dh);
    }
    // golden-hour sparkles drifting over the grass
    for (let i = 0; i < 18; i++) {
      const x = ((i * 137.5 + time * (8 + i % 5)) % 100) / 100 * W, y = H * (.62 + ((i * 53) % 30) / 100) - Math.sin(time * 1.3 + i) * U;
      ctx.fillStyle = `rgba(255,238,160,${.35 + .35 * Math.sin(time * 3 + i * 1.7)})`; ctx.fillRect(x, y, U * .35, U * .35);
    }
    // title block on the calm upper-left sky
    const tx = W * .06, ty = H * .12;
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
    ctx.font = `${U * 5.4}px Silkscreen`; outlined(T.title.split(' ').slice(0, -1).join(' '), tx, ty, '#ffd21f', Math.max(2, U * .35));
    ctx.font = `${U * 7}px Silkscreen`; outlined(T.title.split(' ').slice(-1)[0], tx, ty + U * 7.2, '#ffffff', Math.max(2, U * .4));
    ctx.font = `${U * 1.6}px Silkscreen`; outlined(LANG === 'pl' ? 'GMINA PLATERÓW · MAZOWSZE' : 'PLATERÓW COMMUNE · MASOVIA', tx, ty + U * 12.4, '#f5f0e0', Math.max(1, U * .2));
    // Character selection (same geometry is used by pointer input, including before first paint).
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (const button of characterButtonBounds()) {
      const isSelected = button.id === selectedCharacter;
      ctx.fillStyle = isSelected ? 'rgba(255, 210, 31, 0.3)' : 'rgba(8, 12, 40, 0.72)';
      ctx.fillRect(button.x, button.y, button.w, button.h);
      ctx.strokeStyle = isSelected ? '#ffd21f' : '#c8cee0';
      ctx.lineWidth = Math.max(2, U * .35);
      ctx.strokeRect(button.x, button.y, button.w, button.h);
      const player = PLAYER_SHEETS[button.id];
      const anim = player && (player.meta.anims.walk_down || player.meta.anims.idle_down);
      const frame = anim && anim.frames[0];
      if (frame) {
        const s = Math.min(button.w * .58 / frame.w, button.h * .64 / frame.h);
        const w = frame.w * s, h = frame.h * s;
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(player.sheet, frame.x, frame.y, frame.w, frame.h,
          button.x + (button.w - w) / 2, button.y + U * .4, w, h);
      }
      ctx.font = `${Math.max(U * 1.3, 10 * button.w / (U * 7))}px Silkscreen`;
      ctx.fillStyle = isSelected ? '#ffd21f' : '#f5f0e0';
      const label = T.names[button.id] || button.id.toUpperCase();
      ctx.fillText(label, button.x + button.w / 2, button.y + button.h * .86);
    }
    if (hasSave) {
      ctx.font = `${U * 1.8}px Silkscreen`; ctx.fillStyle = '#fff7d6';
      ctx.fillText(`${LANG === 'pl' ? 'BOHATER' : 'HERO'}: ${heroName()}`, W / 2, H * .37);
      ctx.font = `${U * 1.15}px Silkscreen`; ctx.fillStyle = '#c8cee0';
      ctx.fillText(LANG === 'pl' ? 'N - ZMIEŃ IMIĘ   R - NOWA GRA' : 'N - CHANGE NAME   R - NEW GAME', W / 2, H * .405);
    }
    // prompt + help on a translucent strip at the bottom
    ctx.fillStyle = 'rgba(8,12,40,.72)'; ctx.fillRect(0, H - U * 9.5, W, U * 9.5);
    ctx.textAlign = 'center';
    if (Math.floor(time * 2) % 2) { ctx.font = `${U * 2.5}px Silkscreen`; outlined(hasSave ? T.cont : T.start, W / 2, H - U * 6.2, '#ffd21f', Math.max(1, U * .25)); }
    ctx.font = `${U * 1.4}px Silkscreen`; ctx.fillStyle = '#c8cee0'; ctx.fillText(T.help, W / 2, H - U * 2.6);
  }

  /* ---------- render ---------- */
  function render() {
    const W = cvs.width, H = cvs.height;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = ROOM ? '#1a1410' : '#5f9c3b'; ctx.fillRect(0, 0, W, H);
    camX += (P.x - camX) * .12; camY += (P.y - 16 - camY) * .12;
    const vw = W / zoom, vh = H / zoom;
    const cx = MAP.w < vw ? MAP.w / 2 : Math.max(vw / 2, Math.min(MAP.w - vw / 2, camX)), cy = MAP.h < vh ? MAP.h / 2 : Math.max(vh / 2, Math.min(MAP.h - vh / 2, camY));
    const ox = Math.round(W / 2 - cx * zoom), oy = Math.round(H / 2 - cy * zoom);
    const sx0 = Math.max(0, Math.floor(-ox / zoom)), sy0 = Math.max(0, Math.floor(-oy / zoom));
    const sw = Math.max(1, Math.min(MAP.w - sx0, Math.ceil(W / zoom) + 2)), sh = Math.max(1, Math.min(MAP.h - sy0, Math.ceil(H / zoom) + 2));
    ctx.drawImage(GROUND, sx0, sy0, sw, sh, ox + sx0 * zoom, oy + sy0 * zoom, sw * zoom, sh * zoom);
    const S = (x, y) => [ox + x * zoom, oy + y * zoom];
    lastCam = { ox, oy, zoom, S, toWorld: (px, py) => [(px - ox) / zoom, (py - oy) / zoom] };
    drawClouds(ox, oy, zoom, sx0, sy0, sw, sh);
    for (const d of dust) { const k = d.t / .5; ctx.fillStyle = `rgba(235,220,180,${.55 * (1 - k)})`; const s = (2 + k * 3) * zoom; ctx.fillRect(ox + (d.x - 2 - k * 4) * zoom, oy + (d.y - 2 - k * 3) * zoom, s, s); }

    // everything that stands on the ground, sorted by baseline
    const inView = (x, y) => x > sx0 - 60 && x < sx0 + sw + 60 && y > sy0 - 60 && y < sy0 + sh + 80;
    const draw = [];
    for (const o of MAP.objects) if (o.x < sx0 + sw && o.x + o.w > sx0 && o.y < sy0 + sh && o.y + o.h > sy0) draw.push({ base: o.base, fn: () => ctx.drawImage(OBJ, o.x, o.y, o.w, o.h, ox + o.x * zoom, oy + o.y * zoom, o.w * zoom, o.h * zoom) });
    if (ROOM && ROOM.soltys) draw.push({ base: ROOM.soltys.y, fn: () => { const [a, b] = S(ROOM.soltys.x, ROOM.soltys.y); shadow(a, b, zoom, 8); if (window.CHURCH_ART.soltys) window.fitSprite(ctx, window.CHURCH_ART.soltys, a - 14 * zoom, b - 44 * zoom, 28 * zoom, 44 * zoom); else window.drawSoltys(ctx, a, b, zoom, time); ctx.imageSmoothingEnabled = false; } });
    else if (!ROOM) {
    ITEMS.apples.forEach((a, i) => { if (!Q.apples.includes(i) && inView(a.x, a.y)) draw.push({ base: a.y, fn: () => drawApple(...S(a.x, a.y), zoom) }); });
    (Q.mushroomSpots || []).forEach((m, i) => { if (!(Q.mushrooms || []).includes(i) && inView(m.x, m.y)) draw.push({ base: m.y, fn: () => drawMushroom(...S(m.x, m.y), zoom) }); });
    (Q.trashSpots || []).forEach((t, i) => { if (!(Q.trash || []).includes(i) && inView(t.x, t.y)) draw.push({ base: t.y, fn: () => drawTrashBag(...S(t.x, t.y), zoom) }); });
    if (!Q.cap && inView(ITEMS.cap.x, ITEMS.cap.y)) draw.push({ base: ITEMS.cap.y, fn: () => drawCap(...S(ITEMS.cap.x, ITEMS.cap.y), zoom) });
    for (const b of BALES) if (inView(b.x, b.y)) draw.push({ base: b.y, fn: () => drawBale(b, ...S(b.x, b.y), zoom) });
    for (const n of ITEMS.npcs) if (inView(n.x, n.y)) draw.push({ base: n.y, fn: () => drawNpc(n, ...S(n.x, n.y), zoom) });
    }
    draw.push({ base: P.y, fn: () => drawArek(...S(P.x, P.y), zoom) });
    if (scene === 'play' || scene === 'end') draw.push({ base: FRODO.y, fn: () => drawFrodo(...S(FRODO.x, FRODO.y), zoom) });
    if (!ROOM) HOOKS.world.forEach(f => f((base, fn) => draw.push({ base, fn }), S, inView));
    draw.sort((a, b) => a.base - b.base).forEach(d => d.fn());
    const cemetery = !ROOM && MAP.pois.find(p => p.key === 'cemetery');
    cemeteryZone();   // decides the sunglasses for the next frame too
    if (scene === 'play' && !showMap && cemetery && Math.hypot(P.x - cemetery.x, P.y - cemetery.y) < (SPOT_R.cemetery + 35)) {
      ctx.save(); ctx.globalCompositeOperation = 'saturation'; ctx.globalAlpha = .16; ctx.fillStyle = '#777'; ctx.fillRect(0, 0, W, H); ctx.restore();
    }

    if (ROOM && ROOM.candles) for (const c of ROOM.candles) {   // flickering candle flames
      const fl = Math.sin(time * 13 + c.x) * .5 + Math.sin(time * 7.3 + c.x * 3) * .5, [a, b] = S(c.x, c.y);
      ctx.fillStyle = 'rgba(255,210,90,.18)'; ctx.fillRect(a - 3 * zoom, b - 4 * zoom, 6 * zoom, 6 * zoom);
      ctx.fillStyle = '#ffb02e'; ctx.fillRect(a - zoom, b - (2 + fl * .6) * zoom, 2 * zoom, (3 + fl * .6) * zoom);
      ctx.fillStyle = '#fff4c0'; ctx.fillRect(a - zoom * .5, b - (1 + fl * .4) * zoom, zoom, 2 * zoom);
    }
    for (const f of fx) { ctx.globalAlpha = 1 - f.t / 1.2; ctx.fillStyle = f.c; const s = zoom * 2; ctx.fillRect(ox + f.x * zoom - s / 2, oy + f.y * zoom - s / 2, s, s); }
    ctx.globalAlpha = 1;
    if (DEBUG) { ctx.strokeStyle = 'cyan'; for (const s of MAP.pois) { ctx.beginPath(); ctx.arc(ox + s.x * zoom, oy + s.y * zoom, (s.r || SPOT_R[s.key] || 50) * zoom, 0, 7); ctx.stroke(); } }

    const U = Math.min(W, H * 1.6) / 100;
    ctx.textBaseline = 'middle';
    const near = scene === 'play' && !talk ? nearThing() : null;
    if (near && !near.npc) {
      const [bx, by0] = S(P.x, P.y - CHAR_H - 8), by = by0 + Math.sin(time * 6) * U * .4;
      ctx.textAlign = 'center'; ctx.fillStyle = '#10163a'; ctx.fillRect(bx - U * 2.2, by - U * 2.2, U * 4.4, U * 4.4);
      ctx.fillStyle = '#ffd21f'; ctx.font = `${U * 3}px Silkscreen`; ctx.fillText('…', bx, by);
    }
    // HUD: apples + quest log
    if (scene === 'play' || scene === 'end') {
      const qx = U * 2, qy = U * 2, qw = U * 40, lines = [];
      if (Q.kasia) lines.push([`${T.quests[0]} (${Math.min(mushroomCount(), MUSHROOMS_NEEDED)}/${MUSHROOMS_NEEDED})`, Q.kasia === 2]);
      if (Q.damian) lines.push([T.quests[1], Q.damian === 2]);
      if (Q.marcin) lines.push([T.quests[2], Q.marcin === 2]);
      if (Q.edytka) lines.push([`${T.edytkaQuest} (${Math.min(Q.edytkaN || 0, EDYTKA_TIMES)}/${EDYTKA_TIMES})`, Q.edytka === 2]);
      if (Q.grandpa || questsDone() >= 3) lines.push([T.quests[3], Q.grandpa === 2]);
      lines.push([`${T.trash} (${trashCount()}/${TRASH_TOTAL})`, trashCount() >= TRASH_TOTAL]);   // A04: trash is a quest-list row, not a primary-HUD counter
      HOOKS.questLog.forEach(f => f(lines));
      const qh = U * (5.2 + lines.length * 2.6);
      ctx.fillStyle = 'rgba(8,12,40,0.78)'; ctx.fillRect(qx, qy, qw, qh);
      // Apple and mushroom counters share one compact line.
      const ax = qx + U * 2.4, ay = qy + U * 2.8;
      drawPixels(APPLE_PX, ax - U * 1.3, ay - U * 1.95, U * .2);   // same pixel art as on the map
      ctx.font = `${U * 2}px Silkscreen`; ctx.fillStyle = '#f5f0e0'; ctx.textAlign = 'left';
      ctx.fillText(`× ${appleCount()}`, ax + U * 2, ay);
      const mxh = qx + U * 13.8, myh = ay;
      drawPixels(MUSH_PX, mxh - U * 1.3, myh - U * 1.95, U * .2);
      ctx.fillStyle = '#f5f0e0'; ctx.fillText(`× ${mushroomCount()}/${MUSHROOMS_TOTAL}`, mxh + U * 2, myh);
      ctx.fillStyle = '#ffd21f'; ctx.fillText(fmtTime(Q.playTime), qx + qw - U * 5.6, ay);
      ctx.font = `${U * 1.45}px Silkscreen`;
      lines.forEach(([txt, done], i) => {
        const ly = qy + U * (6.1 + i * 2.6);
        ctx.strokeStyle = done ? '#7cff6b' : '#f5f0e0'; ctx.lineWidth = Math.max(1, U * .2); ctx.strokeRect(qx + U * 1.6, ly - U * .7, U * 1.4, U * 1.4);
        if (done) { ctx.fillStyle = '#7cff6b'; ctx.fillRect(qx + U * 1.9, ly - U * .4, U * .8, U * .8); }
        ctx.fillStyle = done ? '#8aa08a' : '#f5f0e0'; ctx.fillText(txt.toUpperCase(), qx + U * 3.8, ly);
      });
    }
    if (toast) {
      const a = Math.min(1, (1.6 - toast.t) * 3), y = H * .22 - toast.t * U * 3;
      ctx.globalAlpha = a; ctx.font = `${U * 2.6}px Silkscreen`; ctx.textAlign = 'center';
      const tw = ctx.measureText(toast.text).width + U * 3; ctx.fillStyle = 'rgba(8,12,40,.85)'; ctx.fillRect(W / 2 - tw / 2, y - U * 2.2, tw, U * 4.4);
      ctx.fillStyle = '#ffd21f'; ctx.fillText(toast.text, W / 2, y); ctx.globalAlpha = 1;
    }
    if (talk) {
      const bw = Math.min(W - U * 6, U * 92), bh = U * 17, bx = (W - bw) / 2, by = H - bh - U * 3;
      box(bx, by, bw, bh, U);
      ctx.font = `${U * 2.4}px Silkscreen`; ctx.fillStyle = talk.who === 'arek' ? '#ffd21f' : '#7cd0ff'; ctx.textAlign = 'left';
      ctx.fillText(talk.who === 'arek' ? heroName() : T.names[talk.who], bx + U * 3, by + U * 3.6);
      ctx.fillStyle = '#f5f0e0'; ctx.font = `${U * 2.25}px Silkscreen`;
      const full = talk.lines[talk.i].toUpperCase(), shown = full.slice(0, Math.floor(talkT * 45));
      wrapText(shown, bw - U * 6).slice(0, 3).forEach((l, i) => ctx.fillText(l, bx + U * 3, by + U * (7.6 + i * 3.1)));
      if (shown.length >= full.length && Math.floor(time * 3) % 2) { ctx.fillStyle = '#ffd21f'; ctx.fillText('▼', bx + bw - U * 4, by + bh - U * 2.8); }
    }
    if (scene === 'play' && ROOM) {   // room label instead of the village minimap
      ctx.font = `${U * 1.8}px Silkscreen`; ctx.textAlign = 'right';
      const txt = `${ROOM.kind === 'shop' ? (LANG === 'pl' ? 'SKLEP' : 'SHOP') : T.churchLabel} · ${T.exitHint}`, tw = ctx.measureText(txt).width + U * 2;
      ctx.fillStyle = 'rgba(8,12,40,0.78)'; ctx.fillRect(W - tw - U * 2, U * 2, tw, U * 4); ctx.fillStyle = '#ffd21f'; ctx.fillText(txt, W - U * 3, U * 4);
    }
    // minimap
    if (scene === 'play' && !ROOM) {
      const big = showMap, mw = big ? Math.min(W * .8, H * .8 * MAP.w / MAP.h) : U * 16, mh = mw * MAP.h / MAP.w;
      const mx = big ? (W - mw) / 2 : W - mw - U * 2, my = big ? (H - mh) / 2 : U * 2;
      ctx.globalAlpha = big ? 1 : .9; ctx.fillStyle = '#10163a'; ctx.fillRect(mx - U * .5, my - U * .5, mw + U, mh + U);
      ctx.imageSmoothingEnabled = true; ctx.drawImage(MINI, mx, my, mw, mh); ctx.imageSmoothingEnabled = false; ctx.globalAlpha = 1;
      const dot = (x, y, c, r = .5) => { ctx.fillStyle = c; ctx.fillRect(mx + x / MAP.w * mw - U * r, my + y / MAP.h * mh - U * r, U * r * 2, U * r * 2); };
      for (const n of ITEMS.npcs) if (!n.secret) { const st = n.id === 'grandpa' ? Q.grandpa : Q[n.id]; if (st !== 2) dot(n.x, n.y, '#7cd0ff', big ? .6 : .4); }
      HOOKS.minimap.forEach(f => f((x, y, c) => dot(x, y, c, big ? .45 : .3)));
      dot(P.x, P.y, Math.floor(time * 4) % 2 ? '#ff3b30' : '#fff', big ? .7 : .5);
      if (big) {
        if (mapCursor.seen) {
          dot(mapCursor.x, mapCursor.y, '#ffd21f', .65);
          ctx.strokeStyle = '#ffd21f'; ctx.lineWidth = Math.max(1, U * .18); ctx.strokeRect(mx + mapCursor.x / MAP.w * mw - U * 1.1, my + mapCursor.y / MAP.h * mh - U * 1.1, U * 2.2, U * 2.2);
          const label = mapHoverLabel(mapCursor.x, mapCursor.y, U * 2.2 / mw * MAP.w), place = label && { name: label };
          if (place) {
            ctx.font = `${U * 1.65}px Silkscreen`; ctx.textAlign = 'left';
            const labelW = ctx.measureText(place.name).width + U * 3, sx = mx + mapCursor.x / MAP.w * mw + U * 2.5;
            const sy = my + mapCursor.y / MAP.h * mh - U * 2.5, lx = Math.min(mx + mw - labelW, Math.max(mx, sx)), ly = Math.max(my + U * 5, sy - U * 3);
            ctx.fillStyle = 'rgba(8,12,40,.92)'; ctx.fillRect(lx, ly, labelW, U * 3.8);
            ctx.strokeStyle = '#ffd21f'; ctx.lineWidth = Math.max(1, U * .16); ctx.strokeRect(lx, ly, labelW, U * 3.8);
            ctx.fillStyle = '#ffd21f'; ctx.fillText(place.name, lx + U * 1.5, ly + U * 2.55);
          }
        }
      }
      ctx.font = `${U * 1.1}px Silkscreen`; ctx.textAlign = 'right'; ctx.fillStyle = 'rgba(255,255,255,.75)';
      ctx.fillText('© OPENSTREETMAP CONTRIBUTORS', W - U * 1.5, H - U * 1.2);
      drawCoords(U, H, big, mx, my, mw, mh);
    }
    // Direction signs sit only at the board's edges: "← DUŃCY" when the west edge of the map is in view,
    // "WIELKIE KSIĘSTWO LITEWSKIE →" when the east edge is. They fade in as the edge comes on screen.
    if (scene === 'play' && !ROOM && !showMap && lastCam) {
      const edge = directionSignEdges(W);
      ctx.save(); ctx.textBaseline = 'middle'; ctx.fillStyle = '#fff7d6'; ctx.shadowColor = '#10163a'; ctx.shadowBlur = U * .7;
      if (edge.left > 0) { ctx.globalAlpha = edge.left; ctx.textAlign = 'left'; ctx.font = `${U * 1.5}px Silkscreen`; ctx.fillText(DIRECTION_SIGNS.left, edge.leftX + U * 1.5, H * .52); }
      if (edge.right > 0) { ctx.globalAlpha = edge.right; ctx.textAlign = 'right'; ctx.font = `${U * 1.15}px Silkscreen`; ctx.fillText(DIRECTION_SIGNS.right, edge.rightX - U * 1.5, H * .52); }
      ctx.restore();
    }
    if (scene === 'play') HOOKS.hud.forEach(f => f(U, W, H));
    if (scene === 'play' && matchMedia('(pointer:coarse)').matches) {
      ctx.globalAlpha = .3; ctx.fillStyle = '#fff';
      if (joy.active) { ctx.beginPath(); ctx.arc(joy.cx, joy.cy, 70, 0, 7); ctx.fill(); ctx.globalAlpha = .6; ctx.beginPath(); ctx.arc(joy.cx + joy.x * 70, joy.cy + joy.y * 70, 30, 0, 7); ctx.fill(); }
      ctx.globalAlpha = .5; ctx.beginPath(); ctx.arc(W * .89, H * .8, U * 5, 0, 7); ctx.fill();
      ctx.globalAlpha = 1; ctx.fillStyle = '#10163a'; ctx.font = `${U * 2.6}px Silkscreen`; ctx.textAlign = 'center'; ctx.fillText('A', W * .89, H * .8);
    }
    if (trans) { ctx.fillStyle = `rgba(0,0,0,${Math.max(0, 1 - Math.abs(trans.t - .25) / .25)})`; ctx.fillRect(0, 0, W, H); }
    if (scene === 'title') drawSplash(W, H, U);
    if (scene === 'end') {
      ctx.fillStyle = 'rgba(5,8,25,0.8)'; ctx.fillRect(0, 0, W, H);
      ctx.textAlign = 'center'; ctx.fillStyle = '#ffd21f'; ctx.font = `${U * 3.6}px Silkscreen`; ctx.fillText(T.end1, W / 2, H * .075);
      ctx.fillStyle = '#f5f0e0'; ctx.font = `${U * 1.8}px Silkscreen`; ctx.fillText(T.end2, W / 2, H * .145);
      ctx.fillStyle = '#9aa0c0'; ctx.font = `${U * 1.45}px Silkscreen`; ctx.fillText(`${T.end3} ${fmtTime(Q.playTime)} · ${appleCount()}/${ITEMS.apples.length}`, W / 2, H * .205);

      const size = Math.min(U * 32, H * .28, W * .62), x = (W - size) / 2, y = H * .25;
      ctx.fillStyle = 'rgba(8,12,40,0.94)'; ctx.fillRect(x - U, y - U, size + U * 2, size + U * 2);
      ctx.strokeStyle = '#f5f0e0'; ctx.lineWidth = Math.max(2, U * .28); ctx.strokeRect(x - U * .7, y - U * .7, size + U * 1.4, size + U * 1.4);
      if (MEMORY_ART[memoryIndex]) { ctx.imageSmoothingEnabled = false; ctx.drawImage(MEMORY_ART[memoryIndex], x, y, size, size); }

      ctx.fillStyle = '#ffd21f'; ctx.font = `${U * 1.8}px Silkscreen`; ctx.fillText(`${T.memoryTitle} · ${memoryIndex + 1}/${T.memoryFacts.length}`, W / 2, H * .59);
      ctx.fillStyle = '#f5f0e0'; ctx.font = `${U * 1.55}px Silkscreen`;
      ctx.fillText(T.memoryNames[memoryIndex], W / 2, H * .645);
      const fact = wrapText(T.memoryFacts[memoryIndex], Math.min(W - U * 10, U * 86));
      fact.slice(0, 3).forEach((line, i) => ctx.fillText(line, W / 2, H * .71 + i * U * 2.15));
      ctx.fillStyle = '#c8cee0'; ctx.font = `${U * 1.45}px Silkscreen`;
      ctx.fillText(memoryIndex < T.memoryFacts.length - 1 ? T.memoryNext : T.memoryReturn, W / 2, H * .92);
    }
  }

  let last = 0;
  function loop(ts) {
    const dt = Math.min(.05, (ts - last) / 1000 || 0); last = ts;
    update(dt); render();
    requestAnimationFrame(loop);
  }

  async function init() {
    load('img/splash.png').then(i => { SPLASH = i; }, () => { });   // title art; the title still works without it
    [MAP, ITEMS] = await Promise.all([fetch('map.json').then(r => r.json()), fetch('items.json').then(r => r.json())]);
    // A stale generated items file or an old save must not render the same NPC twice.
    // Keep the first authored instance, which preserves the intended range position.
    if (Array.isArray(ITEMS.npcs)) {
      const seenNpcIds = new Set();
      ITEMS.npcs = ITEMS.npcs.filter(n => !seenNpcIds.has(n.id) && seenNpcIds.add(n.id));
    }
    // Field hay bales are exported by render_map.py as MAP.bales (not baked into the ground), so they can be pushed around.
    BALES.splice(0, BALES.length, ...(MAP.bales || []).filter(b => Number.isFinite(b.x) && Number.isFinite(b.y)).map(b => ({
      x: b.x, y: b.y, hx: b.x, hy: b.y, vx: 0, vy: 0, angle: 0, roll: 0,
    })));
    PLAYER_SHEETS = Object.fromEntries(await Promise.all(PLAYABLE_CHARACTERS.map(async character => {
      const sheetName = `${character}_sheet`;
      const [sheet, meta] = await Promise.all([load(`img/${sheetName}.png`), fetch(`img/${sheetName}.json`).then(r => r.json())]);
      return [character, { sheet, meta, sheetName }];
    })));
    const loaded = await Promise.all([
      load('img/map_ground.png'), load('img/map_objects.png'), load('img/map_collide.png'),
      load('img/map_terrain.png'),
      load('img/npcs.png'), load('img/frodo.png'),
      document.fonts.load('20px Silkscreen', 'ŁŚĆŻ'),
      // optional AI art for the church; a missing file just keeps the hand-drawn piece
      fetch('img/church/manifest.json').then(r => r.json()).catch(() => [])
        .then(names => Promise.all(names.map(k => load(`img/church/${k}.png`).then(i => { window.CHURCH_ART[k] = i; }, () => { })))),
      Promise.all(MEMORY_PATHS.map(load)),
    ]);
    const [g, o, c, terrainImg, npcs, dog, _font, _churchArt, memories] = loaded;
    MEMORY_ART = memories;
    const [arek8, arek8meta] = await Promise.all([load('img/arek_sheet_8dir.png'), fetch('img/arek_sheet_8dir.json').then(r => r.json())]);
    PLAYER_SHEETS.arek = { sheet: arek8, meta: arek8meta, sheetName: 'arek_sheet_8dir' };
    GROUND = g; OBJ = o; SPR = PLAYER_SHEETS[selectedCharacter] || PLAYER_SHEETS.arek; NPCIMG = npcs; DOGIMG = dog;
    load('img/frodo_idle.png').then(img => { FRODO_IDLE = img; }, () => { });   // optional idle poses (sit, lick...)
    load('img/trash.png').then(img => { TRASH_IMG = img; }, () => { });   // trash bag pickup art (pixel fallback until loaded)
    load('img/arek_sheet_8dir_noglasses.png').then(img => {
      PLAYER_SHEETS.arek.bare = img;
      if (selectedCharacter === 'arek') SPR = PLAYER_SHEETS.arek;
    }, () => { });   // optional no-glasses variant with the same 8-direction layout
    {   // walking speed and mushroom placement use the same terrain classification
      const t = document.createElement('canvas'); t.width = terrainImg.width; t.height = terrainImg.height;
      const tx2 = t.getContext('2d', { willReadFrequently: true }); tx2.drawImage(terrainImg, 0, 0);
      const px = tx2.getImageData(0, 0, terrainImg.width, terrainImg.height).data; TERRAIN = { w: terrainImg.width, h: terrainImg.height, k: MAP.w / terrainImg.width, v: new Uint8Array(terrainImg.width * terrainImg.height) };
      for (let i = 0; i < TERRAIN.v.length; i++) TERRAIN.v[i] = px[i * 4];
    }
    {   // C06: deterministic forest-floor texture polish (RUNTIME only - the
        // generated docs/img/map_*.png stay byte-identical). The generator paints
        // a flat #1f4f24 forest floor; here we bake low-contrast moss/litter tones
        // plus coarse dappled shade onto floor pixels ONLY (canopy/trunk art is
        // left untouched), with a fixed seed so every load reproduces the exact
        // same texture. One-time init cost; the per-frame render path is unchanged.
        const FLOOR = [31, 79, 36];   // #1f4f24 generator fill
        const TONES = [[22, 58, 26], [24, 64, 29], [28, 71, 32], [30, 76, 35], [33, 80, 37],
                       [35, 86, 40], [36, 83, 39], [38, 92, 42], [40, 88, 40], [42, 95, 45]];
        const SEED = 0x2D06C029 | 0;   // fixed C06 seed
        const FC_START = performance.now();
        const gw = g.width, gh = g.height;
        const gc = document.createElement('canvas');
        gc.width = gw; gc.height = gh;
        const gx = gc.getContext('2d');
        gx.drawImage(g, 0, 0);
        const img = gx.getImageData(0, 0, gw, gh), d = img.data;
        // cheap deterministic spatial hash (no PRNG stream, no call overhead): a
        // full bake touches ~6.5M floor pixels, and each pixel needs ~3 draws
        const draw = (x, y, salt) => {
          let h = (Math.imul(x | 0, 374761393) + Math.imul(y | 0, 668265263) + Math.imul(salt, 1442695041)) | 0;
          h = Math.imul(h ^ h >>> 13, 1274126177) ^ SEED;
          return ((h ^ h >>> 16) >>> 0) / 4294967296;
        };
        let touched = 0, outside = 0, canopyKept = 0;
        let n = 0, sR = 0, sG = 0, sB = 0, ssR = 0, ssG = 0, ssB = 0, maxD = 0, baseExact = 0;
        let fnv = 2166136261 >>> 0;
        const distinct = new Set();
        const note = (r, gg, b) => {
          n++; sR += r; sG += gg; sB += b; ssR += r * r; ssG += gg * gg; ssB += b * b;
          distinct.add((r >> 2) + ':' + (gg >> 2) + ':' + (b >> 2));
          const dd = Math.abs(r - FLOOR[0]) + Math.abs(gg - FLOOR[1]) + Math.abs(b - FLOOR[2]);
          if (dd > maxD) maxD = dd;
          if (dd === 0) baseExact++;
          fnv ^= r; fnv = Math.imul(fnv, 16777619) >>> 0;
          fnv ^= gg; fnv = Math.imul(fnv, 16777619) >>> 0;
          fnv ^= b; fnv = Math.imul(fnv, 16777619) >>> 0;
        };
        // terrain cells map to 4x4 art-res blocks with the generator's (2,2) offset
        for (let ty = 0; ty < TERRAIN.h; ty++) {
          const y0 = 2 + ty * 4;
          if (y0 >= gh) break;
          for (let tx = 0; tx < TERRAIN.w; tx++) {
            if (TERRAIN.v[ty * TERRAIN.w + tx] !== 220) continue;
            const x0 = 2 + tx * 4;
            if (x0 >= gw) continue;
            const vw = Math.min(4, gw - x0), vh = Math.min(4, gh - y0);
            const dapple = draw(tx, ty, 1);      // coarse canopy shade per block
            const dm = dapple < 0.30 ? 0.86 : dapple > 0.73 ? 1.06 : 1;
            for (let yy = 0; yy < vh; yy++) for (let xx = 0; xx < vw; xx++) {
              const ax = x0 + xx, ay = y0 + yy, pi = (ay * gw + ax) * 4;
              const r = d[pi], gg = d[pi + 1], b = d[pi + 2];
              // floor-classified pixels only: close to the flat fill, never canopy/trunk
              if (r >= 60 || gg < 50 || gg > 100 || b >= 60 || gg - r <= 15) { canopyKept++; continue; }
              if (draw(ax, ay, 2) >= 0.52) {
                const t0 = TONES[(draw(ax, ay, 3) * TONES.length) | 0];
                const j = ((draw(ax, ay, 4) - 0.5) * 7) | 0;
                // stay inside the floor colour box so every written pixel remains
                // floor-classified and the bake never touches canopy/trunk art
                d[pi] = Math.min(59, Math.max(0, ((t0[0] + j) * dm) | 0));
                d[pi + 1] = Math.min(100, Math.max(50, ((t0[1] + j) * dm) | 0));
                d[pi + 2] = Math.min(59, Math.max(20, ((t0[2] + (j >> 1)) * dm) | 0));
              }
              if (n < 900000) note(d[pi], d[pi + 1], d[pi + 2]);
              touched++;
            }
          }
        }
        gx.putImageData(img, 0, 0);
        GROUND = gc;   // rendered ground is now the baked canvas (per-frame same as before)
        FOREST_STATS = {
          seed: '0x2D06C029', floorTouched: touched, outsideForest: outside, canopyKept,
          buildMs: performance.now() - FC_START, sampled: n,
          floorMean: [sR / n, sG / n, sB / n],
          floorStdev: [Math.sqrt(ssR / n - (sR / n) ** 2), Math.sqrt(ssG / n - (sG / n) ** 2), Math.sqrt(ssB / n - (sB / n) ** 2)],
          distinctColors: distinct.size, baseExactShare: baseExact / n, cohesionMax: maxD, fnv,
        };
    }
    NPC_HOME = Object.fromEntries(ITEMS.npcs.filter(n => !n.secret).map(n => [n.id, { x: n.x, y: n.y }]));
    const tc = document.createElement('canvas'); tc.width = MAP.w; tc.height = MAP.h;
    const tx = tc.getContext('2d', { willReadFrequently: true }); tx.drawImage(c, 0, 0);
    const d = tx.getImageData(0, 0, MAP.w, MAP.h).data; SOLID = new Uint8Array(MAP.w * MAP.h);
    for (let i = 0; i < SOLID.length; i++) { const v = d[i * 4]; SOLID[i] = v > 200 ? 2 : v > 64 ? 1 : 0; }
    MINI = document.createElement('canvas'); MINI.width = 400; MINI.height = Math.round(400 * MAP.h / MAP.w);
    const mx = MINI.getContext('2d'); mx.drawImage(g, 0, 0, MINI.width, MINI.height); mx.drawImage(o, 0, 0, MINI.width, MINI.height);
    P.x = MAP.spawn.x; P.y = MAP.spawn.y;
    hasSave = loadSave();
    buildReachableMask();
    const newMush = ensureMushrooms(), newTrash = ensureTrash();   // old saves get trash bags on load
    if ((newMush || newTrash) && hasSave) save();
    if (params.has('x') && params.has('y')) { P.x = +params.get('x'); P.y = +params.get('y'); }   // e.g. ?x=1243&y=901
    unstick(); placeFrodoNearArek();
    if (savedDog && !blocked(savedDog.x, savedDog.y) && Math.hypot(savedDog.x - P.x, savedDog.y - P.y) < 400) { FRODO.x = savedDog.x; FRODO.y = savedDog.y; }
    camX = P.x; camY = P.y;
    resize(); requestAnimationFrame(loop);
    // API for features.js
    window.ARK = {
      HOOKS, P, MAP, ITEMS, LANG, ctx, keys, joy, T, CHAR_H, SPEED,
      get Q() { return Q; }, get FRODO() { return FRODO; }, get time() { return time; }, get zoom() { return zoom; }, get talk() { return talk; }, get scene() { return scene; }, get room() { return ROOM; },
      pointer, clickTarget, mapCursor, copyMapCoordinates, get camera() { return lastCam; },
      save, say, popToast, heroText, celebrate, blocked, unstick, drawNpc, drawArekPose, shadow, box, wrapText, fmtTime, terrainAt,
      terrainSpeed: (x, y) => TERRAIN_SPEED[terrainAt(x, y)] || 1,
      teleport(x, y) { P.x = x; P.y = y; P.air = false; P.z = 0; unstick(); },
      burst(x, y, colors, n = 16) { for (let k = 0; k < n; k++) fx.push({ x, y, vx: (Math.random() - .5) * 120, vy: -Math.random() * 150, t: 0, c: colors[k % colors.length] }); },
      load,
    };
    window.dispatchEvent(new Event('ark-ready'));
    window.__game = { P, get playerCharacter() { return selectedCharacter; }, get playerSheetName() { return SPR ? `${SPR.sheetName}.png` : null; }, get cloudCount() { return CLOUDS.length; }, characterButtonCenter(id) {   // CSS-pixel centre of a selector button (tests)
      const b = characterButtonBounds().find(x => x.id === id), k = cvs.width / Math.max(1, innerWidth);
      return b ? [(b.x + b.w / 2) / k, (b.y + b.h / 2) / k] : null;
    }, get playerName() { return heroName(); }, get FRODO() { return FRODO; }, get MAP() { return MAP; }, get sunglasses() { return !(inCemetery && selectedCharacter === 'arek' && SPR.bare); }, mapPlaceName, mapHoverLabel: (x, y, r = 60) => mapHoverLabel(+x, +y, r), worldHoverLabel: (x, y) => worldHoverLabel(+x, +y), worldPickAt: (x, y) => worldPickAt(+x, +y), worldHoverLabelAtCanvas: (px, py) => worldHoverLabelAtCanvas(+px, +py), worldHoverLabelState: () => worldHoverLabelState(Math.min(cvs.width, cvs.height * 1.6) / 100, cvs.width, cvs.height), get bales() { return BALES; }, get showMap() { return showMap; }, set showMap(v) { showMap = !!v; }, terrainAt, mushroomTotal: MUSHROOMS_TOTAL, mushroomNeeded: MUSHROOMS_NEEDED, mushroomCount, mushroomPalette: { white: true }, hudCountersSingleLine: true, directionSigns: DIRECTION_SIGNS, get directionSignVisibility() { const e = directionSignEdges(cvs.width); return { left: e.left, right: e.right }; }, edytkaStay: EDYTKA_STAY, ITEMS, blocked, clickTarget, mapCursor, copyMapCoordinates, enterChurch, get Q() { return Q; }, get scene() { return scene; }, set scene(v) { scene = v; }, isSpawnReachable(x, y) { const gx = Math.floor(x / reachableStep), gy = Math.floor(y / reachableStep); return !!(reachableMask && gx >= 0 && gy >= 0 && gx < reachableW && gy < Math.ceil(MAP.h / reachableStep) && reachableMask[gy * reachableW + gx]); }, get room() { return ROOM; }, get talk() { return talk; }, get toastText() { return toast ? toast.text : null; }, baleMoved() { return BALES.reduce((m, b) => Math.max(m, Math.hypot(b.x - b.hx, b.y - b.hy)), 0); }, pitchState() { return window.__pitchState ? window.__pitchState() : null; }, talkTo: talkNpc, get memoryIndex() { return memoryIndex; }, memoryCount: T.memoryFacts.length, baleGeometry: (zoom = 1) => ({ w: BALE_DRAW.w, h: BALE_DRAW.h, halfW: BALE_DRAW.halfW, top: BALE_DRAW.top, aspect: BALE_DRAW.aspect, area: BALE_DRAW.area, minX: BALE_DRAW.minX, minY: BALE_DRAW.minY, maxX: BALE_DRAW.maxX, maxY: BALE_DRAW.maxY, screenW: BALE_DRAW.w * zoom, screenH: BALE_DRAW.h * zoom }), clouds: () => CLOUDS.map(c => ({ x: (c.x + time * c.speed) % MAP.w, y: c.y, scale: c.scale, alpha: c.alpha })), cloudGeometry: () => ({ unitW: CLOUD_GEOM.unitW, unitH: CLOUD_GEOM.unitH, halfW: CLOUD_GEOM.halfW, halfH: CLOUD_GEOM.halfH, marginX: CLOUD_GEOM.marginX, marginY: CLOUD_GEOM.marginY, blobs: CLOUD_GEOM.blobs }), forestTextureStats: () => FOREST_STATS };
  }
  init().catch(e => { document.body.insertAdjacentHTML('beforeend', `<pre style="color:#f66">${e.message}</pre>`); });
})();

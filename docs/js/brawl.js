/* BIJATYKA — a Little Fighter 2 style local brawler for Chłopków.
   Several people on one machine (3 keyboard schemes + up to 4 gamepads, rebindable) plus
   computer fighters, free-for-all or teams. Started from a purple flag in the south-west.

   LF2 rules it follows
     ATTACK alternates two punches; a dizzy enemy takes a super punch that knocks down.
     Hits add to a hidden "fall" meter: hurt -> dizzy -> knocked down. DEFEND blocks frontal hits
     (10 % damage) until the guard breaks. HP has a dark-red part that slowly regenerates.
     Double-tap left/right = run. Run + ATTACK = dash attack, run + JUMP = long dash jump,
     run + DEFEND = roll. JUMP + ATTACK = jump kick. While falling, JUMP = flip (rowing).
     Walk into a dizzy enemy to grab: ATTACK punches, direction + ATTACK throws.
     Items drop from the sky: widły (light weapon: ATTACK swings, forward + ATTACK throws),
     kamień (heavy: ATTACK throws), Łomża (picked up and drunk: HP + MP), pieczarki (5 throwable mushrooms),
     rural throwables carried overhead: kamień, bańka, opona (rolls), wiadro, grabie, łopata, kosa.
     Specials: DEFEND, forward, ATTACK = ball (Arek apple, Edytka mushroom, Renik vinyl);
               DEFEND, up, ATTACK = Arek pitchfork lunge, Edytka spin kick, Renik breakdance.
     Powers (LF2 Firen / Freeze / Davis style): DEFEND, down, ATTACK = each fighter's element:
               fire = fireball that knocks down and sets the target burning,
               ice = ice shard that freezes the target in a block (next hit shatters it for bonus damage),
               beam = kamehameha: short charge, then a screen-long multi-hit beam (dodge it up/down).
   LF2 physics: movement, jump/dash arcs, gravity, friction, fall/guard meters, hit stop, regen and the Davis attacks use
     original LF2 numbers (F.LF global.js + stock davis.dat) in the LF2 block below, scaled by S = 100/62 and stepped per 1/30 s time unit.
   Art: docs/img/brawl/<fighter>.webp/.json, items.webp/.json, stage_*.webp, built by
   gen/brawl/build_fight_sprites.py from generated sheets. Settings/results in localStorage. */
'use strict';
window.addEventListener('ark-ready', () => {
  const A = window.ARK;
  if (A.__brawlInstalled) return; A.__brawlInstalled = true;
  const PL = A.LANG === 'pl';

  /* ================================================================== LF2 reference numbers
     Original Little Fighter 2 is the rulebook. Every value in this block is an LF2 value in LF2 units
     (px, 30 time units (TU) per second) taken from F.LF LF/global.js (GC.*), LF/mechanics.js, LF/character.js
     (rules and numbers only, no code) and the stock davis.dat (header + frames). LF2 / F.LF global.js.
     S scales LF2 lengths to this view: our standing hurtbox (100 px) / Davis bdy height (62 LF2 px), so motion
     relative to the body equals LF2. Velocities in the game are px/s; PXTU turns "1 LF2 px per TU" into px/s.
     The simulation steps at 60 Hz; fighter physics and fall/guard meters advance once per TU (every 2nd tick),
     exactly LF2's order (state sets velocity, move, ground friction or gravity), so heights and distances equal LF2. */
  const LF2 = {
    TU: 30, S: 100 / 62, hp: 500, mp: 500, mpStart: 200,         // GC.framerate, hp_full, mp_full, mp_start
    gravity: 1.7, friction: 1, minSpeed: 1,                      // GC.gravity, ground friction 1 px/TU^2, GC.min_speed
    walk: 5, walkz: 2.5, run: 10, runz: 1.6, hWalk: 3.7, hWalkz: 1.85, hRun: 6.2, hRunz: 1,   // davis.dat header
    jumpH: 16.3, jumpDist: 10, jumpDistZ: 3.75, dashH: 10, dashDist: 18, dashDistZ: 5, rowDist: 5, rollSpeed: 9,   // roll = frames 102-105 dvx 9
    diagWalk: 2 / 7, diagRun: 1 / 7,                             // x speed lost while also moving in z (state 1 / 2)
    squat: 5,                  // jump press -> launch: frames 210 + 211 (wait 1 = 2 TU each) + entry TU of 212
    hurt: 7, dizzy: 28, broken: 9, crouch: 3, lying: 31, lieInv: 30, roll: 12, skid: 6,   // frames 220-225 (3+4 TU), 226-229 (4x7), 112-114, 215/219, 230/231, invulnerable 30 TU after lying, 102-105, 218
    freeze: 91, shatter: { vx: 4, vy: 3 }, flipHover: 3, flipDvx: 5,   // frame 201 wait 90, frame 202 dvx -4 dvy -3, rowing frame 100, rowing speed 5
    fall: { value: 20, dvy: 6.9, ko: 60, dizzy: 40, recover: .45, juggle: 40 },   // GC.default.fall.*, GC.fall.KO, GC.recover.fall, itr table: falling targets only take fall > 40
    bounce: { xy: 13.4, y: 11, up: 4.25, absorb: { 9: 1, 14: 4, 20: 10, 40: 20, 60: 30 } },   // GC.character.bounceup
    fell: { 2: 0, 3: 1, 5: 2, 6: 4, 9: 5, 13: 7, 25: 9 },        // GC.friction.fell (landing friction by speed)
    bdef: { limit: 40, hit: 45, recover: .5, absorb: { 5: 0, 15: 5 } },   // GC.defend.break_limit 40: block while total bdefend <= 40, breaks above; counter 45 after an unguarded hit; GC.recover.bdefend
    defendFactor: .1, hitStop: 3, hitStopBlock: 4, hitStopBroken: 5,   // GC.defend.injury.factor, GC.default.itr.hit_stop, victim effect 111 / 112
    zwidth: 12, body: [-18, 25], bodyH: 61, catchBox: [-33, 52],        // itr zwidth, Davis bdy x/h, kind-6 box of dizzy/broken frames
    hpRegen: 12, mpRegen: 3,                                     // +1 hp every 12 TU up to the dark bound; +1+floor(lost/100) mp every 3 TU
    // Davis itr in LF2 units, stock davis.dat (LF2 1.9) frame by frame. Each itr = one frame's box: t0/t1 in TU from the first frame of the move
    // (frame lasts wait + 1 TU), x forward from the frame's centerx (itr x - centerx, + w), y = height above the feet (centery - y, - h),
    // injury / fall (default 20) / bdefend / dvx / dvy (negative = up) / arest (attacker waits N TU before the next hit) / vrest (each victim can be hit again after N TU).
    // dur = TU of the whole move, adv = [from TU, to TU, dvx] frame pushes (frame dvx).
    atk: {
      punch: { dur: 8, adv: [[4, 8, 2]], itr: [{ t0: 2, t1: 4, x: [-2, 41], y: [30, 48], injury: 20, fall: 20, bdef: 16, dvx: 2 }] },                 // frames 60-63, itr in 61
      punch2: { dur: 8, adv: [[4, 8, 2]], itr: [{ t0: 2, t1: 4, x: [-1, 40], y: [26, 41], injury: 20, fall: 20, bdef: 16, dvx: 2 }] },                // frames 65-68, itr in 66
      super: { dur: 21, adv: [[8, 10, 5], [13, 15, 6], [15, 18, 1]], itr: [                                                                              // frames 70-75, 38, 39
        { t0: 5, t1: 8, x: [12, 47], y: [29, 74], injury: 40, fall: 70, bdef: 60, dvx: 3, dvy: -10, arest: 15 },                                       // frame 72
        { t0: 15, t1: 18, x: [2, 34], y: [31, 75], injury: 40, fall: 70, bdef: 60, dvx: 7, dvy: -13, arest: 15 }] },                                  // frame 38
      runatk: { dur: 19, adv: [[3, 5, 16]], itr: [                                                                                                       // frames 85-89, 97, 98
        { t0: 5, t1: 7, x: [-43, 45], y: [25, 55], injury: 55, fall: 70, bdef: 60, dvx: 20, vrest: 7 },                                                // frame 87
        { t0: 7, t1: 11, x: [8, 51], y: [27, 54], injury: 40, fall: 70, bdef: 60, dvx: 17, vrest: 10 }] },                                            // frame 88
      jkick: { dur: 16, itr: [                                                                                                                           // jump_attack frames 80-84, 79
        { t0: 6, t1: 10, x: [-8, 44], y: [16, 33], injury: 60, fall: 70, bdef: 30, dvx: 9, dvy: -5, arest: 15 },                                       // frame 83
        { t0: 10, t1: 12, x: [7, 43], y: [15, 31], injury: 60, fall: 70, bdef: 30, dvx: 9, dvy: -5, arest: 15 }] },                                    // frame 84
      dashkick: { dur: 16, itr: [                                                                                                                        // dash_attack frames 90-94, 96 (96 loops until landing)
        { t0: 6, t1: 14, x: [-8, 44], y: [16, 33], injury: 80, fall: 70, bdef: 60, dvx: 14, dvy: -5, arest: 9 },                                       // frame 93
        { t0: 14, t1: 16, x: [7, 43], y: [15, 31], injury: 80, fall: 70, bdef: 60, dvx: 14, dvy: -5, arest: 9 }] },                                    // frame 94
    },
  };
  const TUS = 1 / LF2.TU, PXTU = LF2.S * LF2.TU;      // seconds per TU; px/s of 1 LF2 px per TU
  const lookupAbs = (tab, v) => { v = Math.abs(v); let last; for (const k of Object.keys(tab)) { last = tab[k]; if (v <= +k) return tab[k]; } return last; };   // F.LF util.lookup_abs
  const lf2Atk = a => {
    const ph = a.itr.map(p => ({ t0: p.t0 * TUS, t1: p.t1 * TUS, bx: p.x.map(v => v * LF2.S), hy: p.y.map(v => v * LF2.S), reach: p.x[1] * LF2.S,
      dmg: p.injury, fall: p.fall, bdef: p.bdef, dvx: p.dvx * PXTU, dvy: p.dvy === undefined ? undefined : -p.dvy * PXTU,
      arest: p.arest === undefined ? undefined : p.arest * TUS, vrest: p.vrest === undefined ? undefined : p.vrest * TUS }));
    return { ...ph[0], t1: ph[ph.length - 1].t1, reach: Math.max(...ph.map(p => p.reach)), dur: a.dur * TUS, adv: a.adv, phases: ph.length > 1 ? ph : undefined };
  };

  /* ================================================================== data */
  const FIGHTERS = {
    arek: {
      name: 'AREK', atlas: 'arek', color: '#e34c4c', hp: LF2.hp, superFrame: 'super',
      ball: { name: PL ? 'JABŁKO!' : 'APPLE!', item: 'apple', mp: 75, dmg: 45, fall: 45, speed: 520 },
      spin: { name: PL ? 'WIDŁY!' : 'PITCHFORK!', mp: 150, hits: 3, dmg: 30, fall: 30, dur: .6, vx: 330, frame: 'w_thrust', weapon: 'widly', front: true, reach: 120, dvx: 260 },
      power: { el: 'fire', name: PL ? 'OGNISKO!' : 'BONFIRE!', color: '#ff7a1a' },
    },
    edytka: {
      name: 'EDYTKA', atlas: 'edytka', color: '#4aa8e8', hp: LF2.hp, superFrame: 'kick',
      ball: { name: PL ? 'BOROWIK!' : 'MUSHROOM!', item: 'mushroom', mp: 75, dmg: 45, fall: 45, speed: 470 },
      spin: { name: PL ? 'KOPNIAK Z OBROTU!' : 'SPIN KICK!', mp: 150, hits: 1, dmg: 80, fall: 90, dur: .62, vx: 200, flip: .12, dvy: 480 },
      power: { el: 'ice', name: PL ? 'LODOWY WIATR!' : 'ICE BLAST!', color: '#9fe3ff' },
    },
    renik: {
      name: 'DJ RENIK', atlas: 'renik', color: '#ffd21f', hp: LF2.hp, superFrame: 'super',
      ball: { name: PL ? 'WINYL!' : 'VINYL!', item: 'vinyl', mp: 75, dmg: 40, fall: 40, speed: 600 },
      spin: { name: PL ? 'BREAKDANCE!' : 'BREAKDANCE!', mp: 150, hits: 3, dmg: 30, fall: 30, dur: .8, vx: 90, flip: .1, hy: [0, 50] },
      power: { el: 'beam', name: 'BASS-HAMEHA!', color: '#c86bff' },
    },
    damian: {
      name: 'DAMIAN', atlas: 'damian', color: '#7cff6b', hp: LF2.hp, superFrame: 'super',
      ball: { name: PL ? 'GOL!' : 'GOAL!', item: 'football', mp: 75, dmg: 42, fall: 45, speed: 640 },
      spin: { name: PL ? 'WŚLIZG!' : 'SLIDE TACKLE!', mp: 140, hits: 1, dmg: 55, fall: 90, dur: .55, vx: 460, front: true, reach: 70, hy: [0, 45], dvx: 240, knock: true },
      power: { el: 'fire', name: PL ? 'OGNISTA PIŁKA!' : 'FIREBALL!', color: '#ff5a1a' },
    },
    wesoly: {
      name: 'WESOŁYCH ŚWIĄT', atlas: 'wesoly', color: '#c0392b', hp: LF2.hp, superFrame: 'super',
      ball: { name: PL ? 'MŁOTEK!' : 'HAMMER!', item: 'hammer', mp: 80, dmg: 55, fall: 60, speed: 470 },
      spin: { name: PL ? 'TRZĘSIENIE!' : 'GROUND POUND!', mp: 160, hits: 1, dmg: 60, fall: 100, dur: .6, vx: 0, reach: 115, hy: [0, 40], dvx: 160, knock: true, t0: .22 },
      power: { el: 'ice', name: PL ? 'ŚNIEŻYCA!' : 'BLIZZARD!', color: '#e8f6ff' },
    },
    michal: {
      name: 'MICHAŁ', atlas: 'michal', color: '#8a9a3a', hp: LF2.hp, superFrame: 'super',
      start: 'pistol',
      ball: { name: PL ? 'SERIA!' : 'VOLLEY!', item: 'kulka', gun: true, volley: 3, mp: 75, dmg: 18, fall: 28, speed: 840 },
      spin: { name: PL ? 'SZARŻA!' : 'SHOULDER CHARGE!', mp: 140, hits: 1, dmg: 55, fall: 95, dur: .5, vx: 430, front: true, reach: 60, hy: [10, 110], dvx: 300, knock: true },
      power: { el: 'beam', name: 'KAMEHAMEHA!', color: '#6bd0ff' },
    },
    soltys: {
      name: 'SOŁTYS', atlas: 'soltys', color: '#b07d3a', hp: LF2.hp, superFrame: 'super',
      start: 'teczka',
      ball: { name: PL ? 'TECZKA!' : 'BRIEFCASE!', item: 'teczka', mp: 75, dmg: 48, fall: 60, speed: 460 },
      spin: { name: PL ? 'PIECZĄTKA!' : 'OFFICIAL STAMP!', mp: 150, hits: 1, dmg: 80, fall: 100, dur: .62, vx: 60, front: true, reach: 85, hy: [0, 120], dvx: 120, knock: true, t0: .2 },
      power: { el: 'fire', name: PL ? 'OGIEŃ Z KOMINA!' : 'CHIMNEY FIRE!', color: '#ff8c2a' },
    },
    ernest: {
      name: 'ERNEST', atlas: 'ernest', color: '#2ec4b6', hp: LF2.hp, superFrame: 'super',
      ball: { name: PL ? 'CYTRYNA!' : 'LEMON!', item: 'cytryna', mp: 75, dmg: 38, fall: 40, speed: 500 },
      spin: { name: PL ? 'MŁYNEK KAPITANA!' : 'CAPTAIN WINDMILL!', mp: 150, hits: 3, dmg: 28, fall: 30, dur: .6, vx: 110, hy: [0, 100], reach: 70, dvx: 200 },
      power: { el: 'ice', name: PL ? 'ZIMNY REJS!' : 'COLD CRUISE!', color: '#9fe3ff' },
    },
    felcu: {
      name: 'FELCU', atlas: 'felcu', color: '#5b6cff', hp: LF2.hp, superFrame: 'super',
      ball: { name: PL ? 'KLUCZYK!' : 'CAR KEY!', item: 'kluczyk', mp: 75, dmg: 30, fall: 35, speed: 700 },
      spin: { name: PL ? 'SZARŻA BARKIEM!' : 'SHOULDER CHARGE!', mp: 140, hits: 1, dmg: 55, fall: 95, dur: .5, vx: 430, front: true, reach: 60, hy: [10, 110], dvx: 300, knock: true },
      power: { el: 'fire', name: PL ? 'TURBO PŁOMIEŃ!' : 'TURBO FLAME!', color: '#ff6a1a' },
    },
    tomek: {
      name: 'TOMEK', atlas: 'tomek', color: '#f7931a', hp: LF2.hp, superFrame: 'super',
      ball: { name: PL ? 'ZŁOTY BITCOIN!' : 'GOLD BITCOIN!', item: 'bitcoin', mp: 75, dmg: 40, fall: 42, speed: 560 },
      spin: { name: PL ? 'DO KSIĘŻYCA!' : 'TO THE MOON!', mp: 150, hits: 1, dmg: 75, fall: 90, dur: .62, vx: 70, front: true, reach: 75, hy: [0, 130], dvx: 140, dvy: 480, knock: true },
      power: { el: 'beam', name: PL ? 'HODL-HAMEHA!' : 'HODL-HAMEHA!', color: '#f7931a' },
    },
  };
  const STAGES = {
    farmyard: { name: PL ? 'PODWÓRKO' : 'FARMYARD', img: 'img/brawl/stage_farmyard.webp', top: .535 },
    shop: { name: PL ? 'POD SKLEPEM' : 'AT THE SHOP', img: 'img/brawl/stage_shop.webp', top: .51 },
    // Scrolling arena: the main road from the west entrance to the świetlica, houses in their real Street View order.
    // The image is 720 px high and 15387 px wide (built by gen/brawl/build_road_stage.py); 0.75 maps it onto the 960x540 view.
    road: { name: PL ? 'DROGA PRZEZ WIEŚ' : 'VILLAGE ROAD', img: 'img/brawl/stage_road.webp', top: .5125, world: 11540, lazy: true },
  };
  // Attacks. t0..t1 active window (s), dur total; reach forward (px); hy band above the feet;
  // dmg = injury, fall = fall-meter, bdef = guard damage, dvx/dvy knock velocity.
  const ATK = {
    punch: lf2Atk(LF2.atk.punch),            // Davis punch / super_punch / run_attack / jump_attack / dash_attack (LF2 block above)
    punch2: lf2Atk(LF2.atk.punch2),
    super: lf2Atk(LF2.atk.super),
    runatk: lf2Atk(LF2.atk.runatk),
    jkick: lf2Atk(LF2.atk.jkick),
    dashkick: lf2Atk(LF2.atk.dashkick),
    w_thrust: { t0: .07, t1: .17, dur: .32, reach: 98, hy: [35, 85], dmg: 32, fall: 40, bdef: 20, dvx: 90 },
    w_swing: { t0: .10, t1: .22, dur: .40, reach: 94, hy: [20, 125], dmg: 42, fall: 70, bdef: 35, dvx: 230, dvy: 300 },
    w_jump: { t0: .03, t1: 9, dur: 9, reach: 92, hy: [0, 70], dmg: 42, fall: 70, bdef: 30, dvx: 230, dvy: 260 },
  };
  // Elemental powers shared by every fighter with that element (per-fighter name/colour in FIGHTERS[..].power).
  const POWER = {
    fire: { mp: 120, speed: 470, dmg: 40, fall: 90, bdef: 40, dvx: 230, dvy: 380, burn: 1.6, burnDmg: 5 },
    ice: { mp: 120, speed: 540, dmg: 28, fall: 20, bdef: 30, dvx: 60, freeze: LF2.freeze * TUS },   // frozen 91 TU = LF2 frame 201 (wait 90)
    beam: { mp: 200, charge: .4, end: 1.0, dur: 1.12, tick: .12, dmg: 14, fall: 24, bdef: 16, dvx: 170, hy: [45, 95] },
  };
  const ITEM_DEF = {
    // light = held weapon (drawn into the hands at the grip read from the cyan-marker poses): dmgK/reachK scale ATK.w_*
    widly: { kind: 'light', hp: 8, name: PL ? 'WIDŁY' : 'PITCHFORK', long: true },
    rake: { kind: 'light', hp: 8, name: PL ? 'GRABIE' : 'RAKE', long: true, dmgK: .95 },
    shovel: { kind: 'light', hp: 10, name: PL ? 'ŁOPATA' : 'SHOVEL', long: true, dmgK: 1.1 },
    scythe: { kind: 'light', hp: 8, name: PL ? 'KOSA' : 'SCYTHE', long: true, dmgK: 1.2, reachK: 1.1 },
    broom: { kind: 'light', hp: 6, name: PL ? 'MIOTŁA' : 'BROOM', long: true, dmgK: .75 },
    picket: { kind: 'light', hp: 5, name: PL ? 'SZTACHETA' : 'FENCE PICKET', long: true, dmgK: .95 },
    club: { kind: 'light', hp: 9, name: PL ? 'KIJ' : 'CLUB', dmgK: 1.05, reachK: .8 },
    pan: { kind: 'light', hp: 12, name: PL ? 'PATELNIA' : 'FRYING PAN', dmgK: 1.15, reachK: .7 },
    rollpin: { kind: 'light', hp: 8, name: PL ? 'WAŁEK' : 'ROLLING PIN', dmgK: .9, reachK: .65 },
    teczka: { kind: 'light', hp: 14, name: PL ? 'TECZKA' : 'BRIEFCASE', hang: true, dmgK: 1, reachK: .7 },
    pistol: { kind: 'gun', hp: 1, name: PL ? 'PISTOLET NA KULKI' : 'PAINTBALL PISTOL', ammo: 12 },
    stone: { kind: 'heavy', hp: 99, name: PL ? 'KAMIEŃ' : 'STONE', speed: .6, dmg: 60, grav: .9 },
    churn: { kind: 'heavy', hp: 99, name: PL ? 'BAŃKA' : 'MILK CHURN', speed: .62, dmg: 58, grav: .9 },
    tyre: { kind: 'heavy', hp: 99, name: PL ? 'OPONA' : 'TYRE', speed: .66, dmg: 50, grav: .8, rolls: true },
    bucket: { kind: 'heavy', hp: 99, name: PL ? 'WIADRO' : 'BUCKET', speed: .85, dmg: 35, grav: .6 },
    lomza: { kind: 'drink', hp: 1, name: 'ŁOMŻA' },
    pieczarki: { kind: 'ammo', hp: 1, name: PL ? 'PIECZARKI' : 'MUSHROOMS', ammo: 5 },
  };
  // where the hand holds each weapon sprite (fraction of its width / height) and an extra rotation
  const WGRIP = {
    widly: [.3, .5], rake: [.3, .5], shovel: [.3, .5], scythe: [.28, .3], broom: [.3, .5], picket: [.2, .5],
    club: [.15, .5], pan: [.12, .5], rollpin: [.5, .5], teczka: [.5, 0, -Math.PI / 2], pistol: [.3, .65],
  };
  const ACTIONS = ['up', 'down', 'left', 'right', 'attack', 'jump', 'defend'];
  const ACTION_LABEL = PL
    ? { up: 'GÓRA', down: 'DÓŁ', left: 'LEWO', right: 'PRAWO', attack: 'ATAK', jump: 'SKOK', defend: 'OBRONA' }
    : { up: 'UP', down: 'DOWN', left: 'LEFT', right: 'RIGHT', attack: 'ATTACK', jump: 'JUMP', defend: 'DEFEND' };
  const DEFAULT_KEYS = {
    kb1: { up: 'KeyW', down: 'KeyS', left: 'KeyA', right: 'KeyD', attack: 'KeyF', jump: 'KeyG', defend: 'KeyH' },
    kb2: { up: 'ArrowUp', down: 'ArrowDown', left: 'ArrowLeft', right: 'ArrowRight', attack: 'Period', jump: 'Slash', defend: 'ShiftRight' },
    kb3: { up: 'KeyI', down: 'KeyK', left: 'KeyJ', right: 'KeyL', attack: 'KeyO', jump: 'KeyP', defend: 'BracketLeft' },
  };
  const SCHEMES = ['kb1', 'kb2', 'kb3', 'pad1', 'pad2', 'pad3', 'pad4'];
  const schemeLabel = s => s.startsWith('kb') ? (PL ? `KLAWIATURA ${s[2]}` : `KEYBOARD ${s[2]}`) : (PL ? `PAD ${s[3]}` : `GAMEPAD ${s[3]}`);
  const SLOT_COLORS = ['#e34c4c', '#4aa8e8', '#7cff6b', '#ffd21f'];
  const LS_KEYS = 'ark_brawl_keys_v1', LS_SLOTS = 'ark_brawl_slots_v1', LS_STATS = 'ark_brawl_stats_v1', LS_OPTS = 'ark_brawl_opts_v1';
  const readLS = (k, d) => { try { const v = JSON.parse(localStorage.getItem(k)); return v && typeof v === 'object' ? v : d; } catch (e) { return d; } };
  const writeLS = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } };
  const clone = o => JSON.parse(JSON.stringify(o));
  function loadKeys() {
    const saved = readLS(LS_KEYS, {}), out = clone(DEFAULT_KEYS);
    for (const s of Object.keys(out)) for (const a of ACTIONS) if (saved[s] && typeof saved[s][a] === 'string') out[s][a] = saved[s][a];
    return out;
  }
  const DEFAULT_SLOTS = [
    { type: 'human', fighter: 'arek', ctrl: 'kb1', team: '' },
    { type: 'human', fighter: 'edytka', ctrl: 'kb2', team: '' },
    { type: 'cpu', fighter: 'renik', ctrl: 'kb3', team: '' },
    { type: 'off', fighter: 'arek', ctrl: 'pad1', team: '' },
  ];
  function loadSlots() {
    const saved = readLS(LS_SLOTS, null);
    if (!Array.isArray(saved) || saved.length !== 4) return clone(DEFAULT_SLOTS);
    return saved.map((s, i) => ({
      type: ['human', 'cpu', 'off'].includes(s.type) ? s.type : DEFAULT_SLOTS[i].type,
      fighter: FIGHTERS[s.fighter] ? s.fighter : DEFAULT_SLOTS[i].fighter,
      ctrl: SCHEMES.includes(s.ctrl) ? s.ctrl : DEFAULT_SLOTS[i].ctrl,
      team: ['', 'A', 'B'].includes(s.team) ? s.team : '',
    }));
  }
  const reducedMotion = () => !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  function loadOpts() {
    const o = readLS(LS_OPTS, {});
    return { stage: STAGES[o.stage] || o.stage === 'random' ? o.stage : 'farmyard', items: o.items !== false, level: ['easy', 'normal', 'hard'].includes(o.level) ? o.level : 'normal', sound: o.sound !== false,
      effects: o.effects === undefined ? !reducedMotion() : o.effects !== false };   // screen shake + white hit flash; off by default for people who ask their system for reduced motion
  }
  let KEYS = loadKeys(), SLOTS = loadSlots(), OPTS = loadOpts();
  const keyName = code => !code ? '—' : code.replace(/^Key/, '').replace(/^Digit/, '').replace(/^Arrow(.*)/, (m, d) => ({ Up: '↑', Down: '↓', Left: '←', Right: '→' }[d]))
    .replace('ShiftRight', 'R-SHIFT').replace('ShiftLeft', 'L-SHIFT').replace('ControlRight', 'R-CTRL').replace('ControlLeft', 'L-CTRL')
    .replace('Period', '.').replace('Comma', ',').replace('Slash', '/').replace('Semicolon', ';').replace('Quote', "'").replace('BracketLeft', '[').replace('BracketRight', ']')
    .replace(/^Numpad/, 'NUM ').toUpperCase();

  /* ================================================================== art */
  const ART = {};          // id -> { img, flash, meta }
  const STAGE_IMG = {};
  function loadAtlas(id) {
    if (ART[id]) return ART[id].ready;
    const a = ART[id] = { img: null, flash: null, meta: null };
    a.ready = Promise.all([A.load(`img/brawl/${id}.webp`), fetch(`img/brawl/${id}.json`).then(r => r.json())]).then(([img, meta]) => {
      a.img = img; a.meta = meta;
      try {   // white silhouettes for the hit flash
        const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
        const x = c.getContext('2d'); x.drawImage(img, 0, 0); x.globalCompositeOperation = 'source-in'; x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height);
        a.flash = c;
      } catch (e) { a.flash = null; }
      return a;
    });
    return a.ready;
  }
  function loadStage(id) {
    if (STAGE_IMG[id]) return STAGE_IMG[id].ready;
    const s = STAGE_IMG[id] = { img: null };
    s.ready = A.load(STAGES[id].img).then(img => { s.img = img; return img; }).catch(() => null);
    return s.ready;
  }
  const loadAll = () => Promise.all([...Object.values(FIGHTERS).map(f => loadAtlas(f.atlas)), loadAtlas('items'), ...Object.keys(STAGES).filter(id => !STAGES[id].lazy || (fight && fight.stage === id)).map(loadStage)]);

  /* ================================================================== sound (tiny WebAudio synth) */
  let AC = null;
  function sfx(kind) {
    if (!OPTS.sound) return;
    try {
      if (!AC) AC = new (window.AudioContext || window.webkitAudioContext)();
      if (AC.state === 'suspended') AC.resume();
      const t = AC.currentTime, g = AC.createGain(); g.connect(AC.destination);
      const noise = (dur, f0, f1, vol, type = 'lowpass') => {
        const b = AC.createBuffer(1, Math.ceil(AC.sampleRate * dur), AC.sampleRate), d = b.getChannelData(0);
        for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
        const s = AC.createBufferSource(); s.buffer = b; const fl = AC.createBiquadFilter(); fl.type = type;
        fl.frequency.setValueAtTime(f0, t); fl.frequency.exponentialRampToValueAtTime(f1, t + dur);
        s.connect(fl); fl.connect(g); g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(.001, t + dur); s.start(t); s.stop(t + dur);
      };
      const tone = (dur, f0, f1, vol, type = 'square') => {
        const o = AC.createOscillator(); o.type = type; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + dur);
        o.connect(g); g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(.001, t + dur); o.start(t); o.stop(t + dur);
      };
      if (kind === 'hit') noise(.12, 2200, 300, .35);
      else if (kind === 'heavy') noise(.22, 1400, 120, .5);
      else if (kind === 'block') tone(.06, 900, 600, .12);
      else if (kind === 'whoosh') noise(.14, 600, 3000, .12, 'bandpass');
      else if (kind === 'land') noise(.16, 500, 80, .4);
      else if (kind === 'pick') tone(.08, 600, 1200, .1);
      else if (kind === 'drink') tone(.18, 300, 700, .1, 'triangle');
      else if (kind === 'special') tone(.25, 300, 1400, .1, 'sawtooth');
      else if (kind === 'ko') tone(.5, 220, 55, .2, 'triangle');
      else if (kind === 'break') noise(.25, 3000, 400, .3, 'highpass');
    } catch (e) { /* audio unavailable */ }
  }

  /* ================================================================== venue in the south-west */
  let venue = null;
  function findVenue() {
    const MAP = A.MAP, g = window.__game;
    const ok = (x, y) => x > 40 && y > 40 && x < MAP.w - 40 && y < MAP.h - 40 && !A.blocked(x, y)
      && (!g || !g.isSpawnReachable || g.isSpawnReachable(x, y));
    const sx = MAP.w * .16, sy = MAP.h * .84;
    for (let r = 0; r < 900; r += 14) for (let a = 0; a < Math.PI * 2; a += .35) {
      const x = sx + Math.cos(a) * r, y = sy + Math.sin(a) * r;
      if (ok(x, y)) return { x: Math.round(x), y: Math.round(y) };
    }
    return null;
  }
  queueMicrotask(() => { venue = findVenue(); });
  function drawFlag(sx, sy, s) {
    const c = A.ctx, px = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(sx + x * s, sy + y * s, w * s, h * s); };
    A.shadow(sx, sy, s, 5);
    px(-1, -30, 2, 30, '#5a3a1e');
    for (let i = 0; i < 12; i++) px(1 + i, -29 + i * .35 + Math.sin(A.time * 5 + i * .5) * .8, 1, 8 - i * .6, i % 4 < 2 ? '#9b3fe0' : '#ffd21f');
    const st = readLS(LS_STATS, {}), label = (PL ? 'BIJATYKA' : 'BRAWL') + (st.fights ? ` ${st.fights}` : '');
    c.font = `${6 * s}px PixelifySans`; c.textAlign = 'center'; c.textBaseline = 'middle';
    const tw = c.measureText(label).width + 3 * s;
    c.fillStyle = 'rgba(8,12,40,.8)'; c.fillRect(sx - tw / 2, sy - 40 * s, tw, 8 * s);
    c.fillStyle = '#e8c8ff'; c.fillText(label, sx, sy - 36 * s); c.textAlign = 'left';
  }

  /* ================================================================== input */
  const held = new Set(), edges = [];
  const typing = t => !!(t && t.closest && t.closest('input, textarea, select, [contenteditable="true"], .chat, #player-name-input'));
  let ui = null, fight = null, rebinding = null;
  function onKeyDown(e) {
    if (!ui) return;
    if (rebinding) {
      e.preventDefault(); e.stopImmediatePropagation();
      if (e.code === 'Escape') { rebinding = null; renderLobby(); return; }
      setKey(rebinding.scheme, rebinding.action, e.code); rebinding = null; renderLobby(); return;
    }
    if (e.code !== 'Escape' && (typing(e.target) || typing(document.activeElement))) { if (!fight) e.stopImmediatePropagation(); return; }
    if (e.code === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); if (fight) endFight(); else closeBrawl(); return; }
    if (!fight) { e.stopImmediatePropagation(); return; }
    e.preventDefault(); e.stopImmediatePropagation();
    if (e.code === 'F1' || e.code === 'Pause') { if (!e.repeat && fight.phase !== 'over') fight.paused = !fight.paused; return; }
    if (fight.phase === 'over' && fight.overT > 1.2 && (e.code === 'Enter' || e.code === 'KeyR')) { startFight(); return; }
    if (e.repeat) return;
    held.add(e.code); edges.push([e.code, true]);
  }
  function onKeyUp(e) {
    if (!ui) return;
    if (held.has(e.code)) { held.delete(e.code); edges.push([e.code, false]); }
    e.stopImmediatePropagation(); if (fight) e.preventDefault();
  }
  window.addEventListener('keydown', onKeyDown, true);
  window.addEventListener('keyup', onKeyUp, true);
  window.addEventListener('blur', () => { held.clear(); });
  function setKey(scheme, action, code) {
    for (const s of Object.keys(KEYS)) for (const a of ACTIONS) if (KEYS[s][a] === code && !(s === scheme && a === action)) KEYS[s][a] = KEYS[scheme][action];
    KEYS[scheme][action] = code; writeLS(LS_KEYS, KEYS);
  }
  // Gamepad: d-pad or left stick; X/□ attack, A/✕ jump, B/○ or RB defend.
  const padPrev = {};
  function readPad(n) {
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    const p = pads && pads[n]; if (!p) return null;
    const b = i => !!(p.buttons[i] && p.buttons[i].pressed), ax = p.axes[0] || 0, ay = p.axes[1] || 0;
    return { up: b(12) || ay < -.5, down: b(13) || ay > .5, left: b(14) || ax < -.5, right: b(15) || ax > .5, attack: b(2), jump: b(0), defend: b(1) || b(5) };
  }
  function gatherInputs() {
    const by = {};
    for (const s of Object.keys(KEYS)) {
      const h = {}, pressed = [];
      for (const a of ACTIONS) h[a] = held.has(KEYS[s][a]);
      for (const [code, down] of edges) if (down) for (const a of ACTIONS) if (KEYS[s][a] === code) pressed.push(a);
      by[s] = { held: h, pressed };
    }
    for (let n = 0; n < 4; n++) {
      const st = readPad(n), prev = padPrev[n] || {}, pressed = [];
      const h = st || Object.fromEntries(ACTIONS.map(a => [a, false]));
      for (const a of ACTIONS) if (h[a] && !prev[a]) pressed.push(a);
      padPrev[n] = { ...h }; by[`pad${n + 1}`] = { held: h, pressed };
    }
    edges.length = 0;
    for (const f of fight.fighters) f.input = f.cpu ? cpuThink(f) : (by[f.ctrl] || { held: {}, pressed: [] });
  }

  /* ================================================================== arena */
  const W = 960, H = 540, X0 = 44, X1 = W - 44, Z1 = 532, GRAV = LF2.gravity * LF2.S * LF2.TU * LF2.TU, DT = 1 / 60;   // 1.7 px/TU^2 in px/s^2 (items and special-move arcs use it directly)
  let Z0 = 286;
  const depth = () => Z1 - Z0;
  // Camera: stages with a `world` wider than the view scroll after the fighters (LF2 style). fight.cam = left edge of the view.
  const scrolls = () => !!(fight && fight.ww > W);
  const viewLo = () => scrolls() ? fight.cam : 0;
  const viewHi = () => viewLo() + W;
  const worldHi = () => scrolls() ? fight.ww - 44 : X1;
  const xLo = () => scrolls() ? Math.max(X0, fight.cam + 28) : X0;
  const xHi = () => scrolls() ? Math.min(worldHi(), fight.cam + W - 28) : X1;
  function updateCam() {
    if (!scrolls()) return;
    const live = fight.fighters.filter(alive); if (!live.length) return;
    const humans = live.filter(f => !f.cpu), ref = humans.length ? humans : live;
    const target = ref.reduce((s_, f) => s_ + f.x, 0) / ref.length - W / 2 + 40;
    const goal = Math.max(0, Math.min(fight.ww - W, target));
    fight.cam += Math.max(-420 * DT, Math.min(420 * DT, (goal - fight.cam) * Math.min(1, 5 * DT)));
  }
  const gy = z => Z0 + z;

  /* ================================================================== fighters */
  function makeFighter(slot, i, n) {
    const d = FIGHTERS[slot.fighter];
    const x = X0 + 110 + (X1 - X0 - 220) * (n > 1 ? i / (n - 1) : .5);
    return {
      id: `p${i + 1}`, slot: i, def: d, key: slot.fighter, cpu: slot.type === 'cpu', ctrl: slot.ctrl,
      team: slot.team || `solo${i}`, color: SLOT_COLORS[i],
      x, z: depth() * (.3 + .4 * ((i * 37) % 10) / 10), y: 0, vx: 0, vz: 0, vy: 0, face: x < W / 2 ? 1 : -1,
      hp: d.hp, hpDark: d.hp, hpMax: d.hp, mp: 200, mpMax: 500,
      st: 'stand', t: 0, frameT: 0, fall: 0, bdef: 0, inv: 0, flash: 0, hitstop: 0, punchAlt: 0, hitSet: new Set(), hitsDone: 0, arest: 0, vrest: new Map(),
      running: 0, tap: { left: -1, right: -1 }, hist: [], hold: null, grabbing: null, grabbedBy: null, grabT: 0, grabHits: 0,
      lieFront: false, thrownBy: null, released: false, ko: false, deadT: 0, air: false,
      ai: { queue: [], wait: 0, think: 0, block: 0 },
      input: { held: {}, pressed: [] },
      stats: { kills: 0, dealt: 0, hpLost: 0, mpUsed: 0, picks: 0 },
    };
  }
  const alive = f => !f.ko;
  const enemies = f => fight.fighters.filter(o => o !== f && o.team !== f.team && alive(o));
  const holdKind = f => f.hold ? ITEM_DEF[f.hold.type].kind : null;
  function setSt(f, st) { f.st = st; f.t = 0; f.frameT = 0; f.hitSet = new Set(); f.hitsDone = 0; f.released = false; }
  const FREE = new Set(['stand', 'walk', 'run']);

  function dropHold(f, toss = true) {
    const it = f.hold; if (!it) return;
    f.hold = null; it.owner = null; it.state = 'free'; it.x = f.x; it.z = f.z; it.y = 40;
    it.vx = toss ? (Math.random() - .5) * 120 : 0; it.vy = toss ? 220 : 0; it.vz = 0; it.team = null;
  }
  function releaseGrab(f) {
    const v = f.grabbing; if (v) { v.grabbedBy = null; if (v.st === 'held') { setSt(v, 'dizzy'); v.t = .7; } }
    f.grabbing = null;
  }

  /* -------------------------------------------- damage */
  const lyingSt = s => s === 'lying' || s === 'dead';
  function hurtBox(o) { return { y0: o.y, y1: o.y + (lyingSt(o.st) ? 25 : 100) }; }
  // LF2: lying / getting up (30 TU invulnerable) / rolling (no bdy) cannot be hit; a falling body only takes hits with fall > 40 (itr table)
  function canBeHit(o, fallV) { return alive(o) && o.inv <= 0 && !['lying', 'dead', 'getup', 'roll'].includes(o.st) && !(o.st === 'fall' && fallV !== undefined && fallV <= LF2.fall.juggle); }
  const ZW = LF2.zwidth * LF2.S;
  // horizontal span of an x-range [x0,x1] given relative to a facing-right body, mirrored for a fighter facing left
  const xspan = (o, r) => o.face > 0 ? [o.x + r[0], o.x + r[1]] : [o.x - r[1], o.x - r[0]];
  const BODY = LF2.body.map(v => v * LF2.S), CATCH = LF2.catchBox.map(v => v * LF2.S);
  const overlapX = (a, b) => a[1] >= b[0] && a[0] <= b[1];
  // Hit-stop: the short freeze on impact that makes a punch feel like it landed. The victim freezes slightly longer than the attacker.
  // LF2: the attacker stalls GC.default.itr.hit_stop = 3 TU, the victim's effect lasts 3 TU (hit), 4 TU (blocked, frame 111), 5 TU (guard broken, frame 112).
  const HITSTOP = { block: LF2.hitStopBlock * TUS, broken: LF2.hitStopBroken * TUS, lightA: LF2.hitStop * TUS, lightV: LF2.hitStop * TUS, heavyA: LF2.hitStop * TUS, heavyV: LF2.hitStop * TUS, ko: LF2.hitStop * TUS };
  // LF2 knock-down (character.js falldown): fall meter reset, launch with dvx and dvy (default 6.9 px/TU up), front/back fall family
  function knockDown(o, dir, frontal, a, kx) {
    if (o.hold) dropHold(o);
    setSt(o, 'fall'); o.fall = 0; o.lieFront = !frontal;
    o.vx = kx || dir * 30; o.vy = a.dvy === undefined ? LF2.fall.dvy * PXTU : a.dvy;
  }
  function applyHit(att, o, a, srcX) {
    let stopV = HITSTOP.lightV, stopA = HITSTOP.lightA;   // the pause both fighters feel on impact (seconds)
    const dir = Math.sign(o.x - srcX) || (att ? att.face : 1);
    const frontal = o.face === -dir, air = o.y > 0 || o.vy > 0;
    let dmg = a.dmg;
    // LF2: horizontal push is dvx - 1 px/TU on the ground; guard absorbs part of it (GC.defend.absorb)
    let kx = a.dvx ? dir * Math.max(0, Math.abs(a.dvx) - (air ? 0 : PXTU)) : 0;
    if (o.st === 'defend' && frontal && !a.unblockable) {
      dmg *= LF2.defendFactor; o.bdef += a.bdef;
      kx = dir * Math.max(0, Math.abs(kx) - lookupAbs(LF2.bdef.absorb, kx / PXTU) * PXTU);
      spark(o.x - dir * 18, gy(o.z) - o.y - 60, '#9fd0f0', 6); sfx('block');
      if (o.hp - dmg <= 0) { knockDown(o, dir, frontal, a, kx); stopV = HITSTOP.heavyV; }
      else if (o.bdef > LF2.bdef.limit && !air) { setSt(o, 'brokendef'); o.vx = kx; stopV = HITSTOP.broken; popText(o, PL ? 'PĘKŁO!' : 'BROKEN!', '#ff6b5e'); }   // total guard > 40 (GC.defend.break_limit) breaks it
      else { o.vx = kx; o.t = 0; stopV = HITSTOP.block; popText(o, PL ? 'BLOK' : 'BLOCK', '#9fd0f0'); }
    } else {
      if (o.grabbedBy) releaseGrab(o.grabbedBy);
      if (o.grabbing) releaseGrab(o);
      const wasFrozen = o.st === 'frozen';
      if (wasFrozen) {   // LF2: any hit on a frozen fighter knocks it down (state 13); the shatter bonus damage has no LF2 equivalent
        dmg = Math.round(dmg * 1.3) + 10; spark(o.x, gy(o.z) - o.y - 50, '#d8f4ff', 22); sfx('break'); popText(o, PL ? 'ROZBITY!' : 'SHATTER!', '#9fe3ff');
      }
      o.bdef = LF2.bdef.hit;   // a hit outside the guard sets the guard counter to 45: no blocking for a while
      o.fall += a.fall === undefined ? LF2.fall.value : a.fall; o.flash = .1; o.running = 0;
      spark(o.x - dir * 12, gy(o.z) - o.y - 62, a.el === 'fire' ? '#ff9a2a' : a.el === 'ice' ? '#bfe8ff' : '#fff3b0', 10);
      const freeze = a.el === 'ice' && !wasFrozen && o.hp - dmg > 0;
      const down = !freeze && (wasFrozen || air || o.hp - dmg <= 0 || o.fall > LF2.fall.ko);   // LF2 fall(): frozen / airborne / dying / meter > 60
      sfx(down ? 'heavy' : 'hit');
      fight.shake = Math.max(fight.shake, down ? .16 : .06);
      if (a.el === 'fire') o.burn = Math.max(o.burn || 0, POWER.fire.burn);
      if (freeze) {
        if (o.hold) dropHold(o);
        setSt(o, 'frozen'); o.vx = kx || dir * 60; o.fall = 0; o.burn = 0; o.frozenDur = POWER.ice.freeze;
      } else if (down) knockDown(o, dir, frontal, a, kx);
      else if (o.fall > LF2.fall.dizzy) { setSt(o, 'dizzy'); o.vx = kx; }   // 40 < fall <= 60: dance of pain (frames 226-229)
      else { setSt(o, 'hurt'); o.vx = kx; }
      popText(o, String(Math.round(dmg)), '#fff');
    }
    o.hp = Math.max(0, o.hp - dmg); o.hpDark = Math.max(o.hp, o.hpDark - Math.ceil(dmg / 3));   // LF2 injury(): hp_bound -= ceil(inj / 3)
    o.stats.hpLost += dmg;
    if (att) { att.stats.dealt += dmg; att.hitstop = Math.max(att.hitstop, stopA); }
    o.hitstop = Math.max(o.hitstop, stopV);
    if (o.hp <= 0) { o.lastHitBy = att; if (o.st !== 'fall') knockDown(o, dir, frontal, { dvy: 400 }, dir * 200); }
    return true;
  }
  const W_ATK = new Map();
  function withWeapon(f, a) {   // per-weapon damage / reach on the shared light-weapon moves
    if (!f.hold || holdKind(f) !== 'light' || ![ATK.w_thrust, ATK.w_swing, ATK.w_jump].includes(a)) return a;
    const d = ITEM_DEF[f.hold.type], key = f.hold.type + ':' + Object.keys(ATK).find(k => ATK[k] === a);
    if (!W_ATK.has(key)) W_ATK.set(key, { ...a, dmg: Math.round(a.dmg * (d.dmgK || 1)), reach: Math.round(a.reach * (d.reachK || 1)) });
    return W_ATK.get(key);
  }
  function meleeCheck(f, a, opts = {}) {
    if (a.phases) {   // several itr boxes (one per frame): pick the one of the current frame
      const p = a.phases.find(p => f.t >= p.t0 - 1e-6 && f.t < p.t1 - 1e-6);
      if (!p) return;
      a = { ...a, ...p };
    } else if (f.t < a.t0 || f.t > a.t1) return;
    if (a.arest && f.arest > 1e-6) return;   // LF2 arest: after a hit the attacker cannot hit again for N TU
    const reach = a.reach;
    for (const o of fight.fighters) {
      if (o === f || o.team === f.team || !canBeHit(o, a.fall === undefined ? LF2.fall.value : a.fall)) continue;
      if (a.vrest ? o.vrest.get(f) > 1e-6 : !a.arest && f.hitSet.has(o)) continue;   // vrest: per-victim delay; arest: the attacker timer; otherwise one hit per victim and move
      const dz = Math.abs(o.z - f.z);
      // LF2: the itr rectangle must overlap the target's bdy rectangle (mirrored with facing); z within itr zwidth 12
      const inX = opts.both ? Math.abs(o.x - f.x) <= reach : overlapX(xspan(f, a.bx || [-10, reach]), xspan(o, BODY));
      if (!inX || dz > ZW) continue;
      const hy0 = f.y + a.hy[0], hy1 = f.y + a.hy[1], hb = hurtBox(o);
      if (hy1 < hb.y0 || hy0 > hb.y1) continue;
      f.hitSet.add(o);
      if (a.vrest) o.vrest.set(f, a.vrest); else if (a.arest) f.arest = a.arest;
      if (f.hold && holdKind(f) === 'light') wearItem(f);
      applyHit(f, o, a, f.x);
      if (opts.once) return;
      if (a.arest) break;   // one victim per arest window
    }
    // LF2: attacks bat balls back
    for (const b of fight.balls) if (b.team !== f.team && Math.abs(b.z - f.z) < 18) {
      const dx = (b.x - f.x) * f.face;
      if (dx > -10 && dx < reach + 10) { b.vx = f.face * Math.abs(b.vx) * 1.1; b.team = f.team; b.owner = f; sfx('block'); spark(b.x, gy(b.z) - b.y, '#ffd21f', 8); }
    }
  }
  function wearItem(f) {
    const it = f.hold; if (!it) return;
    it.hp -= 1;
    if (it.hp <= 0) { f.hold = null; it.state = 'gone'; spark(f.x + f.face * 50, gy(f.z) - 60, '#c8c8c8', 14); sfx('break'); popText(f, PL ? 'WIDŁY PĘKŁY' : 'BROKEN', '#c8c8c8'); }
  }
  function onKo(f) {
    f.ko = true; f.deadT = 0; sfx('ko');
    const by = f.lastHitBy; if (by && by !== f) by.stats.kills++;
    banner('K.O.', f.x, gy(f.z) - 110, '#ff6b5e');
  }

  /* -------------------------------------------- specials */
  function special(f, which) {
    const sp = f.def[which], cost = which === 'power' && sp ? POWER[sp.el].mp : sp && sp.mp;
    if (!sp || f.mp < cost) return false;
    if (which === 'power') {
      f.mp -= cost; f.stats.mpUsed += cost;
      if (holdKind(f) === 'heavy') dropHold(f, false);   // Michał keeps his pistol, Sołtys his teczka
      f.running = 0; f.vx = 0; setSt(f, 'power');
      banner(sp.name, f.x, gy(f.z) - 130, sp.color); sfx('special');
      return true;
    }
    f.mp -= sp.mp; f.stats.mpUsed += sp.mp;
    if (f.hold && which === 'ball' && f.def.ball.item === f.hold.type) { f.hold.state = 'gone'; f.hold = null; }   // Sołtys throws the teczka he holds
    else if (f.hold && !(which === 'ball' && f.def.ball.gun && holdKind(f) === 'gun')) dropHold(f, false);
    f.running = 0;
    if (which === 'ball') { setSt(f, 'cast'); f.vx = f.vz = 0; } else { setSt(f, 'spin'); f.vz = 0; f.vx = f.face * sp.vx; if (sp.dvy) { f.vy = 380; f.y = 1; } }
    banner(sp.name, f.x, gy(f.z) - 130, f.color); sfx('special');
    return true;
  }
  function specialInput(f, now) {
    const h = f.hist.filter(p => now - p[1] < .7), n = h.length;
    if (n < 3 || h[n - 1][0] !== 'attack' || h[n - 3][0] !== 'defend') return null;
    const dir = h[n - 2][0];
    if (dir === 'left' || dir === 'right') return { which: 'ball', face: dir === 'left' ? -1 : 1 };
    if (dir === 'up') return { which: 'spin' };
    if (dir === 'down') return { which: 'power' };
    return null;
  }
  const pressedHas = (f, a) => (f.input.pressed || []).includes(a);
  function nearItem(f) {
    let best = null, bd = 1e9;
    for (const it of fight.items) if (it.state === 'ground' && Math.abs(it.x - f.x) < 34 && Math.abs(it.z - f.z) < 16) { const d = Math.abs(it.x - f.x); if (d < bd) { bd = d; best = it; } }
    return best;
  }
  function tryGrab(f) {
    if (f.hold || f.grabbing) return false;
    for (const o of fight.fighters) {
      if (o === f || o.team === f.team || o.st !== 'dizzy' || o.grabbedBy || o.y > 0) continue;
      const dx = (o.x - f.x) * f.face;
      if (dx > 8 && dx < 40 && Math.abs(o.z - f.z) < 12) {
        f.grabbing = o; o.grabbedBy = f; f.running = 0; setSt(f, 'grab'); setSt(o, 'held'); f.grabT = 0; f.grabHits = 0; o.face = -f.face; return true;
      }
    }
    return false;
  }

  /* -------------------------------------------- per-fighter state machine */
  function updateFighter(f, now) {
    const inp = f.input, hd = inp.held || {};
    f.inv = Math.max(0, f.inv - DT); f.flash = Math.max(0, f.flash - DT);
    f.arest = Math.max(0, f.arest - DT);   // LF2 itr.arest / itr.vrest tick down every TU, also during hit stop
    for (const [k, v] of f.vrest) { if (v - DT <= 1e-6) f.vrest.delete(k); else f.vrest.set(k, v - DT); }
    const tu = !!fight.tuEdge;   // true on the tick that completes one LF2 time unit (every 2nd tick)
    f.fall = Math.max(0, f.fall - LF2.fall.recover * LF2.TU * DT); f.bdef = Math.max(0, f.bdef - LF2.bdef.recover * LF2.TU * DT);   // GC.recover.fall / .bdefend per TU
    if (alive(f) && tu) {   // LF2 health regen: +1 hp / 12 TU (up to the dark bound); +1 + floor(lost hp / 100) mp / 3 TU
      if (fight.tuN % LF2.hpRegen === 0 && f.hp > 0 && f.hp < f.hpDark) f.hp = Math.min(f.hpDark, f.hp + 1);
      if (fight.tuN % LF2.mpRegen === 0 && f.mp < f.mpMax) f.mp = Math.min(f.mpMax, f.mp + 1 + Math.floor((f.hpMax - Math.min(f.hp, f.hpMax)) / 100));
    }
    if (f.burn > 0) {   // fire damage over time; never the final blow
      const before = Math.floor(f.burn / .3); f.burn = Math.max(0, f.burn - DT);
      if (Math.floor(f.burn / .3) !== before && f.hp > 1 && alive(f)) {
        const bd = Math.min(POWER.fire.burnDmg, f.hp - 1); f.hp -= bd; f.hpDark = Math.max(f.hp, f.hpDark - 2); f.stats.hpLost += bd;
        if (f.burnBy) f.burnBy.stats.dealt += bd;
      }
      if (Math.random() < .5) fight.fx.push({ x: f.x + (Math.random() - .5) * 26, y: gy(f.z) - f.y - 20 - Math.random() * 60, vx: (Math.random() - .5) * 40, vy: -120 - Math.random() * 80, t: 0, life: .3, color: Math.random() < .5 ? '#ff7a1a' : '#ffd21f' });
    }
    if (f.hitstop > 0) {   // frozen on impact: remember what was pressed so a long pause never eats an input (LF2-style buffer)
      f.hitstop -= DT;
      for (const a of inp.pressed || []) { f.hist.push([a, now]); if (f.hist.length > 8) f.hist.shift(); (f.buf || (f.buf = new Set())).add(a); }
      return;
    }
    for (const a of inp.pressed || []) { f.hist.push([a, now]); if (f.hist.length > 8) f.hist.shift(); }
    if (f.buf && f.buf.size) { f.input = { held: hd, pressed: [...new Set([...(inp.pressed || []), ...f.buf])] }; f.buf.clear(); }   // replay the buffered presses on the first free tick
    f.t += DT; f.frameT += DT;
    const d = f.def, kind = holdKind(f);
    const mx = (hd.right ? 1 : 0) - (hd.left ? 1 : 0), mz = (hd.down ? 1 : 0) - (hd.up ? 1 : 0);

    if (f.ko) { physicsGround(f); f.deadT += DT; return; }

    if (FREE.has(f.st)) {
      for (const a of f.input.pressed || []) if ((a === 'left' || a === 'right') && kind !== 'heavy') {
        const dir = a === 'left' ? -1 : 1;
        if (f.running && dir !== f.running) { f.running = 0; setSt(f, 'skid'); return; }   // LF2 frame 218 stop_running: keeps the speed, friction slides it out
        if (!f.running && now - f.tap[a] < .26) { f.running = dir; f.face = dir; }
        f.tap[a] = now;
      }
      if (pressedHas(f, 'attack') || f.queueAtk) {
        f.queueAtk = false;
        const sp = specialInput(f, now);
        if (sp) { if (sp.face) f.face = sp.face; f.hist.length = 0; if (special(f, sp.which)) return; }
        const it = !f.hold && nearItem(f);
        if (it) { setSt(f, 'pick'); f.pickItem = it; it.state = 'reserved'; f.running = 0; return; }
        if (f.running) { f.running = 0; setSt(f, kind === 'light' ? 'w_atk2' : kind === 'heavy' ? 'heavy_throw' : 'runatk'); return; }
        if (kind === 'heavy') { setSt(f, 'heavy_throw'); return; }
        if (kind === 'gun' && mx !== f.face) { setSt(f, 'shoot'); return; }
        if ((kind === 'light' || kind === 'gun') && mx === f.face) { setSt(f, 'w_throw'); return; }
        if (kind === 'light') { f.punchAlt ^= 1; setSt(f, f.punchAlt ? 'w_atk1' : 'w_atk2'); return; }
        if (!kind && f.ammo > 0 && !fight.fighters.some(o => o !== f && o.team !== f.team && alive(o) && Math.abs(o.x - f.x) < 60 && Math.abs(o.z - f.z) < 16)) {
          f.ammo--; setSt(f, 'toss'); return;
        }
        // LF2: ATTACK becomes the super punch when its itr box meets a kind-6 box (dizzy frames 226-229, broken defend 112-114)
        const sbox = xspan(f, ATK.super.bx);
        const dizzy = fight.fighters.find(o => o !== f && o.team !== f.team && (o.st === 'dizzy' || o.st === 'brokendef') && Math.abs(o.z - f.z) <= ZW && overlapX(sbox, xspan(o, CATCH)));
        if (dizzy) { setSt(f, 'super'); return; }
        f.punchAlt ^= 1; setSt(f, 'punch'); return;
      }
      if (pressedHas(f, 'jump') && kind !== 'heavy') {
        if (f.running) { setSt(f, 'dash'); f.vx = f.running * (LF2.dashDist - 1) * PXTU; f.vz = mz * (LF2.dashDistZ - 1) * PXTU; f.vy = LF2.dashH * PXTU; f.running = 0; sfx('whoosh'); if (tu) dynamics(f); return; }   // state 5 entry: dash_distance-1, dash_height
        setSt(f, 'jumpsquat'); return;
      }
      if (hd.defend || pressedHas(f, 'defend')) {
        if (f.running) { setSt(f, 'roll'); f.vx = f.running * LF2.rollSpeed * PXTU; f.running = 0; sfx('whoosh'); return; }   // frames 102-105: dvx 9, no bdy
        if (kind !== 'heavy') { setSt(f, 'defend'); return; }
      }
      // LF2 states 1 / 2: the state sets vx / vz every TU (x speed reduced while moving in z), then mechanics adds friction
      const heavy = kind === 'heavy';
      if (f.running) {
        f.face = f.running;
        if (tu) { f.vx = f.running * LF2.run * (1 - (mz ? LF2.diagRun : 0)) * PXTU; f.vz = mz * LF2.runz * PXTU; }
        if (f.st !== 'run') { f.st = 'run'; f.frameT = 0; }
        tryGrab(f);
      } else if (mx || mz) {
        if (mx) f.face = mx;
        if (tu) { if (mx) f.vx = mx * (heavy ? LF2.hWalk : LF2.walk) * (1 - (mz ? LF2.diagWalk : 0)) * PXTU; f.vz = mz * (heavy ? LF2.hWalkz : LF2.walkz) * PXTU; }
        if (f.st !== 'walk') { f.st = 'walk'; f.frameT = 0; }
        if (mx) tryGrab(f);
      } else if (f.st !== 'stand') { f.st = 'stand'; f.frameT = 0; }
      if (tu) dynamics(f);
      clampPos(f); return;
    }

    switch (f.st) {
      case 'defend': {
        const sp = pressedHas(f, 'attack') && specialInput(f, now);
        if (sp) { if (sp.face) f.face = sp.face; f.hist.length = 0; if (special(f, sp.which)) return; }
        if (!hd.defend && f.t > .15) setSt(f, 'stand');
        break;
      }
      case 'punch': case 'super': case 'runatk': case 'w_atk1': case 'w_atk2': {
        const a = withWeapon(f, f.st === 'punch' ? (f.punchAlt ? ATK.punch : ATK.punch2) : f.st === 'super' ? ATK.super : f.st === 'runatk' ? ATK.runatk : f.st === 'w_atk1' ? ATK.w_thrust : ATK.w_swing);
        if (f.t <= DT * 1.01 && f.st !== 'punch') sfx('whoosh');
        if (tu) {   // frame pushes (dvx) then LF2 dynamics: friction slides the lunge out
          for (const [t0, t1, dv] of a.adv || []) if (f.t >= t0 * TUS - 1e-6 && f.t < t1 * TUS - 1e-6 && Math.abs(f.vx) < dv * PXTU) f.vx = f.face * dv * PXTU;
          dynamics(f);
        }
        meleeCheck(f, a);
        if (pressedHas(f, 'attack') && f.t > a.t0) f.queueAtk = true;   // LF2-style input buffer: chain the next hit
        if (f.t >= a.dur - 1e-6) setSt(f, 'stand');
        break;
      }
      case 'skid': if (tu) dynamics(f); if (f.t >= LF2.skid * TUS - 1e-6) setSt(f, 'stand'); break;
      case 'jumpsquat':   // frames 210, 211, then at the first TU of 212: vx = dx * (jump_distance - 1), vz likewise, vy = jump_height
        if (tu) {
          if (f.t >= (LF2.squat - .5) * TUS) {
            setSt(f, 'jump'); f.vx = mx * (LF2.jumpDist - 1) * PXTU; f.vz = mz * (LF2.jumpDistZ - 1) * PXTU; f.vy = LF2.jumpH * PXTU; sfx('whoosh');
            airTU(f);
          } else dynamics(f);
        }
        break;
      case 'jump': case 'dash': case 'jkick': case 'dashkick': case 'w_jump': {
        if (pressedHas(f, 'attack') && (f.st === 'jump' || f.st === 'dash')) {
          if (kind === 'light' && mx === f.face) { setSt(f, 'w_throw'); f.air = true; }
          else setSt(f, kind === 'light' ? 'w_jump' : f.st === 'dash' ? 'dashkick' : 'jkick');
        }
        if (f.st === 'jkick') meleeCheck(f, ATK.jkick, { once: true });
        if (f.st === 'dashkick') meleeCheck(f, ATK.dashkick, { once: true });
        if (f.st === 'w_jump') meleeCheck(f, withWeapon(f, ATK.w_jump), { once: true });
        if (f.st === 'jkick' && f.t >= ATK.jkick.dur) setSt(f, 'jump');   // frame 79 returns to the jump (212) while still airborne
        if (tu) airTU(f);
        break;
      }
      case 'roll':   // frames 102-105: dvx 9 is re-applied every TU while friction eats 1; the frames have no bdy
        if (tu) { if (Math.abs(f.vx) < LF2.rollSpeed * PXTU) f.vx = Math.sign(f.vx || f.face) * LF2.rollSpeed * PXTU; dynamics(f); }
        if (f.t >= LF2.roll * TUS - 1e-6) setSt(f, 'land');
        break;
      case 'hurt': if (tu) dynamics(f); if (f.t >= LF2.hurt * TUS - 1e-6) setSt(f, 'stand'); break;
      case 'dizzy': if (tu) dynamics(f); if (f.t >= LF2.dizzy * TUS - 1e-6) setSt(f, 'stand'); break;   // the fall meter keeps decaying, it is not reset
      case 'brokendef': if (tu) dynamics(f); if (f.t >= LF2.broken * TUS - 1e-6) setSt(f, 'stand'); break;
      case 'held': {
        const g = f.grabbedBy;
        if (!g || g.grabbing !== f) { f.grabbedBy = null; setSt(f, 'dizzy'); f.t = .8; break; }
        f.x = g.x + g.face * 36; f.z = g.z; f.face = -g.face; f.y = 0;
        break;
      }
      case 'grab': {
        const v = f.grabbing; f.grabT += DT;
        if (!v || v.st !== 'held') { f.grabbing = null; setSt(f, 'stand'); break; }
        if (pressedHas(f, 'attack')) {
          if (mx) { f.face = mx; f.throwDir = mx; setSt(f, 'throw'); break; }
          setSt(f, 'grabpunch'); break;
        }
        if (pressedHas(f, 'jump') || f.grabT > 2.6) { releaseGrab(f); setSt(f, 'stand'); }
        break;
      }
      case 'grabpunch': {
        const v = f.grabbing; f.grabT += DT;
        if (f.t > .06 && !f.released && v) {
          f.released = true; f.grabHits++;
          v.hp = Math.max(0, v.hp - 20); v.hpDark = Math.max(v.hp, v.hpDark - 7); v.stats.hpLost += 20; f.stats.dealt += 20; v.flash = .1;
          spark(v.x, gy(v.z) - 65, '#fff3b0', 8); sfx('hit'); popText(v, '20', '#fff');
          if (v.hp <= 0 || f.grabHits >= 4) { f.grabbing = null; v.grabbedBy = null; v.lastHitBy = f; setSt(v, 'fall'); v.vx = f.face * 200; v.vy = 380; v.y = 1; v.lieFront = false; }
        }
        if (f.t > .22) setSt(f, f.grabbing ? 'grab' : 'stand');
        break;
      }
      case 'throw': {
        const v = f.grabbing;
        if (f.t > .1 && !f.released && v) {
          f.released = true; f.grabbing = null; v.grabbedBy = null;
          setSt(v, 'fall'); v.thrownBy = f; v.vx = f.throwDir * 400; v.vy = 330; v.y = 20; v.lieFront = false; v.x = f.x + f.throwDir * 20; sfx('whoosh');
        }
        if (f.t > .34) setSt(f, 'stand');
        break;
      }
      case 'fall': {
        // LF2 rowing: JUMP during frame 182 (front fall) / 188 (back fall) of the falling animation; frame 182 starts 5 TU after the hit, 188 after 8, each lasts 4 TU
        const w0 = (f.lieFront ? 8 : 5) * TUS;
        if (pressedHas(f, 'jump') && f.t >= w0 - 1e-6 && f.t < w0 + 4 * TUS && f.hp > 0 && !f.thrownBy) {
          const vx = f.vx ? Math.sign(f.vx) * LF2.flipDvx * PXTU : 0, vz = f.vz ? Math.sign(f.vz) * 2 * PXTU : 0;
          setSt(f, 'flip'); f.vx = vx; f.vz = vz; f.vy = 0; break;
        }
        if (tu) airTU(f, true);
        break;
      }
      case 'flip': if (tu) { if (f.t < LF2.flipHover * TUS) f.vy = 0; airTU(f); } break;   // frame 100 holds vy = 0 for 3 TU, then gravity
      case 'land': if (tu) dynamics(f); if (f.t >= LF2.crouch * TUS - 1e-6) setSt(f, 'stand'); break;   // crouch frames 215 / 219: 3 TU
      case 'lying':   // frames 230 / 231: wait 30 = 31 TU, sliding with ground friction; the exit gives 30 TU of invulnerability (state_exit effect.super)
        if (tu) dynamics(f);
        if (f.t >= (f.hp <= 0 ? .85 : LF2.lying * TUS) - 1e-6) { if (f.hp <= 0) { setSt(f, 'dead'); onKo(f); } else { setSt(f, 'getup'); f.inv = LF2.lieInv * TUS; } }
        break;
      case 'getup': if (tu) dynamics(f); if (f.t >= LF2.crouch * TUS - 1e-6) { setSt(f, 'stand'); f.fall = 0; } break;
      case 'cast': {
        const sp = f.def.ball, times = sp.volley ? [.1, .19, .28] : [.15];
        if (f.t < DT * 1.5) f.shots = 0;
        if ((f.shots || 0) < times.length && f.t > times[f.shots || 0]) {
          f.shots = (f.shots || 0) + 1; f.released = f.shots === times.length;
          fight.balls.push({ owner: f, team: f.team, item: sp.item, x: f.x + f.face * 46, z: f.z, y: sp.gun ? 74 : 62, vx: f.face * sp.speed, dmg: sp.dmg, fall: sp.fall, life: 1.9, spin: 0, nospin: !!sp.gun });
          sfx(sp.gun ? 'block' : 'whoosh');
        }
        if (f.t > (sp.volley ? .46 : .38)) setSt(f, 'stand');
        break;
      }
      case 'spin': {
        const sp = f.def.spin;
        f.x += f.vx * DT; f.vx *= Math.pow(.25, DT);
        if (f.y > 0 || f.vy) { f.vy -= GRAV * DT; f.y += f.vy * DT; if (f.y <= 0) { f.y = 0; f.vy = 0; } }
        const slot = Math.floor(f.t / (sp.dur / sp.hits));
        if (slot >= f.hitsDone && slot < sp.hits) { f.hitSet = new Set(); f.hitsDone = slot + 1; }
        meleeCheck(f, { t0: sp.t0 || .05, t1: sp.dur - .05, reach: sp.reach || 70, hy: sp.hy || [10, 110], dmg: sp.dmg, fall: sp.fall, bdef: 25, dvx: sp.dvx || 200, dvy: sp.hits === 1 ? 420 : 0 }, { both: !sp.front });
        if (sp.t0 && f.t >= sp.t0 && f.t - DT < sp.t0) { fight.shake = .2; sfx('heavy'); spark(f.x + (sp.front ? f.face * 50 : 0), gy(f.z) - 6, '#c8b090', 14); }
        if (f.t >= sp.dur && f.y <= 0) { setSt(f, 'stand'); f.vx = 0; }
        break;
      }
      case 'power': {
        const pw = f.def.power, P = POWER[pw.el];
        if (pw.el !== 'beam') {
          if (f.t > .18 && !f.released) {
            f.released = true;
            fight.balls.push({ owner: f, team: f.team, el: pw.el, color: pw.color, x: f.x + f.face * 46, z: f.z, y: 66, vx: f.face * P.speed, dmg: P.dmg, fall: P.fall, bdef: P.bdef, dvx: P.dvx, dvy: P.dvy, life: 1.9, spin: 0, nospin: true });
            sfx('whoosh');
          }
          if (f.t > .44) setSt(f, 'stand');
          break;
        }
        // kamehameha: charge, then a screen-long beam that hits every P.tick
        f.beamLen = 0;
        if (f.t >= P.charge && f.t < P.end) {
          if (f.t - DT < P.charge) { sfx('special'); fight.shake = Math.max(fight.shake, .12); }
          const x0 = f.x + f.face * 36, len = f.face > 0 ? viewHi() - x0 : x0 - viewLo();
          f.beamLen = Math.max(0, len);
          const slot = Math.floor((f.t - P.charge) / P.tick);
          if (slot >= f.hitsDone) { f.hitSet = new Set(); f.hitsDone = slot + 1; }
          for (const o of fight.fighters) {
            if (o === f || o.team === f.team || f.hitSet.has(o) || !canBeHit(o, P.fall)) continue;
            const dx = (o.x - x0) * f.face;
            if (dx < -14 || dx > f.beamLen || Math.abs(o.z - f.z) > 18) continue;
            const hb = hurtBox(o); if (f.y + P.hy[1] < hb.y0 || f.y + P.hy[0] > hb.y1) continue;
            f.hitSet.add(o); o.lastHitBy = f;
            applyHit(f, o, { dmg: P.dmg, fall: P.fall, bdef: P.bdef, dvx: P.dvx, el: 'beam' }, f.x);
          }
          for (const b of fight.balls) if (b.team !== f.team && Math.abs(b.z - f.z) < 18 && (b.x - x0) * f.face > -10 && (b.x - x0) * f.face < f.beamLen) { b.life = 0; spark(b.x, gy(b.z) - b.y, pw.color, 10); }
        }
        if (f.t >= P.dur) setSt(f, 'stand');
        break;
      }
      case 'frozen':
        if (tu) { dynamics(f); if (f.y <= 0) f.vy = 0; }
        // LF2 frame 201 holds 91 TU, then frame 202 shatters the ice: dvx -4, dvy -3 and the fighter falls (frame 182)
        if (f.t >= (f.frozenDur || LF2.freeze * TUS) && f.y <= 0) { spark(f.x, gy(f.z) - 50, '#d8f4ff', 14); sfx('break'); setSt(f, 'fall'); f.lieFront = false; f.fall = 0; f.vx = -f.face * LF2.shatter.vx * PXTU; f.vy = LF2.shatter.vy * PXTU; }
        clampPos(f);
        break;
      case 'pick': {
        if (f.t > .14 && !f.released) {
          f.released = true; const it = f.pickItem; f.pickItem = null;
          if (it && it.state === 'reserved') {
            f.stats.picks++; sfx('pick');
            if (ITEM_DEF[it.type].kind === 'drink') { it.state = 'gone'; setSt(f, 'drink'); return; }
            if (ITEM_DEF[it.type].kind === 'ammo') { it.state = 'gone'; f.ammo = (f.ammo || 0) + ITEM_DEF[it.type].ammo; popText(f, `${PL ? 'PIECZARKI' : 'MUSHROOMS'} ×${f.ammo}`, '#f4efe0'); setSt(f, 'stand'); return; }
            it.state = 'held'; it.owner = f; f.hold = it;
          }
        }
        if (f.t > .2) setSt(f, 'stand');
        break;
      }
      case 'drink':
        if (f.t < 1.1) {
          f.hpDark = Math.min(f.hpMax, f.hpDark + DT * 90); f.hp = Math.min(f.hpDark, f.hp + DT * 90); f.mp = Math.min(f.mpMax, f.mp + DT * 160);
          if (Math.floor(f.t * 4) !== Math.floor((f.t - DT) * 4)) sfx('drink');
        }
        if (f.t > 1.15) setSt(f, 'stand');
        break;
      case 'w_throw': {
        if (f.t > .1 && !f.released && f.hold) {
          f.released = true; const it = f.hold; f.hold = null;
          Object.assign(it, { state: 'flying', owner: f, team: f.team, x: f.x + f.face * 40, z: f.z, y: f.y + 60, vx: f.face * 560, vy: 60, vz: 0, dmg: 45, fall: 70 });
          sfx('whoosh');
        }
        if (f.air || f.y > 0) { if (tu) airTU(f); if (f.st !== 'w_throw') f.air = false; break; }
        if (f.t > .36) setSt(f, 'stand');
        break;
      }
      case 'heavy_throw': {
        if (f.t > .12 && !f.released && f.hold) {
          f.released = true; const it = f.hold; f.hold = null;
          const idf = ITEM_DEF[it.type];
          Object.assign(it, { state: 'flying', owner: f, team: f.team, x: f.x + f.face * 30, z: f.z, y: 95, vx: f.face * (idf.long ? 520 : 420), vy: idf.long ? 120 : 160, vz: 0, dmg: idf.dmg || 60, fall: 90 });
          sfx('whoosh');
        }
        if (tu) dynamics(f);
        if (f.t > .4) setSt(f, 'stand');
        break;
      }
      case 'shoot': {   // paintball pistol: one orange ball per ATTACK
        if (f.t > .06 && !f.released && f.hold) {
          f.released = true; const it = f.hold; it.ammo = (it.ammo || 0) - 1;
          fight.balls.push({ owner: f, team: f.team, item: 'kulka', x: f.x + f.face * 44, z: f.z, y: 74, vx: f.face * 820, dmg: 14, fall: 20, life: 1.3, spin: 0, nospin: true });
          sfx('block');
          if (it.ammo <= 0) { it.state = 'gone'; f.hold = null; popText(f, PL ? 'PUSTY!' : 'EMPTY!', '#f07820'); }
        }
        if (pressedHas(f, 'attack') && f.t > .1) f.queueAtk = true;
        if (f.t > .26) setSt(f, 'stand');
        break;
      }
      case 'toss':
        if (f.t > .08 && !f.released) {
          f.released = true;
          fight.balls.push({ owner: f, team: f.team, item: 'pieczarka', x: f.x + f.face * 40, z: f.z, y: 70, vx: f.face * 560, dmg: 18, fall: 22, life: 1.4, spin: 0 });
          sfx('whoosh');
        }
        if (f.t > .24) setSt(f, 'stand');
        break;
      case 'win': case 'dead': break;
      default: setSt(f, 'stand');
    }
    clampPos(f);
  }
  function clampPos(f) { f.x = Math.max(xLo(), Math.min(xHi(), f.x)); f.z = Math.max(0, Math.min(depth(), f.z)); }
  // LF2 mechanics.js dynamics(), once per TU: move by the velocity, clamp to the ground, then ground friction (1 px/TU^2, speeds under 1 stop)
  // or gravity (1.7 px/TU^2). Returns true on the TU the fighter reaches the ground while moving down.
  function dynamics(f) {
    f.x += f.vx / LF2.TU; f.z += f.vz / LF2.TU; f.y += f.vy / LF2.TU;
    let landed = false;
    if (f.y <= 0) {
      f.y = 0; landed = f.vy < 0;
      const fr = LF2.friction * PXTU, mn = LF2.minSpeed * PXTU;
      if (f.vx) f.vx -= Math.sign(f.vx) * fr;
      if (f.vz) f.vz -= Math.sign(f.vz) * fr;
      if (f.vx && Math.abs(f.vx) < mn) f.vx = 0;
      if (f.vz && Math.abs(f.vz) < mn) f.vz = 0;
    } else f.vy -= LF2.gravity * PXTU;
    return landed;
  }
  // LF2 fall_onto_ground for a knocked-down body: a hard landing bounces (speed > 13.4 or vy > 11 px/TU), otherwise it lies down and slides
  function landFall(f) {
    const vyd = -f.vy / PXTU, speed = Math.hypot(f.vx, f.vy) / PXTU;
    if (speed > LF2.bounce.xy || vyd > LF2.bounce.y) {
      const ab = lookupAbs(LF2.bounce.absorb, f.vx / PXTU) * PXTU, abz = lookupAbs(LF2.bounce.absorb, f.vz / PXTU) * PXTU;
      f.vx -= Math.sign(f.vx) * Math.min(Math.abs(f.vx), ab); f.vz -= Math.sign(f.vz) * Math.min(Math.abs(f.vz), abz);
      f.vy = LF2.bounce.up * PXTU; sfx('land'); fight.shake = Math.max(fight.shake, .1);
      return;
    }
    const fx = lookupAbs(LF2.fell, f.vx / PXTU) * PXTU, fz = lookupAbs(LF2.fell, f.vz / PXTU) * PXTU;   // GC.friction.fell at the moment of landing
    f.vx -= Math.sign(f.vx) * Math.min(Math.abs(f.vx), fx); f.vz -= Math.sign(f.vz) * Math.min(Math.abs(f.vz), fz);
    f.vy = 0; f.fall = 0; f.bdef = 0; setSt(f, 'lying'); sfx('land');   // state 14 entry resets both meters
  }
  function airTU(f, falling) {
    const landed = dynamics(f);
    if (f.thrownBy && f.st === 'fall') for (const o of fight.fighters) {   // a thrown body knocks over whoever it flies into
      if (o === f || o === f.thrownBy || o.team === f.thrownBy.team || !canBeHit(o, 80) || f.hitSet.has(o)) continue;
      if (Math.abs(o.x - f.x) < 36 && Math.abs(o.z - f.z) < 16 && f.y < 100) { f.hitSet.add(o); applyHit(f.thrownBy, o, { dmg: 35, fall: 80, bdef: 40, dvx: 240, dvy: 300 }, f.x); }
    }
    if (landed) {
      if (falling) {
        if (f.thrownBy) { const t = f.thrownBy; f.thrownBy = null; applyLand(f, t); }
        landFall(f);
      } else { f.air = false; setSt(f, 'land'); }   // jump landing = crouch; the speed is kept and friction slides it out
    }
    clampPos(f);
  }
  function applyLand(f, by) {
    const dmg = 40; f.hp = Math.max(0, f.hp - dmg); f.hpDark = Math.max(f.hp, f.hpDark - 13); f.stats.hpLost += dmg; by.stats.dealt += dmg; f.lastHitBy = by;
    popText(f, String(dmg), '#fff'); fight.shake = .18;
  }
  function physicsGround(f) {
    if (f.y > 0 || f.vy) { f.x += f.vx * DT; f.vy -= GRAV * DT; f.y += f.vy * DT; if (f.y <= 0) { f.y = 0; f.vy = 0; f.vx = 0; } }
  }

  /* -------------------------------------------- items & balls */
  function spawnItem(type, x, z, fromSky = true) {
    const it = { type, x, z, y: fromSky ? 520 : 0, vx: 0, vy: 0, vz: 0, state: fromSky ? 'free' : 'ground', hp: ITEM_DEF[type].hp, owner: null, team: null, spin: 0 };
    if (ITEM_DEF[type].kind === 'gun') it.ammo = ITEM_DEF[type].ammo;
    fight.items.push(it); return it;
  }
  function updateItems() {
    for (const it of fight.items) {
      if (it.state === 'held' && it.owner) { it.x = it.owner.x; it.z = it.owner.z; it.y = it.owner.y; continue; }
      if (it.state === 'free' || it.state === 'flying') {
        const flying = it.state === 'flying';
        it.x += it.vx * DT; it.z += it.vz * DT; it.vy -= GRAV * (flying ? (ITEM_DEF[it.type].grav || .35) : 1) * DT; it.y += it.vy * DT; it.spin += DT * (flying ? 14 : 0);
        if (it.x < X0 - 10 || it.x > worldHi() + 10) { it.vx = -it.vx * .4; it.x = Math.max(X0 - 10, Math.min(worldHi() + 10, it.x)); }
        if (flying) for (const o of fight.fighters) {
          if (o.team === it.team || !canBeHit(o, it.fall)) continue;
          if (Math.abs(o.x - it.x) < 30 && Math.abs(o.z - it.z) < 16 && it.y < o.y + 100 && it.y > o.y - 10) {
            applyHit(it.owner, o, { dmg: it.dmg, fall: it.fall, bdef: 40, dvx: 240, dvy: 300 }, it.x - Math.sign(it.vx) * 30);
            it.state = 'free'; it.vx *= -.25; it.vy = 160;
            if (it.type === 'widly') { it.hp -= 3; if (it.hp <= 0) { it.state = 'gone'; spark(it.x, gy(it.z) - it.y, '#c8c8c8', 14); sfx('break'); } }
            break;
          }
        }
        if (it.y <= 0 && it.state !== 'gone') {
          it.y = 0;
          if (ITEM_DEF[it.type].rolls && it.state === 'flying' && Math.abs(it.vx) > 80) { it.vy = Math.abs(it.vy) > 200 ? -it.vy * .25 : 0; it.vx *= .985; it.y = 0; continue; }   // a tyre keeps rolling and still hits
          if (Math.abs(it.vy) > 260 && ITEM_DEF[it.type].kind !== 'drink') { it.vy = -it.vy * .3; it.vx *= .5; sfx('land'); }
          else { it.vy = 0; it.vx = 0; it.state = 'ground'; it.team = null; it.owner = null; it.spin = 0; }
        }
      }
    }
    fight.items = fight.items.filter(it => it.state !== 'gone');
    if (OPTS.items && fight.phase === 'fight') {
      fight.itemT -= DT;
      if (fight.itemT <= 0) {
        fight.itemT = 9 + Math.random() * 8;
        if (fight.items.filter(i => i.state !== 'held').length < 4) {
          const pool = ['widly', 'lomza', 'lomza', 'pieczarki', 'stone', 'churn', 'tyre', 'bucket', 'rake', 'shovel', 'scythe', 'broom', 'pan', 'club', 'picket', 'rollpin', 'teczka', 'pistol'];
          const type = pool[Math.floor(Math.random() * pool.length)];
          spawnItem(type, viewLo() + X0 + 60 + Math.random() * (W - 2 * X0 - 120), Math.random() * depth());
        }
      }
    }
  }
  function updateBalls() {
    for (const b of fight.balls) {
      b.x += b.vx * DT; b.life -= DT; b.spin += DT * 16;
      if (b.el && Math.random() < .7) fight.fx.push({ x: b.x - Math.sign(b.vx) * 10, y: gy(b.z) - b.y + (Math.random() - .5) * 12, vx: -b.vx * .15, vy: b.el === 'fire' ? -90 : 30, t: 0, life: .25, color: b.el === 'fire' ? (Math.random() < .5 ? '#ff7a1a' : '#ffd21f') : (Math.random() < .5 ? '#bfe8ff' : '#ffffff') });
      if (b.x < viewLo() - 40 || b.x > viewHi() + 40) b.life = 0;
      for (const o of fight.fighters) {
        if (b.life <= 0 || o.team === b.team || !canBeHit(o, b.fall)) continue;
        if (Math.abs(o.x - b.x) < 26 && Math.abs(o.z - b.z) < 18 && b.y > o.y - 10 && b.y < o.y + 100) {
          if (b.el === 'fire') o.burnBy = b.owner;
          applyHit(b.owner, o, b.el ? { dmg: b.dmg, fall: b.fall, bdef: b.bdef, dvx: b.dvx, dvy: b.dvy, el: b.el } : { dmg: b.dmg, fall: b.fall, bdef: 30, dvx: 120 }, b.x - Math.sign(b.vx) * 30);
          if (o.hp <= 0) o.lastHitBy = b.owner;
          b.life = 0; spark(b.x, gy(b.z) - b.y, b.el ? b.color : ({ apple: '#d8262c', vinyl: '#2a2a33', football: '#ffffff', hammer: '#a0a5af', rzutek: '#f07820', kulka: '#f07820', teczka: '#6b4226', szarlotka: '#e0b060', pieczarka: '#f4efe0' }[b.item] || '#8a5a2c'), 12);
        }
      }
      for (const c of fight.balls) if (c !== b && c.team !== b.team && c.life > 0 && b.life > 0 && Math.abs(c.x - b.x) < 24 && Math.abs(c.z - b.z) < 18) {
        c.life = b.life = 0; spark(b.x, gy(b.z) - b.y, '#ffd21f', 16); sfx('heavy');
      }
    }
    fight.balls = fight.balls.filter(b => b.life > 0);
  }
  function spark(x, y, color, n) { for (let k = 0; k < n; k++) fight.fx.push({ x, y, vx: (Math.random() - .5) * 420, vy: -Math.random() * 300, t: 0, life: .25 + Math.random() * .25, color }); fight.bursts.push({ x, y, t: 0 }); }
  function popText(o, text, color) { fight.pops.push({ text, x: o.x, y: gy(o.z) - o.y - 118, t: 0, color }); }
  function banner(text, x, y, color) { fight.banners.push({ text, x, y, t: 0, color }); }

  /* ================================================================== computer fighters */
  const LEVEL = { easy: { react: .55, block: .12, aggr: 2.2, special: .5 }, normal: { react: .32, block: .3, aggr: 3.6, special: 1 }, hard: { react: .16, block: .5, aggr: 5.5, special: 1.6 } };
  function cpuThink(f) {
    const out = { held: {}, pressed: [] }, ai = f.ai, L = LEVEL[OPTS.level] || LEVEL.normal;
    if (!alive(f) || fight.phase !== 'fight') return out;
    if (ai.queue.length) { const step = ai.queue.shift(); out.pressed.push(...step.filter(a => a !== '_hold')); if (ai.hold) out.held[ai.hold] = true; if (!ai.queue.length) ai.hold = null; return out; }
    ai.wait -= DT; ai.think -= DT;
    const press = (...a) => out.pressed.push(...a);
    const move = (sx, sz) => { if (sx > 0) out.held.right = true; if (sx < 0) out.held.left = true; if (sz > 0) out.held.down = true; if (sz < 0) out.held.up = true; };
    if (f.st === 'fall' && f.t > .15 && f.t < .3 && Math.random() < L.block * .2) { press('jump'); return out; }
    const foes = enemies(f); if (!foes.length) return out;
    const tgt = foes.reduce((b, o) => (Math.hypot(o.x - f.x, (o.z - f.z) * 2) < Math.hypot(b.x - f.x, (b.z - f.z) * 2) ? o : b));
    const dx = tgt.x - f.x, dz = tgt.z - f.z, adx = Math.abs(dx), dirX = Math.sign(dx) || f.face;
    if (f.st === 'grab') {
      if (ai.think <= 0) { ai.think = .25; if (f.grabHits >= 2 || Math.random() < .3) { out.held[f.face > 0 ? 'right' : 'left'] = true; press('attack'); } else press('attack'); }
      return out;
    }
    const threat = foes.find(o => ['punch', 'super', 'runatk', 'w_atk1', 'w_atk2'].includes(o.st) && Math.abs(o.x - f.x) < 100 && Math.abs(o.z - f.z) < 20 && o.t < .06);
    if (threat && FREE.has(f.st) && ai.think <= 0) {
      ai.think = L.react;
      if (Math.random() < L.block) { f.face = Math.sign(threat.x - f.x) || f.face; ai.block = .32; }
      else if (Math.random() < .2) press('jump');
    }
    if (ai.block > 0) { ai.block -= DT; out.held.defend = true; return out; }
    const beamer = foes.find(o => o.st === 'power' && o.def.power.el === 'beam' && Math.abs(o.z - f.z) < 22 && (f.x - o.x) * o.face > 0);
    if (beamer && FREE.has(f.st) && Math.random() < .3 + L.block) { move(0, f.z > depth() / 2 ? -1 : 1); return out; }   // side-step the kamehameha
    const ball = fight.balls.find(b => b.team !== f.team && Math.abs(b.z - f.z) < 20 && Math.sign(f.x - b.x) === Math.sign(b.vx) && Math.abs(f.x - b.x) < 170);
    if (ball && FREE.has(f.st) && ai.think <= 0) { ai.think = L.react; if (Math.random() < .5) press('jump'); else move(0, f.z > depth() / 2 ? -1 : 1); return out; }
    if (ai.wait > 0 || !FREE.has(f.st)) return out;
    const wantDrink = f.hp < f.hpMax * .5;
    if (!f.hold && (adx > 110 || wantDrink)) {   // fetch a nearby item when nobody is close (milk when hurt)
      const it = fight.items.filter(i => i.state === 'ground' && (i.type !== 'lomza' || wantDrink))
        .sort((a, b) => Math.abs(a.x - f.x) + Math.abs(a.z - f.z) - Math.abs(b.x - f.x) - Math.abs(b.z - f.z))[0];
      if (it && Math.abs(it.x - f.x) < (wantDrink && it.type === 'lomza' ? 600 : 320) && Math.abs(it.x - f.x) < adx + 40) {
        const ix = it.x - f.x, iz = it.z - f.z;
        if (Math.abs(ix) < 20 && Math.abs(iz) < 10) { press('attack'); ai.wait = .3; return out; }
        move(Math.abs(ix) > 12 ? Math.sign(ix) : 0, Math.abs(iz) > 6 ? Math.sign(iz) : 0); return out;
      }
    }
    if (holdKind(f) === 'heavy' && adx < 380 && Math.abs(dz) < 14) { f.face = dirX; press('attack'); ai.wait = .5; return out; }
    if (holdKind(f) === 'light' && adx > 160 && adx < 420 && Math.abs(dz) < 12 && Math.random() < DT * .8) { f.face = dirX; out.held[dirX > 0 ? 'right' : 'left'] = true; press('attack'); ai.wait = .5; return out; }
    if (f.mp >= f.def.ball.mp && adx > 170 && adx < 560 && Math.abs(dz) < 14 && Math.random() < DT * 1.2 * L.special) {
      ai.queue.push(['defend'], [dx > 0 ? 'right' : 'left'], ['attack']); ai.wait = .6; return out;
    }
    if (f.def.power && f.mp >= POWER[f.def.power.el].mp && Math.abs(dz) < 14 && tgt.st !== 'frozen' && adx > (f.def.power.el === 'beam' ? 120 : 170) && adx < (f.def.power.el === 'beam' ? 700 : 560) && Math.random() < DT * .8 * L.special) {
      f.face = dirX; ai.queue.push(['defend'], ['down'], ['attack']); ai.wait = f.def.power.el === 'beam' ? 1.3 : .7; return out;
    }
    if (f.mp >= f.def.spin.mp && adx < 70 && Math.abs(dz) < 14 && Math.random() < DT * .7 * L.special) { ai.queue.push(['defend'], ['up'], ['attack']); ai.wait = .9; return out; }
    if (holdKind(f) === 'gun' && adx < 520 && Math.abs(dz) < 12) { f.face = dirX; press('attack'); ai.wait = .25 + Math.random() * .2; return out; }
    const range = holdKind(f) === 'light' ? Math.min(80, ATK.w_thrust.reach * (ITEM_DEF[f.hold.type].reachK || 1) * .8) : 50;
    if (Math.abs(dz) > 8) move(0, Math.sign(dz));
    if (adx > range) {
      move(dirX, Math.abs(dz) > 8 ? Math.sign(dz) : 0);
      if (adx > 300 && !f.running && Math.random() < DT * 1.4 && holdKind(f) !== 'heavy') ai.queue.push([dirX > 0 ? 'right' : 'left'], [], [dirX > 0 ? 'right' : 'left']);
      if (f.running && adx < 110 && Math.abs(dz) < 14) press(Math.random() < .25 ? 'jump' : 'attack');
    } else if (adx < 26) move(-dirX, 0);
    else if (Math.abs(dz) < 14) {
      if (f.face !== dirX) move(dirX, 0);
      if (tgt.st === 'dizzy' && Math.random() < .5) move(dirX, 0);   // walk in to grab
      else if (Math.random() < DT * L.aggr * 2) {
        if (Math.random() < .12) { press('jump'); ai.queue.push([], [], [], ['attack']); } else press('attack');
        ai.wait = .12 + Math.random() * .2;
      }
    }
    return out;
  }

  /* ================================================================== fight lifecycle */
  const teamsAlive = () => [...new Set(fight.fighters.filter(alive).map(f => f.team))];
  function startFight() {
    const active = SLOTS.map((s, i) => [s, i]).filter(([s]) => s.type !== 'off');
    const err = validate(); if (err) { setLobbyError(err); return false; }
    held.clear(); edges.length = 0; rebinding = null;
    const ids = Object.keys(STAGES), stageId = OPTS.stage === 'random' ? ids[Math.floor(Math.random() * ids.length)] : OPTS.stage;
    Z0 = Math.round(H * STAGES[stageId].top);
    fight = { cam: 0, ww: STAGES[stageId].world || W, phase: 'intro', t: 0, time: 0, overT: 0, endT: 0, paused: false, stage: stageId, fighters: [], balls: [], items: [], fx: [], bursts: [], pops: [], banners: [], shake: 0, winner: null, itemT: 6 };
    fight.fighters = active.map(([s, i]) => makeFighter(s, i, active.length));
    for (const f of fight.fighters) if (f.def.start) { const it = spawnItem(f.def.start, f.x, f.z, false); it.state = 'held'; it.owner = f; f.hold = it; }   // Sołtys' teczka, Michał's pistol
    if (OPTS.items) { spawnItem('widly', W * .5, depth() * .15, false); spawnItem('lomza', W * .32, depth() * .85, false); spawnItem('pieczarki', W * .7, depth() * .7, false); }
    showFightCanvas(true);
    loadAll().catch(() => {});
    return true;
  }
  function endFight() { fight = null; held.clear(); edges.length = 0; showFightCanvas(false); renderLobby(); }
  function finish() {
    const teams = teamsAlive();
    fight.phase = 'over'; fight.overT = 0;
    fight.winner = teams.length === 1 ? fight.fighters.filter(f => f.team === teams[0]) : [];
    for (const f of fight.winner) if (alive(f) && f.y <= 0) { if (f.hold) dropHold(f); if (f.grabbing) releaseGrab(f); setSt(f, 'win'); }
    const st = readLS(LS_STATS, {}); st.fights = (st.fights || 0) + 1; st.wins = st.wins || {};
    for (const f of fight.winner) st.wins[f.key] = (st.wins[f.key] || 0) + 1;
    writeLS(LS_STATS, st);
  }
  function tick() {
    if (!fight || fight.paused) return;
    fight.t += DT; fight.shake = Math.max(0, fight.shake - DT);
    fight.tuEdge = (fight.tickN = (fight.tickN || 0) + 1) % 2 === 0; if (fight.tuEdge) fight.tuN = (fight.tuN || 0) + 1;   // 60 Hz ticks -> 30 TU/s
    gatherInputs();
    if (fight.phase === 'intro') { if (fight.t > 1.6) { fight.phase = 'fight'; fight.t = 0; } }
    else {
      fight.time += DT;
      if (fight.phase === 'over') fight.overT += DT;
      for (const f of fight.fighters) { if (fight.phase === 'over') f.input = { held: {}, pressed: [] }; updateFighter(f, fight.time); }
      updateBalls(); updateItems(); updateCam();
      if (fight.phase === 'fight' && teamsAlive().length <= 1) {
        fight.endT += DT;
        if (fight.endT > .9 && fight.fighters.every(f => f.y <= 0 && f.st !== 'fall' && f.st !== 'lying')) finish();
      }
    }
    for (const p of fight.fx) { p.t += DT; p.x += p.vx * DT; p.y += p.vy * DT; p.vy += 900 * DT; }
    fight.fx = fight.fx.filter(p => p.t < p.life);
    for (const b of fight.bursts) b.t += DT; fight.bursts = fight.bursts.filter(b => b.t < .12);
    for (const p of fight.pops) { p.t += DT; p.y -= 40 * DT; } fight.pops = fight.pops.filter(p => p.t < .8);
    for (const b of fight.banners) b.t += DT; fight.banners = fight.banners.filter(b => b.t < 1.1);
  }

  /* ================================================================== rendering */
  let cvs = null, cx = null, raf = 0, last = 0, acc = 0;
  const hangs = f => f.hold && (ITEM_DEF[f.hold.type].hang || ITEM_DEF[f.hold.type].kind === 'gun');
  function frameName(f) {
    const k = holdKind(f), d = f.def, cyc = (arr, sp) => arr[Math.floor(f.frameT / sp) % arr.length];
    switch (f.st) {
      case 'stand': return hangs(f) ? 'w_case' : k === 'light' ? 'w_stand' : k === 'heavy' ? 'carry' : 'stand';
      case 'walk': return hangs(f) ? 'w_case' : k === 'light' ? cyc(['w_walk', 'w_stand'], .16) : k === 'heavy' ? 'carry' : cyc(['walk1', 'stand', 'walk2', 'stand'], .12);
      case 'run': return hangs(f) ? 'w_case' : k === 'light' ? 'w_walk' : cyc(['run1', 'run2'], .11);
      case 'shoot': return 'w_shoot';
      case 'skid': return 'dash';
      case 'punch': return f.t < ATK.punch.t0 ? 'stand' : (f.punchAlt ? 'punch1' : 'punch2');
      case 'super': return f.t < ATK.super.t0 ? 'stand' : d.superFrame;
      case 'runatk': return 'dash';
      case 'w_atk1': return f.t < .05 ? 'w_stand' : 'w_thrust';
      case 'w_atk2': return f.t < .06 ? 'w_stand' : 'w_swing';
      case 'w_jump': return 'w_jump';
      case 'w_throw': return f.released ? 'punch1' : 'w_throw';
      case 'heavy_throw': return f.released ? 'punch2' : 'heavy_throw';
      case 'jumpsquat': case 'land': return 'pickup';
      case 'jump': case 'dash': return k === 'light' ? 'w_jump' : 'jump';
      case 'jkick': case 'dashkick': return 'jkick';
      case 'defend': return 'defend';
      case 'hurt': case 'brokendef': return 'hurt';
      case 'dizzy': return 'dizzy';
      case 'held': return 'held';
      case 'grab': return 'grab';
      case 'grabpunch': return f.t < .05 ? 'grab' : 'punch2';
      case 'throw': return 'throw';
      case 'fall': return 'fall';
      case 'flip': case 'roll': return 'roll';
      case 'lying': case 'dead': return f.lieFront ? 'lying_front' : 'lying_back';
      case 'getup': return 'getup';
      case 'cast': return d.ball.gun ? 'w_shoot' : f.released ? 'punch1' : 'cast';
      case 'toss': return f.released ? 'punch2' : 'stand';
      case 'spin': return d.spin.frame || 'special2';
      case 'power': return d.power.el === 'beam' ? (f.t < POWER.beam.charge ? 'cast' : 'punch1') : (f.released ? 'punch1' : 'cast');
      case 'frozen': return 'hurt';
      case 'pick': return 'pickup';
      case 'drink': return 'drink';
      case 'win': return 'win';
      default: return 'stand';
    }
  }
  function drawSprite(atlasId, name, x, y, face, opts = {}) {
    const a = ART[atlasId]; if (!a || !a.img || !a.meta) return false;
    const fr = a.meta.frames[name]; if (!fr) return false;
    const s = (a.meta.scale || .5) * (opts.scale || 1), c = cx;
    c.save(); c.translate(x, y);
    if (opts.rot) c.rotate(opts.rot);
    c.scale(face < 0 ? -s : s, s);
    c.drawImage(a.img, fr.x, fr.y, fr.w, fr.h, -fr.ax, -fr.ay, fr.w, fr.h);
    if (opts.flash && a.flash && OPTS.effects) { c.globalAlpha = Math.min(1, opts.flash * 8) * .85; c.drawImage(a.flash, fr.x, fr.y, fr.w, fr.h, -fr.ax, -fr.ay, fr.w, fr.h); }
    c.restore();
    return true;
  }
  function drawFighter(f) {
    const c = cx, x = f.x, g = gy(f.z);
    c.fillStyle = 'rgba(10,30,10,.32)'; c.beginPath(); c.ellipse(x, g, 26 - Math.min(14, f.y / 12), 7 - Math.min(3, f.y / 40), 0, 0, 7); c.fill();
    let face = f.face, rot = 0, cy = g - f.y;
    if (f.st === 'spin' && f.def.spin.flip) face = Math.floor(f.t / f.def.spin.flip) % 2 ? -f.face : f.face;
    if (f.st === 'flip') { rot = f.face * f.t * 14; cy -= 40; }
    if (f.st === 'fall') rot = -f.face * Math.max(-.5, Math.min(.5, -f.vy / 900));
    const dead = f.st === 'dead';
    if (dead && f.deadT > 1.5) c.globalAlpha = Math.floor(f.deadT * 6) % 2 ? .35 : .7;
    if (f.inv > 0 && FREE.has(f.st) && Math.floor(f.inv * 20) % 2) c.globalAlpha = .5;
    const wob = f.st === 'dizzy' ? Math.sin(fight.t * 18) * 2 : f.st === 'held' ? Math.sin(fight.t * 30) : 0;
    if (f.st === 'flip') { c.save(); c.translate(x, cy); c.rotate(rot); c.translate(-x, -cy); }
    const ok = drawSprite(f.def.atlas, frameName(f), x + wob, f.st === 'flip' ? cy + 40 : cy, face, { rot: f.st === 'fall' ? rot : 0, flash: f.flash });
    if (f.st === 'flip') c.restore();
    const wpn = f.hold && ['light', 'gun'].includes(holdKind(f)) ? f.hold.type : f.st === 'cast' && f.def.ball.gun ? 'pistol' : f.st === 'spin' && f.def.spin.weapon ? f.def.spin.weapon : null;
    if (ok && wpn && f.st !== 'flip' && f.st !== 'fall') drawWeapon(f, wpn, x + wob, cy, face);
    if (ok && f.hold && holdKind(f) === 'heavy' && ['stand', 'walk', 'run', 'carry'].includes(f.st) || (ok && f.hold && f.st === 'heavy_throw' && !f.released)) {
      const a = ART[f.def.atlas], fr = a.meta.frames[frameName(f)], sc = a.meta.scale || .5;
      const top = cy - fr.ay * sc, it = f.hold.type, im = ART.items && ART.items.meta && ART.items.meta.frames[it];
      if (im) {
        drawSprite('items', it, x + (fr.w / 2 - fr.ax) * sc * f.face, top + im.h * .5 * .3, f.face);
      }
    }
    if (!ok) { c.fillStyle = f.color; c.fillRect(x - 14, cy - 95, 28, 95); }
    c.globalAlpha = 1;
    if (f.st === 'frozen') drawIce(f, x, cy);
    if (f.burn > 0 && !dead) drawFlames(f, x, cy);
    if (f.st === 'power' && f.def.power.el === 'beam') drawBeam(f, x, cy);
    if (!dead && fight.phase !== 'over') {
      const tag = f.cpu ? 'CPU' : `P${f.slot + 1}`;
      c.font = '11px PixelifySans'; c.textAlign = 'center'; c.fillStyle = '#10141f'; c.fillText(tag, x + 1, g - f.y - 109);
      c.fillStyle = f.color; c.fillText(tag, x, g - f.y - 110);
    }
  }
  function drawIce(f, x, cy) {   // translucent ice block around a frozen fighter
    const c = cx, left = f.frozenDur - f.t, blink = left < .4 && Math.floor(f.t * 16) % 2;
    c.save(); c.globalAlpha = blink ? .35 : .6;
    c.fillStyle = '#9fe3ff'; c.fillRect(x - 30, cy - 108, 60, 110);
    c.globalAlpha = blink ? .5 : .9; c.strokeStyle = '#e8faff'; c.lineWidth = 2; c.strokeRect(x - 30, cy - 108, 60, 110);
    c.beginPath(); c.moveTo(x - 22, cy - 98); c.lineTo(x - 8, cy - 70); c.moveTo(x + 18, cy - 92); c.lineTo(x + 8, cy - 60); c.moveTo(x - 18, cy - 30); c.lineTo(x - 4, cy - 12); c.stroke();
    c.restore();
  }
  function drawFlames(f, x, cy) {   // flickering flames while burning
    const c = cx; c.save();
    const lying = lyingSt(f.st) || f.st === 'fall', rows = lying ? [0] : [0, 1, 2];
    for (const r of rows) for (let k = 0; k < 4; k++) {
      const fx = x + (k - 1.5) * (lying ? 18 : 12) + Math.sin(fight.t * 20 + k + r) * 3, h = 34 + Math.sin(fight.t * 27 + k * 2 + r) * 12, fy = cy - 6 - r * 34;
      c.globalAlpha = .8; c.fillStyle = '#ff4a10';
      c.beginPath(); c.moveTo(fx - 11, fy); c.quadraticCurveTo(fx, fy - h * 1.3, fx + 11, fy); c.fill();
      c.fillStyle = '#ffd21f'; c.beginPath(); c.moveTo(fx - 5, fy); c.quadraticCurveTo(fx, fy - h * .7, fx + 5, fy); c.fill();
    }
    c.restore();
  }
  function drawBeam(f, x, cy) {   // kamehameha: charge orb, then a long beam
    const c = cx, P = POWER.beam, col = f.def.power.color, hx = x + f.face * 36, hy = cy - 70;
    c.save();
    if (f.t < P.charge) {
      const r = 6 + 16 * (f.t / P.charge) + Math.sin(fight.t * 40) * 2;
      c.globalAlpha = .55; c.fillStyle = col; c.beginPath(); c.arc(hx, hy, r + 6, 0, 7); c.fill();
      c.globalAlpha = 1; c.fillStyle = '#ffffff'; c.beginPath(); c.arc(hx, hy, r * .55, 0, 7); c.fill();
    } else if (f.beamLen > 0) {
      const fade = f.t > P.end - .12 ? Math.max(0, (P.end - f.t) / .12) : 1, w = (22 + Math.sin(fight.t * 50) * 3) * fade;
      const x1 = hx + f.face * f.beamLen, xa = Math.min(hx, x1), bw = Math.abs(x1 - hx);
      c.globalAlpha = .55; c.fillStyle = col; c.fillRect(xa, hy - w, bw, w * 2);
      c.beginPath(); c.arc(hx, hy, w * 1.25, 0, 7); c.fill();
      c.globalAlpha = .95; c.fillStyle = '#ffffff'; c.fillRect(xa, hy - w * .45, bw, w * .9);
      c.beginPath(); c.arc(hx, hy, w * .7, 0, 7); c.fill();
    }
    c.restore();
  }
  function drawWeapon(f, wpn, x, y, face) {   // weapon sprite at the grip of the current frame (see build_fight_sprites.take_grip)
    const a = ART[f.def.atlas], fr = a && a.meta && a.meta.frames[frameName(f)], g = fr && fr.grip;
    const ia = ART.items, im = ia && ia.meta && ia.meta.frames[wpn];
    if (!g || !im || !ia.img) return;
    const s = a.meta.scale || .5, is = ia.meta.scale || .5, gp = WGRIP[wpn] || [.3, .5];
    const c = cx; c.save();
    c.translate(x + face * (g.hx - fr.ax) * s, y + (g.hy - fr.ay) * s);
    c.scale(face < 0 ? -1 : 1, 1);
    c.rotate(Math.atan2(g.ty - g.hy, g.tx - g.hx) + (gp[2] || 0));
    c.drawImage(ia.img, im.x, im.y, im.w, im.h, -gp[0] * im.w * is, -gp[1] * im.h * is, im.w * is, im.h * is);
    c.restore();
  }
  function drawItem(it) {
    const x = it.x, g = gy(it.z);
    cx.fillStyle = 'rgba(10,30,10,.3)'; cx.beginPath(); cx.ellipse(x, g, it.type === 'widly' || ITEM_DEF[it.type].long ? 40 : 18, 5, 0, 0, 7); cx.fill();
    const flying = it.state === 'flying';
    const face = flying && it.vx < 0 ? -1 : 1;
    const rot = flying && !ITEM_DEF[it.type].long && !ITEM_DEF[it.type].rolls ? it.spin : 0;
    drawSprite('items', it.type, x, g - it.y + 2, face, { rot });
    if (it.state === 'ground' && Math.floor(fight.t * 2) % 2) { cx.fillStyle = 'rgba(255,255,255,.4)'; cx.fillRect(x - 2, g - 38, 4, 4); }
  }
  function drawBall(b) {
    const x = b.x, y = gy(b.z) - b.y;
    cx.fillStyle = 'rgba(10,30,10,.3)'; cx.beginPath(); cx.ellipse(x, gy(b.z), 12, 4, 0, 0, 7); cx.fill();
    if (b.el === 'fire') {
      const r = 13 + Math.sin(fight.t * 30) * 2, d = Math.sign(b.vx);
      cx.save(); cx.globalAlpha = .6; cx.fillStyle = '#ff5a1a'; cx.beginPath(); cx.moveTo(x + d * r, y); cx.quadraticCurveTo(x - d * r * 2.6, y - r * 1.4, x - d * r * 3.2, y); cx.quadraticCurveTo(x - d * r * 2.6, y + r * 1.2, x + d * r, y); cx.fill();
      cx.globalAlpha = 1; cx.fillStyle = b.color || '#ff7a1a'; cx.beginPath(); cx.arc(x, y, r, 0, 7); cx.fill();
      cx.fillStyle = '#ffe680'; cx.beginPath(); cx.arc(x + d * 2, y - 1, r * .55, 0, 7); cx.fill(); cx.restore();
      return;
    }
    if (b.el === 'ice') {
      const d = Math.sign(b.vx);
      cx.save(); cx.fillStyle = 'rgba(191,232,255,.45)'; cx.fillRect(x - d * 40, y - 5, d * 30, 10);
      cx.fillStyle = b.color || '#9fe3ff'; cx.strokeStyle = '#ffffff'; cx.lineWidth = 2;
      cx.beginPath(); cx.moveTo(x + d * 18, y); cx.lineTo(x, y - 10); cx.lineTo(x - d * 14, y); cx.lineTo(x, y + 10); cx.closePath(); cx.fill(); cx.stroke(); cx.restore();
      return;
    }
    cx.fillStyle = 'rgba(255,255,255,.35)'; for (let k = 1; k < 4; k++) cx.fillRect(x - Math.sign(b.vx) * k * 13, y - 3, 7, 3);
    if (!drawSprite('items', b.item, x, y + (b.nospin ? 5 : 12), 1, { rot: b.nospin ? 0 : b.spin })) { cx.fillStyle = '#d8262c'; cx.beginPath(); cx.arc(x, y, 10, 0, 7); cx.fill(); }
  }
  function bar(x, y, w, h, v, max, col, dark) {
    const c = cx; c.fillStyle = '#0a1120'; c.fillRect(x - 1, y - 1, w + 2, h + 2);
    if (dark !== undefined) { c.fillStyle = '#5a1418'; c.fillRect(x, y, w * Math.max(0, dark) / max, h); }
    c.fillStyle = col; c.fillRect(x, y, w * Math.max(0, v) / max, h);
  }
  function drawPortrait(f, x, y, s) {
    const a = ART[f.def.atlas]; if (!a || !a.img) return;
    const fr = a.meta.frames.stand;
    cx.save(); cx.beginPath(); cx.rect(x, y, s, s); cx.clip();
    cx.drawImage(a.img, fr.x + fr.w * .12, fr.y, fr.w * .76, fr.w * .76, x, y, s, s);
    cx.restore();
  }
  function drawHud() {
    const c = cx, n = fight.fighters.length, pw = Math.min(232, (W - 20) / n - 6);
    fight.fighters.forEach((f, i) => {
      const x = 10 + i * (pw + 6), y = 6;
      c.fillStyle = 'rgba(8,12,40,.8)'; c.fillRect(x, y, pw, 50);
      c.fillStyle = f.color; c.fillRect(x, y, pw, 2);
      drawPortrait(f, x + 3, y + 5, 42);
      if (f.ko) { c.fillStyle = 'rgba(0,0,0,.55)'; c.fillRect(x + 3, y + 5, 42, 42); }
      c.font = '11px PixelifySans'; c.textAlign = 'left'; c.fillStyle = f.ko ? '#777' : '#f5f0e0';
      c.fillText(f.def.name, x + 50, y + 15);
      c.textAlign = 'right'; c.fillStyle = f.color; c.fillText(f.cpu ? 'CPU' : `P${f.slot + 1}`, x + pw - 5, y + 15);
      bar(x + 50, y + 22, pw - 56, 9, f.hp, f.hpMax, f.hp < f.hpMax * .3 ? '#ff4b3e' : '#e8262c', f.hpDark);
      bar(x + 50, y + 36, pw - 56, 6, f.mp, f.mpMax, '#3f8fe8');
      const hn = f.hold ? ITEM_DEF[f.hold.type].name + (f.hold.ammo ? ` ×${f.hold.ammo}` : '') : f.ammo ? `${PL ? 'PIECZARKI' : 'MUSHROOMS'} ×${f.ammo}` : '';
      if (hn) { c.textAlign = 'left'; c.font = '9px PixelifySans'; c.fillStyle = '#c8cee0'; c.fillText(hn, x + 50, y + 50); }
    });
    c.textAlign = 'center';
    if (fight.phase === 'intro') {
      const k = Math.min(3, Math.floor(fight.t / .5)), txt = k < 3 ? String(3 - k) : (PL ? 'WALKA!' : 'FIGHT!');
      c.font = '64px PixelifySans'; c.fillStyle = '#10141f'; c.fillText(txt, W / 2 + 3, H * .42 + 3);
      c.fillStyle = '#ffd21f'; c.fillText(txt, W / 2, H * .42);
      c.font = '16px PixelifySans'; c.fillStyle = '#fff'; c.fillText(STAGES[fight.stage].name, W / 2, H * .42 + 34);
    } else if (fight.phase === 'fight' && fight.t < .6) {
      c.font = '64px PixelifySans'; c.fillStyle = `rgba(124,255,107,${1 - fight.t / .6})`; c.fillText(PL ? 'WALKA!' : 'FIGHT!', W / 2, H * .42);
    } else if (fight.phase === 'over' && fight.overT > .8) drawResults();
    if (fight.paused) { c.fillStyle = 'rgba(8,12,40,.6)'; c.fillRect(0, 0, W, H); c.font = '40px PixelifySans'; c.fillStyle = '#ffd21f'; c.fillText(PL ? 'PAUZA' : 'PAUSED', W / 2, H / 2); c.font = '13px PixelifySans'; c.fillStyle = '#fff'; c.fillText('F1', W / 2, H / 2 + 28); }
    if (fight.phase !== 'over') { c.font = '10px PixelifySans'; c.fillStyle = 'rgba(255,255,255,.8)'; c.fillText(PL ? 'F1 — PAUZA   ESC — MENU' : 'F1 — PAUSE   ESC — MENU', W / 2, H - 8); }
    c.textAlign = 'left';
  }
  function drawResults() {   // LF2-style result table
    const c = cx, rows = fight.fighters, bw = 740, rh = 30, bh = 100 + rows.length * rh, bx = (W - bw) / 2, by = 90;
    c.fillStyle = 'rgba(8,12,40,.9)'; c.fillRect(bx, by, bw, bh); c.strokeStyle = '#9b3fe0'; c.lineWidth = 2; c.strokeRect(bx, by, bw, bh);
    c.font = '20px PixelifySans'; c.textAlign = 'center'; c.fillStyle = fight.winner.length ? '#7cff6b' : '#ffd21f';
    c.fillText(fight.winner.length ? (PL ? 'WYGRYWA ' : 'WINNER: ') + fight.winner.map(f => f.cpu ? `${f.def.name} (CPU)` : `${f.def.name} P${f.slot + 1}`).join(' + ') : (PL ? 'REMIS' : 'DRAW'), W / 2, by + 30);
    const cols = PL ? ['', 'KO', 'ATAK', 'STRACONE HP', 'MANA', 'PODNIESIONE', 'WYNIK'] : ['', 'KILL', 'ATTACK', 'HP LOST', 'MP USAGE', 'PICKING', 'STATUS'];
    const xs = [bx + 18, bx + 240, bx + 310, bx + 410, bx + 505, bx + 600, bx + 690];
    c.font = '10px PixelifySans'; c.fillStyle = '#9aa0c0';
    cols.forEach((h, i) => { c.textAlign = i ? 'center' : 'left'; c.fillText(h, xs[i], by + 62); });
    rows.forEach((f, r) => {
      const y = by + 90 + r * rh, win = fight.winner.includes(f);
      drawPortrait(f, xs[0], y - 19, 24);
      c.textAlign = 'left'; c.font = '13px PixelifySans'; c.fillStyle = f.color; c.fillText(`${f.def.name} ${f.cpu ? 'CPU' : 'P' + (f.slot + 1)}`, xs[0] + 32, y);
      c.fillStyle = '#f5f0e0'; c.textAlign = 'center';
      [f.stats.kills, f.stats.dealt, f.stats.hpLost, Math.round(f.stats.mpUsed), f.stats.picks].forEach((v, i) => c.fillText(String(v), xs[i + 1], y));
      c.fillStyle = win ? '#7cff6b' : fight.winner.length ? '#ff6b5e' : '#ffd21f'; c.fillText(win ? (PL ? 'WYGRANA' : 'WIN') : fight.winner.length ? (PL ? 'PORAŻKA' : 'LOSE') : (PL ? 'REMIS' : 'DRAW'), xs[6], y);
    });
    if (fight.overT > 1.2) { c.font = '12px PixelifySans'; c.fillStyle = Math.floor(fight.overT * 3) % 2 ? '#ffd21f' : '#fff3b0'; c.textAlign = 'center'; c.fillText(PL ? 'ENTER / R — JESZCZE RAZ     ESC — MENU' : 'ENTER / R — AGAIN     ESC — MENU', W / 2, by + bh - 12); }
  }
  function drawRoadBar() {   // thin progress bar: where the camera is on the way to the hall
    const c = cx, x0 = W / 2 - 150, y0 = H - 24, p = fight.cam / (fight.ww - W);
    c.fillStyle = 'rgba(8,12,24,.65)'; c.fillRect(x0 - 2, y0 - 2, 304, 8);
    c.fillStyle = '#ffd21f'; c.fillRect(x0, y0, 300 * p, 4);
    c.fillStyle = '#fff'; c.fillRect(x0 + 300 * p - 1, y0 - 3, 3, 10);
    c.font = '8px PixelifySans'; c.textAlign = 'left'; c.fillStyle = 'rgba(255,255,255,.85)'; c.fillText(PL ? 'ZACHÓD' : 'WEST', x0 - 46, y0 + 5);
    c.textAlign = 'right'; c.fillText(PL ? 'WSCHÓD' : 'EAST', x0 + 350, y0 + 5); c.textAlign = 'center';
  }
  function drawStage() {
    const s = STAGE_IMG[fight.stage] && STAGE_IMG[fight.stage].img;
    if (s && scrolls()) { const k = s.height / H; cx.imageSmoothingEnabled = true; cx.drawImage(s, Math.round(fight.cam * k), 0, W * k, s.height, 0, 0, W, H); return; }
    if (s) { cx.imageSmoothingEnabled = true; cx.drawImage(s, 0, 0, W, H); return; }
    const g = cx.createLinearGradient(0, 0, 0, Z0); g.addColorStop(0, '#6fb6e8'); g.addColorStop(1, '#cfe9f2');
    cx.fillStyle = g; cx.fillRect(0, 0, W, Z0); cx.fillStyle = '#6b9d45'; cx.fillRect(0, Z0, W, H - Z0);
  }
  function render() {
    if (!fight || !cx) return;
    const c = cx;
    c.setTransform(1, 0, 0, 1, 0, 0); c.fillStyle = '#05070d'; c.fillRect(0, 0, cvs.width, cvs.height);
    const k = Math.min(cvs.width / W, cvs.height / H), ox = (cvs.width - W * k) / 2, oy = (cvs.height - H * k) / 2;
    const sh = OPTS.effects && fight.shake > 0 && !fight.paused ? (Math.random() - .5) * 8 : 0;
    c.setTransform(k, 0, 0, k, ox + sh * k, oy + sh * k * .5);
    c.save(); c.beginPath(); c.rect(0, 0, W, H); c.clip();
    drawStage();
    c.imageSmoothingEnabled = true; c.imageSmoothingQuality = 'high';
    c.save(); c.translate(-viewLo(), 0);
    const list = [
      ...fight.fighters.map(f => [f.z + (f.st === 'held' ? .3 : 0) - (lyingSt(f.st) ? .5 : 0), () => drawFighter(f)]),
      ...fight.items.filter(i => i.state !== 'held' && i.state !== 'reserved').map(i => [i.z - .2, () => drawItem(i)]),
      ...fight.balls.map(b => [b.z + .5, () => drawBall(b)]),
    ];
    list.sort((a, b) => a[0] - b[0]).forEach(it => it[1]());
    for (const b of fight.bursts) drawSprite('items', 'spark', b.x, b.y + 18, 1, { scale: 1 + b.t * 6 });
    for (const p of fight.fx) { c.fillStyle = p.color; c.globalAlpha = Math.max(0, 1 - p.t / p.life); c.fillRect(p.x - 2, p.y - 2, 4, 4); }
    c.globalAlpha = 1; c.textAlign = 'center';
    for (const p of fight.pops) { c.font = '15px PixelifySans'; c.fillStyle = '#10141f'; c.fillText(p.text, p.x + 1, p.y + 1); c.fillStyle = p.color; c.fillText(p.text, p.x, p.y); }
    for (const b of fight.banners) { const by = b.y - b.t * 20; c.font = '18px PixelifySans'; c.globalAlpha = Math.max(0, 1 - b.t / 1.1); c.fillStyle = '#10141f'; c.fillText(b.text, b.x + 2, by + 2); c.fillStyle = b.color; c.fillText(b.text, b.x, by); }
    c.globalAlpha = 1;
    c.restore();
    drawHud();
    if (scrolls()) drawRoadBar();
    c.restore();
  }
  function loop(ts) {
    raf = 0; if (!fight) return;
    const dt = Math.min(.1, (ts - (last || ts)) / 1000); last = ts; acc += dt;
    while (acc >= DT) { tick(); acc -= DT; if (!fight) return; }
    render();
    raf = requestAnimationFrame(loop);
  }
  function showFightCanvas(on) {
    if (!ui) return;
    ui.lobby.hidden = on; cvs.hidden = !on; ui.lobby.style.display = on ? 'none' : 'flex'; cvs.style.display = on ? 'block' : 'none';   // page CSS `canvas{display:block}` and the lobby's inline flex beat the hidden attribute
    if (on) { resize(); last = 0; acc = 0; if (!raf) raf = requestAnimationFrame(loop); cvs.focus(); }
    else if (raf) { cancelAnimationFrame(raf); raf = 0; }
  }
  function resize() { if (!cvs) return; const d = Math.min(2, window.devicePixelRatio || 1); cvs.width = Math.round(innerWidth * d); cvs.height = Math.round(innerHeight * d); }
  window.addEventListener('resize', resize);

  /* ================================================================== lobby */
  const T = PL ? {
    title: 'BIJATYKA', sub: 'Jak w Little Fighter 2: kilka osób przy jednej klawiaturze lub padach + komputer. Ostatnia drużyna na nogach wygrywa.',
    type: { human: 'CZŁOWIEK', cpu: 'KOMPUTER', off: '—' }, team: { '': 'BEZ DRUŻYNY', A: 'DRUŻYNA A', B: 'DRUŻYNA B' },
    start: 'WALKA!', close: 'WYJDŹ', controls: 'STEROWANIE', reset: 'DOMYŚLNE KLAWISZE', press: 'naciśnij klawisz…',
    stage: 'PLANSZA', random: 'LOSOWA', itemsOpt: 'PRZEDMIOTY', level: 'KOMPUTER', levels: { easy: 'ŁATWY', normal: 'NORMALNY', hard: 'TRUDNY' }, sound: 'DŹWIĘK', effects: 'EFEKTY (TRZĘSIENIE, BŁYSK)',
    moves: 'Bieg: 2× w bok · w biegu ATAK / SKOK / OBRONA = atak z rozpędu / długi skok / przewrót · Kopniak: SKOK + ATAK · Oszołomionego chwyć wchodząc w niego, rzut: kierunek + ATAK · Przedmiot: ATAK nad nim, widły rzucasz: do przodu + ATAK · W locie SKOK = przewrót · Specjalne: OBRONA, kierunek, ATAK oraz OBRONA, góra, ATAK · Moc (ogień / lód / kamehameha): OBRONA, dół, ATAK',
    pads: 'Pad: krzyżak/gałka, X/□ atak, A/✕ skok, B/○ lub RB obrona',
    errFew: 'Potrzeba co najmniej 2 zawodników.', errSame: 'Dwóch graczy ma to samo sterowanie: ', errTeam: 'Wszyscy są w jednej drużynie.', errHuman: 'Dodaj co najmniej jednego człowieka.',
  } : {
    title: 'BRAWL', sub: 'Little Fighter 2 style: several people on one keyboard or gamepads plus computer fighters. Last team standing wins.',
    type: { human: 'HUMAN', cpu: 'COMPUTER', off: '—' }, team: { '': 'NO TEAM', A: 'TEAM A', B: 'TEAM B' },
    start: 'FIGHT!', close: 'LEAVE', controls: 'CONTROLS', reset: 'DEFAULT KEYS', press: 'press a key…',
    stage: 'STAGE', random: 'RANDOM', itemsOpt: 'ITEMS', level: 'COMPUTER', levels: { easy: 'EASY', normal: 'NORMAL', hard: 'HARD' }, sound: 'SOUND', effects: 'EFFECTS (SHAKE, FLASH)',
    moves: 'Run: double-tap sideways · Run + ATTACK / JUMP / DEFEND = dash attack / dash jump / roll · Jump kick: JUMP + ATTACK · Walk into a dizzy enemy to grab, direction + ATTACK throws · Items: ATTACK on them, forward + ATTACK throws the pitchfork · JUMP while falling = flip · Specials: DEFEND, direction, ATTACK and DEFEND, up, ATTACK · Power (fire / ice / kamehameha): DEFEND, down, ATTACK',
    pads: 'Gamepad: d-pad/stick, X/□ attack, A/✕ jump, B/○ or RB defend',
    errFew: 'At least 2 fighters are needed.', errSame: 'Two players share the same controls: ', errTeam: 'Everyone is on one team.', errHuman: 'Add at least one human player.',
  };
  function validate() {
    const act = SLOTS.filter(s => s.type !== 'off');
    if (act.length < 2) return T.errFew;
    if (!act.some(s => s.type === 'human')) return T.errHuman;
    const used = {};
    for (const s of act) if (s.type === 'human') { if (used[s.ctrl]) return T.errSame + schemeLabel(s.ctrl); used[s.ctrl] = 1; }
    if (new Set(act.map((s, i) => s.team || `solo${i}`)).size < 2) return T.errTeam;
    return null;
  }
  function setLobbyError(msg) { const e = ui && ui.lobby.querySelector('#brawl-error'); if (e) e.textContent = msg || ''; }
  const css = {
    btn: 'min-height:40px;padding:6px 14px;border:2px solid #ffd21f;border-radius:6px;background:#263a61;color:#fff;font:bold 14px monospace;cursor:pointer',
    sel: 'min-height:34px;padding:4px;border:1px solid #9ba9c4;border-radius:4px;background:#0f1a33;color:#f8f3df;font:13px monospace;min-width:0',
    key: 'min-width:64px;min-height:30px;padding:2px 6px;border:1px solid #9ba9c4;border-radius:4px;background:#0f1a33;color:#ffd21f;font:bold 12px monospace;cursor:pointer',
  };
  const esc = s => String(s).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));
  const opt = (v, label, cur) => `<option value="${esc(v)}"${v === cur ? ' selected' : ''}>${esc(label)}</option>`;
  function paintPortraits() {
    if (!ui) return;
    ui.lobby.querySelectorAll('canvas[data-portrait]').forEach(cv => {
      const f = FIGHTERS[cv.dataset.portrait], a = ART[f.atlas], g = cv.getContext('2d'); g.clearRect(0, 0, cv.width, cv.height);
      if (!a || !a.img) return;
      const fr = a.meta.frames.stand, s = cv.height / fr.h;
      g.imageSmoothingQuality = 'high'; g.drawImage(a.img, fr.x, fr.y, fr.w, fr.h, (cv.width - fr.w * s) / 2, 0, fr.w * s, fr.h * s);
    });
  }
  function renderLobby() {
    if (!ui) return;
    const slots = SLOTS.map((s, i) => `
      <div class="brawl-slot" data-slot="${i}" style="display:grid;grid-template-columns:44px repeat(4,minmax(0,1fr));gap:6px;align-items:center;padding:6px;border-left:4px solid ${SLOT_COLORS[i]};background:#1c2b4d;border-radius:4px${s.type === 'off' ? ';opacity:.6' : ''}">
        <div style="position:relative;width:44px;height:56px"><canvas data-portrait="${s.fighter}" width="88" height="112" style="width:44px;height:56px"></canvas><strong style="position:absolute;left:0;top:0;color:${SLOT_COLORS[i]};text-shadow:0 1px 2px #000">P${i + 1}</strong></div>
        <select data-k="type" aria-label="P${i + 1}" style="${css.sel}">${['human', 'cpu', 'off'].map(v => opt(v, T.type[v], s.type)).join('')}</select>
        <select data-k="fighter" aria-label="fighter ${i + 1}" style="${css.sel}"${s.type === 'off' ? ' disabled' : ''}>${Object.keys(FIGHTERS).map(v => opt(v, FIGHTERS[v].name, s.fighter)).join('')}</select>
        <select data-k="ctrl" aria-label="controls ${i + 1}" style="${css.sel}"${s.type !== 'human' ? ' disabled' : ''}>${SCHEMES.map(v => opt(v, schemeLabel(v), s.ctrl)).join('')}</select>
        <select data-k="team" aria-label="team ${i + 1}" style="${css.sel}"${s.type === 'off' ? ' disabled' : ''}>${['', 'A', 'B'].map(v => opt(v, T.team[v], s.team)).join('')}</select>
      </div>`).join('');
    const rows = ACTIONS.map(a => `<tr><th style="text-align:left;padding:2px 8px;color:#c8cee0">${ACTION_LABEL[a]}</th>${Object.keys(KEYS).map(s => {
      const on = rebinding && rebinding.scheme === s && rebinding.action === a;
      return `<td style="padding:2px"><button type="button" data-rebind="${s}:${a}" style="${css.key}${on ? ';background:#ffd21f;color:#172442' : ''}">${on ? T.press : esc(keyName(KEYS[s][a]))}</button></td>`;
    }).join('')}</tr>`).join('');
    const lab = 'display:flex;flex-direction:column;gap:3px;font-size:11px;color:#9aa0c0';
    const chk = 'display:flex;flex-direction:row;align-items:center;gap:6px;font-size:13px;color:#f8f3df';
    ui.lobby.innerHTML = `<section style="box-sizing:border-box;width:min(96vw,840px);max-height:94vh;overflow:auto;padding:clamp(12px,3vw,24px);border:3px solid #9b3fe0;border-radius:10px;background:#172442;box-shadow:0 12px 45px #0009">
      <h2 style="margin:0 0 6px;font-size:clamp(20px,5vw,32px);color:#e8c8ff;text-align:center;letter-spacing:2px">${T.title}</h2>
      <p style="margin:0 0 14px;text-align:center;line-height:1.4;color:#c8cee0">${T.sub}</p>
      <div style="display:grid;gap:6px">${slots}</div>
      <div style="display:flex;flex-wrap:wrap;gap:12px;justify-content:center;align-items:flex-end;margin-top:10px">
        <label style="${lab}">${T.stage}<select id="brawl-stage" style="${css.sel}">${Object.keys(STAGES).map(k => opt(k, STAGES[k].name, OPTS.stage)).join('')}${opt('random', T.random, OPTS.stage)}</select></label>
        <label style="${lab}">${T.level}<select id="brawl-level" style="${css.sel}">${['easy', 'normal', 'hard'].map(k => opt(k, T.levels[k], OPTS.level)).join('')}</select></label>
        <label style="${chk}"><input id="brawl-items" type="checkbox"${OPTS.items ? ' checked' : ''}> ${T.itemsOpt}</label>
        <label style="${chk}"><input id="brawl-sound" type="checkbox"${OPTS.sound ? ' checked' : ''}> ${T.sound}</label>
        <label style="${chk}"><input id="brawl-effects" type="checkbox"${OPTS.effects ? ' checked' : ''}> ${T.effects}</label>
      </div>
      <p id="brawl-error" role="alert" style="min-height:1.3em;margin:10px 0;color:#ff6b5e;text-align:center"></p>
      <div style="display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-bottom:14px">
        <button id="brawl-start" type="button" style="${css.btn};border-color:#7cff6b;font-size:17px">${T.start}</button>
        <button id="brawl-close" type="button" style="${css.btn}">${T.close}</button>
      </div>
      <details id="brawl-controls"${ui.controlsOpen ? ' open' : ''} style="border-top:1px solid #34476e;padding-top:10px">
        <summary style="cursor:pointer;color:#ffd21f;font-weight:bold">${T.controls}</summary>
        <div style="overflow-x:auto"><table style="margin:10px auto;border-collapse:collapse">
          <tr><th></th>${Object.keys(KEYS).map(s => `<th style="padding:2px 6px;color:#e8c8ff;font-size:12px">${schemeLabel(s)}</th>`).join('')}</tr>${rows}</table></div>
        <p style="margin:4px 0;text-align:center;font-size:12px;color:#9aa0c0">${T.pads}</p>
        <div style="text-align:center;margin-top:8px"><button id="brawl-reset-keys" type="button" style="${css.btn};min-height:32px;font-size:12px">${T.reset}</button></div>
      </details>
      <p style="margin:12px 0 0;text-align:center;font-size:12px;line-height:1.5;color:#9aa0c0">${T.moves}</p>
    </section>`;
    const L = ui.lobby;
    L.querySelectorAll('.brawl-slot select').forEach(sel => sel.addEventListener('change', () => {
      const i = +sel.closest('.brawl-slot').dataset.slot; SLOTS[i][sel.dataset.k] = sel.value; writeLS(LS_SLOTS, SLOTS); renderLobby();
    }));
    L.querySelectorAll('[data-rebind]').forEach(b => b.addEventListener('click', () => { const [scheme, action] = b.dataset.rebind.split(':'); rebinding = { scheme, action }; renderLobby(); }));
    const saveOpts = () => writeLS(LS_OPTS, OPTS);
    L.querySelector('#brawl-stage').addEventListener('change', e => { OPTS.stage = e.target.value; saveOpts(); });
    L.querySelector('#brawl-level').addEventListener('change', e => { OPTS.level = e.target.value; saveOpts(); });
    L.querySelector('#brawl-items').addEventListener('change', e => { OPTS.items = e.target.checked; saveOpts(); });
    L.querySelector('#brawl-sound').addEventListener('change', e => { OPTS.sound = e.target.checked; saveOpts(); });
    L.querySelector('#brawl-effects').addEventListener('change', e => { OPTS.effects = e.target.checked; saveOpts(); });
    L.querySelector('#brawl-controls').addEventListener('toggle', e => { if (ui) ui.controlsOpen = e.target.open; });
    L.querySelector('#brawl-start').addEventListener('click', () => startFight());
    L.querySelector('#brawl-close').addEventListener('click', closeBrawl);
    L.querySelector('#brawl-reset-keys').addEventListener('click', () => { KEYS = clone(DEFAULT_KEYS); writeLS(LS_KEYS, KEYS); rebinding = null; renderLobby(); });
    setLobbyError(validate() && SLOTS.some(s => s.type !== 'off') ? validate() : '');
    paintPortraits();
  }
  function openBrawl() {
    if (ui) return;
    const root = document.createElement('div');
    root.id = 'brawl-overlay'; root.setAttribute('role', 'dialog'); root.setAttribute('aria-modal', 'true'); root.setAttribute('aria-label', T.title);
    root.style.cssText = 'position:fixed;inset:0;z-index:10000;background:rgba(8,12,24,.92);font:15px monospace;color:#f8f3df';
    const lobby = document.createElement('div'); lobby.id = 'brawl-lobby';
    lobby.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:8px';
    cvs = document.createElement('canvas'); cvs.id = 'brawl-canvas'; cvs.tabIndex = 0; cvs.hidden = true;
    cvs.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;background:#05070d;outline:none;display:none';
    cx = cvs.getContext('2d');
    root.append(lobby, cvs); document.body.appendChild(root);
    ui = { root, lobby, controlsOpen: false };
    held.clear(); edges.length = 0; if (A.keys && A.keys.clear) A.keys.clear();
    renderLobby();
    loadAll().then(paintPortraits).catch(() => {});
    const st = lobby.querySelector('#brawl-start'); if (st) st.focus();
  }
  function closeBrawl() {
    fight = null; rebinding = null; if (raf) cancelAnimationFrame(raf); raf = 0;
    if (ui) ui.root.remove(); ui = null; cvs = null; cx = null; held.clear(); edges.length = 0;
  }

  /* ================================================================== village hooks */
  A.HOOKS.near.push(() => (!venue || ui || A.HOOKS.busy.some(f => f()) ? [] : [{ x: venue.x, y: venue.y, r: 30, _brawl: true, onInteract: openBrawl }]));
  A.HOOKS.busy.push(() => !!ui);
  A.HOOKS.world.push((push, S, inView) => {
    if (!venue || !inView(venue.x, venue.y)) return;
    push(venue.y, () => { const [sx, sy] = S(venue.x, venue.y); drawFlag(sx, sy, A.zoom); });
  });
  A.HOOKS.minimap.push(dot => { if (venue) dot(venue.x, venue.y, '#9b3fe0'); });

  A.brawl = {
    FIGHTERS, ATK, STAGES, POWER, LF2, PXTU, applyHit, meleeCheck, open: openBrawl, close: closeBrawl, start: startFight, end: endFight, validate,
    get venue() { return venue ? { ...venue } : null; }, get fight() { return fight; }, get ui() { return ui; },
    get keys() { return clone(KEYS); }, get slots() { return clone(SLOTS); }, get opts() { return { ...OPTS }; },
    setSlots(s) { SLOTS = s.map(x => ({ ...x })); writeLS(LS_SLOTS, SLOTS); renderLobby(); },
    setOpts(o) { Object.assign(OPTS, o); writeLS(LS_OPTS, OPTS); renderLobby(); },
    setKey(scheme, action, code) { setKey(scheme, action, code); renderLobby(); },
    spawnItem: (type, x, z) => spawnItem(type, x, z, false),
    step(n = 1) { const p = fight && fight.paused; if (fight) fight.paused = false; for (let i = 0; i < n && fight; i++) tick(); if (fight) fight.paused = p; render(); },
    render: () => render(),
    frameName, loaded: loadAll,
  };
});

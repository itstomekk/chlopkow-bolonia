/* Companion dogs. The dog picked at the start of the game follows the hero (FRODO object in game.js).
   The real start-of-game dog choice is still to be designed (plans/2026-10-17-kierunek-gry-legends.md section 3);
   until then: ?dog=wajper (or ?dog=frodo) in the URL, remembered in localStorage, or window.chlopkowSetDog('wajper').
   walk: atlas with rows down/up/right/left and `cols` walk frames. poses: strip of 32 px poses facing right + json.
   anims: idle action -> pose names (looped at `rates[action]` fps). routine: idle actions picked at random. */
(function () {
  'use strict';
  const KEY = 'chlopkow_dog';
  const DOGS = {
    frodo: {
      id: 'frodo', name: 'FRODO', walk: 'img/frodo.png', cols: 2, poses: 'img/frodo_poses.png',
      anims: { sit: ['yawn1'], pant: ['pant1', 'pant2', 'pant3', 'pant4'], scratch: ['scratch1', 'scratch2'], sniff: ['sniff1', 'sniff2'],
        lie: ['lie'], lick: ['lick1', 'lick2', 'lick1', 'lick2', 'lickpaw1', 'lickpaw2'],
        yawn: ['yawn1', 'yawn2', 'yawn3', 'yawn3', 'yawn3', 'yawn4', 'yawn1', 'yawn1'], tilt: ['tilt1', 'tilt2', 'tilt2', 'tilt1', 'tilt4', 'tilt4'],
        shake: ['shake1', 'shake2', 'shake3', 'shake4'], wag: ['wag1', 'wag2'], dig: ['dig1', 'dig2', 'dig3', 'dig4'],
        sleep: ['sleep1', 'sleep1', 'sleep2', 'sleep2'], belly: ['belly1', 'belly2'], stretch: ['stretch1', 'stretch1', 'stretch2', 'stretch2'],
        bark: ['bark1', 'bark2'], howl: ['howl1', 'howl2', 'howl2'], playbow: ['playbow'] },
      rates: { pant: 6, lick: 5, scratch: 9, sniff: 4, yawn: 5, tilt: 3, shake: 12, wag: 7, dig: 9, sleep: 1.5, belly: 4, stretch: 2, bark: 5, howl: 2 },
      routine: ['sit', 'pant', 'pant', 'lick', 'scratch', 'sniff', 'lie', 'yawn', 'tilt', 'shake', 'wag', 'dig', 'sleep', 'belly', 'stretch'],
      times: { yawn: 2.2, tilt: 2.4, shake: 1.4, wag: 2.5, dig: 2.6, sleep: 6, belly: 3, stretch: 2 },
    },
    wajper: {
      id: 'wajper', name: 'WAJPER', walk: 'img/wajper_walk4.png', cols: 4, poses: 'img/wajper_poses.png',
      anims: { sit: ['tilt1'], pant: ['pant1', 'pant2', 'pant3', 'pant4'], scratch: ['scratch1', 'scratch2'], sniff: ['sniff1', 'sniff2'],
        lie: ['lie'], lick: ['lick1', 'lick2', 'lick1', 'lick2', 'lickpaw1', 'lickpaw2'],
        yawn: ['yawn1', 'yawn2', 'yawn3', 'yawn3', 'yawn3', 'yawn4', 'yawn1', 'yawn1'], tilt: ['tilt1', 'tilt2', 'tilt2', 'tilt1', 'tilt4', 'tilt4'],
        shake: ['shake1', 'shake2', 'shake3', 'shake4'], wag: ['wag1', 'wag2'], dig: ['dig1', 'dig2', 'dig3', 'dig4'],
        sleep: ['sleep1', 'sleep1', 'sleep2', 'sleep2'], belly: ['belly1', 'belly2'], stretch: ['stretch1', 'stretch1', 'stretch2', 'stretch2'],
        bark: ['bark1', 'bark2'], howl: ['howl1', 'howl2', 'howl2'], playbow: ['playbow'] },
      rates: { pant: 6, lick: 5, scratch: 9, sniff: 4, yawn: 5, tilt: 3, shake: 12, wag: 7, dig: 9, sleep: 1.5, belly: 4, stretch: 2, bark: 5, howl: 2 },
      routine: ['sit', 'pant', 'pant', 'lick', 'scratch', 'sniff', 'lie', 'yawn', 'tilt', 'shake', 'wag', 'dig', 'sleep', 'belly', 'stretch'],
      times: { yawn: 2.2, tilt: 2.4, shake: 1.4, wag: 2.5, dig: 2.6, sleep: 6, belly: 3, stretch: 2 },
    },
  };
  const validDog = value => typeof value === 'string' && Object.prototype.hasOwnProperty.call(DOGS, value);
  let id = 'frodo';
  try {
    const q = new URLSearchParams(location.search).get('dog');
    if (validDog(q)) localStorage.setItem(KEY, q);
    const stored = localStorage.getItem(KEY);
    if (validDog(stored)) id = stored;
  } catch (e) { }
  window.CHLOPKOW_DOGS = DOGS;
  window.CHLOPKOW_DOG = DOGS[id];
  // Takes effect on the next page load (sprites are loaded once with the map).
  window.chlopkowSetDog = d => { if (!validDog(d)) return false; try { localStorage.setItem(KEY, d); } catch (e) { } return true; };
})();

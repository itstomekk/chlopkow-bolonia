(() => {
  'use strict';

  const overlay = document.getElementById('boot-splash');
  const logo = document.getElementById('boot-splash-logo');
  const fallbackTitle = document.getElementById('boot-splash-title');
  const errorText = document.getElementById('boot-splash-error');
  const reloadButton = document.getElementById('boot-splash-reload');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const durations = reducedMotion
    ? { logo: 20, black: 20, map: 40 }
    : { logo: 450, black: 120, map: 650 };
  let stage = 'loading';
  let timer = 0;
  let finishing = false;
  let started = false;
  let logoReady = !logo;
  let failure = false;

  Object.defineProperty(window, '__arkBoot', {
    configurable: false,
    enumerable: false,
    value: {
      get stage() { return stage; },
      finish,
      fail
    }
  });

  function setStage(next) {
    stage = next;
    if (overlay) overlay.dataset.bootStage = next;
  }

  function fallbackLogo() {
    if (!overlay || !logo || !logo.complete || logo.naturalWidth > 0) return;
    overlay.classList.add('logo-missing');
    logoReady = true;
    if (finishing) startFinish();
  }

  if (logo) {
    logo.addEventListener('load', () => {
      logoReady = true;
      if (finishing) startFinish();
    }, { once: true });
    logo.addEventListener('error', fallbackLogo, { once: true });
    if (logo.complete) {
      if (logo.naturalWidth > 0) logoReady = true;
      else fallbackLogo();
    }
  }

  if (reloadButton) reloadButton.addEventListener('click', () => window.location.reload());
  // A blocking splash must block keyboard activation too (Tab/Enter cannot start a hidden form).
  window.addEventListener('keydown', event => {
    if (stage === 'ready' || stage === 'error') return;
    event.preventDefault();
    event.stopImmediatePropagation();
  }, true);

  function waitForTransition(element, property, duration, callback) {
    let finished = false;
    const complete = () => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      element.removeEventListener('transitionend', onEnd);
      callback();
    };
    const onEnd = event => {
      if (event.target === element && event.propertyName === property) complete();
    };
    element.addEventListener('transitionend', onEnd);
    timer = window.setTimeout(complete, duration + (reducedMotion ? 40 : 120));
  }

  // Runs after two animation frames (the previous style change has been painted); never later than 250 ms,
  // so a background tab or a throttled rAF cannot leave the splash stuck.
  function afterPaint(callback) {
    let done = false;
    const run = () => { if (done) return; done = true; clearTimeout(guard); callback(); };
    const guard = window.setTimeout(run, 250);
    window.requestAnimationFrame(() => window.requestAnimationFrame(run));
  }

  function startFinish() {
    if (started || failure || !logoReady || !overlay) return;
    started = true;
    setStage('logo-out');
    // Start the fade on a painted frame: the first frames after game init can stall for hundreds of ms and a
    // timer-based fallback armed earlier would otherwise cut the fade short.
    afterPaint(() => {
      if (failure) return;
      overlay.classList.add('boot-logo-out');
      waitForTransition(logo || overlay, 'opacity', durations.logo, () => {
        if (failure) return;
        // A timer fallback can win before a delayed CSS transition completes. Enforce its endpoint
        // before announcing black: the logo must not leak into the black frame or map reveal.
        for (const element of [logo, fallbackTitle]) {
          if (!element) continue;
          element.style.transition = 'none';
          element.style.opacity = '0';
        }
        setStage('black');
        timer = window.setTimeout(() => {
          if (failure) return;
          // Keep the logo and the fallback title faded out throughout the map reveal.
          if (logo) logo.style.opacity = '0';
          setStage('map-in');
          afterPaint(() => {
            if (failure) return;
            overlay.classList.add('boot-map-in');
            waitForTransition(overlay, 'opacity', durations.map, () => {
              if (failure) return;
              overlay.hidden = true;
              overlay.style.pointerEvents = 'none';
              setStage('ready');
            });
          });
        }, durations.black);
      });
    });
  }

  function finish() {
    if (finishing || failure || !overlay) return;
    finishing = true;
    startFinish();
  }

  function fail(message) {
    if (failure || !overlay) return;
    failure = true;
    finishing = false;
    clearTimeout(timer);
    overlay.classList.remove('boot-logo-out', 'boot-map-in');
    for (const element of [logo, fallbackTitle]) {
      if (!element) continue;
      element.style.opacity = '';
      element.style.transition = '';
    }
    overlay.hidden = false;
    overlay.style.opacity = '1';
    overlay.style.pointerEvents = 'auto';
    overlay.classList.add('boot-error');
    errorText.textContent = String(message == null || message === '' ? 'Nie udało się uruchomić gry.' : message);
    setStage('error');
  }
})();

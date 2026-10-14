# Loading splash and inline character identity

## Approved design

User approved: URL opens to the existing Polonia logo centered on pure black. Only after game assets initialize does the logo fade out to full black; after a brief black frame the map and selection HUD fade in. No crest/logo in the selector or gameplay. This is a loading overlay, not a timed title art sequence. Reduced motion retains the same order with minimal delay. Load failures show a visible safe error/retry instead of a permanent black screen.

Select a character, e.g. Edytka. Replace that selected card's canvas name label with a DOM input at exactly its label position. Input starts empty, placeholder is the default name (Edytka); custom sanitized text becomes the player identity. Blank/whitespace-only text means the chosen character's default name. The default names are Arek, Marcin, Damian, Edytka, DJ Renik, BERCIK. Clicking another card clears the prior draft and uses that card's default. There is one input and a separate Start game action, no boxed name prompt. Choosing does not auto-start. The submitted identity is used in the HUD, dialogue and Nostr arrival, independently of sprite identity. Name remains fixed for the saved game. Continue preserves the saved identity/progress; N starts fresh without destroying existing save before submission. Legacy unnamed continuation still gets an identity choice.

## Ownership

Parent owns docs/js/game.js (inline selector, removing old canvas splash/crest, readiness call), test/player_identity_test.py, test/branding_flow_test.py, PLAN/HANDOFF and runner integration. Delegate owns docs/index.html, NEW docs/js/loading-splash.js and NEW test/loading_splash_test.py. Neither modifies concurrent map/assets/generator changes nor publishes anything.

## Implementation and verification

- [x] Splash regression and standalone early markup/controller: desktop/mobile logo on black before core init; real init triggers finish, stages in order, actual computed zero logo opacity at black. Delayed map and delayed/missing logo, reduced motion, keyboard blocking and real invalid-map init failure covered. No public relay writes.
- [x] Inline identity regression: default/custom Edytka names, selected-card label bounds, hidden canvas label, switching, actual click-to-type and touch, HUD/arrival, continuation and fresh reset covered.
- [x] Replace separate form with compact positioning by characterButtonBounds, sanitize at submission, remove old timed art/crest, expose world/HUD beneath selector and report init errors safely.
- [x] Update old branding/identity/arrival tests, preserve accessible IDs/disclosure, register both new regressions. Ordinary isolated regressions await boot readiness; splash test retains raw navigation timing.
- [x] Parent independently verified focused splash/identity/chat/arrival/selector/branding/save checks, syntax/diff checks and screenshots. Reviewer found Enter on focused Start and short-height layout bugs; both fixed and parent verified, including 1280x720 -> 390x320 resize with retained draft.
- [x] Update PLAN/HANDOFF. No commit/push, no edits to concurrent map/generator files.
- [x] Full batch recorded: 42/44, failures in mowing and eight-direction timing assertions. Direction is now asserted while both keys remain held; five repeats PASS. Parent slow-frame differential reproduced original mowing at 15/70 and synchronized mowing at 70/70. Mowing test now awaits run and each actual cut tile; fresh complete minigames and direction reruns PASS. No runtime movement/minigames changes and no second full-batch 44/44 claimed.

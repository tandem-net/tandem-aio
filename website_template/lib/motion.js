/**
 * ============================================================================
 * MOTION LIBRARY  (lib/motion.js)
 * ============================================================================
 * A central catalogue of Framer Motion configs so animation *feel* is
 * consistent site-wide and tunable from one file. Two concepts live here:
 *
 *   • SPRINGS  — physics presets (stiffness / damping / mass). A spring has no
 *     fixed duration; it settles based on forces. This is what gives the site
 *     its "weighty but responsive" Apple feel instead of robotic linear timing.
 *
 *   • VARIANTS — named animation states (`hidden` → `visible`) that components
 *     pass to `<motion.*>`. Declaring them once keeps choreography uniform and
 *     lets parents orchestrate children via `staggerChildren`.
 *
 * MENTAL MODEL FOR SPRINGS:
 *   stiffness ↑  = snappier / faster pull toward target
 *   damping   ↑  = less overshoot / fewer bounces (acts like friction)
 *   mass      ↑  = heavier object, slower to start and stop
 * ============================================================================
 */

// ---------------------------------------------------------------------------
// SPRING PRESETS
// ---------------------------------------------------------------------------

/**
 * GENTLE — the workhorse for entrance reveals (fade/slide up).
 * Moderate stiffness with high damping = smooth glide, zero bounce. This is the
 * "premium" curve: content arrives confidently and settles without wobble.
 */
export const springGentle = {
  type: "spring",
  stiffness: 120,
  damping: 20,
  mass: 1,
};

/**
 * SNAPPY — for interactive feedback (hover lifts, button taps). Higher
 * stiffness makes it feel instantly reactive to the pointer.
 */
export const springSnappy = {
  type: "spring",
  stiffness: 320,
  damping: 24,
  mass: 0.6,
};

/**
 * FLOATY — for the architecture fragments flying into place. Lower stiffness +
 * a touch of mass means the pieces drift outward with momentum, like debris in
 * zero-g settling onto their targets.
 */
export const springFloaty = {
  type: "spring",
  stiffness: 70,
  damping: 18,
  mass: 1.2,
};

/**
 * SCROLL_SMOOTHING — NOT an animation target but a smoothing filter applied to
 * raw scroll progress via `useSpring`. Raw scroll values are jittery (they jump
 * with every wheel tick); piping them through this spring yields the buttery,
 * inertial parallax you feel on apple.com. Low stiffness = lots of easing.
 */
export const scrollSmoothing = {
  stiffness: 90,
  damping: 30,
  // `restDelta` controls when the spring is considered "at rest" and stops
  // recomputing — smaller = more precise but marginally more CPU.
  restDelta: 0.001,
};

// ---------------------------------------------------------------------------
// REUSABLE VARIANTS
// ---------------------------------------------------------------------------

/**
 * fadeUp — the canonical "reveal on scroll" for headings and paragraphs.
 * Starts 28px low and transparent, lands at natural position, full opacity.
 * `custom` (a delay in seconds) can be passed per-element for cascading reveals.
 */
export const fadeUp = {
  hidden: { opacity: 0, y: 28 },
  visible: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: { ...springGentle, delay },
  }),
};

/**
 * fadeIn — opacity only, no movement. For backgrounds / ambient layers where
 * translation would feel wrong.
 */
export const fadeIn = {
  hidden: { opacity: 0 },
  visible: (delay = 0) => ({
    opacity: 1,
    transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1], delay },
  }),
};

/**
 * staggerParent — a "controller" variant. It has no visual properties of its
 * own; its only job is to time its children. When the parent flips to
 * `visible`, each child's own `visible` fires 0.12s after the previous one,
 * producing a cascade. Children must also declare `hidden`/`visible`.
 */
export const staggerParent = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.12,
      delayChildren: 0.05,
    },
  },
};

/**
 * scaleIn — for cards/tiles. Combines a subtle zoom with the fade so elements
 * feel like they "press in" from glass rather than just appearing.
 */
export const scaleIn = {
  hidden: { opacity: 0, scale: 0.94, y: 20 },
  visible: (delay = 0) => ({
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { ...springGentle, delay },
  }),
};

// ---------------------------------------------------------------------------
// SHARED VIEWPORT CONFIG for `whileInView`.
// `once: true`  → animate the first time only (no replay on scroll-back, which
//                 feels gimmicky and hurts perf).
// `amount: 0.3` → fire when 30% of the element is visible, not the moment a
//                 single pixel enters — gives a more deliberate, settled reveal.
// `margin`      → start slightly BEFORE the element reaches the viewport so the
//                 motion is already underway when the user looks at it.
// ---------------------------------------------------------------------------
export const viewportConfig = {
  once: true,
  amount: 0.3,
  margin: "0px 0px -10% 0px",
};

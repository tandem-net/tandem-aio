"use client";

/**
 * ============================================================================
 * useCountUp — animated number hook  (hooks/useCountUp.js)
 * ============================================================================
 * Drives the "live metric" odometer effect in Section 2. When the target
 * element scrolls into view, the displayed number eases from 0 up to its final
 * value. We build it on Framer Motion primitives rather than a setInterval so
 * the animation is frame-synced (rAF-driven), interruptible, and respects the
 * same easing language as the rest of the site.
 *
 * RETURNS: { ref, display }
 *   • ref     — attach to the element you want to watch; the count starts when
 *               it enters the viewport.
 *   • display — the formatted string to render (e.g. "4.82", "12,480", "38.4M").
 * ============================================================================
 */

import { useEffect, useRef, useState } from "react";
import { useInView, useMotionValue, animate } from "framer-motion";

/**
 * @param {number}  target            final value to count to
 * @param {object}  options
 * @param {number}  options.duration  seconds for the count (default 2)
 * @param {number}  options.decimals  fixed decimal places (default 0)
 * @param {boolean} options.compact   render large numbers as 12.5K / 38.4M
 * @param {string}  options.suffix    appended after the number (e.g. " PFLOPS")
 */
export function useCountUp(
  target,
  { duration = 2, decimals = 0, compact = false, suffix = "" } = {}
) {
  // ---- STATE MANAGEMENT ---------------------------------------------------
  // `ref` marks the DOM node whose visibility gates the animation.
  const ref = useRef(null);

  // `useInView` returns true once the node has entered the viewport. `once`
  // ensures we never re-trigger the count on scroll-back up. `amount: 0.4`
  // waits until the metric is comfortably on-screen before firing.
  const inView = useInView(ref, { once: true, amount: 0.4 });

  // `motionValue` is Framer's mutable, render-free number container. We animate
  // THIS (not React state) so we don't trigger a re-render every single frame —
  // instead we subscribe to it and push a formatted string into `display` only
  // when the rounded output actually changes.
  const motionValue = useMotionValue(0);

  // `display` is the human-readable string the component renders.
  const [display, setDisplay] = useState(formatValue(0, { decimals, compact, suffix }));

  // ---- THE MOTION LAYER ---------------------------------------------------
  useEffect(() => {
    if (!inView) return;

    // `animate(from→to)` returns a controls object. We tween the motionValue
    // from its current 0 up to `target`. The easing below is Apple's signature
    // cubic-bezier: slow-out finish so the last digits gently decelerate into
    // place rather than slamming to a stop.
    const controls = animate(motionValue, target, {
      duration,
      ease: [0.22, 1, 0.36, 1],
      // `onUpdate` fires every animation frame with the live interpolated
      // number. We format it and commit to React state. Because we only call
      // setState with a *string*, React bails out of re-rendering when the
      // visible text hasn't changed (e.g. between two frames that both round
      // to "12,480"), keeping this cheap.
      onUpdate: (latest) => {
        setDisplay(formatValue(latest, { decimals, compact, suffix }));
      },
    });

    // Cleanup: if the component unmounts mid-count (or Strict Mode double-runs
    // the effect in dev), stop the animation so we don't leak a running loop.
    return () => controls.stop();
  }, [inView, target, duration, decimals, compact, suffix, motionValue]);

  return { ref, display };
}

/**
 * formatValue — pure formatter shared by the initial state and every frame.
 * Kept outside the hook so it isn't recreated on each render.
 */
function formatValue(n, { decimals, compact, suffix }) {
  let body;

  if (compact) {
    // Compact notation for the big "tasks completed" style numbers.
    if (n >= 1_000_000) body = (n / 1_000_000).toFixed(1) + "M";
    else if (n >= 1_000) body = (n / 1_000).toFixed(1) + "K";
    else body = n.toFixed(0);
  } else {
    // `toLocaleString` gives us thousands separators (12,480) and respects the
    // requested decimal precision in one call.
    body = n.toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  return body + suffix;
}

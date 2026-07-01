"use client";

/**
 * ============================================================================
 * CoreMetrics  (components/home/CoreMetrics.jsx)
 * ============================================================================
 * Section 2 — "The Scale". Pitch-black band showing three oversized, live
 * counters (FLOPS, active nodes, tasks completed) that smoothly count up the
 * moment they scroll into view. Pure focus on raw network scale.
 *
 * The counting logic is fully encapsulated in the `useCountUp` hook; this
 * component is just layout + the reveal choreography around it.
 * ============================================================================
 */

import { motion } from "framer-motion";
import { METRICS } from "@/lib/data";
import { useCountUp } from "@/hooks/useCountUp";
import { staggerParent, fadeUp, viewportConfig } from "@/lib/motion";
import SectionLabel from "@/components/ui/SectionLabel";

/**
 * MetricStat — one counter. Extracted into its own component because each needs
 * its OWN `useCountUp` hook instance (hooks can't be called in a loop body of
 * the parent; each card calling the hook is the clean, idiomatic pattern).
 */
function MetricStat({ metric }) {
  // ---- STATE MANAGEMENT ---------------------------------------------------
  // The hook owns all state (the in-view trigger + the animated value) and
  // hands back a `ref` to watch and a ready-to-render `display` string.
  // NOTE: we deliberately DON'T pass `suffix` to the hook — the unit (e.g.
  // "PFLOPS") is rendered separately below at a smaller size so the giant digits
  // stay the focal point and never wrap a long word onto a second line.
  const { ref, display } = useCountUp(metric.value, {
    decimals: metric.decimals,
    compact: metric.compact,
    duration: 2.2,
  });

  return (
    // Each stat is also a fadeUp child of the parent stagger, so the three
    // columns reveal in a left-to-right cascade as the band enters view. The
    // count-up (driven by the hook's own in-view detection) plays alongside.
    <motion.div variants={fadeUp} className="text-center">
      {/* THE NUMBER + UNIT.
          LAYOUT/STYLING: `text-metric` is our large clamp() size (2.5rem → 5rem)
          with -0.04em tracking so the digits pack tightly like a scoreboard.
          `tabular-nums` forces fixed-width figures so the layout doesn't jiggle
          horizontally as digits change during the count — essential for a stable
          odometer feel. The number and its unit sit on a shared baseline
          (`items-baseline`) so "PFLOPS" rides alongside the digits at a calmer
          size instead of competing with them. */}
      <div className="flex items-baseline justify-center gap-2">
        <span
          ref={ref}
          className="text-metric font-semibold tabular-nums text-mist-50"
        >
          {display}
        </span>
        {/* Unit label — only rendered when the metric defines a suffix. */}
        {metric.suffix && (
          <span className="text-xl font-medium tracking-tight text-mist-400 sm:text-2xl">
            {metric.suffix.trim()}
          </span>
        )}
      </div>
      {/* LABEL + HINT below the number. */}
      <p className="mt-4 text-[15px] font-medium text-mist-200">{metric.label}</p>
      <p className="mx-auto mt-1.5 max-w-[22ch] text-[13px] leading-relaxed text-mist-600">
        {metric.hint}
      </p>
    </motion.div>
  );
}

export default function CoreMetrics() {
  return (
    // ---- LAYOUT / STYLING ARCHITECTURE -------------------------------------
    //   bg-obsidian-950 (the deepest token) → "pitch black to focus on scale"
    //   py-32 / lg:py-44 → immense vertical negative space isolating the band
    <section className="relative bg-obsidian-950 px-6 py-32 lg:py-44">
      {/* A faint top hairline glow line implies this is a discrete "readout". */}
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 mx-auto h-px max-w-5xl bg-gradient-to-r from-transparent via-white/10 to-transparent"
      />

      <div className="mx-auto max-w-6xl">
        <div className="mb-16 flex justify-center">
          <SectionLabel>Why Tandem</SectionLabel>
        </div>

        {/* ---- MOTION LAYER ---------------------------------------------------
            The grid is the stagger PARENT. `whileInView="visible"` flips it when
            scrolled into view (once), which cascades its `fadeUp` children. The
            individual count-ups are triggered independently by each hook's own
            in-view check — so even though they're orchestrated together, the
            numbers animate in true response to visibility. */}
        <motion.div
          variants={staggerParent}
          initial="hidden"
          whileInView="visible"
          viewport={viewportConfig}
          className="grid grid-cols-1 gap-16 md:grid-cols-3 md:gap-8"
        >
          {METRICS.map((metric) => (
            <MetricStat key={metric.id} metric={metric} />
          ))}
        </motion.div>
      </div>
    </section>
  );
}

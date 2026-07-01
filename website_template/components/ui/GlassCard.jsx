"use client";

/**
 * ============================================================================
 * GlassCard  (components/ui/GlassCard.jsx)
 * ============================================================================
 * The frosted-glass surface that represents a "node" throughout the site. It is
 * the single most-reused visual primitive, so it lives here once and every
 * section composes it. Wraps `motion.div` so any card can be animated by a
 * parent (variants flow through via props spread).
 *
 * Composition pattern: this component owns ONLY the glass surface + glow + hover
 * lift. Callers pass whatever content they want as `children`. That separation
 * keeps it reusable for node modules, pillars, team cards, the CTA box, etc.
 * ============================================================================
 */

import { motion } from "framer-motion";
import { springSnappy } from "@/lib/motion";

export default function GlassCard({
  children,
  className = "",
  glowClass = "",       // e.g. "shadow-glow-rust" to tint the halo per layer
  interactive = true,   // set false for static decorative cards
  ...props              // variants / initial / animate flow straight to motion
}) {
  // ---- LAYOUT / STYLING ARCHITECTURE -------------------------------------
  //   .glass            → the frosted recipe from globals.css (blur + fill + rim)
  //   rounded-3xl       → large 24px radius; Apple uses generous corner radii
  //   p-* is left to caller via className so density is contextual
  //   relative + overflow-hidden → contain the inner top-edge highlight sheen
  const base = "glass rounded-3xl relative overflow-hidden";

  // ---- MOTION LAYER -------------------------------------------------------
  // On hover the card lifts 6px and its glow intensifies (we swap to
  // `shadow-glass-hover` via Tailwind's hover: and layer the coloured glow on
  // top). `springSnappy` keeps the lift crisp. We guard all of this behind
  // `interactive` so purely decorative glass doesn't react to the pointer.
  const hoverMotion = interactive
    ? {
        whileHover: { y: -6 },
        transition: springSnappy,
      }
    : {};

  return (
    <motion.div
      className={`${base} ${interactive ? "hover:shadow-glass-hover " + glowClass : ""} ${className}`}
      {...hoverMotion}
      {...props}
    >
      {/* TOP-EDGE SHEEN: a 1px bright gradient line pinned to the card's top
          inner edge. This is the detail that sells "glass" — it reads as a
          light source glancing off the pane's lip. Pointer-events-none so it
          never intercepts clicks. */}
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent"
      />
      {children}
    </motion.div>
  );
}

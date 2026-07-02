"use client";

/**
 * ============================================================================
 * SectionLabel  (components/ui/SectionLabel.jsx)
 * ============================================================================
 * The small, uppercase, letter-spaced "kicker" that sits above section
 * headlines (e.g. "· THE SCALE ·"). A tiny component, but extracting it keeps
 * the eyebrow styling identical everywhere and gives each one a consistent
 * fade-up reveal when scrolled into view.
 * ============================================================================
 */

import { motion } from "framer-motion";
import { fadeUp, viewportConfig } from "@/lib/motion";

export default function SectionLabel({ children, className = "" }) {
  // ---- LAYOUT / STYLING ---------------------------------------------------
  //   text-xs + tracking-[0.25em] + uppercase → the technical "eyebrow" look
  //   text-mist-400                            → muted so it supports, not shouts
  //   The leading dot is a 6px accent-blue pip that adds a spec-sheet feel.
  // ---- MOTION LAYER -------------------------------------------------------
  //   whileInView fadeUp via the shared variant + viewportConfig so it animates
  //   once, when 30% on screen, matching every other reveal on the site.
  return (
    <motion.div
      className={`flex items-center gap-2.5 text-xs font-medium uppercase tracking-[0.25em] text-mist-400 ${className}`}
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={viewportConfig}
    >
      <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent-blue shadow-glow-blue" />
      {children}
    </motion.div>
  );
}

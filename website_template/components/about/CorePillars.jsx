"use client";

/**
 * ============================================================================
 * CorePillars  (components/about/CorePillars.jsx)
 * ============================================================================
 * About — Section 2 — "The Architecture Trio". A clean three-column bento grid
 * explaining the stack choices: Rust (engine), Go (concurrency), Python/
 * cloudpickle (serialization). Each pillar is a frosted card with a colour-
 * coded tech name and a checklist of properties.
 * ============================================================================
 */

import { motion } from "framer-motion";
import { PILLARS } from "@/lib/data";
import { scaleIn, fadeUp, staggerParent, viewportConfig } from "@/lib/motion";
import GlassCard from "@/components/ui/GlassCard";
import SectionLabel from "@/components/ui/SectionLabel";

// Small inline check glyph for the property lists.
function Check({ className = "" }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M3 7.5L6 10.5L11 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function CorePillars() {
  return (
    <section className="relative bg-obsidian-950 px-6 py-24 lg:py-32">
      <div className="mx-auto max-w-6xl">
        {/* HEADER */}
        <div className="max-w-2xl">
          <SectionLabel>The Core Pillars</SectionLabel>
          <motion.h2
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={viewportConfig}
            className="mt-6 text-section font-semibold text-mist-50"
          >
            Three languages. One deliberate stack.
          </motion.h2>
        </div>

        {/* ---- BENTO GRID -----------------------------------------------------
            Three equal columns on desktop, stacking to one on mobile. The
            stagger parent reveals them in sequence; each uses `scaleIn`. */}
        <motion.div
          variants={staggerParent}
          initial="hidden"
          whileInView="visible"
          viewport={viewportConfig}
          className="mt-14 grid grid-cols-1 gap-5 md:grid-cols-3"
        >
          {PILLARS.map((pillar) => (
            <motion.div key={pillar.id} variants={scaleIn}>
              <GlassCard
                interactive
                glowClass={pillar.glowClass}
                className="flex h-full flex-col p-8"
              >
                {/* KICKER → muted role of the pillar ("The Engine"). */}
                <span className="text-[13px] font-medium uppercase tracking-[0.18em] text-mist-400">
                  {pillar.kicker}
                </span>
                {/* TECH NAME → colour-coded, large, the focal point of the card. */}
                <h3 className={`mt-3 text-3xl font-semibold tracking-tight ${pillar.textClass}`}>
                  {pillar.tech}
                </h3>

                {/* Hairline divider before the property checklist. */}
                <span className="my-6 h-px w-full bg-white/10" />

                {/* PROPERTY CHECKLIST — each item gets the accent-coloured check. */}
                <ul className="space-y-3.5">
                  {pillar.points.map((point) => (
                    <li key={point} className="flex items-center gap-3 text-[15px] text-mist-200">
                      <span className={pillar.textClass}>
                        <Check />
                      </span>
                      {point}
                    </li>
                  ))}
                </ul>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

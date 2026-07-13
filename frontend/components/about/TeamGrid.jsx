"use client";

/**
 * ============================================================================
 * TeamGrid  (components/about/TeamGrid.jsx)            ★ FLAGSHIP DELIVERABLE #2
 * ============================================================================
 * About — Section 3 — "The Team / Open Source Roots". An elegant, minimal grid
 * of co-founder profile cards. Each card has:
 *   • A styled image placeholder (a glowing monogram derived from initials —
 *     swaps to a real photo automatically if `image` is provided in data.js).
 *   • A bold name header.
 *   • A secondary line for University / Major (the `affiliation`).
 *   • A high-impact, single-sentence bio.
 *   • A subtle location tag reinforcing the globally-distributed, decentralized
 *     nature of the project itself.
 *
 * The grid reveals as a staggered cascade and each card lifts on hover.
 *
 * COMMENT TIERS: STATE MANAGEMENT · LAYOUT/STYLING · MOTION.
 * ============================================================================
 */

import { motion } from "framer-motion";
import { FOUNDERS } from "@/lib/data";
import { scaleIn, fadeUp, staggerParent, viewportConfig } from "@/lib/motion";
import GlassCard from "@/components/ui/GlassCard";
import SectionLabel from "@/components/ui/SectionLabel";

/* ----------------------------------------------------------------------------
 * initialsOf — derive a monogram ("Robel Yoseph" → "RY") for the placeholder.
 * Pure helper, defined module-level so it isn't recreated per render.
 * -------------------------------------------------------------------------- */
function initialsOf(name) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2) // first + last only — keeps the monogram to two glyphs
    .map((part) => part[0].toUpperCase())
    .join("");
}

/* ============================================================================
 * TeamCard — a single co-founder card.
 * ========================================================================== */
function TeamCard({ member }) {
  // ---- STATE MANAGEMENT ---------------------------------------------------
  // No interactive React state needed per card — hover is handled declaratively
  // by Framer's `whileHover` (via GlassCard) and Tailwind `group-hover`. The
  // only "branch" is whether a real image exists, decided from the data.
  const hasImage = false;

  return (
    // `scaleIn` is the per-card entrance (zoom + fade + rise). As a child of the
    // grid's stagger parent, its timing is offset from its siblings to cascade.
    <motion.div variants={scaleIn} className="h-full">
      {/* `group` lets inner elements (the monogram glow, the name) react to a
          hover anywhere on the card. h-full so all cards in a row match height. */}
      <GlassCard interactive className="group flex h-full flex-col p-6">
        {/* ---- IMAGE PLACEHOLDER ------------------------------------------
            LAYOUT/STYLING:
              aspect-[4/5]  → a portrait frame, the classic profile proportion.
              rounded-2xl   → softens the frame to match the card radius.
              overflow-hidden + relative → contains the glow + future <img>.
            If a real `image` path is supplied we render it cover-fit; otherwise
            we render the monogram treatment so the card never looks "empty". */}
        <div className="relative aspect-[4/5] w-full overflow-hidden rounded-2xl border border-white/10 bg-obsidian-800">
          {hasImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={member.image}
              alt={member.name}
              className="h-full w-full object-cover transition-transform duration-700 ease-apple group-hover:scale-105"
            />
          ) : (
            <>
              {/* Monogram backdrop: a radial accent glow that intensifies on
                  hover (group-hover bumps its opacity). This is what makes a
                  text placeholder feel intentional and premium rather than
                  like a missing asset. */}
              <div
                aria-hidden="true"
                className="absolute inset-0 bg-[radial-gradient(circle_at_50%_38%,rgba(46,155,255,0.22)_0%,transparent_60%)] opacity-70 transition-opacity duration-500 ease-apple group-hover:opacity-100"
              />
              {/* Faint blueprint grid inside the frame for technical texture. */}
              <div
                aria-hidden="true"
                className="absolute inset-0 bg-mesh-grid bg-grid-sm opacity-20"
              />
              {/* The initials themselves — gradient-clipped for a metallic feel,
                  centered, with tight tracking. */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-gradient text-5xl font-semibold tracking-tight">
                  {initialsOf(member.name)}
                </span>
              </div>
            </>
          )}

          {/* LOCATION TAG — a tiny frosted chip pinned bottom-left, signalling
              where this contributor is on the globe (the "decentralized roots"
              theme). pointer-events-none so it never blocks card interaction. */}
        </div>

        {/* ---- TEXT BLOCK ------------------------------------------------- */}
        <div className="mt-5 flex flex-1 flex-col">
          {/* NAME — bold header. Shifts to pure white on hover (it's already
              near-white; the group-hover nudges it brighter for a subtle lift). */}
          <h3 className="text-[19px] font-semibold tracking-tight text-mist-50">
            {member.name}
          </h3>

          {/* ROLE — accent-blue secondary descriptor. */}
          <p className="mt-1 text-[13px] font-medium text-accent-blue">
            {member.role}
          </p>

          {/* BIO — the single high-impact sentence. `mt-auto` pushes it to the
              bottom so bios align across cards of differing text length. */}
          <p className="mt-4 text-[14px] leading-relaxed text-mist-200">
            {member.bio}
          </p>
        </div>
      </GlassCard>
    </motion.div>
  );
}

/* ============================================================================
 * TeamGrid — the section wrapper.
 * ========================================================================== */
export default function TeamGrid() {
  return (
    <section className="relative px-6 py-24 lg:py-32">
      <div className="mx-auto max-w-6xl">
        {/* HEADER COPY */}
        <div className="max-w-2xl">
          <SectionLabel>Open Source Roots</SectionLabel>
          <motion.h2
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={viewportConfig}
            className="mt-6 text-section font-semibold text-mist-50"
          >
            Built by a distributed team.
          </motion.h2>
          <motion.p
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={viewportConfig}
            className="mt-5 max-w-xl text-balance text-lg leading-relaxed text-mist-400"
          >
            Like the network itself, the people behind Tandem are spread across
            the globe — coordinating without a center.
          </motion.p>
        </div>

        {/* ---- THE GRID -------------------------------------------------------
            LAYOUT/STYLING: responsive column count — 1 col on phones, 2 on
            tablets, 4 on wide screens — using a simple, predictable breakpoint
            ramp. `items-stretch` (grid default) + `h-full` on cards keeps every
            card the same height per row.
            MOTION: the grid is the stagger PARENT; mounting it in view cascades
            each TeamCard's `scaleIn` entrance left-to-right, top-to-bottom. */}
        <motion.div
          variants={staggerParent}
          initial="hidden"
          whileInView="visible"
          viewport={viewportConfig}
          className="mt-14 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4"
        >
          {FOUNDERS.map((member) => (
            <TeamCard key={member.id} member={member} />
          ))}
        </motion.div>
      </div>
    </section>
  );
}

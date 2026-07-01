"use client";

/**
 * ============================================================================
 * HardwareShowcase  (components/home/HardwareShowcase.jsx)
 * ============================================================================
 * Section 4 — "Hardware Agnosticism". A grid of clean, neon-outlined device
 * drawings (gaming desktop, edge server, laptop) over the message that Tandem
 * runs on anything. The outlines are hand-rolled inline SVG so they're crisp,
 * weightless (no image requests), and inherit our accent colour on hover.
 * ============================================================================
 */

import { motion } from "framer-motion";
import { HARDWARE } from "@/lib/data";
import { fadeUp, scaleIn, staggerParent, viewportConfig } from "@/lib/motion";
import GlassCard from "@/components/ui/GlassCard";
import SectionLabel from "@/components/ui/SectionLabel";

/* ----------------------------------------------------------------------------
 * DEVICE GLYPHS — minimal line-art SVGs. `currentColor` lets the stroke inherit
 * whatever text colour the parent sets, so hover can recolour them to accent.
 * stroke-width 1.5 keeps the "thin, sharp" line quality from the brief.
 * -------------------------------------------------------------------------- */
const GLYPH_PROPS = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  className: "h-20 w-20",
  viewBox: "0 0 48 48",
  "aria-hidden": true,
};

function DeviceGlyph({ id }) {
  if (id === "desktop") {
    // Tower + monitor.
    return (
      <svg {...GLYPH_PROPS}>
        <rect x="6" y="8" width="24" height="18" rx="1.5" />
        <path d="M18 26v6M12 38h12" />
        <rect x="34" y="10" width="8" height="28" rx="1.5" />
        <circle cx="38" cy="34" r="1" />
        <path d="M36 14h4M36 17h4" />
      </svg>
    );
  }
  if (id === "server") {
    // Stacked rack units with status lights.
    return (
      <svg {...GLYPH_PROPS}>
        <rect x="10" y="8" width="28" height="9" rx="1.5" />
        <rect x="10" y="20" width="28" height="9" rx="1.5" />
        <rect x="10" y="32" width="28" height="8" rx="1.5" />
        <circle cx="15" cy="12.5" r="1" />
        <circle cx="15" cy="24.5" r="1" />
        <circle cx="15" cy="36" r="1" />
        <path d="M30 12.5h4M30 24.5h4M30 36h4" />
      </svg>
    );
  }
  // laptop
  return (
    <svg {...GLYPH_PROPS}>
      <rect x="9" y="10" width="30" height="20" rx="1.5" />
      <path d="M5 36h38l-2.5-4H7.5L5 36Z" />
    </svg>
  );
}

export default function HardwareShowcase() {
  return (
    // ---- LAYOUT / STYLING --------------------------------------------------
    // Subtle radial lift behind the section so it doesn't read as a flat band.
    <section className="relative overflow-hidden bg-obsidian-950 px-6 py-28 lg:py-40">
      <div
        aria-hidden="true"
        className="absolute left-1/2 top-1/2 -z-10 h-[40rem] w-[40rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(46,155,255,0.06)_0%,transparent_60%)]"
      />

      <div className="mx-auto max-w-6xl">
        {/* HEADER COPY */}
        <div className="mx-auto max-w-2xl text-center">
          <div className="flex justify-center">
            <SectionLabel>Built for Any Device</SectionLabel>
          </div>
          <motion.h2
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={viewportConfig}
            className="mt-6 text-section font-semibold text-mist-50"
          >
            From home desktops to edge servers.
          </motion.h2>
          <motion.p
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={viewportConfig}
            className="mx-auto mt-5 max-w-xl text-balance text-lg leading-relaxed text-mist-400"
          >
            Tandem turns idle silicon into a unified grid. If a device can run a runtime, it can contribute to the network.
          </motion.p>
        </div>

        {/* ---- DEVICE GRID ----------------------------------------------------
            Stagger parent reveals the three cards in sequence. Each card uses
            the `scaleIn` variant (zoom + fade) so they feel like they press in
            from glass. `group` enables the hover recolour on the glyph. */}
        <motion.div
          variants={staggerParent}
          initial="hidden"
          whileInView="visible"
          viewport={viewportConfig}
          className="mt-16 grid grid-cols-1 gap-5 sm:grid-cols-3"
        >
          {HARDWARE.map((device) => (
            <motion.div key={device.id} variants={scaleIn}>
              <GlassCard
                interactive
                className="group flex flex-col items-center gap-5 p-10 text-center"
              >
                {/* Glyph: muted by default, snaps to accent blue on card hover
                    via the `group-hover` colour change + our easing curve. */}
                <div className="text-mist-400 transition-colors duration-500 ease-apple group-hover:text-accent-blue">
                  <DeviceGlyph id={device.id} />
                </div>
                <div>
                  <h3 className="text-[17px] font-semibold tracking-tight text-mist-50">
                    {device.name}
                  </h3>
                  <p className="mt-1 text-[13px] text-mist-400">{device.spec}</p>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

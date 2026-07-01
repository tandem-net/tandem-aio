"use client";

/**
 * ============================================================================
 * ArchitectureReveal  (components/home/ArchitectureReveal.jsx)
 *                                              ★ FLAGSHIP DELIVERABLE #1 (part B)
 * ============================================================================
 * Section 3 — "The Architecture Reveal". The interactive explainer.
 *
 * THE EFFECT, IN PLAIN ENGLISH:
 *   We make the section very TALL (300vh) and PIN an inner canvas to the screen
 *   with `position: sticky`. As the user scrolls through those 3 screens of
 *   height, the canvas stays put while a single "Compute Task" card at the
 *   centre BURSTS APART into three frosted-glass node modules (Rust / Go /
 *   Python) that fly to their positions. Neon mesh lines then DRAW themselves
 *   from the centre to each node. Hovering a node highlights its technical role.
 *
 * WHY STICKY + TALL SECTION:
 *   A sticky child inside a tall parent is the canonical "scrollytelling"
 *   pattern. The parent's height *is* the scroll budget; `useScroll` measures
 *   our progress through it (0→1) and we map that progress onto every animated
 *   property. No scroll math, no manual listeners — Framer derives it.
 *
 * RESPONSIVE STRATEGY:
 *   The pinned spatial choreography only makes sense with room to breathe, so
 *   it runs on `md+`. On phones we render a clean, static vertical stack of the
 *   same three node cards (declared at the bottom) — same content, no overlap.
 *
 * COMMENT TIERS: STATE MANAGEMENT · LAYOUT/STYLING · MOTION.
 * ============================================================================
 */

import { useRef, useState } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { ARCH_NODES } from "@/lib/data";
import { fadeUp, staggerParent, viewportConfig, springSnappy } from "@/lib/motion";
import GlassCard from "@/components/ui/GlassCard";
import SectionLabel from "@/components/ui/SectionLabel";

/* ----------------------------------------------------------------------------
 * COORDINATE SYSTEM
 * We design the canvas in an abstract 800×560 viewBox. The SVG that draws the
 * mesh lines uses these exact units, and the node cards are positioned with
 * PERCENTAGES derived from the same units. Because the SVG uses
 * preserveAspectRatio="none" (it stretches to fill the container), viewBox units
 * and container percentages map to the SAME on-screen points at ANY size — so
 * the line endpoints land dead-centre on the cards, fully responsively.
 * -------------------------------------------------------------------------- */
const VB = { w: 800, h: 560, cx: 400, cy: 280, spreadX: 300, spreadY: 175 };

/** Convert a node's normalized target (-1..1) into absolute viewBox coords. */
function nodePoint(target) {
  return {
    x: VB.cx + target.x * VB.spreadX,
    y: VB.cy + target.y * VB.spreadY,
  };
}

/* ============================================================================
 * ArchNode — ONE frosted node module on the interactive canvas.
 * Extracted so each node can legally own its own `useTransform` hooks (Rules of
 * Hooks: calling hooks inside a child mapped over a constant array is clean).
 * ========================================================================== */
function ArchNode({ node, progress, isActive, onActivate }) {
  // ---- LAYOUT: where this node finally rests (percent of the canvas box) ---
  const point = nodePoint(node.target);
  const leftPct = (point.x / VB.w) * 100;
  const topPct = (point.y / VB.h) * 100;

  // ---- MOTION LAYER (scroll-linked fly-in) --------------------------------
  // Each node starts pulled INWARD toward the centre (so it looks like it spawns
  // out of the bursting task card) and settles at its resting spot.
  //   • The inward pull is proportional to the node's direction × 150px, so a
  //     node further out starts further in — they all converge at the centre.
  //   • opacity/scale ramp in slightly AFTER the central card starts breaking
  //     (window [0.12, 0.4]) so there's a beat of "shatter" before nodes appear.
  const x = useTransform(progress, [0.12, 0.45], [-node.target.x * 150, 0]);
  const y = useTransform(progress, [0.12, 0.45], [-node.target.y * 150, 0]);
  const scale = useTransform(progress, [0.12, 0.45], [0.6, 1]);
  const opacity = useTransform(progress, [0.12, 0.4], [0, 1]);

  return (
    // ANCHOR (static): pinned at the node's percentage spot and centred on it
    // via -translate-1/2. This element does NOT use motion transforms, so the
    // tailwind centering transform is safe here and won't collide with the
    // scroll-driven transforms on the child below.
    <div
      className="absolute z-10 w-[180px] -translate-x-1/2 -translate-y-1/2 lg:w-[220px]"
      style={{ left: `${leftPct}%`, top: `${topPct}%` }}
    >
      {/* FLY-IN WRAPPER (motion): owns the scroll-linked x/y/scale/opacity.
          Keeping these on a dedicated element means the inner GlassCard is free
          to run its OWN hover-lift transform without the two fighting over the
          element's single `transform` property. */}
      <motion.div style={{ x, y, scale, opacity }}>
        <GlassCard
          interactive
          glowClass={node.glowClass}
          // Pointer handlers drive the "highlight its role" interaction. We lift
          // the active node's id to the parent so only one is emphasized and so
          // the connecting mesh line can brighten in sync.
          onMouseEnter={() => onActivate(node.id)}
          onMouseLeave={() => onActivate(null)}
          className={
            "cursor-pointer p-5 transition-colors duration-300 ease-apple " +
            node.borderClass +
            (isActive ? " border-white/25" : "")
          }
        >
          {/* LAYER EYEBROW — tiny coloured tag naming the architectural tier. */}
          <div className={`text-[11px] font-medium uppercase tracking-[0.18em] ${node.textClass}`}>
            {node.layer}
          </div>
          {/* TITLE — the tech name. */}
          <h3 className="mt-2 text-[17px] font-semibold tracking-tight text-mist-50">
            {node.title}
          </h3>
          {/* ROLE — the one-line technical descriptor that the brief asks to
              surface on hover. Always visible but the description below expands. */}
          <p className="mt-0.5 text-[13px] text-mist-400">{node.role}</p>

          {/* DESCRIPTION — collapses to 0 height until hovered, then springs
              open. We animate `height: auto` via Framer (it measures the natural
              height for us) plus opacity for a smooth disclosure. */}
          <motion.div
            initial={false}
            animate={{
              height: isActive ? "auto" : 0,
              opacity: isActive ? 1 : 0,
            }}
            transition={springSnappy}
            className="overflow-hidden"
          >
            <p className="mt-3 text-[13px] leading-relaxed text-mist-200">
              {node.description}
            </p>
          </motion.div>
        </GlassCard>
      </motion.div>
    </div>
  );
}

/* ============================================================================
 * MeshLines — the neon connections drawn from the centre to each node.
 * Rendered as an SVG that fills the canvas; `pathLength` is animated 0→1 so each
 * line literally draws itself as you scroll past the burst.
 * ========================================================================== */
function MeshLines({ progress, activeId }) {
  // The lines draw in over scroll window [0.4, 0.85] — AFTER the nodes have
  // mostly arrived, so connections form once the structure exists.
  const draw = useTransform(progress, [0.4, 0.85], [0, 1]);

  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox={`0 0 ${VB.w} ${VB.h}`}
      // none = stretch viewBox to the box exactly so coords line up with the
      // percentage-positioned cards (see COORDINATE SYSTEM note up top).
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {/* A soft glow filter so the neon lines bloom like emitted light. */}
      <defs>
        <filter id="lineGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {ARCH_NODES.map((node) => {
        const p = nodePoint(node.target);
        const active = activeId === node.id;
        // Map our accent tokens to concrete stroke colours for SVG (SVG can't
        // read Tailwind classes). Kept in sync with tailwind.config.js.
        const stroke =
          node.accent === "rust"
            ? "#F26B3A"
            : node.accent === "cyan"
            ? "#00ADD8"
            : "#FFD43B";

        return (
          <motion.line
            key={node.id}
            x1={VB.cx}
            y1={VB.cy}
            x2={p.x}
            y2={p.y}
            stroke={stroke}
            // Thin + sharp normally; thickens and brightens when its node is
            // hovered, tying the line to the card.
            strokeWidth={active ? 2 : 1}
            // `pathLength` is the fraction of the line drawn. Driving it from the
            // shared `draw` motion value animates the stroke on as we scroll.
            style={{ pathLength: draw, opacity: active ? 1 : 0.5 }}
            filter="url(#lineGlow)"
            vectorEffect="non-scaling-stroke" // keep stroke crisp despite stretch
          />
        );
      })}
    </svg>
  );
}

/* ============================================================================
 * CentralTask — the source card that fragments. Fades + shrinks as the burst
 * begins, handing its "energy" to the nodes flying out.
 * ========================================================================== */
function CentralTask({ progress }) {
  // Whole and bright at the start; dissolves over [0, 0.32] as nodes emerge.
  const opacity = useTransform(progress, [0, 0.32], [1, 0]);
  const scale = useTransform(progress, [0, 0.32], [1, 0.5]);
  // A faint rotation adds kinetic energy to the "shatter" moment.
  const rotate = useTransform(progress, [0, 0.32], [0, -8]);

  return (
    <motion.div
      style={{ opacity, scale, rotate }}
      className="absolute left-1/2 top-1/2 z-20 w-[200px] -translate-x-1/2 -translate-y-1/2"
    >
      <GlassCard interactive={false} className="p-5 shadow-glow-blue">
        <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-accent-blue">
          Incoming Job
        </div>
        <h3 className="mt-2 text-[17px] font-semibold tracking-tight text-mist-50">
          Compute Task
        </h3>
        <p className="mt-0.5 text-[13px] text-mist-400">Python · cloudpickle</p>
        {/* Faux code/progress shimmer bars to imply a real payload. */}
        <div className="mt-4 space-y-1.5">
          <div className="h-1.5 w-full rounded-full bg-white/10" />
          <div className="h-1.5 w-2/3 rounded-full bg-white/10" />
          <div className="h-1.5 w-4/5 rounded-full bg-white/10" />
        </div>
      </GlassCard>
    </motion.div>
  );
}

/* ============================================================================
 * ArchitectureReveal — the section that wires it all together.
 * ========================================================================== */
export default function ArchitectureReveal() {
  // ---- STATE MANAGEMENT ---------------------------------------------------
  // `sectionRef` is the tall scroll track we measure progress against.
  const sectionRef = useRef(null);
  // `activeId` = which node is currently hovered (or null). Lifted here so a
  // hovered card and its mesh line highlight together.
  const [activeId, setActiveId] = useState(null);

  // `useScroll` over the tall section: progress goes 0 (section top hits
  // viewport top) → 1 (section bottom hits viewport bottom). Because the inner
  // canvas is sticky, it stays centred on screen across that whole range.
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end end"],
  });

  return (
    <section className="relative bg-obsidian-950">
      {/* INTRO COPY — scrolls normally above the pinned canvas. */}
      <div className="mx-auto max-w-3xl px-6 pt-28 text-center lg:pt-40">
        <div className="flex justify-center">
          <SectionLabel>How It Works</SectionLabel>
        </div>
        <motion.h2
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={viewportConfig}
          className="mt-6 text-section font-semibold text-mist-50"
        >
          One job. <span className="text-mist-400">Many private nodes.</span>
        </motion.h2>
        <motion.p
          variants={fadeUp}
          initial="hidden"
          whileInView="visible"
          viewport={viewportConfig}
          className="mx-auto mt-5 max-w-xl text-balance text-lg leading-relaxed text-mist-400"
        >
          Scroll to see a compute task move across the mesh — packaged for developers, routed securely, and orchestrated in the background.
        </motion.p>
      </div>

      {/* =================================================================== */}
      {/* DESKTOP / TABLET: the pinned, scroll-driven canvas (md+ only).       */}
      {/* The OUTER div is 300vh tall = the scroll budget. The INNER div is    */}
      {/* `sticky top-0 h-screen` = pinned to the viewport while we scroll the  */}
      {/* outer height past it.                                                */}
      {/* =================================================================== */}
      <div ref={sectionRef} className="relative hidden h-[300vh] md:block">
        <div className="sticky top-0 flex h-screen items-center justify-center overflow-hidden">
          {/* Blueprint grid backdrop, edge-masked into the void. */}
          <div
            aria-hidden="true"
            className="mask-fade-y absolute inset-0 bg-mesh-grid bg-grid-sm opacity-30"
          />

          {/* THE CANVAS BOX — fixed aspect ratio matching our viewBox so the
              SVG lines and the percentage-positioned cards share one coordinate
              space. max-w caps it on large monitors. */}
          <div className="relative mx-auto aspect-[800/560] w-full max-w-4xl px-6">
            {/* z-order: grid (back) → lines → nodes → central task (front). */}
            <MeshLines progress={scrollYProgress} activeId={activeId} />
            {ARCH_NODES.map((node) => (
              <ArchNode
                key={node.id}
                node={node}
                progress={scrollYProgress}
                isActive={activeId === node.id}
                onActivate={setActiveId}
              />
            ))}
            <CentralTask progress={scrollYProgress} />
          </div>
        </div>
      </div>

      {/* =================================================================== */}
      {/* MOBILE FALLBACK: a clean static stack (no pinning/overlap). Same      */}
      {/* content, revealed with the standard fadeUp stagger.                  */}
      {/* =================================================================== */}
      <motion.div
        variants={staggerParent}
        initial="hidden"
        whileInView="visible"
        viewport={viewportConfig}
        className="mx-auto flex max-w-md flex-col gap-4 px-6 py-20 md:hidden"
      >
        {ARCH_NODES.map((node) => (
          <motion.div key={node.id} variants={fadeUp}>
            <GlassCard interactive glowClass={node.glowClass} className="p-5">
              <div className={`text-[11px] font-medium uppercase tracking-[0.18em] ${node.textClass}`}>
                {node.layer}
              </div>
              <h3 className="mt-2 text-[17px] font-semibold tracking-tight text-mist-50">
                {node.title}
              </h3>
              <p className="mt-0.5 text-[13px] text-mist-400">{node.role}</p>
              <p className="mt-3 text-[13px] leading-relaxed text-mist-200">
                {node.description}
              </p>
            </GlassCard>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}

"use client";

/**
 * ============================================================================
 * Hero  (components/home/Hero.jsx)            ★ FLAGSHIP DELIVERABLE #1 (part A)
 * ============================================================================
 * Section 1 — "The Hook". A full-viewport cinematic intro:
 *   • An ambient, breathing "core particle" glow behind the headline.
 *   • A massive, tracking-tight, gradient-masked headline.
 *   • A muted sub-headline.
 *   • Two CTAs (primary filled + secondary chevron link).
 *   • A scroll cue at the bottom.
 *
 * Plus a signature touch: the whole hero parallaxes and fades as you scroll
 * away from it, so it recedes "into the void" rather than just sliding off —
 * the depth trick that makes apple.com feel three-dimensional.
 *
 * COMMENT TIERS used throughout: STATE MANAGEMENT · LAYOUT/STYLING · MOTION.
 * ============================================================================
 */

import { useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import Button from "@/components/ui/Button";
import { staggerParent, fadeUp } from "@/lib/motion";

export default function Hero() {
  // ===== STATE MANAGEMENT ==================================================
  // No React state here — the only "state" is scroll position, which Framer
  // tracks for us via motion values (off the React render loop, so it's cheap).
  //
  // `heroRef` marks the scroll-tracking boundary. `useScroll` with
  // `offset: ["start start", "end start"]` produces `scrollYProgress` that runs
  // 0 → 1 as the hero travels from "its top at the viewport top" to "its bottom
  // at the viewport top" — i.e. across exactly one screen of scrolling away.
  const heroRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });

  // ===== MOTION LAYER (scroll-linked) ======================================
  // Map scroll progress (0→1) onto visual properties. These are *derived*
  // motion values: they update every frame the scroll position changes, with
  // zero re-renders.
  //
  //   opacity : fade the hero out over the first 60% of the scroll-away.
  //   y       : drift content UP 120px as we leave (parallax — content moves
  //             faster than the scroll, implying it's closer to the camera).
  //   scale   : shrink slightly (0.92) so it feels like it's falling backward.
  //   coreScale/coreOpacity : the glow swells and dims as we depart, like a
  //             star receding.
  const opacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);
  const y = useTransform(scrollYProgress, [0, 1], [0, -120]);
  const scale = useTransform(scrollYProgress, [0, 1], [1, 0.92]);
  const coreScale = useTransform(scrollYProgress, [0, 1], [1, 1.6]);
  const coreOpacity = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  return (
    // The ref wraps a tall-ish section so there's scroll distance to map across.
    // `relative` anchors the absolutely-positioned glow; `overflow-hidden` keeps
    // the glow's blur from spilling onto neighbouring sections.
    <section
      ref={heroRef}
      className="relative flex min-h-screen items-center justify-center overflow-hidden px-6"
    >
      {/* ================= AMBIENT BACKGROUND LAYER ========================= */}
      {/* CORE PARTICLE: two stacked radial glows. The CSS `pulseCore` keyframe
          gives it a 6s breathing loop (always-on ambient life), while the
          scroll-linked coreScale/coreOpacity above make it react to departure.
          `pointer-events-none` so it never blocks clicks. */}
      <motion.div
        aria-hidden="true"
        style={{ scale: coreScale, opacity: coreOpacity }}
        className="pointer-events-none absolute left-1/2 top-1/2 -z-10 -translate-x-1/2 -translate-y-1/2"
      >
        {/* Inner hot core — electric blue, tight + bright. */}
        <div className="h-[34rem] w-[34rem] animate-pulseCore rounded-full bg-[radial-gradient(circle,rgba(46,155,255,0.45)_0%,rgba(46,155,255,0.08)_40%,transparent_70%)] blur-2xl" />
        {/* Outer cool halo — larger, fainter, offset timing via blur depth. */}
        <div className="absolute inset-0 -z-10 scale-150 rounded-full bg-[radial-gradient(circle,rgba(120,180,255,0.12)_0%,transparent_60%)] blur-3xl" />
      </motion.div>

      {/* Faint blueprint grid, masked to fade at the edges — adds technical
          texture without competing with the headline. */}
      <div
        aria-hidden="true"
        className="mask-fade-y pointer-events-none absolute inset-0 -z-20 bg-mesh-grid bg-grid-lg opacity-40"
      />

      {/* ================= FOREGROUND CONTENT ============================== */}
      {/* This motion.div carries the scroll-linked parallax (opacity/y/scale).
          Inside it, a SEPARATE stagger orchestration handles the one-time
          entrance reveal on page load — the two motion systems compose cleanly:
          one is scroll-driven (departure), the other time-driven (arrival). */}
      <motion.div
        style={{ opacity, y, scale }}
        className="relative z-10 mx-auto max-w-5xl text-center"
      >
        <motion.div variants={staggerParent} initial="hidden" animate="visible">
          {/* AVAILABILITY PILL — tiny glass chip. The `fadeUp` child reveals
              first in the stagger cascade. */}
          <motion.div variants={fadeUp} className="mb-8 flex justify-center">
            <span className="glass inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-[13px] text-mist-200">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-blue shadow-glow-blue" />
              Private compute for everyday devices
            </span>
          </motion.div>

          {/* HEADLINE — the showpiece.
              LAYOUT/STYLING: `text-hero` is our clamp()-based fluid size from
              tailwind.config (scales 2.75rem → 7rem) with line-height 0.95 and
              -0.04em tracking baked in — the tight optical tracking is what
              makes huge type feel engineered rather than bloated.
              `.text-gradient` clips the silver→blue gradient to the glyphs and
              `animate-shimmer` slowly drifts it for a living metallic sheen. */}
          <motion.h1
            variants={fadeUp}
            className="text-hero text-balance font-bold"
          >
            <span className="text-gradient animate-shimmer">
              The world&apos;s idle compute.
            </span>
            <br />
            <span className="text-mist-50">Made private.</span>
          </motion.h1>

          {/* SUB-HEADLINE — muted gray, constrained measure (max-w-2xl) for
              comfortable reading length (~60 chars). */}
          <motion.p
            variants={fadeUp}
            className="mx-auto mt-7 max-w-2xl text-balance text-lg leading-relaxed text-mist-400 sm:text-xl"
          >
            Tandem lets users turn spare capacity on their own devices into a secure, distributed network that runs in the background of everyday life.
          </motion.p>

          {/* CTA ROW — primary fill + secondary chevron link. flex-wrap so it
              stacks gracefully on narrow screens. */}
          <motion.div
            variants={fadeUp}
            className="mt-10 flex flex-wrap items-center justify-center gap-3"
          >
            <Button href="#join" variant="primary">
              Join the Network
            </Button>
            <Button href="#how-it-works" variant="secondary">
              See How It Works
            </Button>
          </motion.div>
        </motion.div>
      </motion.div>

      {/* ================= SCROLL CUE ====================================== */}
      {/* A minimalist "mouse" that hints there's more below. It fades out on
          scroll using the same `opacity` motion value as the hero content, so
          it disappears in lock-step with everything else. */}
      <motion.div
        style={{ opacity }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
        aria-hidden="true"
      >
        <div className="flex h-9 w-5 items-start justify-center rounded-full border border-white/20 p-1.5">
          {/* The little dot drifts up-and-down forever via a yoyo tween. */}
          <motion.span
            className="h-1.5 w-1.5 rounded-full bg-mist-200"
            animate={{ y: [0, 8, 0] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
      </motion.div>
    </section>
  );
}

"use client";

/**
 * ============================================================================
 * Vision  (components/about/Vision.jsx)
 * ============================================================================
 * About — Section 1 — "The Vision". An asymmetric, editorial layout (think a
 * feature article in an elite tech publication): a short label + giant pull-
 * quote headline on the left, supporting prose offset to the right. Large,
 * elegant type carries the philosophy.
 * ============================================================================
 */

import { motion } from "framer-motion";
import { fadeUp, staggerParent, viewportConfig } from "@/lib/motion";
import SectionLabel from "@/components/ui/SectionLabel";

export default function Vision() {
  return (
    <section className="relative px-6 pt-40 pb-24 lg:pt-48">
      {/* Ambient glow drifting off the top, anchoring the page opener. */}
      <div
        aria-hidden="true"
        className="absolute left-1/2 top-0 -z-10 h-[30rem] w-[50rem] -translate-x-1/2 rounded-full bg-[radial-gradient(ellipse,rgba(46,155,255,0.10)_0%,transparent_65%)] blur-2xl"
      />

      {/* ---- ASYMMETRIC GRID -------------------------------------------------
          12-col grid. Headline occupies the left 7 cols; body prose sits in the
          right 4 cols offset by a column — the deliberate imbalance is what
          gives it an editorial, magazine feel rather than a centered marketing
          block. */}
      <motion.div
        variants={staggerParent}
        initial="hidden"
        whileInView="visible"
        viewport={viewportConfig}
        className="mx-auto grid max-w-6xl grid-cols-1 gap-x-8 gap-y-10 lg:grid-cols-12"
      >
        {/* LEFT: label + oversized statement. */}
        <div className="lg:col-span-7">
          <motion.div variants={fadeUp}>
            <SectionLabel>The Vision</SectionLabel>
          </motion.div>
          <motion.h1
            variants={fadeUp}
            className="mt-7 text-balance text-[clamp(2.25rem,5.5vw,4.5rem)] font-semibold leading-[1.02] tracking-tight text-mist-50"
          >
            The cloud was never supposed to be{" "}
            <span className="text-mist-400">three companies.</span>
          </motion.h1>
        </div>

        {/* RIGHT: supporting prose, offset down and to the right. */}
        <motion.div
          variants={fadeUp}
          className="space-y-5 text-[17px] leading-relaxed text-mist-400 lg:col-span-4 lg:col-start-9 lg:pt-3"
        >
          <p>
            A handful of hyperscalers own the substrate that modern computing
            runs on. Pricing, availability, and access are dictated from a few
            control rooms — while billions of capable machines sit idle.
          </p>
          <p>
            Tandem inverts that model. Instead of renting time on someone
            else&apos;s centralized iron, the network composes a{" "}
            <span className="text-mist-50">distributed virtual data center</span>{" "}
            out of the hardware that already exists — coordinated, peer-to-peer,
            and owned by no one.
          </p>
        </motion.div>
      </motion.div>
    </section>
  );
}

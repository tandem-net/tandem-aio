"use client";

/**
 * ============================================================================
 * CallToAction  (components/home/CallToAction.jsx)
 * ============================================================================
 * Section 5 — "The Closing". A large, deeply-nested container that glows from
 * its borders, holding two ways in:
 *   1. A copy-able one-line install command (`curl -sSL tandem.sh | sh`).
 *   2. An email field to join the developer beta.
 *
 * Includes a tiny bit of real interactivity: the terminal command copies to the
 * clipboard with click feedback, and the email field tracks input state.
 * ============================================================================
 */

import { useState } from "react";
import { motion } from "framer-motion";
import { fadeUp, scaleIn, viewportConfig, springSnappy } from "@/lib/motion";

export default function CallToAction() {
  // ---- STATE MANAGEMENT ---------------------------------------------------
  // `copied`     → toggles the "Copied!" confirmation on the terminal command.
  // `email`      → controlled value of the beta signup input.
  // `submitted`  → swaps the form for a thank-you once "submitted" (no backend
  //                here; this is the front-end UI shell ready to wire to an API).
  const [copied, setCopied] = useState(false);
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const command = "curl -sSL tandem.sh | sh";

  // Copy handler: writes to the clipboard, flips `copied` true, then resets
  // after 2s so the affordance returns to its idle state.
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API can reject (insecure context / permissions). Fail quietly
      // — in production you'd surface a fallback "select to copy" hint.
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault(); // keep it a SPA interaction; no full page reload
    if (!email) return;
    setSubmitted(true); // → here you'd POST to /api/beta-signup
  };

  return (
    <section id="deploy" className="relative bg-obsidian-950 px-6 py-28 lg:py-40">
      {/* ---- THE GLOWING CONTAINER ------------------------------------------
          `scaleIn` makes the whole slab press in from glass on scroll. The
          frosted `.glass` recipe + an oversized inset radial glow gives the
          "subtly glows from the borders" look from the brief. Generous padding
          (p-10 → p-20) creates the deep-nested, premium feel. */}
      <motion.div
        variants={scaleIn}
        initial="hidden"
        whileInView="visible"
        viewport={viewportConfig}
        className="glass relative mx-auto max-w-4xl overflow-hidden rounded-[2rem] p-10 text-center sm:p-16 lg:p-20"
      >
        {/* Inner border-glow: a large soft radial pinned to the slab, masked by
            overflow-hidden so it bleeds from the edges inward. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_center,rgba(46,155,255,0.12)_0%,transparent_70%)]"
        />

        {/* HEADLINE */}
        <motion.h2
          variants={fadeUp}
          className="text-balance text-section font-semibold text-mist-50"
        >
          Join the mesh in minutes.
        </motion.h2>
        <motion.p
          variants={fadeUp}
          className="mx-auto mt-5 max-w-lg text-balance text-lg leading-relaxed text-mist-400"
        >
          Add your device, run the installer, and let Tandem work quietly in the background. Drop your email to get early access.
        </motion.p>

        {/* ---- TERMINAL COMMAND ---------------------------------------------
            A faux terminal row: traffic-light dots, the monospaced command, and
            a copy button. The whole bar is clickable to copy. */}
        <motion.button
          variants={fadeUp}
          onClick={handleCopy}
          whileTap={{ scale: 0.99 }}
          transition={springSnappy}
          className="group mx-auto mt-10 flex w-full max-w-xl items-center gap-3 rounded-2xl border border-white/10 bg-obsidian-900/80 px-4 py-3.5 text-left transition-colors duration-300 ease-apple hover:border-white/20"
        >
          {/* Mac-style window dots — pure decoration that sells "terminal". */}
          <span className="flex gap-1.5 pl-1">
            <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
            <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
            <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
          </span>

          {/* The command. `font-mono` + a green prompt `$` reads as a shell.
              The blinking caret uses the `blink` keyframe from the theme. */}
          <code className="flex-1 truncate font-mono text-[14px] text-mist-200">
            <span className="text-emerald-400">$</span> {command}
            <span className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-blink bg-mist-400" />
          </code>

          {/* Copy affordance swaps label on success. */}
          <span className="shrink-0 rounded-lg bg-white/5 px-3 py-1.5 text-[12px] font-medium text-mist-200 transition-colors group-hover:bg-white/10">
            {copied ? "Copied!" : "Copy"}
          </span>
        </motion.button>

        {/* DIVIDER with "or" */}
        <motion.div
          variants={fadeUp}
          className="mx-auto my-7 flex max-w-xl items-center gap-4 text-[12px] uppercase tracking-[0.2em] text-mist-600"
        >
          <span className="h-px flex-1 bg-white/10" />
          or
          <span className="h-px flex-1 bg-white/10" />
        </motion.div>

        {/* ---- BETA SIGNUP FORM ---------------------------------------------
            Swaps to a confirmation message once submitted. The input + button
            sit in a single pill-shaped frosted container. */}
        <motion.div variants={fadeUp} className="mx-auto max-w-xl">
          {submitted ? (
            // Confirmation state — a gentle fade/scale in.
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={springSnappy}
              className="rounded-full border border-accent-blue/30 bg-accent-blue/10 px-6 py-3.5 text-[15px] text-mist-50"
            >
              You&apos;re on the list. We&apos;ll be in touch soon. ✦
            </motion.div>
          ) : (
            <form
              onSubmit={handleSubmit}
              className="flex flex-col gap-2.5 sm:flex-row"
            >
              {/* Controlled email input. `peer`-free here; styling focuses on a
                  clean ring on focus that matches our accent. */}
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="flex-1 rounded-full border border-white/10 bg-obsidian-900/80 px-5 py-3.5 text-[15px] text-mist-50 placeholder:text-mist-600 outline-none transition-colors duration-300 ease-apple focus:border-accent-blue/60 focus:ring-2 focus:ring-accent-blue/20"
              />
              <button
                type="submit"
                className="rounded-full bg-mist-50 px-6 py-3.5 text-[15px] font-medium text-obsidian-950 transition-colors duration-300 ease-apple hover:bg-mist-200"
              >
                Request access
              </button>
            </form>
          )}
        </motion.div>
      </motion.div>
    </section>
  );
}

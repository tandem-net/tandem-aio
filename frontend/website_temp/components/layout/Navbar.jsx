"use client";

/**
 * ============================================================================
 * Navbar  (components/layout/Navbar.jsx)
 * ============================================================================
 * A fixed, glassmorphic top bar that starts transparent over the hero and
 * "frosts in" once the user scrolls — the exact behaviour of apple.com's nav.
 *
 * Tiers below: STATE MANAGEMENT (scroll detection) → LAYOUT/STYLING → MOTION.
 * ============================================================================
 */

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { NAV_LINKS } from "@/lib/data";
import { springGentle } from "@/lib/motion";

export default function Navbar() {
  // ---- STATE MANAGEMENT ---------------------------------------------------
  // `scrolled` flips true after the user moves a little past the top. We use it
  // to toggle the frosted background so the bar is invisible over the hero but
  // legible over content.
  const [scrolled, setScrolled] = useState(false);
  // `mobileOpen` controls the hamburger menu sheet on small screens.
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    // A passive scroll listener (passive = we never call preventDefault, so the
    // browser can keep scrolling on its own thread = no jank). We only care
    // about a boolean threshold, so the handler is trivially cheap.
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll(); // initialize on mount in case we load mid-page
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    // ---- LAYOUT / STYLING ARCHITECTURE ------------------------------------
    //   fixed inset-x-0 top-0 z-50 → pinned across the top, above everything
    //   The glass treatment (bg + blur + border) is applied CONDITIONALLY based
    //   on `scrolled`, with a CSS transition so it cross-fades smoothly.
    <header
      className={
        "fixed inset-x-0 top-0 z-50 transition-all duration-500 ease-apple " +
        (scrolled
          ? "border-b border-white/5 bg-obsidian-950/70 backdrop-blur-glass"
          : "border-b border-transparent bg-transparent")
      }
    >
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 lg:px-8">
        {/* BRAND — a glowing pip + wordmark. tracking-tight for the logotype. */}
        <a href="#top" className="flex items-center gap-2.5">
          <span className="h-2.5 w-2.5 rounded-full bg-accent-blue shadow-glow-blue" />
          <span className="text-[17px] font-semibold tracking-tight text-mist-50">
            Tandem
          </span>
        </a>

        {/* DESKTOP LINKS — hidden on mobile (`md:flex`). Each link fades from
            muted to white on hover via our easing curve. */}
        <ul className="hidden items-center gap-9 md:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.label}>
              <a
                href={link.href}
                className="text-[14px] text-mist-400 transition-colors duration-300 ease-apple hover:text-mist-50"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        {/* DESKTOP CTA */}
        <a
          href="#join"
          className="hidden rounded-full bg-mist-50 px-4 py-1.5 text-[14px] font-medium text-obsidian-950 transition-colors duration-300 ease-apple hover:bg-mist-200 md:inline-block"
        >
          Join
        </a>

        {/* MOBILE TOGGLE — a minimal two-line icon that morphs to an X. */}
        <button
          className="flex h-10 w-10 items-center justify-center md:hidden"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label="Toggle menu"
          aria-expanded={mobileOpen}
        >
          <div className="flex flex-col gap-1.5">
            {/* The two bars rotate/translate into an X when open. */}
            <motion.span
              className="block h-px w-5 bg-mist-50"
              animate={mobileOpen ? { rotate: 45, y: 3 } : { rotate: 0, y: 0 }}
              transition={springGentle}
            />
            <motion.span
              className="block h-px w-5 bg-mist-50"
              animate={mobileOpen ? { rotate: -45, y: -3 } : { rotate: 0, y: 0 }}
              transition={springGentle}
            />
          </div>
        </button>
      </nav>

      {/* ---- MOTION LAYER: MOBILE SHEET --------------------------------------
          AnimatePresence lets the panel animate OUT (not just in) when removed
          from the tree. It expands its height + fades in, collapsing on close. */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            className="overflow-hidden border-t border-white/5 bg-obsidian-950/90 backdrop-blur-glass md:hidden"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={springGentle}
          >
            <ul className="flex flex-col gap-1 px-6 py-4">
              {NAV_LINKS.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className="block py-2.5 text-[15px] text-mist-200 transition-colors hover:text-mist-50"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}

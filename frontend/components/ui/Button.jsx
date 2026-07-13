"use client";

/**
 * ============================================================================
 * Button  (components/ui/Button.jsx)
 * ============================================================================
 * The two CTA styles from the brief, unified behind one API:
 *   • variant="primary"   → filled white pill (the "Deploy a Node" button)
 *   • variant="secondary" → ghost/text link with a chevron ("Read the Whitepaper")
 *
 * Built on `motion.a` so every button gets the same physics-based hover/tap
 * feedback. Renders an <a> by default (works as a link); pass `as="button"`
 * for form actions.
 * ============================================================================
 */

import { motion } from "framer-motion";
import { springSnappy } from "@/lib/motion";

// A tiny inline chevron so we don't pull an icon dependency for one glyph.
function Chevron({ className = "" }) {
  return (
    <svg
      className={className}
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M6 3.5L10.5 8L6 12.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Button({
  children,
  href = "#",
  variant = "primary",
  className = "",
  ...props
}) {
  // ---- LAYOUT / STYLING ARCHITECTURE -------------------------------------
  // `base` holds geometry + behaviour shared by both variants:
  //   inline-flex + items-center + gap → icon and label sit on one baseline
  //   rounded-full                     → the signature Apple pill shape
  //   text-[15px] font-medium          → restrained, not shouty
  //   transition-colors ... ease-apple → colour shifts use our custom curve
  //   focus-visible ring               → keyboard-accessible focus halo
  const base =
    "group inline-flex items-center justify-center gap-1.5 rounded-full text-[15px] font-medium " +
    "transition-colors duration-300 ease-apple focus:outline-none focus-visible:ring-2 " +
    "focus-visible:ring-accent-blue/70 focus-visible:ring-offset-2 focus-visible:ring-offset-obsidian-950";

  // PRIMARY: solid off-white fill on the dark canvas = maximum contrast / the
  // clear "do this" action. Inverts to a subtle gray on hover (mimics Apple's
  // button behaviour where the fill dims slightly rather than changing colour).
  const primary =
    "bg-mist-50 text-obsidian-950 px-6 py-3 hover:bg-mist-200 shadow-[0_0_30px_-10px_rgba(245,245,247,0.5)]";

  // SECONDARY: no fill — a text link. The accent blue + chevron signals
  // "supplementary". The chevron nudges right on hover via the parent `group`.
  const secondary =
    "text-accent-blue px-3 py-3 hover:text-mist-50";

  const variantClass = variant === "primary" ? primary : secondary;

  // ---- MOTION LAYER -------------------------------------------------------
  // `whileHover`/`whileTap` give a spring-driven scale. `springSnappy` (high
  // stiffness, low mass) makes the press feel immediate and tactile. The scale
  // values are deliberately tiny — 1.03 up, 0.97 down — because at this size a
  // larger scale reads as cartoonish. Apple's buttons barely move; they *imply*.
  return (
    <motion.a
      href={href}
      className={`${base} ${variantClass} ${className}`}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      transition={springSnappy}
      {...props}
    >
      {children}
      {/* Chevron only on the secondary/text variant. `group-hover:translate-x`
          slides it right 2px on hover for a subtle "go" affordance. */}
      {variant === "secondary" && (
        <Chevron className="transition-transform duration-300 ease-apple group-hover:translate-x-0.5" />
      )}
    </motion.a>
  );
}

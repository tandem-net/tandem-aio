/**
 * ============================================================================
 * TAILWIND CONFIG — THE DESIGN SYSTEM / SINGLE SOURCE OF TRUTH
 * ============================================================================
 * Every visual primitive for Project Tandem lives here as a *named token* so
 * that components never hard-code raw hex values. Need to shift the whole site
 * one shade darker? Change `obsidian.900` once and it cascades everywhere.
 *
 * The aesthetic target is "Apple keynote in a dark room": near-black canvas,
 * one or two surgical neon accents, generous space, and glow that reads as
 * *light emission* rather than a drop shadow.
 * ============================================================================
 */

/** @type {import('tailwindcss').Config} */
module.exports = {
  // ---------------------------------------------------------------------------
  // CONTENT — files Tailwind scans to tree-shake unused classes out of the
  // final CSS bundle. If a class isn't referenced in one of these globs it will
  // NOT ship. (This is why dynamically-built class strings can silently vanish;
  // we always write full, static class names.)
  // ---------------------------------------------------------------------------
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],

  theme: {
    extend: {
      // -----------------------------------------------------------------------
      // COLOR PALETTE
      // -----------------------------------------------------------------------
      colors: {
        // `obsidian` is our canvas. Note these are NOT pure #000 — a hair of
        // lift (0x05, 0x0A) keeps OLED screens from crushing detail and lets
        // our glowing borders read against the background.
        obsidian: {
          950: "#050506", // deepest layer — the page background itself
          900: "#0A0A0C", // primary surface
          800: "#101014", // raised surface / card base
          700: "#16161C", // hover surface
          600: "#1E1E26", // hairline borders against the canvas
        },
        // Neutral text ramp. `mist` family handles everything from crisp
        // headline white down to barely-there captions.
        mist: {
          50: "#F5F5F7", // Apple's signature off-white for primary text
          200: "#C7C7CC", // bright secondary text
          400: "#86868B", // Apple's exact muted gray for sub-copy
          600: "#5A5A60", // disabled / faint labels
        },
        // Accent system. Each backend layer of Tandem owns one hue so the
        // architecture diagram is colour-coded and instantly legible.
        accent: {
          blue: "#2E9BFF",   // brand electric blue — primary CTA + headline grad
          cyan: "#00ADD8",   // Go's official brand cyan — the Orchestrator layer
          rust: "#F26B3A",   // warm "oxide" orange — the Rust network layer
          python: "#FFD43B", // Python yellow — the serialization layer
        },
      },

      // -----------------------------------------------------------------------
      // TYPOGRAPHY — load Inter via next/font in app/layout.jsx, expose here.
      // `display` is for hero/section headlines (tight tracking, heavy weight).
      // -----------------------------------------------------------------------
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        display: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      // Custom fluid-ish display sizes. We pair very large sizes with negative
      // letter-spacing — the hallmark of the Apple headline look (tight optical
      // tracking at scale prevents the text from feeling "loose").
      fontSize: {
        "hero": ["clamp(2.75rem, 8vw, 7rem)", { lineHeight: "0.95", letterSpacing: "-0.04em", fontWeight: "700" }],
        "section": ["clamp(2rem, 5vw, 4rem)", { lineHeight: "1.02", letterSpacing: "-0.03em", fontWeight: "600" }],
        "metric": ["clamp(2.5rem, 6vw, 5rem)", { lineHeight: "1", letterSpacing: "-0.04em", fontWeight: "600" }],
      },

      // -----------------------------------------------------------------------
      // SHADOWS = GLOW. We don't use shadows for depth here; we use them as
      // emitted light. `glow-*` tokens are coloured, blurred halos applied to
      // borders and CTAs. The inset variants simulate a lit rim on glass cards.
      // -----------------------------------------------------------------------
      boxShadow: {
        "glow-blue": "0 0 40px -8px rgba(46,155,255,0.45)",
        "glow-rust": "0 0 40px -8px rgba(242,107,58,0.45)",
        "glow-cyan": "0 0 40px -8px rgba(0,173,216,0.45)",
        // Frosted card rim: faint outer glow + a bright inner top edge that
        // mimics a sheet of glass catching ambient light.
        "glass": "0 8px 40px -12px rgba(0,0,0,0.7), inset 0 1px 0 0 rgba(255,255,255,0.06)",
        "glass-hover": "0 16px 60px -12px rgba(0,0,0,0.8), inset 0 1px 0 0 rgba(255,255,255,0.12)",
      },

      // -----------------------------------------------------------------------
      // BACKDROP BLUR — the literal "frost" of frosted glass.
      // -----------------------------------------------------------------------
      backdropBlur: {
        xs: "2px",
        glass: "20px",
      },

      // -----------------------------------------------------------------------
      // BACKGROUND IMAGES — reusable gradients & the technical grid texture.
      // `mesh-grid` is a faint blueprint lattice that sits behind the
      // architecture section to imply a coordinate space / data center floor.
      // -----------------------------------------------------------------------
      backgroundImage: {
        "radial-fade": "radial-gradient(ellipse at center, var(--tw-gradient-stops))",
        "mesh-grid":
          "linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px)",
      },
      backgroundSize: {
        "grid-sm": "40px 40px",
        "grid-lg": "80px 80px",
      },

      // -----------------------------------------------------------------------
      // KEYFRAMES — only for *ambient*, always-on motion (breathing glows,
      // drifting particles). Scroll/entry choreography is handled in JS by
      // Framer Motion, NOT here, because it needs to react to scroll progress.
      // -----------------------------------------------------------------------
      keyframes: {
        // Slow opacity+scale "breathing" for the hero core particle.
        pulseCore: {
          "0%, 100%": { opacity: "0.6", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.08)" },
        },
        // Gradient shimmer that sweeps across the headline text fill.
        shimmer: {
          "0%": { backgroundPosition: "0% 50%" },
          "100%": { backgroundPosition: "200% 50%" },
        },
        // Caret blink for the terminal CTA.
        blink: {
          "0%, 49%": { opacity: "1" },
          "50%, 100%": { opacity: "0" },
        },
      },
      animation: {
        pulseCore: "pulseCore 6s ease-in-out infinite",
        shimmer: "shimmer 8s linear infinite",
        blink: "blink 1.1s step-end infinite",
      },

      // -----------------------------------------------------------------------
      // EASING — a custom cubic-bezier that matches Apple's UI feel: a gentle
      // start, quick middle, soft settle. Used by CSS transitions; Framer
      // Motion springs are configured separately in lib/motion.js.
      // -----------------------------------------------------------------------
      transitionTimingFunction: {
        "apple": "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },

  plugins: [],
};

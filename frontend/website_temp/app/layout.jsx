/**
 * ============================================================================
 * ROOT LAYOUT  (app/layout.jsx)
 * ============================================================================
 * Wraps every page. Responsibilities:
 *   1. Load the Inter font via `next/font` (self-hosted, zero layout shift) and
 *      expose it to Tailwind through the `--font-inter` CSS variable that our
 *      tailwind.config.js `fontFamily.sans` points at.
 *   2. Define document <head> metadata (SEO / social).
 *   3. Render the persistent chrome: Navbar (top) + Footer (bottom) around the
 *      page-specific `children`.
 *
 * This is a SERVER component (no "use client") — it ships zero JS for itself,
 * which keeps first paint fast. Interactive children opt into the client.
 * ============================================================================
 */

import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

// Configure Inter. `variable` emits a CSS custom property we hand to Tailwind.
// `display: "swap"` shows fallback text immediately, swapping to Inter when
// ready — no invisible-text flash. We preload only the latin subset to keep the
// font payload tiny.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

// Next.js reads this object to build the document <head>. Centralizing it here
// means consistent titles/social cards across the whole site.
export const metadata = {
  title: "Tandem — The world's idle compute, unified.",
  description:
    "Project Tandem is a decentralized computing mesh that turns idle machines into a coordinated, distributed data center. Rust core, Go orchestration, Python serialization.",
  metadataBase: new URL("https://tandem.sh"),
  openGraph: {
    title: "Tandem — Data centers, unchained.",
    description:
      "A peer-to-peer compute mesh built on a Rust networking core and Go orchestration.",
    type: "website",
  },
};

// Next 14 wants viewport-level concerns (theme color, width) in their OWN
// `viewport` export rather than inside `metadata`. `themeColor` tints the mobile
// browser chrome to our obsidian black so the address bar blends into the page.
export const viewport = {
  themeColor: "#050506",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    // `inter.variable` puts the font CSS var in scope for the whole tree.
    // `dark` + the body bg lock us into dark mode by default, per the brief.
    <html lang="en" className={`${inter.variable} dark`}>
      <body className="min-h-screen bg-obsidian-950 text-mist-50 selection:bg-accent-blue/30">
        <Navbar />
        {/* `children` is the active route's page. We let pages own their own
            section spacing rather than padding here, so full-bleed hero
            backgrounds can reach the screen edges. */}
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}

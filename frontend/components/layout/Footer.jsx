"use client";

/**
 * ============================================================================
 * Footer  (components/layout/Footer.jsx)
 * ============================================================================
 * Quiet, structured site footer. No heavy motion — footers should feel stable.
 * A single hairline top border separates it from the content void above.
 * ============================================================================
 */

import { NAV_LINKS } from "@/lib/data";

// Small grouped link sets. Kept local to the footer since they're footer-only.
const COLUMNS = [
  { title: "Product", links: ["Overview", "Nodes", "Pricing", "Changelog"] },
  { title: "Developers", links: ["Docs", "API", "CLI", "Status"] },
  { title: "Company", links: ["About", "Blog", "Careers", "Contact"] },
];

export default function Footer() {
  return (
    // ---- LAYOUT / STYLING --------------------------------------------------
    //   border-t hairline + generous py spacing → calm, premium separation
    //   max-w-7xl centers content to match the rest of the site's measure
    <footer className="border-t border-white/5 bg-obsidian-950">
      <div className="mx-auto max-w-7xl px-6 py-16 lg:px-8">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-5">
          {/* BRAND COLUMN spans two cells on desktop for visual weight. */}
          <div className="col-span-2">
            <div className="flex items-center gap-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-accent-blue shadow-glow-blue" />
              <span className="text-[17px] font-semibold tracking-tight">Tandem</span>
            </div>
            <p className="mt-4 max-w-xs text-[14px] leading-relaxed text-mist-400">
              The world&apos;s idle compute, unified into one coordinated mesh.
            </p>
          </div>

          {/* LINK COLUMNS — mapped from the local COLUMNS config. */}
          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h4 className="text-[13px] font-medium text-mist-200">{col.title}</h4>
              <ul className="mt-4 space-y-3">
                {col.links.map((l) => (
                  <li key={l}>
                    <a
                      href="#"
                      className="text-[14px] text-mist-400 transition-colors duration-300 ease-apple hover:text-mist-50"
                    >
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* BASELINE BAR */}
        <div className="mt-14 flex flex-col items-start justify-between gap-4 border-t border-white/5 pt-8 text-[13px] text-mist-600 sm:flex-row sm:items-center">
          <p>© {new Date().getFullYear()} Project Tandem. Open source, everywhere.</p>
          <div className="flex gap-6">
            {NAV_LINKS.map((l) => (
              <a key={l.label} href={l.href} className="transition-colors hover:text-mist-200">
                {l.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}

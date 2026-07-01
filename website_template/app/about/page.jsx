/**
 * ============================================================================
 * ABOUT PAGE  (app/about/page.jsx)
 * ============================================================================
 * Composition root for "/about". Like the home page, it just stacks the
 * editorial sections in reading order. Cleaner, calmer, more text-forward than
 * the homepage — "an elite tech publication" rather than a product launch.
 *
 *   1. Vision ......... the philosophy (asymmetric editorial opener)
 *   2. CorePillars .... the architecture trio (bento grid)
 *   3. TeamGrid ....... the distributed founders (profile grid)
 * ============================================================================
 */

import Vision from "@/components/about/Vision";
import CorePillars from "@/components/about/CorePillars";
import TeamGrid from "@/components/about/TeamGrid";

// Per-page metadata overrides the defaults from the root layout for this route.
export const metadata = {
  title: "About — Project Tandem",
  description:
    "Why Tandem moves compute away from centralized cloud monopolies, the Rust/Go/Python stack behind it, and the distributed team building it.",
};

export default function AboutPage() {
  return (
    <>
      <Vision />
      <CorePillars />
      <TeamGrid />
    </>
  );
}

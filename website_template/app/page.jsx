/**
 * ============================================================================
 * HOME PAGE  (app/page.jsx)
 * ============================================================================
 * Composition root for "/". This file is intentionally tiny: it does nothing
 * but stack the five narrative sections in scroll order. All logic, state, and
 * styling live inside the section components — this is the "table of contents".
 *
 * This is a SERVER component (no "use client"); each section opts into the
 * client itself where it needs interactivity. That keeps the page shell static
 * and fast, with islands of interactivity hydrating independently.
 *
 * SCROLL NARRATIVE:
 *   1. Hero ............ the hook
 *   2. CoreMetrics ..... the scale
 *   3. ArchitectureReveal the interactive explainer
 *   4. HardwareShowcase  the inclusivity
 *   5. CallToAction .... the closing
 * ============================================================================
 */

import Hero from "@/components/home/Hero";
import CoreMetrics from "@/components/home/CoreMetrics";
import ArchitectureReveal from "@/components/home/ArchitectureReveal";
import HardwareShowcase from "@/components/home/HardwareShowcase";
import CallToAction from "@/components/home/CallToAction";

export default function HomePage() {
  return (
    <>
      <Hero />
      <CoreMetrics />
      <ArchitectureReveal />
      <HardwareShowcase />
      <CallToAction />
    </>
  );
}

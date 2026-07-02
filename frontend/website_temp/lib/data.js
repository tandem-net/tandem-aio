/**
 * ============================================================================
 * SITE DATA LAYER  (lib/data.js)
 * ============================================================================
 * Content is deliberately separated from presentation. Every component imports
 * its copy/numbers from here, which means:
 *   1. Non-engineers can edit headlines without touching JSX.
 *   2. The same data can later be swapped for a CMS / live API response
 *      (e.g. METRICS could be replaced by a websocket feed of real telemetry).
 *
 * Nothing here renders anything — these are plain serializable objects.
 * ============================================================================
 */

// ---------------------------------------------------------------------------
// LIVE NETWORK METRICS  (Section 2 — "The Scale")
// `value` is the number we count UP to; `format` tells the counter how to
// render it (compact suffix, decimals, prefix). In production you'd hydrate
// `value` from your telemetry endpoint and let the count-up animation play.
// ---------------------------------------------------------------------------
export const METRICS = [
  {
    id: "nodes",
    label: "Private Nodes Connected",
    value: 8420,
    suffix: "",
    decimals: 0,
    hint: "Home computers and edge devices joined to the mesh.",
  },
  {
    id: "jobs",
    label: "Secure Jobs Processed",
    value: 1280000,
    suffix: "",
    decimals: 0,
    compact: true,
    hint: "Background workloads completed without central hosting.",
  },
  {
    id: "homes",
    label: "Homes Participating",
    value: 3200,
    suffix: "",
    decimals: 0,
    hint: "Everyday users contributing spare compute quietly and safely.",
  },
];

// ---------------------------------------------------------------------------
// ARCHITECTURE NODES  (Section 3 — "The Architecture Reveal")
// The single task card fragments into these three layers. `accent` keys map to
// the colour tokens defined in tailwind.config.js so the diagram is
// self-colour-coding. `glowClass`/`textClass` are pre-written FULL class names
// (never interpolated) so Tailwind's tree-shaker keeps them.
// ---------------------------------------------------------------------------
export const ARCH_NODES = [
  {
    id: "rust",
    layer: "Network Layer",
    title: "Rust P2P Core",
    role: "Low-Latency Mesh",
    description:
      "Memory-safe, zero-cost peer-to-peer transport. Routes task fragments between nodes with microsecond-class overhead.",
    accent: "rust",
    textClass: "text-accent-rust",
    glowClass: "shadow-glow-rust",
    borderClass: "hover:border-accent-rust/60",
    // x/y are normalized offsets (-1..1) describing where this node settles
    // relative to the diagram center once the task "explodes" apart.
    target: { x: -1, y: 0.15 },
  },
  {
    id: "go",
    layer: "Control Plane",
    title: "Go Orchestrator",
    role: "Cluster State & Discovery",
    description:
      "Concurrent backend services that track cluster state, schedule work by capacity, and keep node discovery consistent.",
    accent: "cyan",
    textClass: "text-accent-cyan",
    glowClass: "shadow-glow-cyan",
    borderClass: "hover:border-accent-cyan/60",
    target: { x: 1, y: -0.2 },
  },
  {
    id: "python",
    layer: "Execution Layer",
    title: "Cloudpickle Runtime",
    role: "Dynamic Task Packaging",
    description:
      "Serializes entire Python functions and their dependencies, shipping live code — not just data — to remote workers.",
    accent: "python",
    textClass: "text-accent-python",
    glowClass: "shadow-glow-blue", // python yellow halo reads harsh; reuse soft blue
    borderClass: "hover:border-accent-python/60",
    target: { x: 0, y: 1.1 },
  },
];

// ---------------------------------------------------------------------------
// HARDWARE SHOWCASE  (Section 4 — "Hardware Agnosticism")
// Minimal descriptors; the component draws clean SVG outlines per `id`.
// ---------------------------------------------------------------------------
export const HARDWARE = [
  { id: "desktop", name: "Gaming Rig", spec: "Consumer GPU · idle cycles" },
  { id: "server", name: "Edge Server", spec: "Rack iron · always-on" },
  { id: "laptop", name: "Laptop", spec: "Mobile silicon · burst capacity" },
];

// ---------------------------------------------------------------------------
// CORE PILLARS  (About page — "The Architecture Trio" bento grid)
// ---------------------------------------------------------------------------
export const PILLARS = [
  {
    id: "rust",
    kicker: "The Engine",
    tech: "Rust",
    points: ["Memory safety", "Zero-cost abstractions", "Raw P2P speed"],
    textClass: "text-accent-rust",
    glowClass: "shadow-glow-rust",
  },
  {
    id: "go",
    kicker: "The Concurrency",
    tech: "Go",
    points: ["Robust orchestration", "Stable cluster state", "Efficient discovery"],
    textClass: "text-accent-cyan",
    glowClass: "shadow-glow-cyan",
  },
  {
    id: "python",
    kicker: "The Serialization",
    tech: "Python · Cloudpickle",
    points: ["Dynamic task packaging", "Ship code, not data", "Zero developer friction"],
    textClass: "text-accent-python",
    glowClass: "shadow-glow-blue",
  },
];

// ---------------------------------------------------------------------------
// TEAM  (About page — profile grid)
// `image` is intentionally null so the card renders a styled monogram
// placeholder. Drop a real path (e.g. "/team/ada.jpg") to swap in a photo.
// ---------------------------------------------------------------------------
export const FOUNDERS = [
  {
    id: "founder-1",
    name: "Aryan Chaudhuri",
    role: "Founder · Product & Systems",
    bio: "Leads the vision for a private, distributed compute layer that runs quietly on ordinary machines.",
  },
  {
    id: "founder-2",
    name: "Robel Yoseph",
    role: "Founder · Networking",
    bio: "Designs the mesh logic that helps devices discover each other and cooperate securely.",
  },
  {
    id: "founder-3",
    name: "Wissam Nusiar",
    role: "Founder · Infrastructure",
    bio: "Builds the resilient backbone that keeps the network stable and easy to deploy.",
  },
  {
    id: "founder-4",
    name: "Vishal Ambatipudi",
    role: "Founder · Runtime",
    bio: "Focuses on making execution smooth, lightweight, and accessible for developers.",
  },
  {
    id: "founder-5",
    name: "Shamgar David",
    role: "Founder · Security",
    bio: "Shapes the trust model that allows the network to stay private and reliable.",
  },
  {
    id: "founder-6",
    name: "Ethan Yao",
    role: "Founder · Platform",
    bio: "Brings product polish and practical user experience thinking to the deployment flow.",
  },
];

// ---------------------------------------------------------------------------
// NAV — shared between Navbar instances on every page.
// ---------------------------------------------------------------------------
export const NAV_LINKS = [
  { label: "Home", href: "#top" },
  { label: "Why Tandem", href: "#why" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Founders", href: "#founders" },
  { label: "Join", href: "#join" },
];

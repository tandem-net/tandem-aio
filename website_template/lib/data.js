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
    id: "flops",
    label: "Aggregate Network FLOPS",
    value: 4.82,
    suffix: " PFLOPS",
    decimals: 2,
    hint: "Peak floating-point throughput across all online workers.",
  },
  {
    id: "nodes",
    label: "Active Global Nodes",
    value: 12480,
    suffix: "",
    decimals: 0,
    hint: "Volunteer machines currently advertising spare capacity.",
  },
  {
    id: "tasks",
    label: "Tasks Completed",
    value: 38_400_000,
    suffix: "",
    decimals: 0,
    compact: true, // render as 38.4M
    hint: "Serialized Python jobs executed since genesis.",
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
export const TEAM = [
  {
    id: "founder-1",
    name: "Robel Yoseph",
    role: "Co-Founder · Systems & Networking",
    affiliation: "B.S. Computer Science",
    bio: "Obsessed with squeezing data-center throughput out of the idle silicon already sitting in people's bedrooms.",
    image: null,
    location: "Seattle, USA",
  },
  {
    id: "founder-2",
    name: "A. Founder",
    role: "Co-Founder · Distributed Systems",
    affiliation: "B.S. Electrical Engineering",
    bio: "Believes the next hyperscaler won't own a single server — it will coordinate millions it never bought.",
    image: null,
    location: "Berlin, DE",
  },
  {
    id: "founder-3",
    name: "B. Founder",
    role: "Co-Founder · Runtime & Serialization",
    affiliation: "M.S. Computer Science",
    bio: "Wants shipping a Python function to a stranger's GPU to feel as boring as calling a local method.",
    image: null,
    location: "Bangalore, IN",
  },
  {
    id: "founder-4",
    name: "C. Founder",
    role: "Co-Founder · Protocol & Security",
    affiliation: "B.S. Mathematics",
    bio: "Designs the trust layer that lets untrusted machines cooperate without a central authority watching.",
    image: null,
    location: "São Paulo, BR",
  },
];

// ---------------------------------------------------------------------------
// NAV — shared between Navbar instances on every page.
// ---------------------------------------------------------------------------
export const NAV_LINKS = [
  { label: "Home", href: "/" },
  { label: "About", href: "/about" },
  { label: "Docs", href: "#" },
  { label: "Whitepaper", href: "#" },
];

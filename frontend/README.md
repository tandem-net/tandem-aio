# Project Tandem — Marketing Site

A premium, Apple-grade marketing site for **Project Tandem**, a decentralized
computing mesh. Deep-obsidian dark mode, glassmorphism node cards, neon mesh
lines, and physics-based scroll animation.

Built with **Next.js 14 (App Router) · Tailwind CSS · Framer Motion**.

---

## Quick start

```bash
npm install      # install dependencies
npm run dev      # start the dev server → http://localhost:3000
npm run build    # production build
npm run start    # serve the production build
```

> Requires Node 18.18+ (Node 20+ recommended).

---

## Project structure

```
app/
  layout.jsx            Root layout — fonts, metadata, persistent Navbar/Footer
  globals.css           Tailwind layers + bespoke utilities (glass, gradient text)
  page.jsx              "/"      — stacks the 5 homepage sections
  about/page.jsx        "/about" — stacks the 3 about sections

components/
  layout/
    Navbar.jsx           Fixed nav that frosts-in on scroll (+ mobile sheet)
    Footer.jsx           Structured footer
  ui/
    Button.jsx           Primary (filled) + secondary (chevron) CTA buttons
    GlassCard.jsx        The reusable frosted-glass "node" surface
    SectionLabel.jsx     The uppercase eyebrow/kicker label
  home/
    Hero.jsx             ★ Section 1 — cinematic hero (gradient headline, glow)
    CoreMetrics.jsx        Section 2 — live count-up metrics
    ArchitectureReveal.jsx ★ Section 3 — scroll-driven "task bursts into nodes"
    HardwareShowcase.jsx   Section 4 — device outlines grid
    CallToAction.jsx       Section 5 — terminal command + beta signup
  about/
    Vision.jsx           Section 1 — asymmetric editorial opener
    CorePillars.jsx      Section 2 — Rust/Go/Python bento grid
    TeamGrid.jsx         ★ Section 3 — co-founder profile grid

hooks/
  useCountUp.js          Scroll-triggered animated number counter

lib/
  data.js                ALL site content/copy/numbers (edit here, not in JSX)
  motion.js              Shared Framer Motion springs + variants (the "feel")

tailwind.config.js       The design system: colors, type scale, glow shadows
```

★ = the two flagship deliverables (Homepage Hero + Architecture, About Team grid).

---

## Where to customize

| You want to change…              | Edit…                                        |
| -------------------------------- | -------------------------------------------- |
| Headlines, metrics, team, copy   | `lib/data.js`                                |
| Colors, glow, type sizes         | `tailwind.config.js`                         |
| Animation feel (springs/timing)  | `lib/motion.js`                              |
| Add a real founder photo         | `lib/data.js` → set `image: "/team/x.jpg"`   |
| Glass / gradient-text recipe     | `app/globals.css`                            |

---

## Reading the code

Every file is heavily commented in three tiers so it doubles as a teaching
reference:

- **State Management** — what React/Framer state exists and why.
- **Layout / Styling Architecture** — the reasoning behind specific Tailwind
  utility choices.
- **Motion Layer** — the animation physics (spring stiffness/damping) and the
  scroll-progress → visual-property mappings.

Start with `lib/motion.js` (the animation vocabulary), then read
`components/home/Hero.jsx` and `components/home/ArchitectureReveal.jsx` — they
demonstrate every pattern used elsewhere.

---

## Accessibility & performance notes

- Respects `prefers-reduced-motion` (see `globals.css`) — all motion collapses
  for users who request reduced motion.
- The heavy scroll choreography in `ArchitectureReveal` only runs on `md+`;
  phones get a clean static stack of the same cards.
- Animations use `whileInView` with `once: true`, so they play a single time and
  never thrash on scroll-back.
- Counters animate a Framer `motionValue` (off the React render loop) and only
  commit a new string to state when the visible text actually changes.

> This is a front-end UI shell. The beta form and copy-command are wired for
> interaction but have no backend — search for `POST to` in `CallToAction.jsx`
> for the integration point.

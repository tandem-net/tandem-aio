import React, { useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import { View, Text, StyleSheet } from 'react-native';

// ---------------------------------------------------------------------------
// Frame / animation config
// ---------------------------------------------------------------------------
const FRAME_FOLDER = '/frames_webp';
const FRAME_EXT = '.webp';
const FRAME_COUNT = 560;
const ANIMATION_HEIGHT_VH = 1120; // total scroll length of the pinned stage

const PRELOAD_AHEAD = 40;
const PRELOAD_BEHIND = 10;
const NAV_HEIGHT = 80;

const pad = (n) => String(n).padStart(4, '0');
const frameUrl = (i) => `${FRAME_FOLDER}/frame_${pad(i)}${FRAME_EXT}`;
const reducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------------------------------------------------------------------------
// Design tokens
// ---------------------------------------------------------------------------
const theme = {
  color: {
    bg: '#05060a',
    bgAlt: '#0a0c12',
    textPrimary: '#F5F5F7',
    textSecondary: 'rgba(245,245,247,0.62)',
    textTertiary: 'rgba(245,245,247,0.4)',
    accent: '#CBB989',
    hairline: 'rgba(255,255,255,0.1)',
    glass: 'rgba(255,255,255,0.05)',
  },
  font: {
    display:
      "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif",
    text:
      "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif",
  },
};

// ---------------------------------------------------------------------------
// Scroll-triggered narrative copy, anchored to frames in the pinned stage.
// Adjust `frame` once you can see the real render — these approximate the
// three scrollbar-position screenshots (~30% / 55% / 78% through 560 frames).
// ---------------------------------------------------------------------------
const FADE_FRAMES = 30;
const HOLD_FRAMES = 40;
const HERO_FADE_END = 80; // hero is gone by this frame, well before the coordinator blurb starts fading in

const SECTIONS = [
  {
    key: 'coordinator',
    frame: 168,
    fadeFrames: 28,
    holdFrames: 34,
    eyebrow: '01 — The Server',
    title: 'The Coordinator',
    body: 'A lightweight coordinator keeps every node in sync — routing queries, watching health, and keeping data consistent across the network.',
  },
  {
    key: 'cli',
    frame: 340,
    fadeFrames: 40,
    holdFrames: 44,
    eyebrow: '02 — CLI',
    title: 'One Command Away',
    body: 'Talk to your cluster with a single command-line tool. Deploy, query, and monitor all from your terminal',
  },
  {
    key: 'nodes',
    frame: 500,
    fadeFrames: 32,
    holdFrames: 90,
    eyebrow: '03 — Network',
    title: 'Add Your Node',
    body: 'Turn a spare machine into part of the network. Install the client, join the pool, and start sharing storage and computing power',
  },
];

function sectionOpacity(frame, section) {
  const dist = Math.abs(frame - section.frame);
  const holdFrames = section.holdFrames ?? HOLD_FRAMES;
  const fadeFrames = section.fadeFrames ?? FADE_FRAMES;
  const halfHold = holdFrames / 2;
  if (dist <= halfHold) return 1;
  const fadeDist = dist - halfHold;
  if (fadeDist >= fadeFrames) return 0;
  return 1 - fadeDist / fadeFrames;
}

function heroOpacity(frame) {
  if (frame <= 1) return 1;
  if (frame >= HERO_FADE_END) return 0;
  return 1 - (frame - 1) / (HERO_FADE_END - 1);
}

// ---------------------------------------------------------------------------
// Founders — placeholders. Swap in real names, roles, photos, and GitHub
// links whenever you have them; the empty `github: '#'` hrefs are ready to go.
// ---------------------------------------------------------------------------
const FOUNDERS = [
  { name: 'Wissam Nusiar', role: 'Server', github: 'https://github.com/wnusair' },
  { name: 'Aryan Chaudhuri', role: 'Frontend', github: 'https://github.com/SwordedCat' },
  { name: 'Shamgar David', role: 'CLI', github: 'https://github.com/MrPlankton611' },
  { name: 'Ethan Yao', role: 'Nodes', github: 'https://github.com/P3nguinMinecraft' },
  { name: 'Robel Yoseph', role: 'Frontend', github: 'https://github.com/RobelMessi' },
  { name: 'Vishal Ambatipudi', role: 'Frontend', github: 'https://github.com/Squash882' },
];

// ---------------------------------------------------------------------------
// Small inline icons
// ---------------------------------------------------------------------------
function GitHubIcon(props) {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 .5C5.73.5.5 5.73.5 12c0 5.09 3.29 9.4 7.86 10.93.58.1.79-.25.79-.56 0-.27-.01-1.17-.02-2.12-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.72.08-.7.08-.7 1.15.08 1.76 1.19 1.76 1.19 1.03 1.75 2.7 1.25 3.36.96.1-.75.4-1.25.73-1.54-2.56-.29-5.25-1.28-5.25-5.72 0-1.26.45-2.29 1.19-3.09-.12-.29-.52-1.47.11-3.06 0 0 .97-.31 3.18 1.18a11.1 11.1 0 0 1 5.79 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.24 2.77.12 3.06.74.8 1.19 1.83 1.19 3.09 0 4.45-2.7 5.42-5.27 5.71.42.36.78 1.07.78 2.16 0 1.56-.01 2.82-.01 3.2 0 .31.21.67.8.56A10.98 10.98 0 0 0 23.5 12C23.5 5.73 18.27.5 12 .5Z" />
    </svg>
  );
}

function DownloadIcon(props) {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 3v12" />
      <path d="M6.5 11.5 12 17l5.5-5.5" />
      <path d="M4 21h16" />
    </svg>
  );
}

function CameraIcon(props) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1Z" />
      <circle cx="12" cy="13.5" r="3.4" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Navbar
// ---------------------------------------------------------------------------
function Navbar({ onNavigate }) {
  const links = [
    { key: 'overview', label: 'Overview' },
    { key: 'coordinator', label: 'Coordinator' },
    { key: 'cli', label: 'CLI' },
    { key: 'nodes', label: 'Nodes' },
    { key: 'team', label: 'Team' },
  ];
  return (
    <nav className="tandem-navbar">
      <div className="tandem-navbar-inner">
        <button className="tandem-logo" onClick={() => onNavigate('overview')}>
          Tandem
        </button>
        <div className="tandem-nav-right">
          {links.map((l) => (
            <button
              key={l.key}
              className="tandem-nav-link"
              onClick={() => onNavigate(l.key)}
            >
              {l.label}
            </button>
          ))}
          <button className="tandem-nav-cta" onClick={() => onNavigate('overview')}>
            Download
          </button>
        </div>
      </div>
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Hero — now lives *inside* the pinned stage, laid over frame 1. It's at
// full opacity at the very top of the page and fades out over the first
// stretch of scroll (see HERO_FADE_END), clearing the way for the
// coordinator/CLI/nodes narrative that follows.
// ---------------------------------------------------------------------------
function Hero({ heroRef }) {
  return (
    <View style={styles.heroOverlay} nativeID="overview" ref={heroRef}>
      <View style={styles.heroContent}>
        <Text style={styles.heroEyebrow}>DISTRIBUTED · OPEN SOURCE</Text>
        <Text style={styles.heroTitle}>Tandem</Text>
        <Text style={styles.heroTagline}>
          A database built from the computers you already have.
        </Text>
        <Text style={styles.heroBody}>
          Tandem pools storage and compute across a network of everyday
          machines — your own, or ones you trust — as a cheaper, more open
          alternative to large-scale managed databases.
        </Text>
        <button className="tandem-download-btn">
          <DownloadIcon />
          Download Tandem
        </button>
        <Text style={styles.heroSubtext}>macOS · Linux · Windows</Text>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Pinned animation stage: a tall (ANIMATION_HEIGHT_VH) relative container
// with a sticky inner layer. The sticky layer pins to the viewport for the
// full scroll of its parent, then scrolls away naturally once the parent
// ends — which is what lets normal content pick up right after it. The hero
// sits in this same sticky layer so it's stacked directly over frame 1.
// ---------------------------------------------------------------------------
function AnimationStage({ stageRef, canvasRef, heroRef, narrativeRefs }) {
  return (
    <View style={styles.animationStage} nativeID="animation-stage" ref={stageRef}>
      <View style={styles.stickyLayer}>
        <View style={styles.backgroundContainer} pointerEvents="none">
          <canvas ref={canvasRef} style={styles.backgroundCanvas} />
          <View style={styles.backgroundOverlay} pointerEvents="none" />
        </View>

        <Hero heroRef={heroRef} />

        <View style={styles.narrativeLayer} pointerEvents="none">
          {SECTIONS.map((section, i) => {
            const sectionClass = `tandem-narrative-item tandem-narrative-item--${section.key}`;
            return (
              <div
                key={section.key}
                nativeID={section.key}
                ref={(el) => (narrativeRefs.current[i] = el)}
                className={sectionClass}
              >
                <div className="tandem-narrative-copy">
                  <span className="tandem-narrative-eyebrow">{section.eyebrow}</span>
                  <span className="tandem-narrative-title">{section.title}</span>
                  <span className="tandem-narrative-body">{section.body}</span>
                </div>
              </div>
            );
          })}
        </View>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Open source callout
// ---------------------------------------------------------------------------
function OpenSourceSection() {
  return (
    <View style={styles.openSource} nativeID="open-source">
      <Text style={styles.sectionEyebrow}>OPEN SOURCE</Text>
      <Text style={styles.sectionTitle}>Built in the open</Text>
      <Text style={styles.openSourceBody}>
        The coordinator, the CLI, and the node client are all open source.
        Read the code, run your own network, complete tasks for free.
      </Text>
      <a className="tandem-outline-btn" href="https://github.com/tandem-net/tandem-aio" target="_blank" rel="noreferrer">
        <GitHubIcon />
        View on GitHub
      </a>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Founders / team
// ---------------------------------------------------------------------------
function TeamSection() {
  return (
    <View style={styles.team} nativeID="team">
      <Text style={styles.sectionEyebrow}>TEAM</Text>
      <Text style={styles.sectionTitle}>Built by six people</Text>
      <div className="tandem-founder-grid">
        {FOUNDERS.map((f) => (
          <div className="tandem-founder-card" key={f.name}>
            <div className="tandem-founder-photo">
              <CameraIcon />
            </div>
            <span className="tandem-founder-name">{f.name}</span>
            <span className="tandem-founder-role">{f.role}</span>
            <a
              className="tandem-founder-github"
              href={f.github}
              target="_blank"
              rel="noreferrer"
            >
              <GitHubIcon />
              GitHub
            </a>
          </div>
        ))}
      </div>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Footer
// ---------------------------------------------------------------------------
function Footer({ onNavigate }) {
  const year = new Date().getFullYear();
  return (
    <View style={styles.footer}>
      <div className="tandem-footer-inner">
        <div className="tandem-footer-col">
          <span className="tandem-logo tandem-footer-logo">Tandem</span>
          <span className="tandem-footer-tagline">
            A database built from the computers you already have.
          </span>
        </div>

        <div className="tandem-footer-col">
          <span className="tandem-footer-heading">Site</span>
          <button className="tandem-footer-link" onClick={() => onNavigate('overview')}>Overview</button>
          <button className="tandem-footer-link" onClick={() => onNavigate('coordinator')}>Coordinator</button>
          <button className="tandem-footer-link" onClick={() => onNavigate('cli')}>CLI</button>
          <button className="tandem-footer-link" onClick={() => onNavigate('nodes')}>Nodes</button>
          <button className="tandem-footer-link" onClick={() => onNavigate('team')}>Team</button>
        </div>

        <div className="tandem-footer-col">
          <span className="tandem-footer-heading">Project</span>
          <a className="tandem-footer-link" href="#" target="_blank" rel="noreferrer">GitHub</a>
          <span className="tandem-footer-link tandem-footer-static">Open source · MIT License</span>
        </div>
      </div>

      <div className="tandem-footer-bottom">
        <span>© {year} Tandem. All rights reserved.</span>
      </div>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Main App
// ---------------------------------------------------------------------------
function App() {
  const canvasRef = useRef(null);
  const stageRef = useRef(null);
  const heroRef = useRef(null);
  const cacheRef = useRef(new Map());
  const loadingRef = useRef(new Set());
  const currentRef = useRef(1);
  const rafRef = useRef(0);
  const narrativeRefs = useRef([]);

  const loadBitmap = async (index) => {
    if (index < 1 || index > FRAME_COUNT) return null;
    const cache = cacheRef.current;
    if (cache.has(index)) return cache.get(index);
    if (loadingRef.current.has(index)) return null;
    loadingRef.current.add(index);
    try {
      const res = await fetch(frameUrl(index), { cache: 'force-cache' });
      const blob = await res.blob();
      const bitmap = await createImageBitmap(blob);
      cache.set(index, bitmap);
      return bitmap;
    } catch (e) {
      return null;
    } finally {
      loadingRef.current.delete(index);
    }
  };

  const ensureWindow = (center) => {
    const start = Math.max(1, center - PRELOAD_BEHIND);
    const end = Math.min(FRAME_COUNT, center + PRELOAD_AHEAD);
    for (let i = start; i <= end; i++) loadBitmap(i);

    for (const k of Array.from(cacheRef.current.keys())) {
      if (k < start - 20 || k > end + 20) {
        const b = cacheRef.current.get(k);
        if (b && b.close) try { b.close(); } catch (e) {}
        cacheRef.current.delete(k);
      }
    }
  };

  // Progress is measured against the pinned stage's own scroll range, not
  // the whole document — so content added before/after it doesn't affect
  // playback speed.
  const getStageMetrics = () => {
    const el = stageRef.current;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    const containerTop = rect.top + window.scrollY;
    const containerHeight = el.offsetHeight;
    const viewportHeight = window.innerHeight;
    const scrollableRange = Math.max(containerHeight - viewportHeight, 1);
    return { containerTop, scrollableRange };
  };

  const computeFrame = () => {
    const metrics = getStageMetrics();
    if (!metrics) return currentRef.current;
    const scrolled = window.scrollY - metrics.containerTop;
    const progress = Math.min(1, Math.max(0, scrolled / metrics.scrollableRange));
    const idx = Math.round(progress * (FRAME_COUNT - 1)) + 1;
    return Math.min(FRAME_COUNT, Math.max(1, idx));
  };

  const drawToCanvas = (bitmap) => {
    const canvas = canvasRef.current;
    if (!canvas || !bitmap) return;
    const ctx = canvas.getContext('2d');
    const cw = canvas.width;
    const ch = canvas.height;
    const iw = bitmap.width;
    const ih = bitmap.height;

    const canvasRatio = cw / ch;
    const imageRatio = iw / ih;
    let sx = 0, sy = 0, sw = iw, sh = ih;
    if (imageRatio > canvasRatio) {
      sw = Math.round(ih * canvasRatio);
      sx = Math.round((iw - sw) / 2);
    } else {
      sh = Math.round(iw / canvasRatio);
      sy = Math.round((ih - sh) / 2);
    }

    ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(bitmap, sx, sy, sw, sh, 0, 0, cw, ch);
  };

  const updateOverlays = (frame) => {
    const heroEl = heroRef.current;
    if (heroEl) {
      const opacity = heroOpacity(frame);
      heroEl.style.opacity = String(opacity);
      heroEl.style.pointerEvents = opacity > 0.05 ? 'auto' : 'none';
    }

    SECTIONS.forEach((section, i) => {
      const el = narrativeRefs.current[i];
      if (!el) return;
      const opacity = sectionOpacity(frame, section);
      el.style.opacity = String(opacity);
      el.style.transform = `translateY(${(1 - opacity) * 10}px)`;
      el.style.pointerEvents = opacity > 0.05 ? 'auto' : 'none';
    });
  };

  // Click-to-scroll nav. "overview" and "team" jump to real DOM sections;
  // "coordinator" / "cli" / "nodes" jump to the scroll offset inside the
  // pinned stage where that narrative frame is centered.
  const handleNavigate = (key) => {
    const behavior = reducedMotion() ? 'auto' : 'smooth';

    if (key === 'overview') {
      window.scrollTo({ top: 0, behavior });
      return;
    }

    const frameSection = SECTIONS.find((s) => s.key === key);

    if (frameSection) {
      const metrics = getStageMetrics();
      if (!metrics) return;
      const progress = (frameSection.frame - 1) / (FRAME_COUNT - 1);
      const target = metrics.containerTop + progress * metrics.scrollableRange - NAV_HEIGHT;
      window.scrollTo({ top: target, behavior });
      return;
    }

    const el = document.getElementById(key);
    if (el) {
      const top = el.getBoundingClientRect().top + window.scrollY - NAV_HEIGHT;
      window.scrollTo({ top, behavior });
    }
  };

  useEffect(() => {
    const resize = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const tick = async () => {
      const idx = computeFrame();
      currentRef.current = idx;
      ensureWindow(idx);
      const bmp = cacheRef.current.get(idx);
      if (bmp) drawToCanvas(bmp);
      updateOverlays(idx);
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <View style={styles.appContainer}>
      <Navbar onNavigate={handleNavigate} />
      <AnimationStage
        stageRef={stageRef}
        canvasRef={canvasRef}
        heroRef={heroRef}
        narrativeRefs={narrativeRefs}
      />
      <OpenSourceSection />
      <TeamSection />
      <Footer onNavigate={handleNavigate} />
      <GlobalStyle />
    </View>
  );
}

// ---------------------------------------------------------------------------
// Global CSS — hover states, blur, grid, and things RN StyleSheet can't do.
// ---------------------------------------------------------------------------
function GlobalStyle() {
  return (
    <style>{`
      html, body { background: ${theme.color.bg}; margin: 0; padding: 0; }
      * { box-sizing: border-box; }
      [id] { scroll-margin-top: ${NAV_HEIGHT + 8}px; }

      .tandem-navbar {
        position: fixed;
        top: 0; left: 0; right: 0;
        z-index: 30;
        background: rgba(5,6,10,0.72);
        backdrop-filter: saturate(180%) blur(16px);
        -webkit-backdrop-filter: saturate(180%) blur(16px);
        border-bottom: 1px solid ${theme.color.hairline};
      }
      .tandem-navbar-inner {
        max-width: 1600px;
        margin: 0 auto;
        height: ${NAV_HEIGHT}px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 22px;
      }
      .tandem-logo {
        font-family: ${theme.font.display};
        font-size: 15px;
        font-weight: 600;
        letter-spacing: -0.2px;
        color: ${theme.color.textPrimary};
        background: none;
        border: none;
        cursor: pointer;
        padding: 0;
      }
      .tandem-nav-right {
        display: flex;
        align-items: center;
        gap: 26px;
      }
      .tandem-nav-link {
        font-family: ${theme.font.text};
        font-size: 12.5px;
        font-weight: 400;
        color: ${theme.color.textSecondary};
        background: none;
        border: none;
        cursor: pointer;
        padding: 0;
        transition: color 0.2s ease;
      }
      .tandem-nav-link:hover { color: ${theme.color.textPrimary}; }
      .tandem-nav-cta {
        font-family: ${theme.font.text};
        font-size: 12.5px;
        font-weight: 500;
        color: ${theme.color.bg};
        background: ${theme.color.textPrimary};
        border: none;
        border-radius: 980px;
        padding: 7px 16px;
        cursor: pointer;
        transition: opacity 0.2s ease, transform 0.2s ease;
      }
      .tandem-nav-cta:hover { opacity: 0.85; }
      .tandem-nav-cta:active { transform: scale(0.97); }

      .tandem-download-btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-family: ${theme.font.text};
        font-size: 16px;
        font-weight: 500;
        color: ${theme.color.bg};
        background: ${theme.color.textPrimary};
        border: none;
        border-radius: 980px;
        padding: 13px 26px;
        cursor: pointer;
        box-shadow: 0 8px 30px rgba(0,0,0,0.35);
        transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
      }
      .tandem-download-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 36px rgba(0,0,0,0.45);
        opacity: 0.92;
      }
      .tandem-download-btn:active { transform: translateY(0) scale(0.98); }

      .tandem-outline-btn {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-family: ${theme.font.text};
        font-size: 14px;
        font-weight: 500;
        color: ${theme.color.textPrimary};
        background: transparent;
        border: 1px solid ${theme.color.hairline};
        border-radius: 980px;
        padding: 10px 20px;
        cursor: pointer;
        text-decoration: none;
        transition: border-color 0.2s ease, background 0.2s ease;
      }
      .tandem-outline-btn:hover {
        border-color: rgba(255,255,255,0.3);
        background: ${theme.color.glass};
      }

      /* Base layout for every mapped section block */
      .tandem-narrative-item {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: min(360px, 70vw);
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: 8px;
        opacity: 0;
        transition: transform 0.1s linear;
      }
      /* Controls the text wrapper alignment for the mapped section copy */
      .tandem-narrative-copy {
        display: flex;
        flex-direction: column;
        align-items: inherit;
        text-align: inherit;
        gap: 8px;
        width: 100%;
      }
      /* Coordinator-specific layout and text controls */
      .tandem-narrative-item--coordinator {
        /* tweak this block only */
      }
      .tandem-narrative-item--coordinator .tandem-narrative-eyebrow {
        font-size: 20px;
      }
      .tandem-narrative-item--coordinator .tandem-narrative-title {
        font-size: 45px;
      }
      .tandem-narrative-item--coordinator .tandem-narrative-body {
        font-size: 16px;
        line-height: 1.5;
      }
      /* CLI-specific layout and text controls */
      .tandem-narrative-item--cli {
        width: min(630px, 78vw);
        left: calc(50% - 120px);
        transform: translate(0, -50%);
        align-items: flex-start;
        text-align: left;
      }
      .tandem-narrative-item--cli .tandem-narrative-copy {
        max-width: 620px;
      }
      .tandem-narrative-item--cli .tandem-narrative-eyebrow {
        font-size: 20px;
      }
      .tandem-narrative-item--cli .tandem-narrative-title {
        font-size: 60px;
      }
      .tandem-narrative-item--cli .tandem-narrative-body {
        font-size: 20px;
        line-height: 1.6;
      }
      /* Nodes-specific layout and text controls */
      .tandem-narrative-item--nodes {
        /* tweak this block only */
      }
      .tandem-narrative-item--nodes .tandem-narrative-eyebrow {
        font-size: 20px;
      }
      .tandem-narrative-item--nodes .tandem-narrative-title {
        font-size: 50px;
      }
      .tandem-narrative-item--nodes .tandem-narrative-body {
        font-size: 18px;
        line-height: 1.5;
      }
      /* Shared eyebrow font styling for all mapped sections */
      .tandem-narrative-eyebrow {
        font-family: ${theme.font.text};
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.2px;
        color: ${theme.color.accent};
        text-transform: uppercase;
      }
      /* Controls the title font size for all mapped sections */
      .tandem-narrative-title {
        font-family: ${theme.font.display};
        font-size: 24px;
        font-weight: 600;
        letter-spacing: -0.3px;
        color: ${theme.color.textPrimary};
      }
      /* Controls the body font size for all mapped sections */
      .tandem-narrative-body {
        font-family: ${theme.font.text};
        font-size: 14.5px;
        line-height: 1.5;
        color: ${theme.color.textSecondary};
      }

      .tandem-founder-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 20px;
        width: 100%;
        max-width: 1000px;
        margin-top: 44px;
      }
      .tandem-founder-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        gap: 6px;
        padding: 32px 20px 26px;
        background: ${theme.color.glass};
        border: 1px solid ${theme.color.hairline};
        border-radius: 16px;
        transition: border-color 0.2s ease, transform 0.2s ease;
      }
      .tandem-founder-card:hover {
        border-color: rgba(255,255,255,0.22);
        transform: translateY(-2px);
      }
      .tandem-founder-photo {
        width: 84px;
        height: 84px;
        border-radius: 50%;
        border: 1px dashed rgba(255,255,255,0.22);
        display: flex;
        align-items: center;
        justify-content: center;
        color: ${theme.color.textTertiary};
        margin-bottom: 14px;
      }
      .tandem-founder-name {
        font-family: ${theme.font.display};
        font-size: 16px;
        font-weight: 600;
        color: ${theme.color.textPrimary};
      }
      .tandem-founder-role {
        font-family: ${theme.font.text};
        font-size: 13px;
        color: ${theme.color.textSecondary};
        margin-bottom: 16px;
      }
      .tandem-founder-github {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        font-family: ${theme.font.text};
        font-size: 12.5px;
        font-weight: 500;
        color: ${theme.color.textPrimary};
        text-decoration: none;
        border: 1px solid ${theme.color.hairline};
        border-radius: 980px;
        padding: 7px 14px;
        transition: border-color 0.2s ease, background 0.2s ease;
      }
      .tandem-founder-github:hover {
        border-color: rgba(255,255,255,0.3);
        background: rgba(255,255,255,0.08);
      }

      .tandem-footer-inner {
        max-width: 1100px;
        margin: 0 auto;
        display: grid;
        grid-template-columns: 1.4fr 1fr 1fr;
        gap: 32px;
        padding: 56px 24px 40px;
      }
      .tandem-footer-col {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .tandem-footer-logo { font-size: 16px; cursor: default; }
      .tandem-footer-tagline {
        font-family: ${theme.font.text};
        font-size: 13px;
        color: ${theme.color.textTertiary};
        max-width: 260px;
        line-height: 1.5;
      }
      .tandem-footer-heading {
        font-family: ${theme.font.text};
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        color: ${theme.color.textTertiary};
        margin-bottom: 4px;
      }
      .tandem-footer-link {
        font-family: ${theme.font.text};
        font-size: 13px;
        color: ${theme.color.textSecondary};
        background: none;
        border: none;
        text-align: left;
        text-decoration: none;
        cursor: pointer;
        padding: 0;
        width: fit-content;
        transition: color 0.2s ease;
      }
      .tandem-footer-link:hover { color: ${theme.color.textPrimary}; }
      .tandem-footer-static { cursor: default; }
      .tandem-footer-static:hover { color: ${theme.color.textSecondary}; }

      .tandem-footer-bottom {
        border-top: 1px solid ${theme.color.hairline};
        padding: 18px 24px 28px;
        text-align: center;
        font-family: ${theme.font.text};
        font-size: 12px;
        color: ${theme.color.textTertiary};
      }

      @media (max-width: 860px) {
        .tandem-founder-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .tandem-footer-inner { grid-template-columns: 1fr 1fr; }
      }
      @media (max-width: 640px) {
        .tandem-nav-right { gap: 14px; }
        .tandem-nav-link:not(.tandem-nav-cta) { display: none; }
        .tandem-narrative-title { font-size: 20px; }
        .tandem-narrative-body { font-size: 13.5px; }
        .tandem-founder-grid { grid-template-columns: 1fr; }
        .tandem-footer-inner { grid-template-columns: 1fr; }
      }
    `}</style>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------
const styles = StyleSheet.create({
  appContainer: {
    backgroundColor: theme.color.bg,
  },

  // Hero — absolutely positioned inside the sticky layer, stacked over
  // frame 1. Fades out as scroll begins (see heroOpacity/HERO_FADE_END).
  heroOverlay: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    zIndex: 3,
    paddingTop: 180,
    paddingHorizontal: 24,
    paddingBottom: 60,
    alignItems: 'center',
    justifyContent: 'flex-start',
  },
  heroContent: {
    width: '100%',
    maxWidth: 660,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroEyebrow: {
    fontFamily: theme.font.text,
    fontSize: 11, // changes the hero eyebrow text size
    fontWeight: '600',
    letterSpacing: 1.4,
    color: theme.color.accent,
    marginBottom: 18,
  },
  heroTitle: {
    fontFamily: theme.font.display,
    fontSize: 'clamp(48px, 9vw, 92px)', // changes the hero title text size
    fontWeight: '700',
    letterSpacing: -2,
    color: theme.color.textPrimary,
    marginBottom: 14,
    textAlign: 'center',
  },
  heroTagline: {
    fontFamily: theme.font.display,
    fontSize: 'clamp(18px, 2.6vw, 26px)', // changes the hero tagline text size
    fontWeight: '500',
    letterSpacing: -0.3,
    color: theme.color.textPrimary,
    textAlign: 'center',
    maxWidth: 620,
    marginBottom: 18,
  },
  heroBody: {
    fontFamily: theme.font.text,
    fontSize: 16, // changes the hero body text size
    lineHeight: 26,
    fontWeight: '400',
    color: theme.color.textSecondary,
    textAlign: 'center',
    maxWidth: 480,
    marginBottom: 34,
  },
  heroSubtext: {
    fontFamily: theme.font.text,
    fontSize: 12, // changes the hero subtext size
    fontWeight: '400',
    color: theme.color.textTertiary,
    marginTop: 14,
    letterSpacing: 0.2,
  },

  // Animation stage
  animationStage: {
    position: 'relative',
    height: `${ANIMATION_HEIGHT_VH}vh`,
  },
  stickyLayer: {
    position: 'sticky',
    top: 0,
    height: '100vh',
    overflow: 'hidden',
  },
  backgroundContainer: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    overflow: 'hidden',
    backgroundColor: theme.color.bg,
  },
  backgroundCanvas: {
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    opacity: 0.98,
  },
  backgroundOverlay: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.16)',
  },
  narrativeLayer: {
    position: 'absolute',
    top: 0, left: 0, right: 345 , bottom: 140,
    zIndex: 2,
    backgroundColor: 'transparent',
  },

  // Open source
  openSource: {
    position: 'relative',
    zIndex: 1,
    backgroundColor: theme.color.bg,
    alignItems: 'center',
    paddingVertical: 120,
    paddingHorizontal: 24,
  },
  sectionEyebrow: {
    fontFamily: theme.font.text,
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 1.4,
    color: theme.color.accent,
    marginBottom: 14,
  },
  sectionTitle: {
    fontFamily: theme.font.display,
    fontSize: 'clamp(28px, 4vw, 40px)',
    fontWeight: '700',
    letterSpacing: -0.8,
    color: theme.color.textPrimary,
    textAlign: 'center',
    marginBottom: 16,
  },
  openSourceBody: {
    fontFamily: theme.font.text,
    fontSize: 16,
    lineHeight: 25,
    color: theme.color.textSecondary,
    textAlign: 'center',
    maxWidth: 460,
    marginBottom: 28,
  },

  // Team
  team: {
    position: 'relative',
    zIndex: 1,
    backgroundColor: theme.color.bgAlt,
    alignItems: 'center',
    paddingVertical: 120,
    paddingHorizontal: 24,
    borderTopWidth: 1,
    borderTopColor: theme.color.hairline,
  },

  // Footer
  footer: {
    position: 'relative',
    zIndex: 1,
    backgroundColor: theme.color.bg,
    borderTopWidth: 1,
    borderTopColor: theme.color.hairline,
  },
});

const root = createRoot(document.getElementById('root'));
root.render(<App />);
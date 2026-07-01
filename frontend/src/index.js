import React, { useEffect, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import { View, Text, StyleSheet } from 'react-native';

const FRAME_FOLDER = '/frames';
const FRAME_COUNT = 200;
const SCROLL_MULTIPLIER = 1.5;

const formatFrame = (value) => String(value).padStart(4, '0');
const getFrameUrl = (frameNumber) => `${FRAME_FOLDER}/frame_${formatFrame(frameNumber)}.png`;

function App() {
  const imageRef = useRef(null);
  const currentFrameRef = useRef(1);
  const lastFrameRef = useRef(0);
  const rafRef = useRef(0);

  const updateFrameFromScroll = () => {
    const scrollTop = window.scrollY;
    const documentHeight = document.documentElement.scrollHeight;
    const windowHeight = window.innerHeight;
    const maxScroll = Math.max(documentHeight - windowHeight, 1);
    const progress = Math.min(1, Math.max(0, scrollTop / maxScroll));
    const rawFrame = Math.round(progress * (FRAME_COUNT - 1)) + 1;
    currentFrameRef.current = Math.min(FRAME_COUNT, Math.max(1, rawFrame));
  };

  useEffect(() => {
    const tick = () => {
      updateFrameFromScroll();
      const image = imageRef.current;
      const nextFrame = currentFrameRef.current;

      if (image && nextFrame !== lastFrameRef.current) {
        image.src = getFrameUrl(nextFrame);
        lastFrameRef.current = nextFrame;
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  return (
    <View style={styles.appContainer}>
      <View style={styles.backgroundContainer} pointerEvents="none">
        <img ref={imageRef} alt="background frame" style={styles.backgroundImage} />
        <View style={styles.backgroundOverlay} pointerEvents="none" />
      </View>
      <View style={styles.contentContainer}>
        <Text style={styles.heading}>Scroll to scrub the background</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  appContainer: {
    flex: 1,
    minHeight: '400vh',
    backgroundColor: '#050814',
    color: '#ffffff',
  },
  contentContainer: {
    minHeight: '400vh',
    paddingTop: 80,
    paddingHorizontal: 24,
  },
  backgroundContainer: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: -1,
    overflow: 'hidden',
    backgroundColor: '#050814',
  },
  backgroundImage: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    opacity: 0.98,
    pointerEvents: 'none',
  },
  backgroundOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.14)',
  },
  heading: {
    fontSize: 38,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 24,
  },
});

const root = createRoot(document.getElementById('root'));
root.render(<App />);

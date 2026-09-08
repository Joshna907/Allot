export function mountHeroFlow(canvas) {
  if (!canvas) return () => {};

  // The canvas is decorative. Keep the page functional when animation is
  // unavailable or reduced motion is requested.
  canvas.setAttribute("aria-hidden", "true");
  return () => {};
}

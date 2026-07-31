// ambient.js — soft glow cursor ("the trace") + respects touch & reduced-motion
// Purely decorative visual layer. Does not read/write any app state
// and makes no calls into bridge.js — safe to include or remove independently.
(function () {
  const canUseFineCursor = window.matchMedia(
    "(hover: hover) and (pointer: fine)",
  ).matches;
  if (!canUseFineCursor) return; // leave native cursor + touch devices untouched

  const dot = document.getElementById("cursor-dot");
  const outline = document.getElementById("cursor-outline");
  const shadow = document.getElementById("cursor-shadow");
  if (!dot || !outline || !shadow) return;

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  let mouseX = window.innerWidth / 2;
  let mouseY = window.innerHeight / 2;
  let outlineX = mouseX,
    outlineY = mouseY;
  let shadowX = mouseX,
    shadowY = mouseY;

  window.addEventListener("mousemove", (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    dot.style.left = mouseX + "px";
    dot.style.top = mouseY + "px";
    shadow.style.opacity = "1";
  });

  function animate() {
    const outlineEase = prefersReducedMotion ? 1 : 0.18;
    const shadowEase = prefersReducedMotion ? 1 : 0.09;

    outlineX += (mouseX - outlineX) * outlineEase;
    outlineY += (mouseY - outlineY) * outlineEase;
    shadowX += (mouseX - shadowX) * shadowEase;
    shadowY += (mouseY - shadowY) * shadowEase;

    outline.style.left = outlineX + "px";
    outline.style.top = outlineY + "px";
    shadow.style.left = shadowX + "px";
    shadow.style.top = shadowY + "px";

    requestAnimationFrame(animate);
  }
  requestAnimationFrame(animate);

  // Grow "the trace" over anything interactive
  const hoverTargets =
    'button, a, [role="button"], .drop-zone, input, select, textarea';
  document.addEventListener("mouseover", (e) => {
    if (e.target.closest(hoverTargets))
      document.body.classList.add("cursor-hover");
  });
  document.addEventListener("mouseout", (e) => {
    if (e.target.closest(hoverTargets))
      document.body.classList.remove("cursor-hover");
  });
})();

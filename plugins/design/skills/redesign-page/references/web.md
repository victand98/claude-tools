# Web checks

Apply together with `baseline.md`. The project's rules win where they differ.

## Layout

- Content reflows at a width of 320 CSS px with no scrolling in two dimensions, except content that needs a
  two-dimensional layout, such as maps, diagrams, video and data tables (WCAG 1.4.10). This is the same as a 1280
  px window at 400% zoom.
- Text can be resized to 200% without loss of content or function (WCAG 1.4.4). Use relative units for type and
  spacing unless the project's tokens say otherwise.
- Use the breakpoints and layout primitives the project already uses (media queries, container queries, grid
  utilities). Do not introduce a second system.

## Input and focus

- Everything works with keyboard alone, in a logical order, with no keyboard trap.
- The focus indicator is visible and the focused element is not hidden behind sticky headers, banners or
  overlays (WCAG 2.4.7 and 2.4.11).
- Hover is never the only way to reveal anything. Touch, pointer and keyboard each have a path.
- Pointer targets are at least 24 by 24 CSS px, or have at least 24 px of space around them (WCAG 2.5.8, level AA).
  Use 44 px for touch-first controls.

## Semantics and system preferences

- Prefer native elements. Use ARIA only where no native element fits, and keep name, role and value correct.
- Honor `prefers-color-scheme`, `prefers-reduced-motion` and `prefers-contrast`, and check forced-colors mode
  when the project supports it.

## Verification

- Run the project's component, visual-regression and end-to-end tests at each frame width and theme.
- Run the project's automated accessibility check if it has one. Automated tools find only part of the issues,
  so also do a keyboard pass and a check at 200% text and 400% zoom.
- Report anything you could not check as unchecked, not as passing.

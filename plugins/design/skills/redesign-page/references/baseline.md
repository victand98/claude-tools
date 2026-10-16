# Baseline for every platform

The project's own documented rules win wherever they are stricter or different. Use this file for what the project
does not say.

## Layout and frames

Lay out by the space available to the app, never by device type or orientation. Space changes at runtime through
rotation, split screen, resizable windows and foldables, so every frame must still work when the window moves from
one size to another. Keep the same functionality at every size; change only how much is visible at once.

When the project defines no breakpoints, design these frames:

| Frame | Width | Notes |
|---|---|---|
| Compact | 360 | Phones in portrait. For web, also check 320 CSS px (reflow). |
| Medium | 600 | First width where a layout usually changes. |
| Expanded | 900 | Within the 840 to 1199 range. |
| Large | 1440 | Web and desktop only (1200 and up). |
| Compact height | 800 by 360 | Phone in landscape: height under 480, so two-pane layouts do not fit. |

These follow the window size classes in the Android adaptive guidance (compact under 600, medium 600 to 839,
expanded 840 to 1199, large 1200 to 1599, extra-large 1600 and up; height compact under 480, medium 480 to 899,
expanded 900 and up). Apple's size classes (compact and regular, per axis) say the same thing: decide from the
available space and consider every combination. Test the smallest and largest frames first.

Every frame is drawn in each theme the project supports, normally light and dark, and in a higher-contrast variant
when the project or platform has one.

## Accessibility baseline

WCAG 2.2 level AA is the baseline for web, native and hybrid apps, with these concrete checks:

- Text contrast is at least 4.5:1, or 3:1 for large text (18 pt, or 14 pt bold). Meaningful icons, graphics and
  control boundaries are at least 3:1. Check both light and dark themes.
- Text can be enlarged to at least 200% without loss of content or function. Test at the largest size the
  platform allows, not only at 200%.
- Information is never carried by color alone; add a shape, icon or text.
- Every interactive element has a clear name, role and state for assistive technology.
- Anything done by a gesture or hover can also be done by a plain tap, click or keyboard action.
- Motion respects the system reduce-motion setting; no autoplaying media without a control.
- Orientation is not locked unless it is essential.
- Target size minimums are in `web.md` and `mobile.md`.

Full AAA conformance is not a blanket target. Adopt individual AAA criteria when they are cheap, for example larger
touch targets, and say so in the plan.

## States and content

Draw and build, for each component: default, pressed, focused, disabled, selected and error where they apply, plus
hover on pointer platforms. For each screen: loading, empty, error and populated, with long text, large text and
right-to-left layout. A layout that clips or overlaps at large text is a defect; wrap or stack instead of
truncating, and never truncate meaning.

## Tokens

The project's token source is the single source of truth. Bind Figma variables to it and model themes as variable
modes. If the project has no token source, propose the W3C Design Tokens format (stable version 2025.10) and ask
before adding it; never convert an existing token format without being asked.

# Mobile checks (iOS, Android, cross-platform)

Apply together with `baseline.md`. The project's rules win where they differ. For a cross-platform framework such
as Flutter or React Native, meet the stricter value of each platform and follow each platform's conventions where
they differ.

## Layout

- Decide layout from the size class or window size, not from device type or orientation. Consider every
  combination, including a phone in landscape (wide but short) and an app resized in split screen, on iPad windows,
  on foldables and on resizable Android windows.
- Keep functionality the same as space changes. On wider windows, show more at once instead of removing features,
  for example a tab bar becoming a sidebar or navigation rail.
- Respect safe areas and system insets (notch, Dynamic Island, home indicator, system bars). Backgrounds and media
  may extend edge to edge; controls and text stay inside the safe area.
- Use the platform's standard margins and layout guides instead of hard-coded insets.

## Text

- Support the system text size setting: Dynamic Type on iOS, font scale on Android. Apple's guidance is to allow
  at least 200% enlargement; test at the largest accessibility sizes, not only the default ones.
- At large sizes, stack side-by-side elements, let rows grow in height, and wrap instead of truncating. Controls
  that cannot grow, such as tab bars, need another way to stay perceivable (iOS offers the Large Content Viewer).
- Defaults and minimums on iOS and iPadOS are 17 pt and 11 pt for custom type. Thin weights need larger sizes.
- Test long words, right-to-left layout and scripts with tall ascenders or diacritics.

## Touch

- Minimum control sizes: iOS and iPadOS default 44 by 44 pt (28 by 28 pt absolute minimum); Android 48 by 48 dp.
  Cross-platform apps use 48.
- Space controls apart: about 12 pt around controls with a bezel and about 24 pt around controls without one
  (Apple guidance).
- Every swipe or multi-finger gesture has an on-screen alternative.

## Assistive technology and system settings

- Label every control and meaningful image for VoiceOver and TalkBack, with the right role and state.
- Support external keyboards and switch input where the platform offers them.
- Honor reduce motion (replace large movement with fades), increase contrast and dark mode. Check contrast in both
  appearances.

## Verification

- Run the project's unit, widget and UI tests, plus screenshot or golden tests where it has them, at the smallest
  and largest frames, in each theme, at the largest text size, and in landscape.
- Check on a simulator or emulator, and on a real device when the project has one in its workflow: font scale at
  maximum, display zoom, split screen or resized window.
- Use the platform audit tools if available: Accessibility Inspector on iOS and Accessibility Scanner on Android.
- Report anything you could not check as unchecked, not as passing.

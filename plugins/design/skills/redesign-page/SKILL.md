---
name: redesign-page
description: Redesign or migrate a screen, page or flow onto the project's design system, Figma first, for web, iOS, Android or cross-platform apps. Use to restyle UI with the project's design tokens and components.
argument-hint: "[page name or route] [one-line goal]"
disable-model-invocation: true
---

Redesign `$ARGUMENTS` on this project's design system.

## Before anything

1. Confirm the Figma MCP connector is available (for example by calling `whoami`). If it is not, stop and tell the
   user to connect Figma first. This skill does not run without it.
2. Discover the project's conventions. Look for, and read, whichever of these exist: `DESIGN.md`, `CLAUDE.md`,
   `AGENTS.md`, `.claude/rules/`, a design tokens file or folder, a component catalog or storybook, and the Figma
   library link. Whatever the project documents about its design system always applies and wins over the
   references below where it is stricter or different. Follow it; do not restate it in the plan.
3. Detect the target platforms from the project (for example `package.json` or web markup for web, an Xcode project
   or SwiftUI for iOS, Gradle or Compose for Android, `pubspec.yaml`, React Native, Expo or Kotlin Multiplatform
   for cross-platform) and confirm them with the user.
4. Read, from the `references/` folder next to this file, `baseline.md` always, `web.md` when web is in scope and
   `mobile.md` when iOS, Android or a cross-platform mobile app is in scope.
5. Enter plan mode. If any of these is missing, ask in full sentences before continuing:
   - the goal for the user and what is wrong today
   - scope in and out, including the loading, empty, error and populated states
   - an existing Figma frame, or permission to design it in the library file
   - the acceptance checks
   - anything from steps 2 and 3 you could not find: the Figma library file, the target platforms, the breakpoints
     and themes to cover, the token source of truth, and the commands that verify the work (tests, lint, token
     checks, conformance checks)

## Process

1. List the catalog components that cover the page, what is missing, and the legacy widgets, styles and
   hardcoded values the page uses today.
2. Add each missing component to the Figma library first, with variants bound to variables and every interactive
   state the platform has. Use the `figma-use` and `figma-generate-library` skills.
3. Design the page in Figma at the project's breakpoints, or the defaults in `baseline.md` when it has none, in
   every theme it supports, composed only from library instances. Design the smallest and largest frames first,
   then the ones between. Use the `figma-generate-design` skill.
4. If a UX critique skill is available (for example `/ui-ux-pro-max`), run it on the frames for hierarchy,
   spacing, touch targets, states and accessibility. It advises only: tokens and styles come from the project's
   design system and token source.
5. Review the frames with the user. Raise concerns and options before the plan is approved.
6. Plan, then build from the approved frames. A new token or component changes the token source, the design
   system documentation and the Figma library in the same change.
7. Verify with the commands the project defines, in every touched module or package: tests, linter or analyzer on
   touched files, and any token generation, design-doc lint or conformance check the project has. Then run the
   verification checks in the platform references. After removing legacy usages, refresh the project's
   conformance baseline if it keeps one and update any migration status it tracks.

## Done when

- the built screen matches the approved Figma frames
- tests or screenshots cover every frame size and theme in scope, and the largest supported text size
- the accessibility baseline in `baseline.md` and the checks in the platform references pass, or each exception
  is listed for the user with a reason
- touched files pass the project's lint and follow its code conventions
- the work is in atomic commits; nothing is pushed unless the user asks

# Design Review Rubric — Industrial Web Apps

Use this after Playwright passes. The purpose is to prevent technically-correct but visually generic releases.

## 1. Visual system
- Restrained palette with one primary accent and neutral support colors.
- Clear typography hierarchy; technical labels may use monospace sparingly.
- Consistent spacing rhythm and grid alignment.
- Subtle borders/dividers instead of excessive cards and shadows.
- Avoid decorative graphics that do not help a decision or task.

## 2. Interaction quality
- Every interactive control has hover, active, disabled and keyboard-focus states.
- Transitions are short and purposeful; no animation should delay work.
- Primary and secondary actions are visually distinguishable.
- Progressive disclosure is preferred over showing every control at once.
- Back/navigation behavior is predictable.

## 3. Industrial usability
- Data density is high enough for engineering work but remains scannable.
- Important warnings, deviations and required actions use consistent callouts.
- Green/yellow/orange/red semantics are consistent and never the sole signal.
- Tables preserve readable headers and usable scrolling.
- Charts prioritize interpretation and action over decoration.
- Critical values are visible without excessive scrolling.

## 4. Responsive / field use
- Desktop is primary, but tablet and phone must not break.
- Sidebar/menu has a narrow-screen strategy.
- No horizontal overflow.
- Touch targets remain usable.
- Fixed headers never cover content.

## 5. Accessibility / legibility
- Focus-visible feedback is present.
- Contrast is sufficient for prolonged use.
- Text sizing avoids giant display type inside operational screens.
- Status is communicated with text/icon in addition to color.

## 6. Release decision
- PASS: functional QA passes and no critical visual/usability findings remain.
- PASS WITH OBSERVATIONS: only cosmetic or non-blocking findings remain.
- FAIL: broken flow, clipped/overlapped content, console errors, unusable responsive state, unclear status/action, or LKG regression.

## Reference pattern

The Facebook reference workflow emphasized:
1. Strong design rules rather than vague "make it pretty" prompts.
2. Better taste/reference material.
3. Browser-based validation after implementation.

Web QA Lab adopts the same principle but adapts it for internal industrial engineering applications: restrained visual identity, deterministic functional checks, browser inspection and release gating.

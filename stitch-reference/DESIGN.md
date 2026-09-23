---
name: Auralis System
colors:
  surface: '#fdf8f8'
  surface-dim: '#ddd9d8'
  surface-bright: '#fdf8f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f7f3f2'
  surface-container: '#f1edec'
  surface-container-high: '#ebe7e6'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1c1b1b'
  on-surface-variant: '#444748'
  inverse-surface: '#313030'
  inverse-on-surface: '#f4f0ef'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c8c6c5'
  secondary: '#5e5e5e'
  on-secondary: '#ffffff'
  secondary-container: '#e1dfdf'
  on-secondary-container: '#626262'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1d1b1a'
  on-tertiary-container: '#868381'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c8c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474646'
  secondary-fixed: '#e4e2e2'
  secondary-fixed-dim: '#c7c6c6'
  on-secondary-fixed: '#1b1c1c'
  on-secondary-fixed-variant: '#464747'
  tertiary-fixed: '#e6e1df'
  tertiary-fixed-dim: '#cac6c3'
  on-tertiary-fixed: '#1d1b1a'
  on-tertiary-fixed-variant: '#484645'
  background: '#fdf8f8'
  on-background: '#1c1b1b'
  surface-variant: '#e5e2e1'
typography:
  h1:
    fontFamily: Inter
    fontSize: 84px
    fontWeight: '600'
    lineHeight: '1.05'
    letterSpacing: -0.04em
  h2:
    fontFamily: Inter
    fontSize: 64px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.03em
  h3:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: '0'
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.1em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  max_width: 1280px
  columns: '12'
  gutter: 32px
  container_padding: 32px
  section_gap_min: 140px
  section_gap_max: 180px
  unit_base: 8px
---

## Brand & Style

The visual identity of this design system is rooted in "Engineered Softness." It is a premium, enterprise-grade aesthetic that balances technical precision with an approachable, editorial clarity. The target audience consists of high-level decision-makers and technical operators who value restrained sophistication over decorative excess.

The design style is a hybrid of **Minimalism** and **Tonal Layering**. It moves away from heavy shadows in favor of "mounted" UI components—elements that feel physically inset or layered through subtle shifts in neutral values. The mood is quiet, authoritative, and structured, evoking the feeling of high-end laboratory equipment or architectural blueprints. The inclusion of sparse, muted gradients provides a "technical soul," preventing the interface from feeling cold while maintaining a professional, institutional weight.

## Colors

The palette is a study in "Warm Neutrals" and "Cool Taupes." By utilizing a base of #F7F7F5, the interface avoids the sterile nature of pure white, opting instead for a soft, paper-like foundation. 

- **Primary Canvas:** The background (#F7F7F5) acts as the base plate.
- **Structural Layers:** Panels (#F3F2EF) create a recessed look, while White Cards (#FCFCFB) represent the highest interactive surface level.
- **Accents:** Muted coral, blue, and green gradients are never used as solid fills for large areas. Instead, they are applied as "Glows"—subtle blurs behind icons, thin indicator bars, or soft radial pulses that signify activity or system health.
- **Contrast:** Typography maintains a strict hierarchy with #111111 for high-readability headers and #6B6B6B for metadata and auxiliary labels.

## Typography

This design system utilizes **Inter** (representing the Geist aesthetic) to achieve a technical, geometric rhythm. The typography is highly editorial, favoring large-scale headlines with tight tracking to create a "dense" and impactful presence.

- **Headlines:** H1 and H2 should always be set with negative letter-spacing to emphasize the engineered, locked-in feel of the characters.
- **Body:** Standard body text is set at 16px or 18px with generous line heights to ensure readability within complex data environments.
- **Labels:** Small utility text utilizes uppercase styling with increased letter-spacing to provide clear distinction from narrative body text. 
- **Hierarchy:** Use weight, not just size, to define importance. Headers are consistently Semibold, while functional data is Regular.

## Layout & Spacing

The layout philosophy is a **Fixed-Modular Grid**. Content is constrained to a 1280px container to ensure a premium, centered viewing experience that feels curated rather than stretched.

- **Grid:** A strict 12-column structure with 32px gutters provides the "engine" for the UI. Elements should align precisely to these vertical lines.
- **Rhythm:** Section spacing is intentionally expansive (140px-180px). This "white space" is a key brand asset, elevating the content and signaling an enterprise-grade focus on clarity.
- **Incremental Spacing:** All internal component spacing (padding, margins) follows an 8px base unit. This ensures that even the most complex panels feel mathematically consistent and "mounted."

## Elevation & Depth

This design system rejects traditional drop shadows in favor of **Tonal Layering** and **Low-Contrast Outlines**. 

Depth is achieved through the relationship between the background (#F7F7F5) and the surfaces:
1. **The Base Plate:** The background (#F7F7F5).
2. **The Recessed Layer:** Panels (#F3F2EF) which are used for sidebars, secondary navigation, or groupings. These should appear "cut into" the base.
3. **The Elevated Layer:** Cards (#FCFCFB) which use ultra-light borders (#E7E7E4). 

For interaction, use a "Glow" effect instead of a shadow. When a card is hovered or active, a very soft, low-opacity radial gradient (coral, blue, or green) may appear behind the component or along its top edge, creating a sense of internal light rather than external weight.

## Shapes

The shape language is "Soft-Industrial." While the layout is rigid and grid-based, the corners are generously rounded to provide a modern, premium feel.

- **Primary Cards:** Use a significant radius of 24px to 28px. This large curve softens the "technical" edges of the data and creates a modular, containerized look.
- **Interactive Elements:** Buttons and form inputs use a tighter radius (8px-12px) to signify they are precision tools within the larger containers.
- **Consistency:** Never use sharp 0px corners. Every element, from the largest container to the smallest chip, must carry a degree of curvature to maintain the "soft enterprise" visual direction.

## Components

Components in this design system should feel "mounted" to the grid.

- **Buttons:** Primary buttons are solid #111111 with #FCFCFB text. Secondary buttons use the #E7E7E4 border with no fill. For "Technical" actions, buttons may include a 2px bottom-border glow in one of the accent colors.
- **Cards:** White cards (#FCFCFB) must have a 1px border of #E7E7E4. They should always be placed on top of the #F3F2EF panel color or the #F7F7F5 background to ensure a subtle but visible "lift."
- **Inputs:** Fields are minimal, using the #F3F2EF background and a subtle bottom-border. Focus states should trigger a soft glow in the Accent Blue gradient.
- **Chips/Badges:** Small, pill-shaped elements using #F3F2EF backgrounds. Use the Accent UI Glows as small 6px dot indicators within the chips to represent status.
- **Lists:** Clean, horizontal rows separated by 1px #E7E7E4 lines. Metadata should be set in #6B6B6B using the `label-caps` typography style.
- **Additional Suggestion - The "Module Header":** A component that combines an H3 headline with a small accent glow and a "Status" label, used to anchor every major section of the UI.
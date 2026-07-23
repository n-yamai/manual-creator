---
name: Precision Flow
colors:
  surface: '#f9f9ff'
  surface-dim: '#cfdaf2'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f0f3ff'
  surface-container: '#e7eeff'
  surface-container-high: '#dee8ff'
  surface-container-highest: '#d8e3fb'
  on-surface: '#111c2d'
  on-surface-variant: '#424656'
  inverse-surface: '#263143'
  inverse-on-surface: '#ecf1ff'
  outline: '#727687'
  outline-variant: '#c2c6d8'
  surface-tint: '#0054d6'
  primary: '#0050cb'
  on-primary: '#ffffff'
  primary-container: '#0066ff'
  on-primary-container: '#f8f7ff'
  inverse-primary: '#b3c5ff'
  secondary: '#4648d4'
  on-secondary: '#ffffff'
  secondary-container: '#6063ee'
  on-secondary-container: '#fffbff'
  tertiary: '#565a5b'
  on-tertiary: '#ffffff'
  tertiary-container: '#6f7274'
  on-tertiary-container: '#f6f8fa'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae1ff'
  primary-fixed-dim: '#b3c5ff'
  on-primary-fixed: '#001849'
  on-primary-fixed-variant: '#003fa4'
  secondary-fixed: '#e1e0ff'
  secondary-fixed-dim: '#c0c1ff'
  on-secondary-fixed: '#07006c'
  on-secondary-fixed-variant: '#2f2ebe'
  tertiary-fixed: '#e0e3e5'
  tertiary-fixed-dim: '#c4c7c9'
  on-tertiary-fixed: '#191c1e'
  on-tertiary-fixed-variant: '#444749'
  background: '#f9f9ff'
  on-background: '#111c2d'
  surface-variant: '#d8e3fb'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  margin-mobile: 16px
  margin-tablet: 24px
  gutter: 12px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 24px
---

## Brand & Style

The brand personality focuses on efficiency and clarity, transforming complex video data into structured, actionable knowledge. The design system adopts a **Corporate / Modern** style with subtle **Minimalist** influences to ensure the user's focus remains on the content—the video frames and the resulting steps.

The UI should evoke a sense of professional reliability and "smart" automation. This is achieved through a systematic application of whitespace, a constrained color palette, and high-precision typography. The aesthetic is clean, functional, and intentionally unobtrusive, prioritizing utility for high-stakes professional environments.

## Colors

The palette is anchored by a vibrant **Action Blue** (#0066FF) which denotes primary interactions and "smart" AI features. **Indigo** (#6366F1) serves as a secondary accent specifically for timeline navigation, video processing states, and editing transitions. 

The background utilizes a layered approach with **Clean White** (#FFFFFF) for cards and active surfaces, and **Slate Tint** (#F8FAFC) for the base application canvas to reduce eye strain. Text follows a strict hierarchy using **Deep Slate** (#1E293B) for maximum legibility and contrast against the cool-toned backgrounds.

## Typography

This design system utilizes **Inter** for its systematic, utilitarian nature. The type scale is optimized for information density, essential for multi-step documentation.

- **Headlines:** Bold weights with tight letter spacing for a modern, authoritative feel.
- **Body:** Standardized at 16px for primary readability, with a 14px variant for secondary metadata or sidebars.
- **Labels:** Used for timestamps, step numbers, and UI tags, often utilizing semi-bold or medium weights to differentiate from body text.

## Layout & Spacing

The layout follows a **Fluid Grid** model optimized for mobile-first workflows. On mobile devices, a 4-column system is used with 16px side margins. 

The vertical rhythm is based on a 4px baseline grid. Elements within a "step" (image + description) should use `stack-sm` (8px) for internal grouping and `stack-lg` (24px) to separate distinct steps in the procedure. High density is balanced by generous margins around the primary content area to maintain a "clean" and professional atmosphere.

## Elevation & Depth

Visual hierarchy is established through **Tonal Layers** and **Ambient Shadows**. 

1. **Base Layer:** The background (#F8FAFC) acts as the canvas.
2. **Surface Layer:** White cards (#FFFFFF) are used to contain individual steps or video players.
3. **Elevated State:** Active elements or modals use a soft, diffused shadow (0px 4px 12px, 5% opacity Deep Slate) to appear floating without creating visual noise.

Low-contrast outlines (1px, 10% Deep Slate) are preferred over heavy shadows for input fields and list separators to maintain the "Clean/Smart" aesthetic.

## Shapes

The design system employs a **Rounded** (Level 2) logic. 

- **Primary Components:** Buttons, input fields, and small cards use a **0.5rem (8px)** radius to feel modern but structured.
- **Containers:** Main content blocks and image thumbnails use **1rem (16px)** for a softer, more approachable look.
- **Status Pills:** Tags and progress indicators use **Full Rounding (Pill)** to distinguish them from interactive buttons.

## Components

### Buttons
Primary buttons use the Action Blue background with white text. Secondary buttons use a subtle ghost style with a light gray border. All buttons have a height of 48px on mobile for touch accessibility.

### Cards (Step Containers)
Each step in the generated manual is housed in a white card. The card contains a video frame thumbnail (top or left) with a 12px corner radius, followed by the text description.

### Timeline / Progress
A dedicated Indigo-colored progress bar or stepper component is used to show the current position in the video and the corresponding step being edited.

### Input Fields
Fields for "Step Title" or "Instruction Text" use a 1px border (#E2E8F0) that thickens and changes to Action Blue when focused. Labels sit above the field in `label-md` style.

### AI Suggestions (Chips)
"Smart" suggestions or auto-detected keywords appear as small Indigo-tinted chips with 50% transparency backgrounds to indicate they are secondary to the manual content.
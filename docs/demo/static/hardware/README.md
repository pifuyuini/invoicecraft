# Cassette console hardware

Generated with the built-in ImageGen tool on 2026-10-28, using the user-provided cassette console design as material guidance. These are isolated transparent component textures; navigation, labels, state and controls are implemented in HTML, CSS and JavaScript. No generated full-screen UI is used.

- `dial-face.webp`: 320×320 RGBA. Stationary charcoal knob and scale ring, without a pointer. CSS rotates only the separate rectangular live index mark.
- `fastener.webp`: 96×96 RGBA. Steel slotted fastener for 15–20px corner fixtures.

Both original 1254×1254 RGBA images were resized with the existing remote Pillow environment to WebP at quality 90. Transparency was verified at all four corners. No dependencies were installed.

## Dial prompt


Use case: product-mockup.
Asset type: one transparent raster UI component for an actual Cassette Futurism control panel, not a complete UI mockup.
Primary request: recreate ONLY the dark rotary brightness knob and surrounding dial ring from the reference image's right DISPLAY panel as an isolated photoreal physical hardware component. The reference is style/material guidance, not an image to reproduce in full.
Subject: a perfectly centered, front-facing, circular matte charcoal molded plastic rotary knob with fine knurled grip edges, nested brushed steel and dark olive concentric bevels, and a thin outer dark scale ring with fine cream unlabelled radial tick marks around a 270-degree arc. Broad substantial knob face with a very subtle machined texture. Its center face is completely blank, no indicator mark. All geometry appears circular and symmetrical from straight on, no perspective or tilt.
Lighting/mood: restrained upper-left soft fixed highlights and natural small edge shadows that make physical thickness readable at 90–100 pixels. No glow or glossy neon.
Color palette: charcoal black, aged dark olive, muted brushed steel and tiny beige scale ticks, matching the reference hardware.
Constraints: genuinely transparent background outside the circular component; generous consistent transparent padding around the full ring. Entire component stays in frame. No letters, no numbers, no MIN/MAX labels, no words, no pointer or index mark on the knob, no arrow or triangle anywhere, no surrounding rectangular panel, no screen, no other knobs, no buttons, no hands. The live indicator will be added in code, so DO NOT bake in a position pointer. Output one clean square cutout, not a collage.

## Fastener prompt


Use case: product-mockup. Asset type: a single transparent raster UI hardware fastener cutout for a Cassette Futurism console. Input image is STYLE REFERENCE ONLY: match the slotted metal screw heads at the corners of the provided 1970s/1980s equipment case. Primary request: ONE machined circular slotted steel screw head, seen perfectly straight-on from the front, centered in a square canvas. Dark olive-gray worn steel surface, substantial rounded machined bevel, thin washer edge, clean upper-left silver highlight, restrained tiny contact shadow contained close to the round perimeter. A SINGLE straight flat-head screwdriver SLOT angled approximately 40 degrees, deep charcoal recess with narrow bevel. Large clear simple geometry so it stays recognizable at 16–20 pixels. Head fills approximately 86 percent of the square width; equal clear transparent padding around every side. Actual transparent background outside the screw, no panel or surrounding surface. Photoreal hardware material, subtle fine radial machining, not glossy chrome. Constraints: one screw only, no Phillips cross, no bolts with hex holes, no arrow or triangle, no letters/numbers/logo/marking, no caption, no UI labels, no colored glow, no extra objects, no environment, no perspective, no white or gray rectangle, no checkered background drawn into the image. Preserve an actual alpha channel.

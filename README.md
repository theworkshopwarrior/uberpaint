# UberPaint Guide

## CHANGELIST 0.9.8 (since 0.7):
- Layer displacement intensity/offset sliders
- Layers are now renamable
- New layer type: Paint Layers allow for paint-like effects, e.g. graffiti
- The entirety of UberPaint was switched to a new, cleaner internal naming structure
- Layers now default to the top of the list when added
- Brush colors are set to white (foreground) and black (background) by default upon entering paint mode
- Duplicate material entries no longer cause errors
- UberPaint auto detects displacement maps from within the source materials, making displacement blending more convient for most users

⚠ Note that there *are* several known issues that must be resolved before officially releasing this version.
## Overview

UberPaint is an open-source Blender addon intended to dramatically simplify the process of painting materials.  Whereas it was previously necessary to make materials into node groups, manually add image textures, and blend it all together, UberPaint automatically handles all of that and provides a simple layer-based solution.  It supports both texture painting and vertex painting, and has advanced features such as displacement falloff blending.

**Usage:**
1. Add source materials into your scene.  These could be asphalt, plaster, or anything you intend to paint. ![Materials](https://github.com/user-attachments/assets/eab95670-706f-45f6-8d48-93dc677eb371)
2. Select the target object to be used, using the eyedropper at the top.
3. Add layers in UberPaint and assign them to corresponding materials.
![Layers](https://github.com/user-attachments/assets/d2af9ad4-c413-4118-9e0b-ae9e300161c5)
5. Choose weather to use image textures or vertex colors.  Image textures are ideal for low-poly objects, but do not allow for real-time painting in Cycles.  On the other hand, vertex colors are ideal for high mesh density objects where performance is more of a priority. Once you have decided, generate a blend material.
6. Click the "Paint Layer" button at the far right of each layer in the list to paint it, and click once again to exit paint mode. <img width="1224" height="750" alt="image" src="https://github.com/user-attachments/assets/bd4d97d5-dc66-4503-827e-d8e0c8187929" />
7. Tweak layer properties as needed, such as displacement falloff blending.
![dis_maps](https://github.com/user-attachments/assets/4dba5008-aaac-4412-984a-2df49740fe75)

**Full Tutorial:**
https://www.youtube.com/watch?v=meX3cbtdVbI&t=8s

**⚠ Current Limitations**
- When a source material is edited, the changes are not reflected in UberPaint objects until the blend material is updated once again.
- Updating/building blend materials can cause lag depending on quantity and complexity.
  
If you'd like to try something new, test the new alpha release!  [UberPaint Alpha 0.9.8 Alpha](https://github.com/theworkshopwarrior/uberpaint/tree/release/v0.9.8-alpha)

Enjoy!

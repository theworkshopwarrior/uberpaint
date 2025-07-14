# UberPaint Guide
**Overview** 

UberPaint is an open-source Blender addon intended to dramatically simplify the process of painting materials.  Whereas it was previously neccasary to make materials into node groups, manually add texture maps, and blend it all together, UberPaint automatically handles that and provides a simple layer-based solution.  It supports both texture painting and vertex paint, and it has advanced features such as displacement falloff blending.

**Procedure:**
1. Add source materials into your scene.  These could be asphalt, plaster, or anything you intend to mix.
2. Add the materials as layers in UberPaint.
3. Generate a blend material, this will be automatically applied to the selected object.
4. Tweak properties as needed, such as displacement falloff blending.

**Full Tutorial:**
https://www.youtube.com/watch?v=meX3cbtdVbI&t=8s

**⚠ Current Limitations**
- When a source material is edited, the changes are not reflected in UberPaint objects until the blend material is updated once again.
- Updating/building blend materials can cause lag depedending on quanity and complexity.
  

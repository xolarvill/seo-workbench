# Brand/Style Presets Reference

> Load this on-demand when the user asks about presets or brand consistency.

## Preset Schema

Use these fields as a brand/style brief in the selected project’s existing asset or task artifact. The JSON is a source format example; an available provider must explicitly support it before treating it as an API payload:

```json
{
  "name": "tech-saas",
  "description": "Clean tech SaaS brand",
  "colors": ["#2563EB", "#1E40AF", "#F8FAFC"],
  "style": "clean minimal tech illustration, flat vectors, soft shadows",
  "typography": "bold geometric sans-serif",
  "lighting": "bright diffused studio, no harsh shadows",
  "mood": "professional, trustworthy, modern",
  "default_ratio": "16:9",
  "default_resolution": "2K"
}
```

## Example Presets

### tech-saas
- **Colors:** #2563EB, #1E40AF, #F8FAFC (blue + white)
- **Style:** Clean minimal tech illustration, flat vectors, soft shadows
- **Typography:** Bold geometric sans-serif
- **Mood:** Professional, trustworthy, modern

### luxury-brand
- **Colors:** #1A1A1A, #C9A96E, #FAFAF5 (black + gold + cream)
- **Style:** Elegant high-end photography, rich textures, deep contrast
- **Typography:** Thin elegant serif, generous letter-spacing
- **Mood:** Exclusive, sophisticated, aspirational

### editorial-magazine
- **Colors:** #000000, #FFFFFF, #FF3B30 (black + white + accent red)
- **Style:** Bold editorial photography, strong geometric composition
- **Typography:** Condensed all-caps sans-serif headlines
- **Mood:** Bold, provocative, contemporary

## How Presets Merge into Reasoning Brief

When an existing project preset is selected, use its values as defaults for the image brief:
1. **Colors** → inform palette descriptions in Context and Style components
2. **Style** → becomes the base for the Style component
3. **Typography** → used for any text rendering
4. **Lighting** → becomes the base for the Lighting component
5. **Mood** → influences Action and Context components

User instructions always override preset values. If a user says "make it dark"
but the preset has bright lighting, follow the user's instruction.

## Managing Presets

Read the current project's existing brand and asset guidance first. Store a new
reusable brief in that project only when the task calls for it, and record its
path with the task artifact. No preset-management executable or global preset
store is supplied here. For a connected provider's preset API, discover and
verify its actual supported operations before using them.

# SEO Image Presets

Composition briefs for common SEO image uses. These JSON examples describe
creative intent; they are not a local executable preset format. Map relevant
fields to an available tool and confirm its supported dimensions and parameters.

## Preset Templates

### og-default:Standard OG/Social Preview

```json
{
  "name": "og-default",
  "description": "Clean, professional OG image for social sharing",
  "aspect_ratio": "16:9",
  "resolution": "1K",
  "domain_mode": "Product",
  "style": {
    "colors": ["#FFFFFF", "#F5F5F5"],
    "mood": "Professional, clean, trustworthy",
    "lighting": "Bright, even studio lighting with soft shadows",
    "typography": "Modern sans-serif if text needed"
  },
  "post_processing": "magick output.png -resize 1200x630^ -gravity center -extent 1200x630 output-og.webp"
}
```

### blog-hero:Widescreen Blog Hero Image

```json
{
  "name": "blog-hero",
  "description": "Dramatic widescreen hero for blog posts",
  "aspect_ratio": "16:9",
  "resolution": "2K",
  "domain_mode": "Cinema",
  "style": {
    "colors": ["contextual"],
    "mood": "Dramatic, atmospheric, editorial",
    "lighting": "Golden hour or moody blue hour, directional",
    "typography": "None:image only"
  },
  "post_processing": "magick output.png -quality 85 output-hero.webp"
}
```

### product-white:E-commerce Product Shot

```json
{
  "name": "product-white",
  "description": "Clean white background product photography",
  "aspect_ratio": "4:3",
  "resolution": "2K",
  "domain_mode": "Product",
  "style": {
    "colors": ["#FFFFFF"],
    "mood": "Clean, professional, catalog-ready",
    "lighting": "360-degree soft studio lighting, minimal shadows",
    "typography": "None"
  },
  "prompt_suffix": "Studio product photography, clean white background, professional catalog shot, high resolution",
  "post_processing": "magick output.png -fuzz 5% -transparent white output-transparent.png"
}
```

### social-square:Social Media Square

```json
{
  "name": "social-square",
  "description": "1:1 square image for social media platforms",
  "aspect_ratio": "1:1",
  "resolution": "1K",
  "domain_mode": "UI/Web",
  "style": {
    "colors": ["brand-contextual"],
    "mood": "Engaging, scroll-stopping, platform-native",
    "lighting": "Bright, even, high-contrast",
    "typography": "Bold sans-serif if text needed, under 25 characters"
  }
}
```

### infographic-vertical:Data-Heavy Infographic

```json
{
  "name": "infographic-vertical",
  "description": "Tall vertical infographic for data visualization",
  "aspect_ratio": "2:3",
  "resolution": "4K",
  "domain_mode": "Infographic",
  "style": {
    "colors": ["brand-contextual", "data-visualization palette"],
    "mood": "Informative, structured, authoritative",
    "lighting": "Flat, even, no dramatic shadows",
    "typography": "Clear hierarchy:headline, subheads, body, captions"
  },
  "notes": "Use thinking: high for better text rendering accuracy"
}
```

### favicon-mark:Favicon / App Icon

```json
{
  "name": "favicon-mark",
  "description": "Minimal iconic mark for favicon or app icon",
  "aspect_ratio": "1:1",
  "resolution": "512",
  "domain_mode": "Logo",
  "style": {
    "colors": ["2-3 brand colors max"],
    "mood": "Minimal, recognizable, scalable",
    "lighting": "Flat, no shadows",
    "typography": "Single letter or symbol only"
  },
  "post_processing": "magick output.png -resize 32x32 favicon.ico && magick output.png -resize 180x180 apple-touch-icon.png"
}
```

## Custom Brand Briefs

Read existing brand and product guidance from the current project. Add placement,
colors, mood, typography, reference assets, and desired output dimensions to the
existing task brief. Reuse a named brand preset only when its file or connected
provider record actually exists and the tool supports it.

Brand facts and supplied references guide colors, mood, and product details; the
placement determines composition and dimensions. JSON resolution/model hints and
post-processing strings above are source examples. Conversion commands require
an installed tool and actual file inspection before use. For transparent product
cutouts, prefer the available editor's supported background-removal operation
rather than deleting every white pixel in a product image.

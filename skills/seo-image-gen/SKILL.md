---
name: seo-image-gen
description: "AI image generation for SEO assets: OG/social preview images, blog hero images, schema images, product photography, infographics. Uses an actually available image generation tool. Use when user says \"generate image\", \"OG image\", \"social preview\", \"hero image\", \"blog image\", \"product photo\", \"infographic\", \"seo image\", \"create visual\", \"image-gen\", \"favicon\", \"schema image\", \"pinterest pin\", \"generate visual\", \"banner\", or \"thumbnail\"."
argument-hint: "[og|hero|product|infographic|custom|batch] <description>"
user-invokable: true
license: MIT
compatibility: "Image generation requires an available tool; planning works from supplied assets"
metadata:
  author: AgriciDaniel
  version: "1.9.6"
  category: seo
---

# SEO Image Generation

Plan and generate OG previews, article heroes, product illustrations, infographics,
and schema images with an available image tool. Read the tool's applicable skill
and parameter contract before generating. This repository supplies the SEO brief
and handoff method; image providers are discovered in the active environment.

## Inputs and Available Capability

Start from the target placement, actual dimensions, brand guidance, and existing
assets in the project. Inspect supplied reference images before editing. Verify
which generation or editing tool is available and what file outputs it returns.
If none is available, deliver a concrete image brief and asset requirements for a
designer or later tool session. A missing provider does not trigger installation.

## SEO Image Use Cases

These are brief starting points. Translate them into the selected tool's supported
parameters and verify the actual output dimensions.

| Use Case | Aspect Ratio | Resolution | Domain Mode | Notes |
|----------|-------------|------------|-------------|-------|
| **OG/Social Preview** | `16:9` | `1K` | Product or UI/Web | Clean, professional, text-friendly |
| **Blog Hero** | `16:9` | `2K` | Cinema or Editorial | Dramatic, atmospheric, editorial quality |
| **Schema Image** | `4:3` | `1K` | Product | Clean, descriptive, schema ImageObject |
| **Social Square** | `1:1` | `1K` | UI/Web | Platform-optimized square |
| **Product Photo** | `4:3` | `2K` | Product | White background, studio lighting |
| **Infographic** | `2:3` | `4K` | Infographic | Data-heavy, vertical layout |
| **Favicon/Icon** | `1:1` | `512` | Logo | Minimal, scalable, recognizable |
| **Pinterest Pin** | `2:3` | `2K` | Editorial | Tall vertical card |

## Generation Method

1. Identify the placement and reader purpose: preview, hero, product, diagram, or icon.
2. Read [SEO image presets](references/seo-image-presets.md) for relevant composition ideas.
3. Read [prompt engineering](references/prompt-engineering.md) for its six-component
   brief method when helpful. Build a concrete brief: subject, setting, composition, style, brand colors, text,
   required dimensions, source references, and output format. Keep product details
   faithful to supplied product photography and specifications.
4. Use the available generation/editing tool with supported arguments. For batches,
   establish the requested number of variants and any actual provider charge.
5. Inspect the result for accurate product details, text, cropping, and placement.
6. Save or link the returned asset, then record the remaining production steps.

## Asset Handoff

- Supply the actual output path, dimensions, and brief used. State model/settings
  only when the tool exposes them.
- Write descriptive alt text for the image's role. Decorative images may need an
  empty alt attribute; avoid adding keywords that the image does not depict.
- Suggest a descriptive filename. Choose a web format and compression after
  inspecting the returned file; run conversion only with an available supported
  tool and retain the original.
- For an OG image, include the intended crop, width, height, and alt text. A local
  asset path is not a public `og:image` URL.
- For ImageObject or Product markup, pass verified asset properties to `schema`.
  Use a real hosted URL only after an authorized upload and readback.
- Content asset operations use the existing project workflow described in
  [Workbench operations](../seo/references/workbench-operations.md). Generation
  alone does not upload, publish, or alter metadata.

## Provider and Cost Handling

Use current tool responses or the verified provider contract for costs and limits.
Record actual returned usage when available. Do not quote historical model prices
as an estimate for a different provider, or invent a local usage ledger. On tool
failure, retain the brief and returned error; use a supported retry or alternative
only when actually available.

## Cross-Skill Use

Read `images` for analysis of existing assets, `schema` for structured data, and
`write-content` for placement in a draft. A site audit may recommend generation;
perform generation when the user's requested scope includes creating the asset.

## Provider-Specific References

The preserved [Gemini model notes](references/gemini-models.md),
[MCP examples](references/mcp-tools.md), [cost notes](references/cost-tracking.md),
[preset format](references/presets.md), and
[post-processing recipes](references/post-processing.md) describe the source
integration. Use them only when the actual selected provider supports that
contract; verify current tool parameters and installed conversion capabilities.

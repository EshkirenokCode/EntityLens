# Interface research and design decisions

Reviewed 2026-10-24. The application is an analyst tool: the primary task is comparing source observations and making reversible decisions. A marketing hero, oversized metrics and low-contrast decoration weakened the earlier interface.

| Reference | Observed pattern | Application in Concord |
|---|---|---|
| [Dribbble: data reconciliation](https://dribbble.com/search/data-reconciliation) | Dense comparison tables and source panels; inspected gallery visually | Aligned A/B source panels, compact candidate rows, explicit field labels |
| [Mobbin dashboard study](https://mobbin.com/blog/what-good-dashboard-design-looks-like) | Dashboard hierarchy should support decisions, rather than simply display data | Secondary context reduced; review dominates the page |
| [Linear interface refresh](https://linear.app/now/behind-the-latest-design-refresh) | Navigation recedes and controls occupy predictable locations | Quiet sidebar, compact header, consistent actions, restrained borders |
| [Refero Linear reference](https://refero.design/pages/7a7ea171-0cf4-4475-8b45-cc8ec44fde8f) | Reference discovered; article content unavailable to text extraction | No claims about unobserved screens; used accessible Linear primary documentation instead |

Implemented a neutral white/slate palette with blue selection, amber review state and distinct source accents. System fonts remove external font requests. Counts use tabular monospaced digits. The old decorative street-grid image became an explicitly labeled coordinate schematic; it does not imply accurate roads or tiles. The classifier is shown as a decimal model score, never a rounded percentage that resembles certainty.

Desktop preserves queue/comparison/context panels. Intermediate widths omit secondary context. Narrow views stack the queue above records, preserve accessible navigation labels, and stack A/B fields below 440px. This is a purpose-built implementation; no template assets or screenshots were copied into the product.

Portfolio judgment: suitable to demonstrate an honest local ML engineering prototype and review workflow. It is not evidence of production accuracy, independent benchmark quality, authenticated public deployment or production-scale infrastructure. Pair UI screenshots with the methodology and explicit limitations.

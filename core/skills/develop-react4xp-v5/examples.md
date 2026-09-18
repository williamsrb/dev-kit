# React4XP Examples

## Example 1: Add a content-type component

Goal: Render `com.acme.app:article`.

1) Create view:
- `src/main/resources/react4xp/components/content/Article.tsx`

2) Create processor:
- `src/main/resources/react4xp/components/content/ArticleProcessor.ts`

3) Register both:
- `componentRegistry.addContentType('com.acme.app:article', { View: Article })`
- `dataFetcher.addContentType('com.acme.app:article', { processor: articleProcessor })`

Expected outcome:
- Article content renders with shaped props from processor.

## Example 2: Add a part with config-based processor

Goal: Render part `com.acme.app:promo-banner`.

Processor pattern:
- Read `params.component.config`
- Return serializable props only

Registration pattern:
- `componentRegistry.addPart('com.acme.app:promo-banner', { View: PromoBanner })`
- `dataFetcher.addPart('com.acme.app:promo-banner', { processor: promoBannerProcessor })`

## Example 3: Add rich text + macro support

Goal: Render HTML area with embedded custom macro.

Processor pattern:
- Use `processHtml({ value, dataFetcher, component, imageWidths })`
- Return processed rich text data in props

View pattern:
- Render with `<RichText data={...} meta={meta} common={common} component={component} />`

Macro wiring:
- `componentRegistry.addMacro('factbox', { View: Factbox })`
- `dataFetcher.addMacro('factbox', { processor: factboxProcessor })`

## Example 4: Add a page with regions

Goal: Page descriptor `com.acme.app:main`.

View pattern:
- Use `Region` components with exact region names from CMS:
  - `component.regions.main.components`

Registration:
- `componentRegistry.addPage('com.acme.app:main', { View: MainPage })`

## Example 5: Controller render baseline

```ts
const React4xp = require('/lib/enonic/react4xp');

exports.get = function (request) {
  const entry = 'react4xp/entries/App';
  const props = {};

  const { body, pageContributions } = React4xp.render(entry, props, request, {
    ssr: true,
    hydrate: true
  });

  return {
    body,
    pageContributions
  };
};
```

Notes:
- Passing `request` allows mode-aware behavior.
- Keep `ssr` and `hydrate` intentional for each endpoint/component.

## Example 6: Report format after task execution

```md
Updated files:
- src/main/resources/react4xp/components/parts/PromoBanner.tsx
- src/main/resources/react4xp/components/parts/PromoBannerProcessor.ts
- src/main/resources/react4xp/componentRegistry.tsx
- src/main/resources/react4xp/dataFetcher.ts

Wiring:
- addPart('com.acme.app:promo-banner', { View: PromoBanner })
- addPart('com.acme.app:promo-banner', { processor: promoBannerProcessor })

Verification:
- enonic dev: pass
- Preview render in Content Studio: pass
- enonic project build: pass
```

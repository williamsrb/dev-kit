# XP App — Enonic React4XP

Enonic XP application for {PROJECT_DISPLAY_NAME} (`com.example.{PROJECT_SHORT_NAME}`), built with React4XP 6.x.

## Key Source Paths

```
xp/src/main/resources/
├── i18n/
│   └── phrases.properties                      # Translation keys (all components)
├── react4xp/
│   ├── dataFetcher.ts                          # Registers all component processors
│   ├── componentRegistry.tsx                   # Registers all React components
│   ├── components/
│   │   ├── pages/default/
│   │   │   ├── default.tsx                     # React page component
│   │   │   └── processor.ts                    # Data processor (returns regions)
│   │   ├── layouts/{name}/
│   │   │   ├── {name}.tsx                      # React layout component
│   │   │   └── processor.ts                    # Data processor (returns regions + componentProps)
│   │   ├── parts/{name}/
│   │   │   ├── {name}.tsx                      # React part component
│   │   │   └── processor.ts                    # Data processor (returns componentProps)
│   │   ├── macros/{name}/
│   │   │   ├── {name}.tsx                      # React macro component
│   │   │   └── processor.ts                    # Data processor
│   │   └── prototype/                          # Copied from prototype (do not edit directly)
│   ├── shared/                                 # Shared assets, fonts, SCSS (copied from prototype)
│   └── utils/
│       └── prototype/                          # Utility functions (copied from prototype)
└── site/
    ├── content-types/{name}/
    │   ├── {name}.xml                          # Content type descriptor
    │   └── {name}.d.ts                         # TypeScript interface ({PascalName}Data)
    ├── parts/{name}/
    │   ├── {name}.xml                          # Part descriptor
    │   └── {name}.d.ts                         # TypeScript interfaces ({PascalName}PartData + Props)
    ├── layouts/{name}/
    │   ├── {name}.xml                          # Layout descriptor
    │   └── {name}.d.ts                         # TypeScript interface ({PascalName}LayoutProps)
    ├── macros/{name}/
    │   ├── {name}.xml                          # Macro descriptor
    │   └── {name}.d.ts                         # TypeScript interface ({PascalName}MacroProps)
    ├── x-data/{name}/
    │   └── {name}.xml                          # X-data descriptor
    └── mixins/{name}/
        └── {name}.xml                          # Mixin descriptor
```

## React4XP Architecture

### Data Flow

1. A request hits Enonic XP.
2. `dataFetcher.ts` routes it to the matching processor.
3. The processor fetches content/config, transforms it, and returns `componentProps` (and `regions` for pages/layouts).
4. `componentRegistry.tsx` maps the component key to its React component.
5. The React component receives `{ component, meta, data, common }` from `@enonic/react-components` and reads `data.componentProps` for its typed props.

### Registering a New Component

**1. Add to `dataFetcher.ts`:**
```typescript
import { myPartProcessor } from './components/parts/my-part/processor';
dataFetcher.addPart(`${app.name}:my-part`, { processor: myPartProcessor });
```

**2. Add to `componentRegistry.tsx`:**
```typescript
import { MyPart } from './components/parts/my-part/my-part';
componentRegistry.addPart('com.example.{PROJECT_SHORT_NAME}:my-part', { View: MyPart });
```

### Processor Pattern

```typescript
import type { ComponentProcessor } from '@enonic-types/lib-react4xp/DataFetcher';

export const myPartProcessor: ComponentProcessor<'com.example.{PROJECT_SHORT_NAME}:my-part'> = ({ component, dataFetcher }) => {
    const { config } = component as PartComponent;
    return {
        componentProps: {
            title: config.title,
            body: processHtml({ value: config.body as string, component, dataFetcher }),
        },
    };
};
```

- Layouts and pages must also return `regions` from the component.
- Use `processHtml` from `/lib/enonic/react4xp` for HtmlArea fields.
- Use `processTextArea` from `/lib/app/extension/portal` to convert plain text newlines before passing to `processHtml`.
- Use `myImageUrl(ref, 'width(500)')` from `/lib/app/extension/portal` for image URL generation.

### React Component Pattern

```typescript
import { type ComponentProps, type LayoutData } from '@enonic/react-components';
import type { MyPartProps } from '/site/parts/my-part/my-part.d';

export const MyPart = ({ component, meta, data, common }: ComponentProps<LayoutData>) => {
    const props = data.componentProps as MyPartProps;
    return <div>{props.title}</div>;
};
```

## Schema Conventions

All schema files follow the patterns in `.claude/skills/apply-react4xp-practices/`.

Key rules:
- All names use **kebab-case**.
- Every `<label>` and `<display-name>` must have an `i18n` attribute. Add translations to `i18n/phrases.properties`.
- Content types generate `{PascalName}Data` interfaces.
- Parts generate both `{PascalName}PartData` (raw Enonic fields) and `{PascalName}PartProps` (React props).
- Layouts generate `{PascalName}LayoutProps`. Macros generate `{PascalName}MacroProps`.
- `HtmlArea` fields: `string` in `*Data`, `ExtendedRichTextData` (from `@enonic/react-components`) in `*Props`.

## Build

The build is managed by Gradle inside the Docker container (see root `Makefile`):

- TypeScript (non-React) compiled by **tsup** via `buildXpResources` task.
- React/TSX compiled by **react4xp** Gradle task.
- Assets compiled by **buildAssets** task.
- Run `make full` from the project root to copy prototype components and do a full build+deploy.

---
title: "SkillMeat Architecture Diagram Specification"
description: "Full spec for entity map and functional flow diagrams of SkillMeat."
status: draft
updated: 2026-01-04
audience: developers,devex,product,marketing
---

# SkillMeat Architecture Diagram Specification

This document defines the full spec for a two-part architectural flow diagram of SkillMeat. It includes entity inventory, visual language, layout guidance, and ready-to-render Mermaid diagrams.

## Goals
- Make primary entities, features, and data movement legible at a glance.
- Show how CLI, Web UI, API, and core services connect to artifacts, collections, and projects.
- Provide a reusable visual system (colors, shapes, line styles, legend) for consistent rendering in Mermaid, Figma, or Excalidraw.

## Diagram set
1. Entity/relationship map (domain objects and storage locations).
2. Functional flow map (features acting on entities, end-to-end).

## Visual language

### Color palette (unique per entity)
- Artifact: #F4A261
- Collection: #2A9D8F
- Project: #264653
- Deployment Record: #E76F51
- Snapshot: #8D99AE
- Manifest/Lock: #F2CC8F
- Tag: #84A59D
- Context Entity: #BC6C25
- Template: #118AB2
- Marketplace Listing: #FFBA08
- Marketplace Source: #8D6E63
- MCP Server: #00A896
- Cache Record: #577590
- Notification: #EF476F
- Analytics Report: #06D6A0
- Bundle/Share Link: #F77F00

### Shape tokens (unique color + shape per entity)
- Artifact: parallelogram `[/Artifact/]`
- Collection: rounded rectangle `(Collection)`
- Project: hexagon `{{Project}}`
- Deployment Record: subroutine `[[Deployment Record]]`
- Snapshot: cylinder `[(Snapshot)]`
- Manifest/Lock: inverse parallelogram `[\Manifest/Lock\]`
- Tag: circle `((Tag))`
- Context Entity: diamond `{Context Entity}`
- Template: stadium `([Template])`
- Marketplace Listing: rectangle `[Marketplace Listing]`
- Marketplace Source: asymmetric `>Marketplace Source]` (or rectangle with icon badge in Figma)
- MCP Server: hexagon `{{MCP Server}}` (if hex is used for Project, swap to rectangle + icon in Figma)
- Cache Record: cylinder `[(Cache Record)]`
- Notification: parallelogram `[/Notification/]`
- Analytics Report: stadium `([Analytics Report])`
- Bundle/Share Link: subroutine `[[Bundle/Share Link]]`

Note: Mermaid has a limited set of shapes. If a shape must repeat in Mermaid, keep color unique and add a small text badge (e.g., "MCP", "PRJ") in Figma to preserve shape distinction.

### Line styles
- Solid arrow: write/mutate.
- Dashed arrow `-.->`: read/query.
- Dotted arrow `..>`: async event or notification.

### Layout guidance
- Use left-to-right flow for the entity map, top-to-bottom for the functional map.
- Group by domain (Sources, Collection Store, Project, Marketplace, MCP, Cache/DB, Observability).
- Keep the entity nodes as primary objects; process nodes should be neutral gray.
- Provide a visible legend and color key.

## Primary entities (inventory)
- Artifact (skill, command, agent, mcp, hook)
- Collection
- Project
- Deployment Record
- Snapshot
- Manifest/Lock (collection metadata)
- Tag
- Context Entity
- Template
- Marketplace Listing
- Marketplace Source
- MCP Server
- Cache Record (Project, Artifact, Collection cache rows)
- Notification
- Analytics Report
- Bundle/Share Link

## Primary features (inventory)
- Add/import artifacts from GitHub or local sources
- Deploy/undeploy to projects
- Sync/merge and drift detection
- Update/versioning and rollback
- Search/discovery (content + metadata)
- Analytics/usage reporting
- Marketplace publish/install
- MCP server deploy/health management
- Notifications and alerts
- Template and context entity management
- Tags and filtering
- Bundle/share (export/import)

## Feature-to-entity mapping

| Feature | Trigger | Reads | Writes | Primary Entities |
| --- | --- | --- | --- | --- |
| Add/Import | CLI/Web | Source, Manifest/Lock | Artifact, Collection, Manifest/Lock, Cache Record | Artifact, Collection, Manifest/Lock, Cache Record |
| Deploy/Undeploy | CLI/Web | Collection, Artifact | Project, Deployment Record, Cache Record | Project, Deployment Record |
| Sync/Merge | CLI/Web | Project, Deployment Record, Collection | Artifact, Collection, Snapshot, Cache Record | Project, Collection, Snapshot |
| Update/Version | CLI/Web | Manifest/Lock, Artifact | Artifact, Snapshot, Manifest/Lock | Artifact, Snapshot |
| Search/Discovery | CLI/Web | Cache Record, Artifact, Tags | Analytics Report (optional) | Artifact, Tag, Cache Record |
| Analytics | CLI/Web | Cache Record, Usage Events | Analytics Report | Analytics Report, Cache Record |
| Marketplace Install | CLI/Web | Marketplace Listing, Bundle | Artifact, Collection, Manifest/Lock | Marketplace Listing, Artifact |
| Marketplace Publish | CLI/Web | Artifact, Bundle | Marketplace Listing | Marketplace Listing, Bundle |
| MCP Manage | CLI/Web | MCP Server | Claude Desktop Config | MCP Server |
| Notifications | System | Events from Update/Sync/Marketplace | Notification | Notification |
| Templates/Context | CLI/Web | Collection, Artifact | Template, Context Entity | Template, Context Entity |
| Tags | CLI/Web | Artifact | Tag | Tag |
| Bundle/Share | CLI/Web | Artifact, Collection | Bundle/Share Link | Bundle/Share Link |

## Diagram 1: Entity/relationship map (Mermaid)

```mermaid
flowchart LR
  %% Domains
  subgraph Sources[Sources]
    GH{{GitHub Source}}
    LS{{Local Source}}
    MSRC>Marketplace Source]
  end

  subgraph CollectionStore[Collection Store (~/.skillmeat)]
    COL(Collection)
    ART[/Artifact/]
    META[\Manifest/Lock\]
    TAG((Tag))
    CTX{Context Entity}
    TMP([Template])
    SNAP[(Snapshot)]
  end

  subgraph ProjectSurface[Project (.claude)]
    PROJ{{Project}}
    ARTI[/Artifact Instance/]
    DEP[[Deployment Record]]
  end

  subgraph Marketplace[Marketplace]
    MLIST[Marketplace Listing]
    BUND[[Bundle/Share Link]]
  end

  subgraph MCP[MCP]
    MCP{{MCP Server}}
    CCFG[(Claude Desktop Config)]
  end

  subgraph CacheDB[Cache/DB]
    CDB[(Cache Record)]
  end

  subgraph Observability[Analytics/Notifications]
    ANAL([Analytics Report])
    NOTE[/Notification/]
  end

  %% Relationships
  GH --> ART
  LS --> ART
  MSRC --> MLIST
  ART --> COL
  COL --> META
  COL --> SNAP
  ART --> TAG
  ART --> CTX
  ART --> TMP
  COL --> PROJ
  ART --> ARTI
  PROJ --> DEP
  DEP --> CDB
  COL --> CDB
  ART --> CDB
  ART --> MLIST
  MLIST --> BUND
  MCP --> CCFG
  CDB -.-> ANAL
  CDB ..> NOTE

  %% Styling
  class ART artifact;
  class COL collection;
  class PROJ project;
  class DEP deployment;
  class SNAP snapshot;
  class META manifest;
  class TAG tag;
  class CTX context;
  class TMP template;
  class MLIST marketlisting;
  class MSRC marketsource;
  class MCP mcp;
  class CDB cache;
  class NOTE notification;
  class ANAL analytics;
  class BUND bundle;

  classDef artifact fill:#F4A261,stroke:#8A4B2A,color:#1B1B1B;
  classDef collection fill:#2A9D8F,stroke:#1B5B52,color:#0B1412;
  classDef project fill:#264653,stroke:#14232A,color:#EAF2F2;
  classDef deployment fill:#E76F51,stroke:#9F3E27,color:#1B1B1B;
  classDef snapshot fill:#8D99AE,stroke:#5B6573,color:#0B0B0B;
  classDef manifest fill:#F2CC8F,stroke:#B8914D,color:#1B1B1B;
  classDef tag fill:#84A59D,stroke:#57746D,color:#0B0B0B;
  classDef context fill:#BC6C25,stroke:#7B4517,color:#1B1B1B;
  classDef template fill:#118AB2,stroke:#0C5C78,color:#FFFFFF;
  classDef marketlisting fill:#FFBA08,stroke:#C98F00,color:#1B1B1B;
  classDef marketsource fill:#8D6E63,stroke:#5F463E,color:#FFFFFF;
  classDef mcp fill:#00A896,stroke:#007564,color:#0B0B0B;
  classDef cache fill:#577590,stroke:#3B4E5F,color:#FFFFFF;
  classDef notification fill:#EF476F,stroke:#B0334F,color:#FFFFFF;
  classDef analytics fill:#06D6A0,stroke:#049C73,color:#0B0B0B;
  classDef bundle fill:#F77F00,stroke:#B65F00,color:#1B1B1B;
```

## Diagram 2: Functional flow map (Mermaid)

```mermaid
flowchart TB
  %% Actors and Interfaces
  U[User]
  CLI[CLI]
  WEB[Web UI]
  API[API]

  %% Core Services (neutral)
  ADD([Add/Import])
  DEPLOY([Deploy/Undeploy])
  SYNC([Sync/Drift/Merge])
  UPDATE([Update/Version])
  SNAPSHOT([Snapshot/Rollback])
  SEARCH([Search/Discovery])
  ANALYTICS([Analytics])
  MARKET([Marketplace Publish/Install])
  MCPMGR([MCP Manage/Health])
  NOTIFY([Notifications])
  TEMPLATE([Templates/Context])
  TAGS([Tagging])
  SHARE([Bundle/Share])

  %% Entities
  ART[/Artifact/]
  COL(Collection)
  META[\Manifest/Lock\]
  SNAP[(Snapshot)]
  PROJ{{Project}}
  DEP[[Deployment Record]]
  TAG((Tag))
  CTX{Context Entity}
  TMP([Template])
  CDB[(Cache Record)]
  MLIST[Marketplace Listing]
  MSRC>Marketplace Source]
  MCP{{MCP Server}}
  CCFG[(Claude Desktop Config)]
  NOTE[/Notification/]
  ANAL([Analytics Report])
  BUND[[Bundle/Share Link]]
  GH{{GitHub/Local Source}}

  %% User entry
  U --> CLI --> API
  U --> WEB --> API

  %% Add/Import
  GH --> ADD
  API --> ADD --> ART --> COL
  ADD --> META
  ADD --> CDB

  %% Deploy
  COL -.-> DEPLOY
  ART -.-> DEPLOY
  DEPLOY --> PROJ --> DEP
  DEP --> CDB

  %% Sync/Merge
  PROJ -.-> SYNC
  COL -.-> SYNC
  SYNC --> ART
  SYNC --> SNAP
  SYNC --> CDB

  %% Update/Version
  META -.-> UPDATE
  UPDATE --> ART
  UPDATE --> SNAP

  %% Snapshot/Rollback
  COL -.-> SNAPSHOT
  SNAPSHOT --> SNAP
  SNAPSHOT --> ART

  %% Search/Discovery
  CDB -.-> SEARCH
  SEARCH -.-> ART
  SEARCH -.-> TAG

  %% Analytics
  CDB -.-> ANALYTICS
  ANALYTICS --> ANAL

  %% Marketplace
  MARKET --> MLIST
  MSRC -.-> MARKET
  MARKET --> BUND
  MARKET --> ART

  %% MCP
  MCPMGR --> MCP --> CCFG

  %% Templates/Context
  TEMPLATE --> TMP
  TEMPLATE --> CTX

  %% Tagging
  TAGS --> TAG

  %% Bundle/Share
  SHARE --> BUND

  %% Notifications
  UPDATE ..> NOTIFY --> NOTE
  SYNC ..> NOTIFY
  MARKET ..> NOTIFY

  %% Styling
  class ART artifact;
  class COL collection;
  class PROJ project;
  class DEP deployment;
  class SNAP snapshot;
  class META manifest;
  class TAG tag;
  class CTX context;
  class TMP template;
  class MLIST marketlisting;
  class MSRC marketsource;
  class MCP mcp;
  class CDB cache;
  class NOTE notification;
  class ANAL analytics;
  class BUND bundle;

  classDef artifact fill:#F4A261,stroke:#8A4B2A,color:#1B1B1B;
  classDef collection fill:#2A9D8F,stroke:#1B5B52,color:#0B1412;
  classDef project fill:#264653,stroke:#14232A,color:#EAF2F2;
  classDef deployment fill:#E76F51,stroke:#9F3E27,color:#1B1B1B;
  classDef snapshot fill:#8D99AE,stroke:#5B6573,color:#0B0B0B;
  classDef manifest fill:#F2CC8F,stroke:#B8914D,color:#1B1B1B;
  classDef tag fill:#84A59D,stroke:#57746D,color:#0B0B0B;
  classDef context fill:#BC6C25,stroke:#7B4517,color:#1B1B1B;
  classDef template fill:#118AB2,stroke:#0C5C78,color:#FFFFFF;
  classDef marketlisting fill:#FFBA08,stroke:#C98F00,color:#1B1B1B;
  classDef marketsource fill:#8D6E63,stroke:#5F463E,color:#FFFFFF;
  classDef mcp fill:#00A896,stroke:#007564,color:#0B0B0B;
  classDef cache fill:#577590,stroke:#3B4E5F,color:#FFFFFF;
  classDef notification fill:#EF476F,stroke:#B0334F,color:#FFFFFF;
  classDef analytics fill:#06D6A0,stroke:#049C73,color:#0B0B0B;
  classDef bundle fill:#F77F00,stroke:#B65F00,color:#1B1B1B;
```

## Figma/Excalidraw production notes
- Use the same palette and shape tokens; keep a legend block in the bottom-right.
- For Mermaid shape collisions, add a small two-letter badge in the top-left of each entity (AR, CO, PR, DR, SN, ML, TG, CE, TM, ML, MS, MC, DB, NT, AN, BL).
- Use tiers: Sources (left), Collection Store (center-left), Project Surface (center-right), Marketplace/MCP (right), Cache/Observability (bottom).
- Add 1-2 callouts for "Three-tier Artifact Flow" and "Bidirectional Sync" to connect with existing documentation.

## Acceptance checklist
- All primary entities listed in the inventory appear in the entity map.
- Functional flow shows at least: add/import, deploy, sync/merge, update/version, search, analytics, marketplace, MCP, notifications.
- Each entity is visually unique by color + shape, with a visible legend.
- Both diagrams are readable on a single page at 16:9 and 4:3.

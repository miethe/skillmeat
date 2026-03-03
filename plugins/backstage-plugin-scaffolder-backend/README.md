# @skillmeat/backstage-plugin-scaffolder-backend

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Backstage scaffolder backend module providing custom actions for [SkillMeat (SAM)](https://github.com/miethe/skillmeat) IDP integration.

Two actions are provided:

- **`skillmeat:context:inject`** — Calls the SAM scaffold API to fetch a rendered Golden Context Pack and writes the resulting files into the scaffolder workspace.
- **`skillmeat:deployment:register`** — Registers a completed deployment with SAM after `publish:github` creates the repository, linking the repo to the SAM artifact used as the scaffold source.

---

## Installation

```bash
# From your Backstage root
yarn --cwd packages/backend add @skillmeat/backstage-plugin-scaffolder-backend
```

---

## Configuration

### New Backend System (recommended)

Add the module to your backend in `packages/backend/src/index.ts`:

```typescript
import { createBackend } from '@backstage/backend-defaults';
import { skillmeatScaffolderModule } from '@skillmeat/backstage-plugin-scaffolder-backend';

const backend = createBackend();
backend.add(import('@backstage/plugin-scaffolder-backend/alpha'));
backend.add(skillmeatScaffolderModule);
await backend.start();
```

### Legacy Backend

Import the action factories and pass them to `createRouter` in `packages/backend/src/plugins/scaffolder.ts`:

```typescript
import {
  createSkillMeatInjectAction,
  createSkillMeatRegisterAction,
} from '@skillmeat/backstage-plugin-scaffolder-backend';

// Inside createRouter({ ..., actions }):
const actions = [
  ...builtinActions,
  createSkillMeatInjectAction(),
  createSkillMeatRegisterAction(),
];
```

### App Config

Add the SAM API connection details to `app-config.yaml`:

```yaml
skillmeat:
  baseUrl: https://sam.internal:8080
  token: ${SAM_API_TOKEN} # Optional — omit for unauthenticated internal deployments
```

Both `baseUrl` and `token` can also be supplied as per-step inputs in the template, which takes precedence over the global config.

---

## Actions Reference

### `skillmeat:context:inject`

Calls `POST /api/v1/integrations/idp/scaffold` on the SAM API and writes the returned base64-encoded files into the Backstage scaffolder workspace.

#### Inputs

| Field       | Type                      | Required | Description                                                                 |
|-------------|---------------------------|----------|-----------------------------------------------------------------------------|
| `targetId`  | `string`                  | Yes      | SAM artifact identifier in `type:name` format (e.g. `composite:fin-serv-compliance`) |
| `variables` | `Record<string, string>`  | No       | Template variable substitutions applied during rendering                    |
| `baseUrl`   | `string`                  | No       | Override the `skillmeat.baseUrl` app-config value for this step             |
| `token`     | `string`                  | No       | Override the `skillmeat.token` app-config value for this step               |

#### Outputs

| Field          | Type     | Description                                          |
|----------------|----------|------------------------------------------------------|
| `filesWritten` | `number` | Number of files written to the scaffolder workspace  |

#### Example

```yaml
steps:
  - id: inject-context
    name: Inject AI Context Pack
    action: skillmeat:context:inject
    input:
      targetId: "composite:fin-serv-compliance"
      variables:
        PROJECT_NAME: ${{ parameters.name }}
        PROJECT_DESCRIPTION: ${{ parameters.description }}
        AUTHOR: ${{ parameters.owner }}
```

---

### `skillmeat:deployment:register`

Calls `POST /api/v1/integrations/idp/register-deployment` on the SAM API to associate a newly created repository with the SAM artifact used during scaffolding. Run this after `publish:github` so the `repoUrl` is available.

#### Inputs

| Field       | Type                      | Required | Description                                                                 |
|-------------|---------------------------|----------|-----------------------------------------------------------------------------|
| `repoUrl`   | `string`                  | Yes      | HTTPS URL of the newly created repository (typically from `publish:github` output) |
| `targetId`  | `string`                  | Yes      | SAM artifact identifier in `type:name` format (e.g. `composite:fin-serv-compliance`) |
| `metadata`  | `Record<string, string>`  | No       | Arbitrary key-value metadata stored with the deployment record              |
| `baseUrl`   | `string`                  | No       | Override the `skillmeat.baseUrl` app-config value for this step             |
| `token`     | `string`                  | No       | Override the `skillmeat.token` app-config value for this step               |

#### Outputs

| Field             | Type      | Description                                                              |
|-------------------|-----------|--------------------------------------------------------------------------|
| `deploymentSetId` | `string`  | UUID of the created or matched DeploymentSet record in SAM               |
| `created`         | `boolean` | `true` if a new deployment was created; `false` if an existing one was matched |

#### Example

```yaml
steps:
  - id: register-deployment
    name: Register SAM Deployment
    action: skillmeat:deployment:register
    input:
      repoUrl: ${{ steps.publish.output.remoteUrl }}
      targetId: "composite:fin-serv-compliance"
      metadata:
        team: ${{ parameters.owner }}
        scaffolded_at: ${{ parameters.name }}
```

---

## Complete Template Example

A full scaffolder template demonstrating both actions in sequence:

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: spring-boot-with-ai-context
  title: Spring Boot Microservice with AI Context
  description: Creates a Spring Boot project pre-loaded with a SkillMeat Golden Context Pack
spec:
  owner: platform-engineering
  type: service

  parameters:
    - title: Project Details
      required:
        - name
        - description
      properties:
        name:
          title: Name
          type: string
          description: Unique name for the new service
        description:
          title: Description
          type: string
        owner:
          title: Owner
          type: string
          ui:field: OwnerPicker

  steps:
    - id: fetch
      name: Fetch Base Template
      action: fetch:template
      input:
        url: ./skeleton
        values:
          name: ${{ parameters.name }}

    - id: inject-context
      name: Inject AI Context Pack
      action: skillmeat:context:inject
      input:
        targetId: "composite:fin-serv-compliance"
        variables:
          PROJECT_NAME: ${{ parameters.name }}
          PROJECT_DESCRIPTION: ${{ parameters.description }}
          AUTHOR: ${{ parameters.owner }}

    - id: publish
      name: Publish to GitHub
      action: publish:github
      input:
        allowedHosts: ['github.com']
        repoUrl: github.com?owner=org&repo=${{ parameters.name }}

    - id: register-deployment
      name: Register SAM Deployment
      action: skillmeat:deployment:register
      input:
        repoUrl: ${{ steps.publish.output.remoteUrl }}
        targetId: "composite:fin-serv-compliance"
        metadata:
          team: ${{ parameters.owner }}
          service_name: ${{ parameters.name }}

    - id: register
      name: Register in Catalog
      action: catalog:register
      input:
        repoContentsUrl: ${{ steps.publish.output.repoContentsUrl }}
        catalogInfoPath: /catalog-info.yaml

  output:
    links:
      - title: Repository
        url: ${{ steps.publish.output.remoteUrl }}
      - title: Open in catalog
        entityRef: ${{ steps.register.output.entityRef }}
```

---

## Development

Build the plugin locally:

```bash
cd plugins/backstage-plugin-scaffolder-backend
yarn install
yarn build
```

Lint and type-check:

```bash
yarn lint
yarn tsc --noEmit
```

To test the actions against a running SAM instance, set `skillmeat.baseUrl` in your local `app-config.local.yaml`:

```yaml
skillmeat:
  baseUrl: http://localhost:8080
```

---

## License

Apache-2.0 — see [LICENSE](../../LICENSE) for details.

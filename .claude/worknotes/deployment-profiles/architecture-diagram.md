# Multi-Platform Deployment Profiles - Architecture Diagram

## Data Flow: Create Profile

```
Frontend (Web)
├─ Page: /projects/[id]/profiles
│  ├─ Form State: ProfileFormState
│  │  ├─ profile_id: string
│  │  ├─ platform: Platform (enum)
│  │  ├─ root_dir: string (auto-populated from platform)
│  │  ├─ artifact_path_map_json: string (JSON)
│  │  ├─ project_config_filenames: string (newline/comma-separated)
│  │  ├─ context_path_prefixes: string (newline/comma-separated)
│  │  └─ supported_artifact_types: string (comma-separated)
│  │
│  └─ Event: handleCreate()
│     ├─ Call: parseCreatePayload(form)
│     │  ├─ Parse JSON: artifact_path_map_json → object
│     │  ├─ Split strings: toList() → arrays
│     │  └─ Return: CreateDeploymentProfileRequest
│     │
│     └─ Call: createProfile.mutateAsync(request)
│        ├─ Mutation: useCreateDeploymentProfile()
│        │  └─ API: createDeploymentProfile(projectId, data)
│        │
│        └─ API Client Function (lib/api/deployment-profiles.ts)
│           └─ POST /projects/{projectId}/profiles
│              └─ Body: CreateDeploymentProfileRequest
│
├─ HTTP POST /api/v1/projects/{projectId}/profiles
│
└─ Backend (FastAPI)
   ├─ Router: deployment_profiles.py
   │  └─ Handler: create_profile()
   │     ├─ Resolve: _resolve_project_db_id(projectId)
   │     │  └─ Support both direct IDs and base64-encoded paths
   │     │
   │     └─ Call: DeploymentProfileRepository.create()
   │        ├─ Platform: Platform.CLAUDE_CODE → "claude_code" (enum value)
   │        ├─ DB Validation:
   │        │  ├─ Check constraint: platform IN (valid values)
   │        │  └─ Unique constraint: (project_id, profile_id)
   │        │
   │        └─ Insert into deployment_profiles table
   │           ├─ id: UUID (generated)
   │           ├─ project_id: string (FK)
   │           ├─ profile_id: string (user-provided)
   │           ├─ platform: string (enum value)
   │           ├─ root_dir: string
   │           ├─ artifact_path_map: JSON
   │           ├─ config_filenames: JSON array
   │           ├─ context_prefixes: JSON array
   │           ├─ supported_types: JSON array
   │           ├─ created_at: datetime (auto)
   │           └─ updated_at: datetime (auto)
   │
   └─ Response: DeploymentProfileRead (200 Created)
      ├─ Map DB fields to response fields:
      │  ├─ config_filenames → project_config_filenames
      │  ├─ context_prefixes → context_path_prefixes
      │  └─ supported_types → supported_artifact_types
      │
      └─ Return serialized profile

Frontend (Web) - Continued
├─ Receive: DeploymentProfileRead (201)
├─ Toast: "Profile created"
├─ Query invalidation: deploymentProfileKeys.list(projectId)
└─ UI updates: profiles list shows new profile
```

---

## Platform Auto-Population Flow

```
User selects platform in dropdown
        ↓
onValueChange event fires
        ↓
Call: defaultRootDir(selectedPlatform)
        ├─ Platform.CLAUDE_CODE → ".claude"
        ├─ Platform.CODEX → ".codex"
        ├─ Platform.GEMINI → ".gemini"
        ├─ Platform.CURSOR → ".cursor"
        └─ Platform.OTHER → ".custom"
        ↓
Update form state:
  setCreateForm(prev => ({
    ...prev,
    platform: value as Platform,
    root_dir: defaultRootDir(value as Platform)
  }))
        ↓
UI re-renders with new root_dir value
        ↓
User can still manually override root_dir if needed
```

---

## Form State Conversion Flow

### Creating Profile (Form → API)

```
ProfileFormState (Component State)
{
  profile_id: "claude-default",
  platform: "claude_code",                    // enum value
  root_dir: ".claude",
  artifact_path_map_json: "{\"skill\": \"skills/\"}",  // STRING
  project_config_filenames: "CLAUDE.md\n.claude.config",  // STRING
  context_path_prefixes: ".claude/context/\n.claude/",   // STRING
  supported_artifact_types: "skill, command, agent"      // STRING
}
        ↓
parseCreatePayload(form)
        ├─ JSON.parse(artifact_path_map_json)
        │  └─ "{\"skill\": \"skills/\"}" → {skill: "skills/"}
        ├─ toList(project_config_filenames)
        │  └─ "CLAUDE.md\n.claude.config".split(/[\n,]/) → ["CLAUDE.md", ".claude.config"]
        ├─ toList(context_path_prefixes)
        │  └─ ".claude/context/\n.claude/".split(/[\n,]/) → [".claude/context/", ".claude/"]
        └─ toList(supported_artifact_types)
           └─ "skill, command, agent".split(/[\n,]/) → ["skill", "command", "agent"]
        ↓
CreateDeploymentProfileRequest (API Request)
{
  profile_id: "claude-default",
  platform: "claude_code",
  root_dir: ".claude",
  artifact_path_map: {skill: "skills/"},
  project_config_filenames: ["CLAUDE.md", ".claude.config"],
  context_path_prefixes: [".claude/context/", ".claude/"],
  supported_artifact_types: ["skill", "command", "agent"]
}
        ↓
JSON.stringify() for HTTP body
        ↓
Sent to API: POST /projects/{projectId}/profiles
```

### Reading Profile (DB → Component)

```
Database (SQLite)
{
  id: "abc123...",
  project_id: "proj1",
  profile_id: "claude-default",
  platform: "claude_code",              // stored as string
  root_dir: ".claude",
  artifact_path_map: {skill: "skills/"}, // stored as JSON
  config_filenames: ["CLAUDE.md", "..."],  // stored as JSON array
  context_prefixes: [...],              // stored as JSON array
  supported_types: [...],               // stored as JSON array
  created_at: "2026-02-09T...",
  updated_at: "2026-02-09T..."
}
        ↓
_to_read_model() in router (deployment_profiles.py)
        ├─ Map DB columns to API response fields:
        │  ├─ config_filenames → project_config_filenames
        │  ├─ context_prefixes → context_path_prefixes
        │  └─ supported_types → supported_artifact_types
        └─ Return DeploymentProfileRead
        ↓
HTTP Response (200 OK)
DeploymentProfileRead {
  id: "abc123...",
  project_id: "proj1",
  profile_id: "claude-default",
  platform: "claude_code",
  root_dir: ".claude",
  artifact_path_map: {skill: "skills/"},
  project_config_filenames: ["CLAUDE.md", "..."],
  context_path_prefixes: [...],
  supported_artifact_types: [...],
  created_at: "2026-02-09T...",
  updated_at: "2026-02-09T..."
}
        ↓
React Query caches response
        ↓
useDeploymentProfiles() returns DeploymentProfile[]
        ↓
Component receives profiles from useDeploymentProfiles hook
        ↓
profileToForm(profile) for editing
        ├─ JSON.stringify(artifact_path_map, null, 2)
        │  └─ {skill: "skills/"} → "{\"skill\": \"skills/\"}"  // PRETTY
        ├─ (arrays).join('\n')
        │  └─ ["CLAUDE.md", "..."].join('\n') → "CLAUDE.md\n..."
        └─ Return ProfileFormState
        ↓
Form displayed with stringified/formatted values
```

---

## Database Schema

```sql
CREATE TABLE deployment_profiles (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  root_dir TEXT NOT NULL,
  artifact_path_map JSON,
  config_filenames JSON,        -- List[str]
  context_prefixes JSON,        -- List[str]
  supported_types JSON,         -- List[str]
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,

  UNIQUE(project_id, profile_id),
  CHECK(platform IN ('claude_code', 'codex', 'gemini', 'cursor', 'other')),
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX idx_deployment_profiles_project_profile
  ON deployment_profiles(project_id, profile_id);
```

**Key Constraints**:
- **Primary Key**: `id` (UUID)
- **Unique**: `(project_id, profile_id)` - profile IDs must be unique per project
- **Foreign Key**: `project_id` → `projects.id` (CASCADE DELETE)
- **Check**: Platform must be one of 5 valid enum values

---

## API Endpoint Mapping

### Create Profile
```
POST /api/v1/projects/{project_id}/profiles
Content-Type: application/json

Request Body (CreateDeploymentProfileRequest):
{
  "profile_id": "claude-default",
  "platform": "claude_code",
  "root_dir": ".claude",
  "artifact_path_map": {"skill": "skills/"},
  "project_config_filenames": ["CLAUDE.md"],
  "context_path_prefixes": [".claude/context/"],
  "supported_artifact_types": ["skill", "command", "agent"]
}

Response (201 Created):
DeploymentProfileRead (same structure with id, created_at, updated_at added)
```

### List Profiles
```
GET /api/v1/projects/{project_id}/profiles

Response (200 OK):
List[DeploymentProfileRead]
[
  {
    "id": "uuid1",
    "project_id": "proj1",
    "profile_id": "claude-default",
    ... (rest of DeploymentProfileRead)
  },
  ...
]
```

### Get Single Profile
```
GET /api/v1/projects/{project_id}/profiles/{profile_id}

Response (200 OK):
DeploymentProfileRead
```

### Update Profile
```
PUT /api/v1/projects/{project_id}/profiles/{profile_id}
Content-Type: application/json

Request Body (UpdateDeploymentProfileRequest):
{
  "platform": "codex",  // Optional
  "root_dir": ".codex",  // Optional
  "artifact_path_map": {...},  // Optional
  ...
}

Note: profile_id is IMMUTABLE (not included in update)

Response (200 OK):
DeploymentProfileRead (updated)
```

### Delete Profile
```
DELETE /api/v1/projects/{project_id}/profiles/{profile_id}

Response (204 No Content)
```

---

## Type System: Frontend ↔ Backend Alignment

### Platform Enum
```
TypeScript (web/types/enums.ts)        Python (core/enums.py)
Platform.CLAUDE_CODE = 'claude_code' ↔ Platform.CLAUDE_CODE = 'claude_code'
Platform.CODEX = 'codex'             ↔ Platform.CODEX = 'codex'
Platform.GEMINI = 'gemini'           ↔ Platform.GEMINI = 'gemini'
Platform.CURSOR = 'cursor'           ↔ Platform.CURSOR = 'cursor'
Platform.OTHER = 'other'             ↔ Platform.OTHER = 'other'

** Values must match exactly **
```

### Field Naming (DB ↔ API)
```
Database Column          API Field (Response)
─────────────────────────────────────────────
config_filenames      → project_config_filenames
context_prefixes      → context_path_prefixes
supported_types       → supported_artifact_types
(others)              → (same name)
```

---

## Component Tree

```
/projects/[id]/profiles (Page)
├─ Create Card
│  ├─ Profile ID Input
│  ├─ Platform Select Dropdown
│  │  └─ onValueChange → defaultRootDir() → root_dir auto-populates
│  ├─ Root Dir Input (overridable)
│  ├─ Artifact Path Map Textarea (JSON)
│  ├─ Config Filenames Textarea (newline/comma-separated)
│  ├─ Context Prefixes Textarea (newline/comma-separated)
│  ├─ Supported Artifact Types Input (comma-separated)
│  └─ Create Button
│     └─ onClick → handleCreate()
│        └─ mutateAsync(parseCreatePayload(createForm))
│
├─ Configured Profiles List
│  └─ for each profile:
│     ├─ Display Mode:
│     │  ├─ Profile ID
│     │  ├─ Root Dir
│     │  ├─ Platform Badge
│     │  ├─ Artifact Path Map (JSON display)
│     │  ├─ Edit Button
│     │  └─ Delete Button
│     │
│     └─ Edit Mode:
│        ├─ Platform Select (changeable)
│        ├─ Root Dir Input (changeable)
│        ├─ Artifact Path Map Textarea (changeable)
│        ├─ Save Button
│        │  └─ onClick → handleSaveEdit()
│        │     └─ mutateAsync({profileId, data: parseUpdatePayload()})
│        └─ Cancel Button
│
└─ useDeploymentProfiles(projectId)
   └─ Query cache (staleTime: 60s)
      ├─ invalidateQueries on create/update/delete
      └─ Returns: DeploymentProfile[]
```

---

## Integration with Deployments

```
Deployment Flow (when deploying artifact)
├─ User selects artifact to deploy
├─ Option A: Deploy to single profile
│  ├─ Select from: useProfileSelector()
│  └─ Send: deploymentParams = {
│       all_profiles: false,
│       deployment_profile_id: selectedProfileId
│     }
│
├─ Option B: Deploy to all profiles
│  └─ Send: deploymentParams = {
│       all_profiles: true,
│       deployment_profile_id: undefined
│     }
│
└─ API processes deployment per profile
   ├─ For each profile:
   │  ├─ Resolve: artifact_path_map[artifact_type] → target_subdir
   │  ├─ Construct: {root_dir}/{target_subdir}/{artifact_name}/
   │  ├─ Deploy artifact files there
   │  ├─ Create: ArtifactDeploymentInfo with:
   │  │  ├─ deployment_profile_id
   │  │  ├─ platform
   │  │  └─ profile_root_dir
   │  └─ Store in DB
   │
   └─ Response includes:
      ├─ deployed_profiles: [profile_ids...]
      ├─ platform
      └─ profile_root_dir
```

---

## Query Key Structure (React Query)

```
deploymentProfileKeys
├─ all: ['deployment-profiles']
├─ list(projectId?: string)
│  └─ ['deployment-profiles', projectId]
│     Query hook: useDeploymentProfiles(projectId)
│     Stale time: 60 seconds
│     Invalidated on: create/update/delete profile
│
└─ status(projectId?: string, artifactId?: string)
   └─ ['deployment-profiles', 'status', projectId, artifactId]
      Query hook: useDeploymentStatus(artifactId, projectId)
      Purpose: Check deployment status per profile
      Returns: DeploymentStatus (aggregated across profiles)
```

---

## Settings Page Architecture (Current)

```
/settings (Page)
├─ General Settings Card
│  └─ (placeholder)
│
├─ API Configuration Card
│  ├─ API URL (read-only)
│  └─ Version (read-only)
│
└─ GitHub Settings Component

Note: Platform Defaults NOT YET IMPLEMENTED
Future enhancement could add:
├─ Default Platform Selection
├─ Platform-specific Root Dirs
├─ Platform-specific Artifact Maps
├─ Platform-specific Config Filenames
├─ Platform-specific Context Prefixes
└─ Platform-specific Supported Types
```

# MeatyPrompts Architecture Reference

## Layered Architecture

MeatyPrompts follows a strict layered architecture with clear separation of concerns:

```
Routers → Services → Repositories → Database
```

### Layer Responsibilities

**1. Routers (API Layer)**
- HTTP request handling and validation
- Route definitions and endpoint mapping
- Request/response formatting
- Return DTOs only (never ORM models)
- OpenAPI documentation
- Authentication/authorization checks

**Location**: `services/api/app/routers/`

**2. Services (Business Logic Layer)**
- Business logic and workflows
- DTO validation and transformation
- Orchestration of repository calls
- Return DTOs only (never ORM models)
- No direct database access
- Error handling and logging

**Location**: `services/api/app/services/`

**3. Repositories (Data Access Layer)**
- All database I/O operations
- RLS (Row Level Security) enforcement
- Transaction management
- Cursor pagination implementation
- ORM model usage (internal only)
- Automatic rollback on exceptions

**Location**: `services/api/app/repositories/`

**4. Database**
- PostgreSQL with RLS policies
- Alembic migrations
- Indexes and constraints
- Audit triggers and functions

**Location**: `services/api/alembic/versions/`

---

## Non-Negotiables

### 1. Separation of Concerns

❌ **NEVER**:
- SQL in services or routers
- ORM models in service return types
- Direct database access from services
- Business logic in repositories

✅ **ALWAYS**:
- DTOs for service/router interfaces
- All DB I/O through repositories
- Business logic in services
- Transaction management in repositories

### 2. Data Transfer Objects (DTOs)

**Purpose**: Clean contract between layers

**Location**: `services/api/app/schemas/`

**Rules**:
- Services return DTOs, never ORM models
- Pydantic schemas for validation
- Separate request/response DTOs
- No circular dependencies

**Example**:
```python
# schemas/prompt.py
class PromptResponse(BaseModel):
    id: UUID
    title: str
    content: str
    created_at: datetime

# services/prompt_service.py
def get_prompt(id: UUID) -> PromptResponse:
    orm_model = repo.get_by_id(id)
    return PromptResponse.from_orm(orm_model)
```

### 3. Error Handling

**ErrorResponse Envelope**: All errors use standard envelope

```python
{
    "error": {
        "code": "RESOURCE_NOT_FOUND",
        "message": "Prompt not found",
        "details": {...}
    }
}
```

**Location**: `services/api/app/core/errors.py`

### 4. Pagination

**Cursor Pagination**: All list endpoints use cursor pagination

```python
{
    "items": [...],
    "pageInfo": {
        "hasNextPage": true,
        "endCursor": "cursor_value"
    }
}
```

**Location**: `services/api/app/core/pagination.py`

### 5. Observability

**OpenTelemetry Spans**: All operations instrumented

```python
with tracer.start_as_current_span("prompt.get") as span:
    span.set_attribute("prompt_id", str(prompt_id))
    # operation
```

**Structured Logging**: JSON logs with context

```python
logger.info("Prompt retrieved", extra={
    "trace_id": trace_id,
    "span_id": span_id,
    "user_id": user_id,
    "prompt_id": prompt_id
})
```

**Location**: `services/api/app/core/observability.py`

---

## Layer-Specific Patterns

### Database Layer Patterns

**Migrations**:
```python
# Alembic migration
def upgrade():
    op.create_table(
        'prompts',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        # ...
        sa.PrimaryKeyConstraint('id')
    )

    # RLS Policy
    op.execute("""
        ALTER TABLE prompts ENABLE ROW LEVEL SECURITY;
        CREATE POLICY user_isolation ON prompts
        USING (user_id = current_setting('app.user_id'));
    """)
```

**Indexes**:
```python
op.create_index(
    'idx_prompts_user_id_created',
    'prompts',
    ['user_id', 'created_at'],
    postgresql_ops={'created_at': 'DESC'}
)
```

### Repository Layer Patterns

**Base Repository**:
```python
class BaseRepository:
    def __init__(self, session: Session):
        self._session = session

    @contextmanager
    def _transaction_context(self):
        try:
            yield
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            logger.error("Transaction rolled back", exc_info=e)
            raise
```

**Cursor Pagination**:
```python
def list_prompts(self, cursor: str = None, limit: int = 20) -> tuple[list[PromptORM], PageInfo]:
    query = self._session.query(PromptORM)

    if cursor:
        decoded = decode_cursor(cursor)
        query = query.filter(PromptORM.created_at < decoded['created_at'])

    items = query.order_by(PromptORM.created_at.desc()).limit(limit + 1).all()
    has_next = len(items) > limit

    if has_next:
        items = items[:limit]

    return items, PageInfo(hasNextPage=has_next, endCursor=encode_cursor(items[-1]))
```

### Service Layer Patterns

**DTO Mapping**:
```python
class PromptService:
    def __init__(self, repo: PromptRepository):
        self._repo = repo

    def get_prompt(self, prompt_id: UUID) -> PromptResponse:
        orm_model = self._repo.get_by_id(prompt_id)
        if not orm_model:
            raise NotFoundException(f"Prompt {prompt_id} not found")

        return PromptResponse.from_orm(orm_model)
```

**Business Logic**:
```python
def create_prompt(self, request: CreatePromptRequest) -> PromptResponse:
    # Validation
    if len(request.content) > MAX_CONTENT_LENGTH:
        raise ValidationException("Content too long")

    # Business logic
    prompt = self._repo.create({
        "title": request.title,
        "content": request.content,
        "user_id": request.user_id
    })

    # Return DTO
    return PromptResponse.from_orm(prompt)
```

### API Layer Patterns

**Router Setup**:
```python
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/prompts", tags=["prompts"])

@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: UUID,
    service: PromptService = Depends(get_prompt_service)
):
    return service.get_prompt(prompt_id)
```

**Error Handling**:
```python
@router.post("/", response_model=PromptResponse)
async def create_prompt(
    request: CreatePromptRequest,
    service: PromptService = Depends(get_prompt_service)
):
    try:
        return service.create_prompt(request)
    except ValidationException as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error("Unexpected error", exc_info=e)
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Frontend Architecture

### UI Component Pattern

**Import from @meaty/ui only**:
```typescript
// ✅ Correct
import { Button, Card } from '@meaty/ui';

// ❌ Wrong
import { Button } from '@radix-ui/react-button';
```

**Location**:
- Shared components: `packages/ui/src/components/`
- Web app: `apps/web/src/components/`
- Mobile app: `apps/mobile/src/components/`

### React Query Pattern

**Data Fetching**:
```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['prompts', promptId],
  queryFn: () => api.getPrompt(promptId)
});
```

**Mutations**:
```typescript
const mutation = useMutation({
  mutationFn: (data: CreatePromptRequest) => api.createPrompt(data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['prompts'] });
  }
});
```

---

## Testing Architecture

### Unit Tests

- Services: Mock repositories
- Repositories: Use test database
- Components: Mock API calls

### Integration Tests

- API endpoints with real database
- Repository + Service integration
- Component + API integration

### E2E Tests

- Full user journeys
- Playwright with auth bypass
- Critical workflows only

---

## Authentication

**Clerk Integration**:
- Frontend: Clerk React components
- Backend: JWT validation with JWKS
- Dev bypass: X-Dev-Auth-Bypass header (dev only)

**Location**:
- Frontend: `apps/web/src/providers/AuthProvider.tsx`
- Backend: `services/api/app/core/auth.py`

---

## References

- **ADRs**: `/docs/architecture/ADRs/`
- **API Docs**: `/docs/api/`
- **Guides**: `/docs/guides/`
- **Symbol System**: `/ai/symbols-*.json`

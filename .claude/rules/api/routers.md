# Router Layer Rules

<!-- Path Scope: skillmeat/api/routers/**/*.py -->

FastAPI router layer patterns.

## Layer Contract

**Routers SHOULD**:
- Define HTTP endpoints and parse requests
- Serialize responses via Pydantic
- Call service/manager layer for business logic

**Routers must NOT**:
- Access database directly
- Implement business logic
- Handle file I/O directly

## Architecture Flow

```
routers/ → managers/services → repositories → database
```

## Key Patterns

| Pattern | Rule |
|---------|------|
| All handlers | `async def` |
| Status codes | GET→200, POST→201, PUT→200, DELETE→204 |
| Errors | Log before raising HTTPException |
| Types | Explicit type hints always |

## Dependencies

```python
# Use Annotated type aliases
DbSessionDep = Annotated[Session, Depends(get_db_session)]
```

## Detailed Reference

For available routers, examples, and HTTPException patterns:
**Read**: `.claude/context/key-context/router-patterns.md`

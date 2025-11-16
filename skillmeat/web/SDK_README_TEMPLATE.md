# SkillMeat TypeScript SDK

This is an auto-generated TypeScript SDK for the SkillMeat API. It provides type-safe access to all API endpoints with full TypeScript support.

> **⚠️ Warning**: This directory is auto-generated. Do not modify files in this directory directly. Your changes will be overwritten on the next SDK generation.

## Generation

This SDK is generated from the OpenAPI specification using `openapi-typescript-codegen`.

To regenerate the SDK:

```bash
# Using the CLI (recommended)
skillmeat web generate-sdk

# Or using the script directly
./scripts/generate-sdk.sh

# Or using pnpm in the web directory
cd skillmeat/web
pnpm run generate-sdk
```

## Installation

The SDK is part of the SkillMeat web package and does not require separate installation.

## Quick Start

### Basic Usage

```typescript
import { apiClient } from '@/lib/api-client';

// List collections
const collections = await apiClient.collections.listCollections();

// Get a specific collection
const collection = await apiClient.collections.getCollection({
  name: 'my-collection',
});

// Create a new collection
const newCollection = await apiClient.collections.createCollection({
  requestBody: {
    name: 'new-collection',
    description: 'My new collection',
  },
});
```

### Authentication

The SDK automatically handles authentication using tokens stored in localStorage.

```typescript
import { auth } from '@/lib/api-client';

// Set authentication token
auth.setToken('your-jwt-token');

// Check if authenticated
if (auth.isAuthenticated()) {
  console.log('User is authenticated');
}

// Remove token (logout)
auth.removeToken();
```

### Error Handling

The SDK throws `ApiError` for HTTP errors:

```typescript
import { apiClient, ApiError } from '@/lib/api-client';

try {
  const collection = await apiClient.collections.getCollection({
    name: 'non-existent',
  });
} catch (error) {
  if (error instanceof ApiError) {
    console.error(`API Error (${error.statusCode}): ${error.message}`);
    console.error('Details:', error.details);
  } else {
    console.error('Unexpected error:', error);
  }
}
```

### Custom Configuration

You can create a custom API client instance with different configuration:

```typescript
import { createApiClient } from '@/lib/api-client';

const customClient = createApiClient({
  baseUrl: 'https://api.example.com',
  apiVersion: 'v2',
  onUnauthorized: () => {
    // Handle 401 errors (e.g., redirect to login)
    window.location.href = '/login';
  },
  onError: (error) => {
    // Global error handler
    console.error('API Error:', error);
  },
});
```

## React Hooks

### Example: Using with React Query

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

// Fetch collections
function useCollections() {
  return useQuery({
    queryKey: ['collections'],
    queryFn: () => apiClient.collections.listCollections(),
  });
}

// Create collection
function useCreateCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      apiClient.collections.createCollection({ requestBody: data }),
    onSuccess: () => {
      // Invalidate collections query to refetch
      queryClient.invalidateQueries({ queryKey: ['collections'] });
    },
  });
}

// Usage in component
function CollectionsPage() {
  const { data: collections, isLoading, error } = useCollections();
  const createCollection = useCreateCollection();

  const handleCreate = async () => {
    try {
      await createCollection.mutateAsync({
        name: 'new-collection',
        description: 'Created from UI',
      });
    } catch (error) {
      console.error('Failed to create collection:', error);
    }
  };

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <button onClick={handleCreate}>Create Collection</button>
      <ul>
        {collections?.map((collection) => (
          <li key={collection.name}>{collection.name}</li>
        ))}
      </ul>
    </div>
  );
}
```

### Example: Server-Side Data Fetching (Next.js)

```typescript
// app/collections/page.tsx
import { apiClient } from '@/lib/api-client';

export default async function CollectionsPage() {
  // Fetch data on the server
  const collections = await apiClient.collections.listCollections();

  return (
    <div>
      <h1>Collections</h1>
      <ul>
        {collections.map((collection) => (
          <li key={collection.name}>{collection.name}</li>
        ))}
      </ul>
    </div>
  );
}
```

## Pagination

The API client includes utilities for handling pagination:

```typescript
import { apiClient, apiUtils } from '@/lib/api-client';

// Build pagination parameters
const params = apiUtils.buildPaginationParams({
  page: 1,
  pageSize: 20,
});

// Fetch paginated data
const artifacts = await apiClient.artifacts.listArtifacts({
  skip: params.skip,
  limit: params.limit,
});

// Build paginated response
const response = apiUtils.buildPaginatedResponse(
  artifacts.items,
  artifacts.total,
  { page: 1, pageSize: 20 },
);

console.log('Has more pages:', response.hasMore);
console.log('Total items:', response.total);
```

## Loading States

Handle loading states with the utility function:

```typescript
import { apiClient, apiUtils } from '@/lib/api-client';
import { useState } from 'react';

function MyComponent() {
  const [loading, setLoading] = useState(false);

  const handleFetch = async () => {
    const collections = await apiUtils.withLoading(
      () => apiClient.collections.listCollections(),
      setLoading,
    );

    console.log('Collections:', collections);
  };

  return (
    <button onClick={handleFetch} disabled={loading}>
      {loading ? 'Loading...' : 'Fetch Collections'}
    </button>
  );
}
```

## Available Services

The SDK provides the following services (exact endpoints depend on the API):

- `health` - Health check endpoints
- `collections` - Collection management
- `artifacts` - Artifact management
- `deployments` - Deployment management
- `analytics` - Usage analytics
- `marketplace` - Marketplace integration

Refer to the generated types in `./models` for detailed request/response schemas.

## TypeScript Support

The SDK is fully typed with TypeScript. Your IDE will provide autocomplete and type checking:

```typescript
// Type inference works automatically
const collection = await apiClient.collections.getCollection({
  name: 'my-collection',
});

// TypeScript knows the shape of 'collection'
console.log(collection.name); // ✓ Valid
console.log(collection.invalidField); // ✗ TypeScript error
```

## API Reference

For detailed API documentation, see:

- OpenAPI Specification: `../api/openapi.json`
- Interactive API Docs: http://localhost:8000/docs (when running dev server)
- ReDoc Documentation: http://localhost:8000/redoc (when running dev server)

## Troubleshooting

### SDK is out of sync with API

Regenerate the SDK:

```bash
skillmeat web generate-sdk
```

### Type errors after updating

1. Regenerate the SDK
2. Restart your TypeScript server (in VSCode: `Cmd+Shift+P` > "Restart TS Server")
3. Check that your API usage matches the latest schema

### Authentication not working

Ensure you have a valid token:

```typescript
import { auth } from '@/lib/api-client';

// Generate a token via CLI
// skillmeat web token generate --show-token

// Set it in your app
auth.setToken('your-token-here');

// Verify
console.log('Authenticated:', auth.isAuthenticated());
```

## Development

### Modifying the SDK Wrapper

The SDK wrapper (`../lib/api-client.ts`) is NOT auto-generated and can be modified.

It provides:

- Configured SDK instance (`apiClient`)
- Authentication helpers (`auth`)
- Utility functions (`apiUtils`)
- Custom error types (`ApiError`)

### Customizing Generation

The SDK generation is configured in:

- `../package.json` - npm script with generation options
- `../../api/openapi.py` - OpenAPI spec customization
- `../../scripts/generate-sdk.sh` - Generation orchestration

## Support

For issues or questions:

- Check the main SkillMeat documentation
- Review the API documentation at `/docs`
- Open an issue on GitHub

---

**Version**: Auto-generated from API
**Generated**: Check file modification time
**Generator**: openapi-typescript-codegen

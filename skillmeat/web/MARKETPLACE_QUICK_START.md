# Marketplace UI Quick Start Guide

## Running the Marketplace

### 1. Start the Backend API

```bash
cd /home/user/skillmeat
python -m skillmeat.api.server
```

The API will run on `http://localhost:8000`

### 2. Start the Web Interface

```bash
cd /home/user/skillmeat/skillmeat/web
npm run dev
# or
pnpm dev
```

The web app will run on `http://localhost:3000`

### 3. Navigate to Marketplace

Open browser: `http://localhost:3000/marketplace`

## File Structure

```
skillmeat/web/
├── app/
│   └── marketplace/
│       ├── page.tsx                 # Main catalog page
│       ├── [listing_id]/
│       │   └── page.tsx             # Detail page
│       └── publish/
│           └── page.tsx             # Publish wizard
├── components/
│   └── marketplace/
│       ├── MarketplaceListingCard.tsx
│       ├── MarketplaceFilters.tsx
│       ├── MarketplaceListingDetail.tsx
│       ├── MarketplaceBrokerSelector.tsx
│       ├── MarketplaceInstallDialog.tsx
│       ├── MarketplacePublishWizard.tsx
│       └── MarketplaceStats.tsx
├── hooks/
│   └── useMarketplace.ts            # React Query hooks
├── types/
│   └── marketplace.ts               # TypeScript types
├── lib/
│   └── utils.ts                     # Utilities (cn function)
└── __tests__/
    └── marketplace/                 # Unit tests
```

## Key User Flows

### Browse Listings

1. Navigate to `/marketplace`
2. See statistics dashboard
3. Browse listings in grid view
4. Use filters (search, tags, license, publisher)
5. Click "Load More" for pagination

### View Listing Detail

1. Click any listing card
2. See full details, metadata, tags
3. View signature verification
4. Access external links (homepage, repo)

### Install Bundle

1. From listing detail, click "Install Bundle"
2. Select conflict resolution strategy
3. Review trust warning
4. Click "Install Bundle"
5. See success toast notification

### Publish Bundle

1. Click "Publish Bundle" from marketplace
2. Enter bundle path
3. Select broker
4. Fill metadata (description, tags, links)
5. Review and confirm
6. See submission result

## Testing

### Run Unit Tests

```bash
npm run test
# or
pnpm test
```

### Run E2E Tests

```bash
npm run test:e2e
# or
pnpm test:e2e
```

### Run E2E Tests in UI Mode

```bash
npm run test:e2e:ui
```

## API Endpoints Used

- `GET /api/marketplace/listings` - Fetch paginated listings
- `GET /api/marketplace/listings/{id}` - Get listing detail
- `GET /api/marketplace/brokers` - List available brokers
- `POST /api/marketplace/install` - Install bundle
- `POST /api/marketplace/publish` - Publish bundle

## Configuration

### Environment Variables

Create `.env.local` in web directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Broker Setup

Brokers must be configured in the backend:

```bash
skillmeat broker enable skillmeat --endpoint https://marketplace.skillmeat.dev/api
```

## Troubleshooting

### "Failed to load listings"

- Check backend API is running
- Verify broker configuration
- Check network tab for API errors
- Ensure CORS is configured

### "No brokers available for publishing"

- At least one broker must support publishing
- Check `broker.supports_publish = true`
- Verify broker is enabled

### TypeScript Errors

```bash
npm run type-check
```

### Build Errors

```bash
rm -rf .next
npm run build
```

## Component Props Reference

### MarketplaceListingCard

```tsx
<MarketplaceListingCard listing={listing} onClick={(listing) => console.log(listing)} />
```

### MarketplaceFilters

```tsx
<MarketplaceFilters filters={filters} onFiltersChange={setFilters} brokers={brokers} />
```

### MarketplaceInstallDialog

```tsx
<MarketplaceInstallDialog
  listing={selectedListing}
  isOpen={isDialogOpen}
  onClose={() => setIsDialogOpen(false)}
  onConfirm={(strategy) => handleInstall(strategy)}
  isInstalling={isLoading}
/>
```

### MarketplacePublishWizard

```tsx
<MarketplacePublishWizard
  brokers={brokers}
  onPublish={async (data) => await publishBundle(data)}
  onCancel={() => router.push('/marketplace')}
/>
```

## Next Steps

1. Configure marketplace brokers in backend
2. Create test bundles for publishing
3. Run E2E tests to verify flows
4. Customize styling if needed
5. Deploy to production

## Support

- GitHub Issues: https://github.com/miethe/skillmeat/issues
- Documentation: See MARKETPLACE_UI_IMPLEMENTATION.md
- API Docs: http://localhost:8000/docs (when API running)

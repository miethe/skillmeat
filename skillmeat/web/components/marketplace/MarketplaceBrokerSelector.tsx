'use client';

import { Check, Server } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { BrokerInfo } from '@/types/marketplace';

interface MarketplaceBrokerSelectorProps {
  brokers: BrokerInfo[];
  selected?: string;
  onChange: (brokerName: string) => void;
}

export function MarketplaceBrokerSelector({
  brokers,
  selected,
  onChange,
}: MarketplaceBrokerSelectorProps) {
  // Filter to only enabled brokers that support publishing
  const availableBrokers = brokers.filter((broker) => broker.enabled && broker.supports_publish);

  if (availableBrokers.length === 0) {
    return (
      <Card className="p-6 text-center">
        <Server className="mx-auto mb-3 h-12 w-12 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">No brokers available for publishing.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Please configure at least one broker in settings.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-3" role="radiogroup" aria-label="Select broker">
      {availableBrokers.map((broker) => {
        const isSelected = selected === broker.name;

        return (
          <Card
            key={broker.name}
            className={`cursor-pointer p-4 transition-all ${
              isSelected
                ? 'border-primary bg-primary/5 shadow-sm'
                : 'hover:border-primary/50 hover:shadow-sm'
            }`}
            onClick={() => onChange(broker.name)}
            role="radio"
            aria-checked={isSelected}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onChange(broker.name);
              }
            }}
          >
            <div className="flex items-start gap-3">
              {/* Selection Indicator */}
              <div
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 ${
                  isSelected ? 'border-primary bg-primary' : 'border-muted-foreground'
                }`}
              >
                {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
              </div>

              {/* Broker Info */}
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex items-center gap-2">
                  <h3 className="font-semibold capitalize">{broker.name}</h3>
                  {isSelected && (
                    <Badge variant="secondary" className="text-xs">
                      Selected
                    </Badge>
                  )}
                </div>

                {broker.description && (
                  <p className="mb-2 text-sm text-muted-foreground">{broker.description}</p>
                )}

                <p className="truncate font-mono text-xs text-muted-foreground">
                  {broker.endpoint}
                </p>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

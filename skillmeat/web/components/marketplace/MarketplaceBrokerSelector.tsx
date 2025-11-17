"use client";

import { Check, Server } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { BrokerInfo } from "@/types/marketplace";

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
  const availableBrokers = brokers.filter(
    (broker) => broker.enabled && broker.supports_publish
  );

  if (availableBrokers.length === 0) {
    return (
      <Card className="p-6 text-center">
        <Server className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          No brokers available for publishing.
        </p>
        <p className="text-xs text-muted-foreground mt-1">
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
            className={`p-4 cursor-pointer transition-all ${
              isSelected
                ? "border-primary bg-primary/5 shadow-sm"
                : "hover:border-primary/50 hover:shadow-sm"
            }`}
            onClick={() => onChange(broker.name)}
            role="radio"
            aria-checked={isSelected}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onChange(broker.name);
              }
            }}
          >
            <div className="flex items-start gap-3">
              {/* Selection Indicator */}
              <div
                className={`mt-0.5 h-5 w-5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                  isSelected
                    ? "border-primary bg-primary"
                    : "border-muted-foreground"
                }`}
              >
                {isSelected && <Check className="h-3 w-3 text-primary-foreground" />}
              </div>

              {/* Broker Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold capitalize">{broker.name}</h3>
                  {isSelected && (
                    <Badge variant="secondary" className="text-xs">
                      Selected
                    </Badge>
                  )}
                </div>

                {broker.description && (
                  <p className="text-sm text-muted-foreground mb-2">
                    {broker.description}
                  </p>
                )}

                <p className="text-xs text-muted-foreground font-mono truncate">
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

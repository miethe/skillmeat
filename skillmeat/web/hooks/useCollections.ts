import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

export interface CollectionSummary {
  id: string;
  name: string;
  artifact_count?: number;
}

export function useCollections() {
  return useQuery<CollectionSummary[]>({
    queryKey: ["collections"],
    queryFn: async () => {
      const res = await fetch("/api/v1/collections");
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to load collections");
      }
      const data = await res.json();
      // Normalize shape: expect items array or raw list
      if (Array.isArray(data)) return data as CollectionSummary[];
      if (Array.isArray(data.items)) return data.items as CollectionSummary[];
      return [];
    },
    onError: (err: any) => {
      toast.error("Failed to load collections", { description: err.message });
    },
  });
}

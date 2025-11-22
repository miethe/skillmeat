import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

export interface CollectionArtifact {
  id: string;
  name: string;
  type: string;
}

export function useCollectionArtifacts(collection?: string) {
  return useQuery<CollectionArtifact[]>({
    queryKey: ["collection-artifacts", collection],
    enabled: !!collection,
    queryFn: async () => {
      const res = await fetch(`/api/v1/collections/${collection}/artifacts`);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to load artifacts");
      }
      const data = await res.json();
      if (Array.isArray(data.items)) {
        return data.items.map((item: any) => ({
          id: item.id || `${item.type}:${item.name}`,
          name: item.name,
          type: item.type,
        }));
      }
      if (Array.isArray(data)) {
        return data.map((item: any) => ({
          id: item.id || `${item.type}:${item.name}`,
          name: item.name,
          type: item.type,
        }));
      }
      return [];
    },
    onError: (err: any) => {
      toast.error("Failed to load artifacts", { description: err.message });
    },
  });
}

'use client';

import { useState } from 'react';
import { Plus, Trash2, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { EnvVarEntry } from '@/types/mcp';

interface MCPEnvEditorProps {
  envVars: EnvVarEntry[];
  onChange: (envVars: EnvVarEntry[]) => void;
  disabled?: boolean;
}

export function MCPEnvEditor({ envVars, onChange, disabled }: MCPEnvEditorProps) {
  const [showValues, setShowValues] = useState<Record<number, boolean>>({});

  const handleAdd = () => {
    onChange([...envVars, { key: '', value: '' }]);
  };

  const handleRemove = (index: number) => {
    const newEnvVars = envVars.filter((_, i) => i !== index);
    onChange(newEnvVars);

    // Clean up showValues state
    const newShowValues = { ...showValues };
    delete newShowValues[index];
    setShowValues(newShowValues);
  };

  const handleKeyChange = (index: number, key: string) => {
    const newEnvVars = [...envVars];
    const current = newEnvVars[index];
    if (!current) return;

    newEnvVars[index] = { ...current, key };
    onChange(newEnvVars);
  };

  const handleValueChange = (index: number, value: string) => {
    const newEnvVars = [...envVars];
    const current = newEnvVars[index];
    if (!current) return;

    newEnvVars[index] = { ...current, value };
    onChange(newEnvVars);
  };

  const toggleShowValue = (index: number) => {
    setShowValues((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  return (
    <div className="space-y-3">
      {/* Environment variable rows */}
      {envVars.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed py-6 text-center text-sm text-muted-foreground">
          No environment variables configured
        </div>
      ) : (
        <div className="space-y-2">
          {envVars.map((envVar, index) => (
            <div key={index} className="flex items-start gap-2 rounded-lg border bg-muted/50 p-3">
              <div className="flex-1 space-y-2">
                {/* Key input */}
                <Input
                  placeholder="Variable name (e.g., ROOT_PATH)"
                  value={envVar.key}
                  onChange={(e) => handleKeyChange(index, e.target.value)}
                  disabled={disabled}
                  className="font-mono text-sm"
                  aria-label={`Environment variable name ${index + 1}`}
                />

                {/* Value input */}
                <div className="relative">
                  <Input
                    type={showValues[index] ? 'text' : 'password'}
                    placeholder="Variable value"
                    value={envVar.value}
                    onChange={(e) => handleValueChange(index, e.target.value)}
                    disabled={disabled}
                    className="pr-10 font-mono text-sm"
                    aria-label={`Environment variable value ${index + 1}`}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleShowValue(index)}
                    className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                    disabled={disabled}
                    aria-label={showValues[index] ? 'Hide value' : 'Show value'}
                  >
                    {showValues[index] ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </Button>
                </div>

                {/* Required indicator */}
                {envVar.required && (
                  <p className="text-xs text-muted-foreground">Required by package.json</p>
                )}
              </div>

              {/* Remove button */}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleRemove(index)}
                disabled={disabled}
                className="mt-1"
                aria-label={`Remove environment variable ${index + 1}`}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Add button */}
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleAdd}
        disabled={disabled}
        className="w-full"
      >
        <Plus className="mr-2 h-4 w-4" />
        Add Environment Variable
      </Button>

      {/* Help text */}
      <p className="text-sm text-muted-foreground">
        Environment variables will be added to the MCP server configuration. Sensitive values should
        be managed securely.
      </p>
    </div>
  );
}

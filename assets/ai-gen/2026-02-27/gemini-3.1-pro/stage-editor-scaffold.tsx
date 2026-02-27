'use client';

import React, { useState, useEffect } from 'react';
import { X, Plus } from 'lucide-react';
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { cn } from '@skillmeat/web/lib/utils.ts';

export type WorkflowStage = {
  id: string;
  name: string;
  description: string;
  agentName: string;
  tools: string[];
  contextModules: string[];
  timeout: number;
  retryCount: number;
  failureAction: 'stop' | 'skip' | 'retry';
  executionMode?: 'sequential' | 'parallel';
  inheritGlobal?: boolean;
};

interface StageEditorProps {
  stage: WorkflowStage | null;
  open: boolean;
  onClose: () => void;
  onSave: (stage: WorkflowStage) => void;
}

const StageEditor: React.FC<StageEditorProps> = ({ stage, open, onClose, onSave }) => {
  const [formData, setFormData] = useState<WorkflowStage>({
    id: '',
    name: '',
    description: '',
    agentName: '',
    tools: [],
    contextModules: [],
    timeout: 60,
    retryCount: 0,
    failureAction: 'stop',
    executionMode: 'sequential',
    inheritGlobal: true,
  });

  const [newTool, setNewTool] = useState('');
  const [newModule, setNewModule] = useState('');
  const [timeoutUnit, setTimeoutUnit] = useState<'seconds' | 'minutes'>('seconds');

  useEffect(() => {
    if (stage) {
      setFormData(stage);
    }
  }, [stage]);

  const handleAddTool = () => {
    if (newTool.trim()) {
      setFormData(prev => ({ ...prev, tools: [...prev.tools, newTool.trim()] }));
      setNewTool('');
    }
  };

  const removeTool = (index: number) => {
    setFormData(prev => ({ ...prev, tools: prev.tools.filter((_, i) => i !== index) }));
  };

  const handleAddModule = () => {
    if (newModule.trim()) {
      setFormData(prev => ({ ...prev, contextModules: [...prev.contextModules, newModule.trim()] }));
      setNewModule('');
    }
  };

  const removeModule = (index: number) => {
    setFormData(prev => ({ ...prev, contextModules: prev.contextModules.filter((_, i) => i !== index) }));
  };

  return (
    <>
      {/* Backdrop */}
      <div 
        className={cn(
          "fixed inset-0 bg-black/20 transition-opacity z-40",
          open ? "opacity-100" : "opacity-0 pointer-events-none"
        )} 
        onClick={onClose} 
      />

      {/* Slide-over Panel */}
      <div 
        className={cn(
          "fixed right-0 top-0 h-full w-[480px] border-l bg-background shadow-xl z-50 transition-transform duration-300 ease-in-out flex flex-col",
          open ? "translate-x-0" : "translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold truncate">
            {formData.name || 'Edit Stage'}
          </h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Scrollable Form Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          
          {/* Section 1: Basic Info */}
          <section>
            <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">Basic Info</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="stage-name">Name</Label>
                <Input 
                  id="stage-name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Enter stage name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="stage-desc">Description</Label>
                <Textarea 
                  id="stage-desc"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="What happens in this stage?"
                  rows={3}
                />
              </div>
              <div className="space-y-2">
                <Label>Execution Mode</Label>
                <RadioGroup 
                  value={formData.executionMode} 
                  onValueChange={(val: 'sequential' | 'parallel') => setFormData({ ...formData, executionMode: val })}
                  className="flex gap-4"
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="sequential" id="sequential" />
                    <Label htmlFor="sequential">Sequential</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="parallel" id="parallel" />
                    <Label htmlFor="parallel">Parallel</Label>
                  </div>
                </RadioGroup>
              </div>
            </div>
          </section>

          {/* Section 2: Roles */}
          <section>
            <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">Roles</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="agent-name">Primary Agent</Label>
                <Input 
                  id="agent-name"
                  value={formData.agentName}
                  onChange={(e) => setFormData({ ...formData, agentName: e.target.value })}
                  placeholder="e.g. sonnet-engineer"
                />
              </div>
              <div className="space-y-2">
                <Label>Tools</Label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {formData.tools.map((tool, idx) => (
                    <Badge key={idx} variant="secondary" className="flex items-center gap-1 pl-2 pr-1 py-1">
                      {tool}
                      <button onClick={() => removeTool(idx)} className="hover:text-destructive transition-colors">
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input 
                    placeholder="Add tool..." 
                    value={newTool}
                    onChange={(e) => setNewTool(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddTool()}
                  />
                  <Button variant="outline" size="icon" onClick={handleAddTool}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </section>

          {/* Section 3: Context Policy */}
          <section>
            <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">Context Policy</h3>
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="inherit-global" 
                  checked={formData.inheritGlobal}
                  onCheckedChange={(checked) => setFormData({ ...formData, inheritGlobal: checked === true })}
                />
                <Label htmlFor="inherit-global" className="text-sm font-medium leading-none cursor-pointer">
                  Inherit Global Context
                </Label>
              </div>
              <div className="space-y-2">
                <Label>Context Modules</Label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {formData.contextModules.map((mod, idx) => (
                    <Badge key={idx} variant="secondary" className="flex items-center gap-1 pl-2 pr-1 py-1">
                      {mod}
                      <button onClick={() => removeModule(idx)} className="hover:text-destructive transition-colors">
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Input 
                    placeholder="Add module..." 
                    value={newModule}
                    onChange={(e) => setNewModule(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddModule()}
                  />
                  <Button variant="outline" size="icon" onClick={handleAddModule}>
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          </section>

          {/* Section 4: Advanced */}
          <section>
            <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">Advanced</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="timeout">Timeout</Label>
                  <Input 
                    id="timeout" 
                    type="number" 
                    value={formData.timeout}
                    onChange={(e) => setFormData({ ...formData, timeout: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Unit</Label>
                  <Select value={timeoutUnit} onValueChange={(v: 'seconds' | 'minutes') => setTimeoutUnit(v)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="seconds">Seconds</SelectItem>
                      <SelectItem value="minutes">Minutes</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="retry-count">Retry Count</Label>
                <Input 
                  id="retry-count" 
                  type="number" 
                  value={formData.retryCount}
                  onChange={(e) => setFormData({ ...formData, retryCount: parseInt(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Failure Action</Label>
                <Select 
                  value={formData.failureAction} 
                  onValueChange={(val: 'stop' | 'skip' | 'retry') => setFormData({ ...formData, failureAction: val })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="stop">Stop Workflow</SelectItem>
                    <SelectItem value="skip">Skip Stage</SelectItem>
                    <SelectItem value="retry">Retry Stage</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="p-4 border-t flex items-center justify-end gap-3 bg-muted/50">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button 
            onClick={() => onSave(formData)} 
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            Save Changes
          </Button>
        </div>
      </div>
    </>
  );
};

export default StageEditor;

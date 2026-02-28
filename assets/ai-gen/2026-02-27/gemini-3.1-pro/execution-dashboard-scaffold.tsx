'use client';

import * as React from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  Ban,
  Pause,
  RotateCcw,
  Bot,
  Wrench,
  Timer,
  FileClock,
  Book,
} from 'lucide-react';

// Assuming shadcn/ui is installed and configured
// import { Badge, BadgeProps } from '@/components/ui/badge';
// import { Button } from '@/components/ui/button';
// import { Progress } from '@/components/ui/progress';
// import { ScrollArea } from '@/components/ui/scroll-area';
// import { cn } from '@/lib/utils';
// For standalone component, we define these here
const cn = (...classes: (string | undefined | null | false)[]) => classes.filter(Boolean).join(' ');
const Button = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement>>(({ className, ...props }, ref) => (
  <button ref={ref} className={cn('inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50', className)} {...props} />
));
Button.displayName = 'Button';
const Badge = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { variant?: 'default' | 'secondary' | 'destructive' | 'outline' }>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2', className)} {...props} />
));
Badge.displayName = 'Badge';
type BadgeProps = React.ComponentProps<typeof Badge>;
const Progress = React.forwardRef<HTMLDivElement, { value: number } & React.HTMLAttributes<HTMLDivElement>>(({ className, value, ...props }, ref) => (
  <div ref={ref} className={cn('relative h-4 w-full overflow-hidden rounded-full bg-secondary', className)} {...props}>
    <div className="h-full w-full flex-1 bg-primary transition-all" style={{ transform: `translateX(-${100 - (value || 0)}%)` }} />
  </div>
));
Progress.displayName = 'Progress';
const ScrollArea = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn("relative overflow-hidden", className)} {...props}>
        <div className="h-full w-full rounded-[inherit]" style={{overflow: 'scroll'}}>{children}</div>
    </div>
));
ScrollArea.displayName = 'ScrollArea';


// --- TYPE DEFINITIONS ---
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused' | 'waiting';

export type ExecutionRun = {
  id: string;
  workflowId: string;
  workflowName: string;
  runNumber: number;
  status: ExecutionStatus;
  startedAt: string;
  completedAt?: string;
};

export type StageTimelineItem = {
  id: string;
  name: string;
  status: ExecutionStatus;
  duration?: string;
  elapsed?: string;
  agentName?: string;
  tools?: string[];
  contextModules?: Array<{ name: string; size: string }>;
  logs?: string[];
};

// --- HELPERS & HOOKS ---
const statusBadgeProps = (status: ExecutionStatus): {
  variant: BadgeProps['variant'];
  className: string;
  icon: React.ElementType;
} => {
  switch (status) {
    case 'pending':
      return { variant: 'outline', className: 'text-muted-foreground border-border', icon: Clock };
    case 'running':
      return { variant: 'default', className: 'bg-blue-100 text-blue-700 border-blue-200', icon: Loader2 };
    case 'completed':
      return { variant: 'default', className: 'bg-green-100 text-green-700 border-green-200', icon: CheckCircle2 };
    case 'failed':
      return { variant: 'default', className: 'bg-red-100 text-red-700 border-red-200', icon: XCircle };
    case 'cancelled':
      return { variant: 'default', className: 'bg-amber-100 text-amber-700 border-amber-200', icon: Ban };
    case 'paused':
      return { variant: 'default', className: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: Pause };
    case 'waiting':
      return { variant: 'outline', className: 'text-muted-foreground border-border', icon: Clock };
    default:
      return { variant: 'secondary', className: '', icon: Clock };
  }
};

const useLiveDuration = (startTime: string, isActive: boolean) => {
    const [duration, setDuration] = React.useState('');

    React.useEffect(() => {
        if (!isActive || !startTime) {
            setDuration('');
            return;
        }

        const start = new Date(startTime).getTime();
        const intervalId = setInterval(() => {
            const now = Date.now();
            const diff = now - start;
            const seconds = Math.floor(diff / 1000);
            const minutes = Math.floor(seconds / 60);
            const formatted = `${minutes}m ${seconds % 60}s`;
            setDuration(formatted);
        }, 1000);

        return () => clearInterval(intervalId);
    }, [startTime, isActive]);

    return duration;
};

// --- STUB COMPONENTS ---

const StatusBadge = ({ status }: { status: ExecutionStatus }) => {
  const { variant, className, icon: Icon } = statusBadgeProps(status);
  return (
    <Badge variant={variant} className={cn('flex items-center gap-1.5 capitalize', className)}>
      <Icon className={cn('h-3.5 w-3.5', status === 'running' && 'animate-spin')} />
      {status}
    </Badge>
  );
};

const SmallStatusBadge = ({ status }: { status: ExecutionStatus }) => {
  const { className, icon: Icon } = statusBadgeProps(status);
  return (
    <div className={cn('flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full', className)}>
      <Icon className={cn('h-3 w-3', status === 'running' && 'animate-spin')} />
    </div>
  );
};

export const ExecutionHeader: React.FC<{
  execution: ExecutionRun;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onRerun: () => void;
}> = ({ execution, onPause, onResume, onCancel, onRerun }) => {
  const renderButtons = () => {
    switch (execution.status) {
      case 'running':
        return (
          <>
            <Button variant="outline" size="sm" onClick={onPause} className="bg-background px-3 py-1 h-8 text-xs">
              <Pause className="mr-2 h-4 w-4" /> Pause
            </Button>
            <Button variant="destructive" size="sm" onClick={onCancel} className="px-3 py-1 h-8 text-xs">
              <Ban className="mr-2 h-4 w-4" /> Cancel
            </Button>
          </>
        );
      case 'paused':
        return (
          <>
            <Button size="sm" onClick={onResume} className="px-3 py-1 h-8 text-xs bg-primary text-primary-foreground">
              Resume
            </Button>
            <Button variant="destructive" size="sm" onClick={onCancel} className="px-3 py-1 h-8 text-xs">
              <Ban className="mr-2 h-4 w-4" /> Cancel
            </Button>
          </>
        );
      default:
        return (
          <Button variant="outline" size="sm" onClick={onRerun} className="bg-background px-3 py-1 h-8 text-xs">
            <RotateCcw className="mr-2 h-4 w-4" /> Re-run
          </Button>
        );
    }
  };

  return (
    <div className="flex items-center justify-between border-b bg-background px-6 py-4">
      <div className="flex items-center gap-2">
        <Link href={`/workflows/${execution.workflowId}`} className="text-sm font-medium text-indigo-600 hover:underline">
          {execution.workflowName}
        </Link>
        <span className="text-sm text-muted-foreground">&middot;</span>
        <Badge variant="secondary">Run #{execution.runNumber}</Badge>
        <span className="text-sm text-muted-foreground">&middot;</span>
        <p className="text-xs text-muted-foreground">
          Started on {new Date(execution.startedAt).toLocaleString()}
        </p>
      </div>
      <div className="flex items-center gap-4">
        <StatusBadge status={execution.status} />
        <div className="flex items-center gap-2">{renderButtons()}</div>
      </div>
    </div>
  );
};

export const ExecutionProgress: React.FC<{
  completedStages: number;
  totalStages: number;
}> = ({ completedStages, totalStages }) => {
  const progressValue = totalStages > 0 ? (completedStages / totalStages) * 100 : 0;

  return (
    <div className="flex items-center gap-4 border-b bg-muted/20 px-6 py-3">
      <Progress value={progressValue} className="h-2 flex-1" />
      <p className="text-sm text-muted-foreground whitespace-nowrap">
        {completedStages} of {totalStages} stages complete
      </p>
    </div>
  );
};

export const ExecutionDetail: React.FC<{
  stage: StageTimelineItem | null;
  execution: ExecutionRun;
}> = ({ stage, execution }) => {
  const liveElapsed = useLiveDuration(stage ? execution.startedAt : '', stage?.status === 'running');

  if (!stage) {
    return (
      <div className="flex flex-1 items-center justify-center p-6 text-muted-foreground bg-background">
        Select a stage to view details
      </div>
    );
  }

  const { name, status, agentName, tools, duration, contextModules, logs } = stage;

  return (
    <div className="flex-1 overflow-y-auto p-6 bg-background">
      <div className="mb-6 flex items-center gap-3">
        <h2 className="text-lg font-semibold">{name}</h2>
        <StatusBadge status={status} />
      </div>

      <div className="space-y-6">
        <section>
          <h3 className="mb-3 text-sm font-medium text-muted-foreground">Agent & Tools</h3>
          <div className="flex flex-wrap items-center gap-2">
            {agentName && (
              <Badge variant="default" className="bg-indigo-100 text-indigo-700 hover:bg-indigo-200 border-indigo-200">
                <Bot className="mr-1.5 h-3.5 w-3.5" /> {agentName}
              </Badge>
            )}
            {tools?.map((tool) => (
              <Badge key={tool} variant="secondary">
                <Wrench className="mr-1.5 h-3.5 w-3.5" /> {tool}
              </Badge>
            ))}
          </div>
        </section>

        <section>
          <h3 className="mb-3 text-sm font-medium text-muted-foreground">Timing</h3>
          <div className="grid grid-cols-2 gap-4 rounded-lg border p-4">
            <div className="flex items-start gap-3">
              <FileClock className="mt-1 h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Started</p>
                <p className="text-sm font-medium">{new Date(execution.startedAt).toLocaleTimeString()}</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Timer className="mt-1 h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Duration</p>
                <p className="text-sm font-medium">
                  {status === 'running' ? `${liveElapsed} (running)` : duration || 'N/A'}
                </p>
              </div>
            </div>
          </div>
        </section>

        {contextModules && contextModules.length > 0 && (
          <section>
            <h3 className="mb-3 text-sm font-medium text-muted-foreground">Context Consumed</h3>
            <ul className="space-y-2 rounded-lg border p-4">
              {contextModules.map((mod) => (
                <li key={mod.name} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2"><Book className="h-4 w-4 text-muted-foreground" /><span>{mod.name}</span></div>
                  <span className="font-mono text-xs text-muted-foreground">{mod.size}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {logs && logs.length > 0 && (
          <section>
            <h3 className="mb-3 text-sm font-medium text-muted-foreground">Log Viewer</h3>
            <ScrollArea className="h-64 max-h-64 w-full rounded-lg border">
              <div className="bg-muted/30 p-4 font-mono text-xs">
                {logs.map((log, index) => {
                  const isError = /error/i.test(log);
                  return (
                    <div key={index}>
                      <span className={cn(isError && 'text-red-600 bg-red-50 px-1 rounded')}>{log}</span>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </section>
        )}
      </div>
    </div>
  );
};

const StageTimeline: React.FC<{
    stages: StageTimelineItem[];
    selectedStageId: string | null;
    onSelectStage: (id: string) => void;
}> = ({ stages, selectedStageId, onSelectStage }) => {
    return (
        <div className="w-72 border-r bg-muted/10 p-4 overflow-y-auto">
            <h3 className="px-2 text-sm font-semibold text-muted-foreground">Stages</h3>
            <div className="mt-2 space-y-1">
                {stages.map(stage => (
                    <button
                        key={stage.id}
                        onClick={() => onSelectStage(stage.id)}
                        className={cn(
                            "flex w-full items-center gap-3 rounded-md p-2 text-left text-sm transition-colors",
                            selectedStageId === stage.id ? "bg-accent text-accent-foreground" : "hover:bg-accent/50"
                        )}
                    >
                        <SmallStatusBadge status={stage.status} />
                        <span className="flex-1 truncate">{stage.name}</span>
                        {stage.duration && <span className="text-xs text-muted-foreground">{stage.duration}</span>}
                    </button>
                ))}
            </div>
        </div>
    );
};

// --- MOCK DATA ---
const MOCK_EXECUTION: ExecutionRun = {
  id: 'run_abc123',
  workflowId: 'wf_xyz789',
  workflowName: 'Onboarding New Customer',
  runNumber: 42,
  status: 'running',
  startedAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
};

const MOCK_STAGES: StageTimelineItem[] = [
  { id: 'stage_1', name: 'Initialize Environment', status: 'completed', duration: '12s', agentName: 'SetupAgent', tools: ['Provisioner'], contextModules: [{name: 'config.json', size: '1.2kb'}]},
  { id: 'stage_2', name: 'Verify Customer Data', status: 'failed', duration: '3s', agentName: 'ValidationAgent', tools: ['SalesforceAPI'], logs: ['[ERROR] Salesforce API connection timeout.'] },
  { id: 'stage_3', name: 'Provision Services', status: 'running', agentName: 'ProvisioningAgent', tools: ['AWSLambda', 'StripeAPI'], contextModules: [{name: 'user_profile.md', size: '5.8kb'}, {name: 'service_plan.txt', size: '0.8kb'}], logs: ['Invoking Lambda function create-user-account', 'Calling Stripe to create subscription...', 'error: Stripe API key is invalid or expired. Please check credentials.']},
  { id: 'stage_4', name: 'Send Welcome Email', status: 'pending', agentName: 'CommsAgent', tools: ['SendGrid']},
  { id: 'stage_5', name: 'Waiting for Dependency', status: 'waiting', duration: '1h 5m', agentName: 'Orchestrator', tools: []},
  { id: 'stage_6', name: 'Finalize and Report', status: 'pending', agentName: 'CleanupAgent', tools: ['DatadogAPI']},
  { id: 'stage_7', name: 'On Hold Feature', status: 'paused', duration: '2m 15s', agentName: 'PauseAgent', tools: []},
  { id: 'stage_8', name: 'Archived Task', status: 'cancelled', duration: '5s', agentName: 'LegacyAgent', tools: []},
];

// --- PAGE COMPONENT ---
export default function ExecutionDashboardPage() {
  const params = useParams();
  const [selectedStageId, setSelectedStageId] = React.useState<string | null>(MOCK_STAGES[2].id);
  const [execution, setExecution] = React.useState<ExecutionRun>(MOCK_EXECUTION);
  const [stages, setStages] = React.useState<StageTimelineItem[]>(MOCK_STAGES);

  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'j' || event.key === 'k') {
        event.preventDefault();
        const currentIndex = stages.findIndex(s => s.id === selectedStageId);
        if (currentIndex === -1) {
            setSelectedStageId(stages[0]?.id || null);
            return;
        }
        const nextIndex = event.key === 'j'
          ? Math.min(currentIndex + 1, stages.length - 1)
          : Math.max(currentIndex - 1, 0);
        if(nextIndex !== currentIndex) {
            setSelectedStageId(stages[nextIndex].id);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => { window.removeEventListener('keydown', handleKeyDown); };
  }, [selectedStageId, stages]);

  const selectedStage = stages.find(s => s.id === selectedStageId) || null;

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <ExecutionHeader
        execution={execution}
        onPause={() => setExecution(e => ({ ...e, status: 'paused' }))}
        onResume={() => setExecution(e => ({ ...e, status: 'running' }))}
        onCancel={() => setExecution(e => ({ ...e, status: 'cancelled' }))}
        onRerun={() => console.log('Rerun clicked')}
      />
      <ExecutionProgress
        completedStages={stages.filter(s => s.status === 'completed').length}
        totalStages={stages.length}
      />
      <main className="flex flex-1 overflow-hidden">
        <StageTimeline
          stages={stages}
          selectedStageId={selectedStageId}
          onSelectStage={setSelectedStageId}
        />
        <ExecutionDetail stage={selectedStage} execution={execution} />
      </main>
    </div>
  );
}

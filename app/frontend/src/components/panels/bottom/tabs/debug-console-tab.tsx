interface DebugConsoleTabProps {
  className?: string;
}

export function DebugConsoleTab({ className }: DebugConsoleTabProps) {
  return (
    <div className={className}>
      <div className="h-full bg-background/50 rounded-md p-3 text-sm overflow-auto">
        <div className="text-muted-foreground">
          调试控制台已就绪...
        </div>
      </div>
    </div>
  );
} 
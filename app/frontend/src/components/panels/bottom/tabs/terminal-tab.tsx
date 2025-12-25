interface TerminalTabProps {
  className?: string;
}

export function TerminalTab({ className }: TerminalTabProps) {
  return (
    <div className={className}>
      <div className="h-full rounded-md p-3 font-mono text-sm text-green-500 overflow-auto">
        <div className="whitespace-pre-wrap">
          <span className="text-blue-500">$ </span>
          <span className="text-primary">欢迎使用 AI 对冲基金终端</span>
          {'\n'}
          <span className="text-muted-foreground">在此输入命令...</span>
          {'\n'}
          <span className="text-blue-500">$ </span>
          <span className="animate-pulse">_</span>
        </div>
      </div>
    </div>
  );
} 
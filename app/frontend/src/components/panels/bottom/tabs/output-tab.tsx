import { useFlowContext } from '@/contexts/flow-context';
import { useNodeContext } from '@/contexts/node-context';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';
import { BacktestOutput } from './backtest-output';
import { sortAgents } from './output-tab-utils';
import { RegularOutput } from './regular-output';

interface OutputTabProps {
  className?: string;
}

export function OutputTab({ className }: OutputTabProps) {
  const { currentFlowId } = useFlowContext();
  const { getAgentNodeDataForFlow, getOutputNodeDataForFlow } = useNodeContext();
  const [updateTrigger, setUpdateTrigger] = useState(0);
  
  // 获取当前流数据
  const agentData = getAgentNodeDataForFlow(currentFlowId?.toString() || null);
  const outputData = getOutputNodeDataForFlow(currentFlowId?.toString() || null);

  // 定期强制重新渲染以显示实时更新
  useEffect(() => {
    const interval = setInterval(() => {
      setUpdateTrigger(prev => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // 检测是否为回测运行
  const isBacktestRun = agentData && agentData['backtest'];

  // 对代理进行排序显示（从常规代理列表中排除回测代理）
  const sortedAgents = sortAgents(Object.entries(agentData).filter(([agentId]) => agentId !== 'backtest'));
  
  return (
    <div className={cn("h-full overflow-y-auto font-mono text-sm", className)}>
      {/* 如果是回测运行则渲染回测输出 */}
      {isBacktestRun && (
        <BacktestOutput agentData={agentData} outputData={outputData} />
      )}

      {/* 如果不是回测运行则渲染常规输出 */}
      {!isBacktestRun && (
        <RegularOutput sortedAgents={sortedAgents} outputData={outputData} />
      )}

      {/* 空状态 */}
      {!outputData && sortedAgents.length === 0 && !isBacktestRun && (
        <div className="text-center py-8 text-muted-foreground">
          没有可显示的输出。运行分析以查看进度和结果。
        </div>
      )}
    </div>
  );
} 
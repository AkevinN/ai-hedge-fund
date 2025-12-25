import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useNodeContext } from '@/contexts/node-context';
import { formatTimeFromTimestamp } from '@/utils/date-utils';
import { formatContent } from '@/utils/text-utils';
import { AlignJustify, Copy, Loader2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface AgentOutputDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  nodeId: string;
  flowId: string | null;
}

export function AgentOutputDialog({ 
  isOpen, 
  onOpenChange, 
  name, 
  nodeId,
  flowId
}: AgentOutputDialogProps) {
  const { getAgentNodeDataForFlow } = useNodeContext();
  
  // 使用传入的 flowId 而非从流程上下文获取
  const agentNodeData = getAgentNodeDataForFlow(flowId);
  const nodeData = agentNodeData[nodeId] || { 
    status: 'IDLE', 
    ticker: null, 
    message: '', 
    messages: [],
    lastUpdated: 0
  };

  const messages = nodeData.messages || [];
  const nodeStatus = nodeData.status;
  
  const [copySuccess, setCopySuccess] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const initialFocusRef = useRef<HTMLDivElement>(null);

  // 将所有消息中的分析收集到单个分析字典中
  const allAnalysis = messages
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()) // 按时间戳排序
    .reduce<Record<string, string>>((acc, msg) => {
      // 将此消息的分析添加到累积分析中
      if (msg.analysis) {
        // 处理分析数据 - 可能是字符串或对象
        if (typeof msg.analysis === 'string') {
          const analysisStr = msg.analysis;
          // 如果是字符串，尝试解析为JSON
          try {
            const parsed = JSON.parse(analysisStr);
            if (parsed && typeof parsed === 'object') {
              // 如果解析成功且是对象，合并到累积分析
              const validDecisions = Object.entries(parsed)
                .filter(([_, value]) => value !== null && value !== undefined)
                .reduce((obj, [key, value]) => {
                  obj[key] = String(value);
                  return obj;
                }, {} as Record<string, string>);
              if (Object.keys(validDecisions).length > 0) {
                return { ...acc, ...validDecisions };
              }
            }
          } catch (e) {
            // 如果JSON解析失败，直接使用字符串
            // 这可能是单个股票的分析结果
            if (msg.ticker && (analysisStr as string).trim().length > 0) {
              return { ...acc, [msg.ticker]: analysisStr };
            }
          }
        } else if (typeof msg.analysis === 'object' && msg.analysis !== null) {
          // 如果已经是对象，直接合并
          const validDecisions = Object.entries(msg.analysis)
            .filter(([_, value]) => value !== null && value !== undefined)
            .reduce((obj, [key, value]) => {
              obj[key] = String(value);
              return obj;
            }, {} as Record<string, string>);
          if (Object.keys(validDecisions).length > 0) {
            return { ...acc, ...validDecisions };
          }
        }
      }
      return acc;
    }, {});

  // 获取所有具有决策的唯一股票代码
  const tickersWithDecisions = Object.keys(allAnalysis);

  // 节点更改时重置选定的股票代码
  useEffect(() => {
    setSelectedTicker(null);
  }, [nodeId]);

  // 如果没有选择股票代码但我们有决策，则选择第一个
  useEffect(() => {
    if (tickersWithDecisions.length > 0 && (!selectedTicker || !tickersWithDecisions.includes(selectedTicker))) {
      setSelectedTicker(tickersWithDecisions[0]);
    }
  }, [tickersWithDecisions, selectedTicker]);

  // 获取选定的决策文本
  const selectedDecision = selectedTicker && allAnalysis[selectedTicker] ? allAnalysis[selectedTicker] : null;

  const copyToClipboard = () => {
    if (selectedDecision) {
      navigator.clipboard.writeText(selectedDecision)
        .then(() => {
          setCopySuccess(true);
          setTimeout(() => setCopySuccess(false), 2000);
        })
        .catch(err => {
          console.error('Failed to copy text: ', err);
        });
    }
  };

  return (
    <Dialog 
      open={isOpen} 
      onOpenChange={onOpenChange}
      defaultOpen={false}
      modal={true}
    >
      <DialogTrigger asChild>
        <div className="border-t border-border p-3 flex justify-end items-center cursor-pointer hover:bg-accent/50" onClick={() => onOpenChange(true)}>
          <div className="flex items-center gap-1">
            <div className="text-subtitle text-muted-foreground">输出</div>
            <AlignJustify className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
        </div>
      </DialogTrigger>
      <DialogContent 
        className="sm:max-w-[900px]" 
        autoFocus={false} 
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>{name}</DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-6 pt-4" ref={initialFocusRef} tabIndex={-1}>
          {/* 活动日志部分 */}
          <div>
            <h3 className="font-medium mb-3 text-primary">日志</h3>
            <div className="h-[400px] overflow-y-auto border border-border rounded-lg p-3">
              {messages.length > 0 ? (
                <div className="p-3 space-y-3">
                  {messages
                    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()) // Sort newest first for log
                    .map((msg, idx) => (
                    <div key={idx} className="border-l-2 border-primary pl-3 text-sm">
                      <div className="text-foreground">
                        {msg.ticker && <span>[{msg.ticker}] </span>}
                        {msg.message}
                      </div>
                      <div className="text-muted-foreground">
                        {formatTimeFromTimestamp(msg.timestamp)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  暂无活动
                </div>
              )}
            </div>
          </div>

          {/* 分析部分 */}
          <div>
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-medium text-primary">分析</h3>
              <div className="flex items-center gap-2">
                {/* 股票代码选择器 */}
                {tickersWithDecisions.length > 0 && (
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-muted-foreground font-medium">股票:</span>
                    <select 
                      className="text-xs p-1 rounded bg-background border border-border cursor-pointer"
                      value={selectedTicker || ''}
                      onChange={(e) => setSelectedTicker(e.target.value)}
                      autoFocus={false}
                    >
                      {tickersWithDecisions.map((ticker) => (
                        <option key={ticker} value={ticker}>
                          {ticker}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>
            <div className="h-[400px] overflow-y-auto border border-border rounded-lg p-3">
              {tickersWithDecisions.length > 0 ? (
                <div className="p-3 rounded-lg text-sm leading-relaxed">
                  {selectedTicker && (
                    <div className="mb-3 flex justify-between items-center">
                      <div className=" text-muted-foreground font-medium">{selectedTicker} 摘要</div>
                      {selectedDecision && (
                        <button
                          onClick={copyToClipboard}
                          className="flex items-center gap-1.5 text-xs p-1.5 rounded hover:bg-accent transition-colors text-muted-foreground"
                          title="复制到剪贴板"
                        >
                          <Copy className="h-3.5 w-3.5 " />
                          <span className="font-medium">{copySuccess ? '已复制!' : '复制'}</span>
                        </button>
                      )}
                    </div>
                  )}
                  {selectedDecision ? (
                    (() => {
                      const { isJson, formattedContent } = formatContent(selectedDecision);

                      if (isJson) {
                        // 使用 react-syntax-highlighter 获得更好的 JSON 渲染
                        return (
                          <div className="overflow-auto rounded-md text-xs">
                            <SyntaxHighlighter
                              language="json"
                              style={vscDarkPlus}
                              customStyle={{
                                margin: 0,
                                padding: '0.75rem',
                                fontSize: '0.875rem',
                                lineHeight: 1.5,
                                whiteSpace: 'pre-wrap',
                                wordWrap: 'break-word',
                                overflowWrap: 'break-word',
                              }}
                              showLineNumbers={false}
                              wrapLines={true}
                              wrapLongLines={true}
                            >
                              {formattedContent as string}
                            </SyntaxHighlighter>
                          </div>
                        );
                      } else {
                        // 显示为常规文本段落
                        return (
                          (formattedContent as string[]).map((paragraph, idx) => (
                            <p key={idx} className="mb-3 last:mb-0">{paragraph}</p>
                          ))
                        );
                      }
                    })()
                  ) : nodeStatus === 'IN_PROGRESS' ? (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                      <Loader2 className="h-5 w-5 animate-spin mr-2" />
                      分析进行中...
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                      {selectedTicker} 暂无分析结果
                    </div>
                  )}
                </div>
              ) : nodeStatus === 'IN_PROGRESS' ? (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                  分析进行中...
                </div>
              ) : nodeStatus === 'COMPLETE' ? (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  分析已完成，无结果
                </div>
              ) : nodeStatus === 'ERROR' ? (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  分析失败
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  暂无分析结果
                </div>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
} 
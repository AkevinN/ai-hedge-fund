import { useNodeContext } from '@/contexts/node-context';
import { api } from '@/services/api';
import { backtestApi } from '@/services/backtest-api';
import { BacktestRequest, HedgeFundRequest } from '@/services/types';
import { useCallback, useEffect, useRef, useState } from 'react';

// 特定 flow 的连接状态
export type FlowConnectionState = 'idle' | 'connecting' | 'connected' | 'error' | 'completed';

interface FlowConnectionInfo {
  state: FlowConnectionState;
  abortController: (() => void) | null;
  startTime: number;
  lastActivity: number;
  error?: string;
}

// 全局连接管理器 - 跟踪所有活动的 flow 连接
class FlowConnectionManager {
  private connections = new Map<string, FlowConnectionInfo>();
  private listeners = new Set<() => void>();

  // 获取 flow 的连接信息
  getConnection(flowId: string): FlowConnectionInfo {
    return this.connections.get(flowId) || {
      state: 'idle',
      abortController: null,
      startTime: 0,
      lastActivity: 0,
    };
  }

  // 设置 flow 的连接信息
  setConnection(flowId: string, info: Partial<FlowConnectionInfo>): void {
    const existing = this.getConnection(flowId);
    const updated = {
      ...existing,
      ...info,
      lastActivity: Date.now(),
    };

    this.connections.set(flowId, updated);
    this.notifyListeners();
  }

  // 移除 flow 的连接
  removeConnection(flowId: string): void {
    const connection = this.connections.get(flowId);
    if (connection?.abortController) {
      connection.abortController();
    }
    this.connections.delete(flowId);
    this.notifyListeners();
  }

  // 添加连接变化的监听器
  addListener(listener: () => void): void {
    this.listeners.add(listener);
  }

  // 移除监听器
  removeListener(listener: () => void): void {
    this.listeners.delete(listener);
  }

  // 通知所有监听器有变化
  private notifyListeners(): void {
    this.listeners.forEach(listener => listener());
  }
}

// 全局实例
export const flowConnectionManager = new FlowConnectionManager();

/**
 * 用于管理 flow 连接和执行的 Hook
 * @param flowId 要管理的 flow 的 ID
 * @returns 连接状态和控制函数
 */
export function useFlowConnection(flowId: string | null) {
  const nodeContext = useNodeContext();
  const [, forceUpdate] = useState({});
  const listenerRef = useRef<() => void>();

  // 连接变化时强制重新渲染
  useEffect(() => {
    const listener = () => forceUpdate({});
    listenerRef.current = listener;
    flowConnectionManager.addListener(listener);

    return () => {
      if (listenerRef.current) {
        flowConnectionManager.removeListener(listenerRef.current);
      }
    };
  }, []);

  // 获取当前连接状态
  const connection = flowId ? flowConnectionManager.getConnection(flowId) : null;
  const isConnecting = connection?.state === 'connecting';
  const isConnected = connection?.state === 'connected';
  const isError = connection?.state === 'error';
  const isCompleted = connection?.state === 'completed';

  // 检查是否有 agents 正在处理
  const isProcessing = flowId ? (() => {
    const agentData = nodeContext.getAgentNodeDataForFlow(flowId);
    return Object.values(agentData).some(agent => agent.status === 'IN_PROGRESS');
  })() : false;

  // 如果有 flow ID 且没有正在运行，则可以运行
  const canRun = Boolean(flowId && !isConnecting && !isConnected && !isProcessing);

  // 启动 flow 连接
  const runFlow = useCallback((params: HedgeFundRequest) => {
    if (!flowId || !canRun) return;

    // 重置此 flow 的节点状态
    nodeContext.resetAllNodes(flowId);

    // 设置连接状态
    flowConnectionManager.setConnection(flowId, {
      state: 'connecting',
      startTime: Date.now(),
    });

    try {
      // 启动 API 调用
      const abortController = api.runHedgeFund(params, nodeContext, flowId);

      // 用 abort controller 更新连接
      flowConnectionManager.setConnection(flowId, {
        state: 'connected',
        abortController,
      });

      // TODO: 我们应该增强 API 以在连接完成时通知我们
      // 目前，我们将依赖 SSE 流的完成事件

    } catch (error) {
      console.error('Failed to start hedge fund run:', error);
      flowConnectionManager.setConnection(flowId, {
        state: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
        abortController: null,
      });
    }
  }, [flowId, canRun, nodeContext]);

  // 启动回测连接
  const runBacktest = useCallback((params: BacktestRequest) => {
    if (!flowId || !canRun) return;

    // 重置此 flow 的节点状态
    nodeContext.resetAllNodes(flowId);

    // 设置连接状态
    flowConnectionManager.setConnection(flowId, {
      state: 'connecting',
      startTime: Date.now(),
    });

    try {
      // 启动回测 API 调用
      const abortController = backtestApi.runBacktest(params, nodeContext, flowId);

      // 用 abort controller 更新连接
      flowConnectionManager.setConnection(flowId, {
        state: 'connected',
        abortController,
      });

      // TODO: 我们应该增强 API 以在连接完成时通知我们
      // 目前，我们将依赖 SSE 流的完成事件

    } catch (error) {
      console.error('Failed to start backtest:', error);
      flowConnectionManager.setConnection(flowId, {
        state: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
        abortController: null,
      });
    }
  }, [flowId, canRun, nodeContext]);

  // 停止 flow 连接
  const stopFlow = useCallback(() => {
    if (!flowId) return;

    console.log(`[stopFlow] Stopping flow ${flowId}`);
    const connection = flowConnectionManager.getConnection(flowId);
    console.log(`[stopFlow] Current connection state:`, connection);

    if (connection.abortController) {
      console.log(`[stopFlow] Calling abort controller for flow ${flowId}`);
      connection.abortController();
    } else {
      console.log(`[stopFlow] No abort controller found for flow ${flowId}`);
    }

    // 停止时只重置节点状态，保留所有数据（回测结果、消息等）
    nodeContext.resetNodeStatuses(flowId);

    // 更新连接状态
    flowConnectionManager.setConnection(flowId, {
      state: 'idle',
      abortController: null,
    });

    console.log(`[stopFlow] Flow ${flowId} stopped and reset to idle`);
  }, [flowId, nodeContext]);

  // 从陈旧状态恢复（加载 flow 时调用）
  const recoverFlowState = useCallback(() => {
    if (!flowId) return;

    const connection = flowConnectionManager.getConnection(flowId);

    // 如果我们认为已连接但没有处理中的节点，可能是陈旧状态
    if ((connection.state === 'connected' || connection.state === 'connecting') && !isProcessing) {
      // 检查连接是否过旧（超过 5 分钟）
      const isStale = Date.now() - connection.lastActivity > 5 * 60 * 1000;

      if (isStale) {
        console.log(`Recovering stale connection for flow ${flowId}`);
        flowConnectionManager.setConnection(flowId, {
          state: 'idle',
          abortController: null,
        });
      }
    }
  }, [flowId, isProcessing]);

  return {
    // 状态
    isConnecting,
    isConnected,
    isError,
    isCompleted,
    isProcessing,
    canRun,
    error: connection?.error,

    // 操作
    runFlow,
    runBacktest,
    stopFlow,
    recoverFlowState,
  };
}

// 用于获取任何 flow 的连接状态的工具 Hook（用于监控）
export function useFlowConnectionState(flowId: string | null) {
  const [, forceUpdate] = useState({});

  useEffect(() => {
    if (!flowId) return;

    const unsubscribe = flowConnectionManager.addListener(() => {
      forceUpdate({});
    });

    return unsubscribe;
  }, [flowId]);

  return flowId ? flowConnectionManager.getConnection(flowId) : null;
}

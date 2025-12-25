import { useFlowContext } from '@/contexts/flow-context';
import { useNodeContext } from '@/contexts/node-context';
import {
  clearFlowNodeStates,
  getNodeInternalState,
  setNodeInternalState,
  setCurrentFlowId as setNodeStateFlowId
} from '@/hooks/use-node-state';
import { useToastManager } from '@/hooks/use-toast-manager';
import { flowService } from '@/services/flow-service';
import { Flow } from '@/types/flow';
import { useCallback, useEffect, useState } from 'react';

export interface UseFlowManagementReturn {
  // 状态
  flows: Flow[];
  searchQuery: string;
  isLoading: boolean;
  openGroups: string[];
  createDialogOpen: boolean;

  // 计算值
  filteredFlows: Flow[];
  recentFlows: Flow[];
  templateFlows: Flow[];

  // 操作
  setSearchQuery: (query: string) => void;
  setOpenGroups: (groups: string[]) => void;
  setCreateDialogOpen: (open: boolean) => void;
  handleAccordionChange: (value: string[]) => void;
  handleCreateNewFlow: () => void;
  handleFlowCreated: (newFlow: Flow) => Promise<void>;
  handleSaveCurrentFlow: () => Promise<void>;
  handleLoadFlow: (flow: Flow) => Promise<void>;
  handleDeleteFlow: (flow: Flow) => Promise<void>;
  handleRefresh: () => Promise<void>;

  // 内部函数（用于测试/高级使用）
  loadFlows: () => Promise<void>;
  createDefaultFlow: () => Promise<void>;
}

export function useFlowManagement(): UseFlowManagementReturn {
  // 获取 flow context、node context 和 toast manager
  const { saveCurrentFlow, loadFlow, reactFlowInstance, currentFlowId } = useFlowContext();
  const { exportNodeContextData } = useNodeContext();
  const { success, error } = useToastManager();

  // Flow 状态
  const [flows, setFlows] = useState<Flow[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [openGroups, setOpenGroups] = useState<string[]>(['recent-flows']);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // 增强的保存函数，包含内部节点状态和节点上下文数据
  const saveCurrentFlowWithStates = useCallback(async (): Promise<Flow | null> => {
    try {
      // 从 React Flow 获取当前节点
      const currentNodes = reactFlowInstance.getNodes();

      // 获取节点上下文数据（运行时数据：agent 状态、消息、输出数据）
      const flowId = currentFlowId?.toString() || null;
      const nodeContextData = exportNodeContextData(flowId);

      // 用内部状态增强节点
      const nodesWithStates = currentNodes.map((node: any) => {
        const internalState = getNodeInternalState(node.id);
        return {
          ...node,
          data: {
            ...node.data,
            // 只有在有实际状态需要保存时才添加 internal_state
            ...(internalState && Object.keys(internalState).length > 0 ? { internal_state: internalState } : {})
          }
        };
      });

      // 临时用增强后的节点替换 React Flow 中的节点
      reactFlowInstance.setNodes(nodesWithStates);

      try {
        // 使用 context 的保存函数，它会正确处理 currentFlowId
        const savedFlow = await saveCurrentFlow();

        if (savedFlow) {
          // 基本保存后，用节点上下文数据更新
          const updatedFlow = await flowService.updateFlow(savedFlow.id, {
            ...savedFlow,
            data: {
              ...savedFlow.data,
              nodeContextData, // 从节点上下文添加运行时数据
            }
          });

          return updatedFlow;
        }

        return savedFlow;
      } finally {
        // 恢复原始节点（React Flow 中不带 internal_state）
        reactFlowInstance.setNodes(currentNodes);
      }
    } catch (err) {
      console.error('Failed to save flow with states:', err);
      return null;
    }
  }, [reactFlowInstance, saveCurrentFlow, exportNodeContextData, currentFlowId]);

  // 增强的加载函数，恢复内部节点状态和节点上下文数据
  const loadFlowWithStates = useCallback(async (flow: Flow) => {
    try {
      // 首先，设置 flow ID 用于节点状态隔离
      setNodeStateFlowId(flow.id.toString());

      // 加载 flow 时不清除配置状态 - useNodeState 自动处理 flow 隔离
      // 加载 flow 时不重置运行时数据 - 保留所有运行时状态
      // 运行时数据只应在通过 Play 按钮显式启动新运行时重置
      console.log(`[FlowManagement] Loading flow ${flow.id} (${flow.name}), preserving all state (configuration + runtime)`);

      // 使用 context 加载 flow（处理 currentFlowId、currentFlowName 等）
      await loadFlow(flow);

      // 然后为每个节点恢复内部状态（use-node-state 数据）
      if (flow.nodes) {
        flow.nodes.forEach((node: any) => {
          if (node.data?.internal_state) {
            setNodeInternalState(node.id, node.data.internal_state);
          }
        });
      }

      // 注意：我们有意不在此处恢复 nodeContextData
      // 运行时执行数据（消息、分析、agent 状态）应该从头开始
      // 只有上面的配置数据（tickers、模型选择）会被恢复

      console.log('Flow loaded with complete state restoration:', flow.name);
    } catch (error) {
      console.error('Failed to load flow with states:', error);
      throw error; // 重新抛出以在调用函数中处理
    }
  }, [loadFlow]);

  // 为新用户创建默认 flow
  const createDefaultFlow = useCallback(async () => {
    try {
      console.log('Creating default flow for new user...');
      // 获取当前 React Flow 状态，如果不存在则回退到空数组
      const nodes = reactFlowInstance?.getNodes() || [];
      const edges = reactFlowInstance?.getEdges() || [];
      const viewport = reactFlowInstance?.getViewport() || { x: 0, y: 0, zoom: 1 };

      const defaultFlow = await flowService.createDefaultFlow(nodes, edges, viewport);
      console.log('Default flow created:', defaultFlow);
      setFlows([defaultFlow]);

      // 在加载之前设置 flow ID 用于节点状态隔离
      setNodeStateFlowId(defaultFlow.id.toString());
      await loadFlowWithStates(defaultFlow);
      console.log('Default flow loaded successfully');
    } catch (error) {
      console.error('Failed to create default flow:', error);
    }
  }, [reactFlowInstance, loadFlowWithStates]);

  // 从 API 加载 flows
  const loadFlows = useCallback(async () => {
    setIsLoading(true);
    try {
      console.log('Loading flows from API...');
      const flowsData = await flowService.getFlows();
      console.log('Loaded flows:', flowsData);
      setFlows(flowsData);

      if (flowsData.length === 0) {
        // 如果用户没有 flows，创建默认 flow
        console.log('No flows found, creating default flow...');
        await createDefaultFlow();
      } else {
        // 尝试从 localStorage 恢复上次选择的 flow
        const lastSelectedFlowId = localStorage.getItem('lastSelectedFlowId');
        let flowToLoad = null;

        if (lastSelectedFlowId) {
          // 尝试找到上次选择的 flow
          flowToLoad = flowsData.find(flow => flow.id === parseInt(lastSelectedFlowId));
          if (flowToLoad) {
            console.log('Restoring last selected flow:', flowToLoad.name);
          }
        }

        // 如果没有上次选择的 flow 或它不再存在，使用最近的 flow
        if (!flowToLoad) {
          flowToLoad = flowsData.reduce((latest, current) => {
            const latestDate = new Date(latest.updated_at || latest.created_at);
            const currentDate = new Date(current.updated_at || current.created_at);
            return currentDate > latestDate ? current : latest;
          });
          console.log('Loading most recent flow:', flowToLoad.name);
        }

        // 在加载之前获取完整的 flow 数据
        const fullFlow = await flowService.getFlow(flowToLoad.id);
        await loadFlowWithStates(fullFlow);
      }
    } catch (error) {
      console.error('Error loading flows:', error);
    } finally {
      setIsLoading(false);
    }
  }, [createDefaultFlow, loadFlowWithStates]);

  // 在挂载时加载 flows
  useEffect(() => {
    loadFlows();
  }, [loadFlows]);

  // 根据搜索查询过滤 flows
  const filteredFlows = flows.filter(flow =>
    flow.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    flow.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    flow.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  // 按 updated_at 降序排序 flows，然后分组
  const sortedFlows = [...filteredFlows].sort((a, b) => {
    const dateA = new Date(a.updated_at || a.created_at);
    const dateB = new Date(b.updated_at || b.created_at);
    return dateB.getTime() - dateA.getTime();
  });

  // 分组 flows
  const recentFlows = sortedFlows.filter(f => !f.is_template).slice(0, 10);
  const templateFlows = sortedFlows.filter(f => f.is_template);

  // 事件处理器
  const handleAccordionChange = useCallback((value: string[]) => {
    setOpenGroups(value);
  }, []);

  const handleCreateNewFlow = useCallback(() => {
    setCreateDialogOpen(true);
  }, []);

  const handleFlowCreated = useCallback(async (newFlow: Flow) => {
    // 加载新 flow 并记住它
    await loadFlowWithStates(newFlow);
    localStorage.setItem('lastSelectedFlowId', newFlow.id.toString());

    // 刷新 flows 列表以显示新 flow
    await loadFlows();
  }, [loadFlowWithStates, loadFlows]);

  const handleSaveCurrentFlow = useCallback(async () => {
    try {
      const savedFlow = await saveCurrentFlowWithStates();
      if (savedFlow) {
        // 记住已保存的 flow
        localStorage.setItem('lastSelectedFlowId', savedFlow.id.toString());
        // 刷新 flows 列表
        await loadFlows();
        success(`"${savedFlow.name}" 已保存！`, 'flow-save');
      } else {
        error('保存工作流失败', 'flow-save-error');
      }
    } catch (err) {
      console.error('Failed to save flow:', err);
      error('保存工作流失败', 'flow-save-error');
    }
  }, [saveCurrentFlowWithStates, loadFlows, success, error]);

  const handleLoadFlow = useCallback(async (flow: Flow) => {
    try {
      // 获取包括节点、边和视口的完整 flow 数据
      const fullFlow = await flowService.getFlow(flow.id);
      await loadFlowWithStates(fullFlow);
      // 记住选择的 flow
      localStorage.setItem('lastSelectedFlowId', flow.id.toString());
      console.log('Flow loaded:', fullFlow.name);
    } catch (error) {
      console.error('Failed to load flow:', error);
    }
  }, [loadFlowWithStates]);

  const handleRefresh = useCallback(async () => {
    await loadFlows();
  }, [loadFlows]);

  const handleDeleteFlow = useCallback(async (flow: Flow) => {
    try {
      await flowService.deleteFlow(flow.id);
      // 清除已删除 flow 的节点状态
      clearFlowNodeStates(flow.id.toString());
      // 如果是上次选择的 flow，从 localStorage 中移除
      const lastSelectedFlowId = localStorage.getItem('lastSelectedFlowId');
      if (lastSelectedFlowId === flow.id.toString()) {
        localStorage.removeItem('lastSelectedFlowId');
      }
      // 刷新 flows 列表
      await loadFlows();
    } catch (error) {
      console.error('Failed to delete flow:', error);
    }
  }, [loadFlows]);

  return {
    // 状态
    flows,
    searchQuery,
    isLoading,
    openGroups,
    createDialogOpen,

    // 计算值
    filteredFlows,
    recentFlows,
    templateFlows,

    // 操作
    setSearchQuery,
    setOpenGroups,
    setCreateDialogOpen,
    handleAccordionChange,
    handleCreateNewFlow,
    handleFlowCreated,
    handleSaveCurrentFlow,
    handleLoadFlow,
    handleDeleteFlow,
    handleRefresh,

    // 内部函数
    loadFlows,
    createDefaultFlow,
  };
} 
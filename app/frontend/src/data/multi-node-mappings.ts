export interface MultiNodeDefinition {
  name: string;
  nodes: {
    componentName: string;
    offsetX: number;
    offsetY: number;
  }[];
  edges: {
    source: string;
    target: string;
  }[];
}

const multiNodeDefinition: Record<string, MultiNodeDefinition> = {
  "价值投资者": {
    name: "价值投资者",
    nodes: [
      { componentName: "股票输入", offsetX: 0, offsetY: 0 },
      { componentName: "Ben Graham", offsetX: 400, offsetY: -400 },
      { componentName: "Charlie Munger", offsetX: 400, offsetY: 0 },
      { componentName: "Warren Buffett", offsetX: 400, offsetY: 400 },
      { componentName: "投资组合管理器", offsetX: 800, offsetY: 0 },
    ],
    edges: [
      { source: "股票输入", target: "Ben Graham" },
      { source: "股票输入", target: "Charlie Munger" },
      { source: "股票输入", target: "Warren Buffett" },
      { source: "Ben Graham", target: "投资组合管理器" },
      { source: "Charlie Munger", target: "投资组合管理器" },
      { source: "Warren Buffett", target: "投资组合管理器" },
    ],
  },
  "数据巫师": {
    name: "数据巫师",
    nodes: [
      { componentName: "股票输入", offsetX: 0, offsetY: 0 },
      { componentName: "Technical Analyst", offsetX: 400, offsetY: -550 },
      { componentName: "Fundamentals Analyst", offsetX: 400, offsetY: -200 },
      { componentName: "Sentiment Analyst", offsetX: 400, offsetY: 150 },
      { componentName: "Valuation Analyst", offsetX: 400, offsetY: 500 },
      { componentName: "投资组合管理器", offsetX: 800, offsetY: 0 },
    ],
    edges: [
      { source: "股票输入", target: "Technical Analyst" },
      { source: "股票输入", target: "Fundamentals Analyst" },
      { source: "股票输入", target: "Sentiment Analyst" },
      { source: "股票输入", target: "Valuation Analyst" },
      { source: "Technical Analyst", target: "投资组合管理器" },
      { source: "Fundamentals Analyst", target: "投资组合管理器" },
      { source: "Sentiment Analyst", target: "投资组合管理器" },
      { source: "Valuation Analyst", target: "投资组合管理器" },

    ],
  },
  "市场先锋": {
    name: "市场先锋",
    nodes: [
      { componentName: "股票输入", offsetX: 0, offsetY: 0 },
      { componentName: "Michael Burry", offsetX: 400, offsetY: -400 },
      { componentName: "Bill Ackman", offsetX: 400, offsetY: 0 },
      { componentName: "Stanley Druckenmiller", offsetX: 400, offsetY: 400 },
      { componentName: "投资组合管理器", offsetX: 800, offsetY: 0 },
    ],
    edges: [
      { source: "股票输入", target: "Michael Burry" },
      { source: "股票输入", target: "Bill Ackman" },
      { source: "股票输入", target: "Stanley Druckenmiller" },
      { source: "Michael Burry", target: "投资组合管理器" },
      { source: "Bill Ackman", target: "投资组合管理器" },
      { source: "Stanley Druckenmiller", target: "投资组合管理器" },
    ],
  },
};

export function getMultiNodeDefinition(name: string): MultiNodeDefinition | null {
  return multiNodeDefinition[name] || null;
}

export function isMultiNodeComponent(componentName: string): boolean {
  return componentName in multiNodeDefinition;
} 
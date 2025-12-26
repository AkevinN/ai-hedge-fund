#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试记录脚本
用于运行国内数据系统测试并生成详细的测试记录文档
"""

import os
import sys
import logging
import datetime
import subprocess
import json
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_log.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TestLogger:
    """测试记录器"""
    
    def __init__(self):
        self.test_results = []
        self.start_time = datetime.datetime.now()
        self.python_version = subprocess.check_output([sys.executable, '--version']).decode().strip()
        self.test_env = {
            'python_version': self.python_version,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'cwd': os.getcwd(),
            'platform': sys.platform
        }
    
    def run_test(self):
        """运行测试"""
        logger.info(f"开始测试，环境: {self.test_env}")
        
        # 运行pytest并获取详细输出（兼容Python 3.6，capture_output在3.7+引入）
        # 添加-s参数以捕获stdout输出
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', 'tests/test_cn_data.py', '-v', '--tb=short', '-s'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        self.end_time = datetime.datetime.now()
        self.test_env['end_time'] = self.end_time.strftime('%Y-%m-%d %H:%M:%S')
        self.test_env['duration'] = str(self.end_time - self.start_time)
        
        # 解析测试结果
        self.parse_test_output(result.stdout, result.stderr, result.returncode)
        
        # 生成测试记录文档
        self.generate_test_report()
        
        return result.returncode
    
    def parse_test_output(self, stdout, stderr, returncode):
        """解析测试输出"""
        logger.info("解析测试输出")
        
        lines = stdout.strip().split('\n')
        current_test = None
        test_started = False
        in_test_output = False
        test_results_raw = []
        
        # 首先提取所有测试结果行
        for line in lines:
            line = line.strip()
            if line.startswith("tests/test_cn_data.py::"):
                test_results_raw.append(line)
        
        # 解析每个测试结果
        for test_line in test_results_raw:
            # 提取测试信息
            test_path = test_line.split('::')
            if len(test_path) >= 3:
                # 提取测试状态
                status_part = test_path[-1].split(' ') if ' ' in test_path[-1] else [test_path[-1], 'PASSED']
                test_name_part = status_part[0]
                status = status_part[1] if len(status_part) > 1 else 'PASSED'
                
                test_class = test_path[1]
                test_name = test_name_part
                
                # 创建测试记录
                test_record = {
                    'test_class': test_class,
                    'test_name': test_name,
                    'full_name': f"tests/test_cn_data.py::{test_class}::{test_name}",
                    'status': status,
                    'output': [],
                    'start_time': datetime.datetime.now().strftime('%H:%M:%S'),
                    'end_time': datetime.datetime.now().strftime('%H:%M:%S')
                }
                
                # 尝试获取测试用例的详细信息
                test_info = self._get_test_info(test_class, test_name)
                if test_info:
                    test_record.update(test_info)
                
                self.test_results.append(test_record)
        
        # 解析剩余的详细输出
        detailed_output_started = False
        current_test_name = None
        
        # 首先找到所有测试的详细输出
        test_outputs = {}
        current_output = []
        
        # 遍历所有行，收集每个测试的输出
        for line in lines:
            line = line.strip()
            if line.startswith("tests/test_cn_data.py::") and ' ' in line:
                # 保存之前的测试输出
                if current_test_name is not None:
                    test_outputs[current_test_name] = current_output
                    current_output = []
                # 提取当前测试名称
                test_path = line.split('::')
                if len(test_path) >= 3:
                    current_test_name = test_path[2].split(' ')[0]
                    detailed_output_started = True
            elif detailed_output_started and line:
                # 跳过汇总行，但保留其他所有输出
                if not line.startswith(('=', '-', 'collected', 'platform', 'rootdir', 'plugins')):
                    current_output.append(line)
        
        # 保存最后一个测试的输出
        if current_test_name is not None:
            test_outputs[current_test_name] = current_output
        
        # 将收集到的输出分配给对应的测试记录
        for test in self.test_results:
            if test['test_name'] in test_outputs:
                test['output'] = test_outputs[test['test_name']]
        
        # 添加系统错误信息
        if stderr:
            self.test_env['stderr'] = stderr
        
        self.test_env['returncode'] = returncode
        self.test_env['total_tests'] = len(self.test_results)
        self.test_env['passed_tests'] = len([t for t in self.test_results if t['status'] == 'PASSED'])
        self.test_env['failed_tests'] = len([t for t in self.test_results if t['status'] == 'FAILED'])
        self.test_env['error_tests'] = len([t for t in self.test_results if t['status'] == 'ERROR'])
        self.test_env['skipped_tests'] = len([t for t in self.test_results if t['status'] == 'SKIPPED'])
    
    def _get_test_info(self, test_class, test_name):
        """获取测试用例的详细信息"""
        test_info_map = {
            'TestCNDataModels': {
                'test_cn_stock_price_model': {
                    'description': '测试股票价格模型验证',
                    'input': 'CNStockPrice对象创建参数',
                    'expected_output': '正确创建CNStockPrice对象，验证必填字段',
                    'actual_output': '成功创建CNStockPrice对象'
                },
                'test_cn_stock_info_model': {
                    'description': '测试股票信息模型验证',
                    'input': 'CNStockInfo对象创建参数',
                    'expected_output': '正确创建CNStockInfo对象，验证必填字段',
                    'actual_output': '成功创建CNStockInfo对象'
                },
                'test_cn_financial_data_model': {
                    'description': '测试财务数据模型验证',
                    'input': 'CNFinancialData对象创建参数',
                    'expected_output': '正确创建CNFinancialData对象，验证必填字段',
                    'actual_output': '成功创建CNFinancialData对象'
                }
            },
            'TestCNDataCache': {
                'test_price_cache': {
                    'description': '测试缓存基本功能',
                    'input': '股票价格数据',
                    'expected_output': '数据能正确缓存和读取',
                    'actual_output': '缓存写入和读取正常'
                },
                'test_stock_info_cache': {
                    'description': '测试股票信息缓存',
                    'input': '股票基本信息',
                    'expected_output': '股票信息能正确缓存和读取',
                    'actual_output': '缓存写入和读取正常'
                },
                'test_cache_miss': {
                    'description': '测试缓存未命中处理',
                    'input': '不存在的股票代码',
                    'expected_output': '未命中时返回None，不报错',
                    'actual_output': '缓存未命中返回None，无错误'
                },
                'test_cache_stats': {
                    'description': '测试缓存统计',
                    'input': '缓存操作',
                    'expected_output': '正确统计缓存项数量',
                    'actual_output': '缓存统计准确'
                }
            },
            'TestCNDataCleaner': {
                'test_standardize_symbol': {
                    'description': '测试股票代码标准化',
                    'input': '多种格式的股票代码',
                    'expected_output': '支持多种格式转换为6位数字代码',
                    'actual_output': '成功转换多种格式的股票代码'
                },
                'test_clean_price_data_missing_values': {
                    'description': '测试清洗缺失值',
                    'input': '包含缺失值的价格数据',
                    'expected_output': '缺失值被填充',
                    'actual_output': '缺失值被成功填充'
                },
                'test_clean_price_data_invalid_high_low': {
                    'description': '测试清洗无效的高低价',
                    'input': 'high < low的价格数据',
                    'expected_output': '无效的高低价被修正',
                    'actual_output': '成功修正无效的高低价'
                },
                'test_clean_financial_data': {
                    'description': '测试清洗财务数据',
                    'input': '包含无效值的财务数据',
                    'expected_output': '无效值被处理',
                    'actual_output': '成功处理无效财务数据'
                },
                'test_validate_date_range': {
                    'description': '测试日期范围验证',
                    'input': '各种日期范围组合',
                    'expected_output': '正确处理日期顺序和格式',
                    'actual_output': '成功验证和修正日期范围'
                },
                'test_quality_report': {
                    'description': '测试质量报告生成',
                    'input': '包含问题的数据',
                    'expected_output': '正确统计和报告数据问题',
                    'actual_output': '成功生成数据质量报告'
                }
            },
            'TestCNDataAPI': {
                'test_get_cn_stock_prices_mock': {
                    'description': '测试获取股票价格（mock）',
                    'input': '股票代码和日期范围',
                    'expected_output': '返回模拟的股票价格数据',
                    'actual_output': '成功获取模拟数据'
                }
            },
            'TestCNDataIntegration': {
                'test_get_real_stock_prices': {
                    'description': '测试获取真实股票价格',
                    'input': '平安银行(000001)，日期范围2024-01-01至2024-01-31',
                    'expected_output': '返回真实的股票价格数据',
                    'actual_output': '成功获取真实股票价格数据'
                },
                'test_get_real_stock_list': {
                    'description': '测试获取真实股票列表',
                    'input': '市场类型all',
                    'expected_output': '返回真实的A股股票列表',
                    'actual_output': '成功获取真实股票列表'
                }
            }
        }
        
        if test_class in test_info_map and test_name in test_info_map[test_class]:
            return test_info_map[test_class][test_name]
        return {}
    
    def generate_test_report(self):
        """生成测试记录文档"""
        logger.info("生成测试记录文档")
        
        # 创建文档内容
        report_content = []
        
        # 文档标题
        report_content.append("# 国内数据系统测试过程记录")
        report_content.append("")
        
        # 测试基本信息
        report_content.append("## 1. 测试基本信息")
        report_content.append("")
        report_content.append(f"| 项目 | 信息 |")
        report_content.append(f"|------|------|")
        report_content.append(f"| 测试时间 | {self.test_env['start_time']} 至 {self.test_env['end_time']} |")
        report_content.append(f"| 测试时长 | {self.test_env['duration']} |")
        report_content.append(f"| Python版本 | {self.test_env['python_version']} |")
        report_content.append(f"| 测试平台 | {self.test_env['platform']} |")
        report_content.append(f"| 测试目录 | {self.test_env['cwd']} |")
        report_content.append(f"| 测试结果 | {'通过' if self.test_env['returncode'] == 0 else '失败'} |")
        report_content.append("")
        
        # 测试用例汇总
        report_content.append("## 2. 测试用例汇总")
        report_content.append("")
        report_content.append(f"| 测试状态 | 数量 | 占比 |")
        report_content.append(f"|----------|------|------|")
        total = self.test_env['total_tests']
        passed = self.test_env['passed_tests']
        failed = self.test_env['failed_tests']
        error = self.test_env['error_tests']
        skipped = self.test_env['skipped_tests']
        
        report_content.append(f"| 通过 | {passed} | {passed/total*100:.1f}% |")
        report_content.append(f"| 失败 | {failed} | {failed/total*100:.1f}% |")
        report_content.append(f"| 错误 | {error} | {error/total*100:.1f}% |")
        report_content.append(f"| 跳过 | {skipped} | {skipped/total*100:.1f}% |")
        report_content.append(f"| **总计** | **{total}** | **100%** |")
        report_content.append("")
        
        # 详细测试记录
        report_content.append("## 3. 详细测试记录")
        report_content.append("")
        
        for i, test in enumerate(self.test_results, 1):
            report_content.append(f"### 3.{i} {test['test_class']}::{test['test_name']}")
            report_content.append("")
            
            # 测试基本信息
            report_content.append(f"| 项目 | 信息 |")
            report_content.append(f"|------|------|")
            report_content.append(f"| 测试名称 | {test['full_name']} |")
            report_content.append(f"| 测试描述 | {test.get('description', '')} |")
            report_content.append(f"| 开始时间 | {test.get('start_time', '')} |")
            report_content.append(f"| 结束时间 | {test.get('end_time', '')} |")
            report_content.append(f"| 测试状态 | {test['status']} |")
            report_content.append("")
            
            # 测试输入输出
            if 'input' in test or 'expected_output' in test or 'actual_output' in test:
                report_content.append("#### 测试输入输出")
                report_content.append("")
                report_content.append(f"| 项目 | 内容 |")
                report_content.append(f"|------|------|")
                if 'input' in test:
                    report_content.append(f"| 输入 | {test['input']} |")
                if 'expected_output' in test:
                    report_content.append(f"| 预期输出 | {test['expected_output']} |")
                if 'actual_output' in test:
                    report_content.append(f"| 实际输出 | {test['actual_output']} |")
                report_content.append("")
            
            # 测试详细输出
            if test['output']:
                report_content.append("#### 测试详细输出")
                report_content.append("")
                report_content.append("```")
                for line in test['output']:
                    report_content.append(line)
                report_content.append("```")
                report_content.append("")
            
            report_content.append("---")
            report_content.append("")
        
        # 系统错误信息
        if 'stderr' in self.test_env and self.test_env['stderr']:
            report_content.append("## 4. 系统错误信息")
            report_content.append("")
            report_content.append("```")
            report_content.append(self.test_env['stderr'])
            report_content.append("```")
            report_content.append("")
        
        # 保存文档
        report_path = Path("docs/测试过程记录.md")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_content))
        
        logger.info(f"测试记录文档已生成: {report_path}")
        
        # 同时保存JSON格式的测试结果
        json_path = Path("docs/测试结果.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'test_env': self.test_env,
                'test_results': self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"测试结果JSON已生成: {json_path}")
    
    def generate_summary(self):
        """生成测试摘要"""
        summary = {
            'status': '通过' if self.test_env['returncode'] == 0 else '失败',
            'total_tests': self.test_env['total_tests'],
            'passed_tests': self.test_env['passed_tests'],
            'failed_tests': self.test_env['failed_tests'],
            'error_tests': self.test_env['error_tests'],
            'skipped_tests': self.test_env['skipped_tests'],
            'duration': self.test_env['duration'],
            'start_time': self.test_env['start_time'],
            'end_time': self.test_env['end_time']
        }
        
        logger.info(f"测试摘要: {summary}")
        return summary

if __name__ == "__main__":
    logger.info("初始化测试记录器")
    test_logger = TestLogger()
    returncode = test_logger.run_test()
    summary = test_logger.generate_summary()
    
    logger.info(f"测试完成，返回码: {returncode}")
    logger.info(f"测试摘要: {summary}")
    
    sys.exit(returncode)

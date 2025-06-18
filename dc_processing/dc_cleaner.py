#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DC数据清洗器 - 主程序
功能：将ASEData/DC目录下的所有xlsx测试数据文件清洗整理成统一格式的DC数据文件
作者：cc
创建时间：2025-06-18
"""

import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dc_cleaner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DCDataCleaner:
    """DC数据清洗器主类"""
    
    def __init__(self, input_dir: str = "../ASEData/DC", output_dir: str = "../output"):
        """
        初始化DC数据清洗器
        
        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.ensure_output_dir()
        
    def ensure_output_dir(self):
        """确保输出目录存在"""
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建输出目录: {self.output_dir}")
    
    def scan_dc_files(self) -> List[Path]:
        """
        扫描DC目录下所有xlsx文件
        
        Returns:
            文件路径列表
        """
        logger.info(f"开始扫描DC文件目录: {self.input_dir}")
        
        if not self.input_dir.exists():
            logger.error(f"输入目录不存在: {self.input_dir}")
            return []
        
        # 扫描所有xlsx文件，排除临时文件(~$开头)
        xlsx_files = []
        for file_path in self.input_dir.glob("*.xlsx"):
            if not file_path.name.startswith("~$"):
                xlsx_files.append(file_path)
        
        logger.info(f"找到 {len(xlsx_files)} 个DC数据文件")
        for file_path in xlsx_files:
            logger.info(f"  - {file_path.name}")
        
        return xlsx_files
    
    def extract_batch_info(self, file_path: Path) -> str:
        """
        从文件名中提取批次信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            批次字符串（使用正则表达式提取FA4Z-2484这样的模式）
        """
        filename = file_path.name
        
        # 使用正则表达式提取形如FA4Z-2484的模式（4个字母数字 + 短横线 + 4个数字）
        pattern = r'[A-Z0-9]{4}-[0-9]{4}'
        match = re.search(pattern, filename)
        
        if match:
            lot_id = match.group()
            logger.debug(f"提取批次信息: {filename} -> {lot_id}")
            return lot_id
        else:
            # 如果正则匹配失败，回退到使用完整文件名
            lot_id = file_path.stem
            logger.warning(f"正则匹配失败，使用完整文件名: {filename} -> {lot_id}")
            return lot_id
    
    def extract_test_condition_value(self, df: pd.DataFrame, param_col: int) -> Optional[str]:
        """
        提取IDSS参数的测试条件数值
        
        Args:
            df: Excel数据表
            param_col: IDSS参数所在列
            
        Returns:
            测试条件数值字符串，如"40.0"，失败返回None
        """
        try:
            # 第5行（索引4）是测试条件行，第7列（索引6）是Bias1
            if df.shape[0] < 5:
                logger.warning("文件行数不足，无法获取测试条件行")
                return None
            
            row5 = df.iloc[4, :]  # 第5行（索引4）
            
            # 获取IDSS参数对应列的测试条件
            if param_col < len(row5):
                condition_value = row5.iloc[param_col]
                if pd.isna(condition_value):
                    logger.debug(f"IDSS参数列{param_col}的测试条件为空")
                    return None
                
                condition_str = str(condition_value).strip()
                logger.debug(f"IDSS测试条件原始值: '{condition_str}'")
                
                # 使用正则表达式提取数值部分
                # 匹配类似 "(VDS)40.0V" 或 "40.0V" 中的数值部分
                pattern = r'(\d+\.?\d*)'
                match = re.search(pattern, condition_str)
                
                if match:
                    numeric_value = match.group(1)
                    logger.debug(f"提取到IDSS测试条件数值: '{numeric_value}'")
                    return numeric_value
                else:
                    logger.warning(f"无法从测试条件中提取数值: '{condition_str}'")
                    return None
            else:
                logger.warning(f"IDSS参数列{param_col}超出测试条件行范围")
                return None
                
        except Exception as e:
            logger.error(f"提取IDSS测试条件时出错: {str(e)}")
            return None

    def extract_dc_data(self, file_path: Path) -> Optional[pd.DataFrame]:
        """
        从单个xlsx文件中提取DC测试数据
        
        Args:
            file_path: 单个xlsx文件路径
            
        Returns:
            DataFrame包含动态数量的测试参数和文件名，失败返回None
        """
        logger.info(f"开始处理文件: {file_path.name}")
        
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path, header=None, engine='openpyxl')
            logger.debug(f"文件读取成功，形状: {df.shape}")
            
            # 提取批次信息
            lot_id = self.extract_batch_info(file_path)
            
            # 1. 定位第1行的CONT列和参数列
            if df.shape[0] < 2:
                logger.error(f"文件 {file_path.name} 行数不足")
                return None
                
            row1 = df.iloc[1, :]  # 第1行（索引1）参数行
            
            # 找到CONT列位置
            cont_col = None
            for i, val in enumerate(row1):
                if not pd.isna(val) and str(val).strip() == 'CONT':
                    cont_col = i
                    break
            
            if cont_col is None:
                logger.error(f"文件 {file_path.name} 未找到CONT列")
                return None
            
            logger.debug(f"CONT列位置: {cont_col}")
            
            # 2. 提取CONT右边的所有参数，跳过SAME
            test_params = []
            for i in range(cont_col + 1, len(row1)):
                val = row1.iloc[i]
                if not pd.isna(val) and str(val).strip() != '':
                    param_name = str(val).strip()
                    if param_name != 'SAME':
                        test_params.append((i, param_name))
            
            logger.debug(f"找到 {len(test_params)} 个测试参数")
            
            # 3. 获取第6行的单位信息
            if df.shape[0] < 7:
                logger.error(f"文件 {file_path.name} 行数不足，无法获取单位行")
                return None
                
            row6 = df.iloc[6, :]  # 第6行（索引6）单位行
            
            # 4. 参数-单位匹配，特殊处理IDSS参数
            param_unit_pairs = []
            for col, param in test_params:
                unit_val = row6.iloc[col] if col < len(row6) else None
                # 单位为空时设为None，避免显示N/A
                if pd.isna(unit_val) or str(unit_val).strip() == '':
                    unit_name = None
                else:
                    unit_name = str(unit_val).strip()
                
                # 特殊处理IDSS和ISGS参数：添加测试条件
                if param.upper() in ['IDSS', 'ISGS']:
                    test_condition = self.extract_test_condition_value(df, col)
                    if test_condition:
                        # 将IDSS/ISGS改为IDSS/ISGS+测试条件，如IDSS40.0, ISGS40.0
                        enhanced_param = f"{param}{test_condition}"
                        logger.info(f"{param}参数增强: {param} -> {enhanced_param}")
                        param_unit_pairs.append((col, enhanced_param, unit_name))
                    else:
                        # 如果无法提取测试条件，保持原参数名
                        logger.warning(f"无法为{param}参数提取测试条件，保持原名: {param}")
                        param_unit_pairs.append((col, param, unit_name))
                else:
                    param_unit_pairs.append((col, param, unit_name))
            
            # 5. 重复参数编号处理
            from collections import Counter
            param_names = [pair[1] for pair in param_unit_pairs]
            param_counts = Counter(param_names)
            
            param_counters = {}
            final_params = []
            
            for col, param, unit in param_unit_pairs:
                if param in param_counters:
                    param_counters[param] += 1
                    numbered_param = f"{param}{param_counters[param]}"
                else:
                    param_counters[param] = 1
                    if param_counts[param] > 1:
                        numbered_param = f"{param}1"
                    else:
                        numbered_param = param
                
                # 只有当单位不为空时才添加括号
                if unit is not None:
                    final_param_name = f"{numbered_param}({unit})"
                else:
                    final_param_name = numbered_param
                final_params.append((col, final_param_name))
            
            logger.debug(f"最终参数列表: {[param[1] for param in final_params]}")
            
            # 6. 定位Test No.行
            test_no_row = None
            for i in range(df.shape[0]):
                for j in range(df.shape[1]):
                    if not pd.isna(df.iloc[i, j]) and "Test No" in str(df.iloc[i, j]):
                        test_no_row = i
                        break
                if test_no_row is not None:
                    break
            
            if test_no_row is None:
                logger.error(f"文件 {file_path.name} 未找到Test No.行")
                return None
            
            data_start_row = test_no_row + 1
            logger.debug(f"数据起始行: {data_start_row}")
            
            # 7. 提取测试数据
            test_data = []
            for row_idx in range(data_start_row, df.shape[0]):
                row_data = {'lot_ID': lot_id}
                
                # 提取每个参数列的数据
                for col, param_name in final_params:
                    value = df.iloc[row_idx, col]
                    row_data[param_name] = value
                
                test_data.append(row_data)
            
            # 转换为DataFrame
            result_df = pd.DataFrame(test_data)
            
            if not result_df.empty:
                logger.info(f"文件 {file_path.name} 提取成功，数据行数: {len(result_df)}")
                logger.info(f"参数列数: {len(final_params)}")
            else:
                logger.warning(f"文件 {file_path.name} 提取结果为空")
            
            return result_df
            
        except Exception as e:
            logger.error(f"处理文件 {file_path.name} 时出错: {str(e)}")
            return None
    
    def merge_all_dc_data(self, data_frames: List[pd.DataFrame]) -> pd.DataFrame:
        """
        合并所有文件的DC数据
        
        Args:
            data_frames: 多个DataFrame
            
        Returns:
            统一的DataFrame
        """
        logger.info(f"开始合并 {len(data_frames)} 个数据框")
        
        if not data_frames:
            logger.warning("没有可合并的数据框")
            return pd.DataFrame()
        
        try:
            # 合并所有数据框
            merged_df = pd.concat(data_frames, ignore_index=True)
            logger.info(f"数据合并完成，总行数: {len(merged_df)}")
            return merged_df
            
        except Exception as e:
            logger.error(f"合并数据时出错: {str(e)}")
            return pd.DataFrame()
    
    def clean_and_format_dc(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DC数据清洗和格式化
        
        Args:
            df: 原始合并数据
            
        Returns:
            清洗后的标准格式数据
        """
        logger.info("开始DC数据清洗和格式化")
        
        if df.empty:
            logger.warning("输入数据为空，跳过清洗")
            return df
        
        try:
            # 1. 生成连续NUM编号
            df = df.reset_index(drop=True)
            df.insert(0, 'NUM', range(1, len(df) + 1))
            
            # 2. 过滤掉空行或无效数据行
            # 保留lot_ID不为空的行
            before_filter = len(df)
            df = df.dropna(subset=['lot_ID'])
            after_filter = len(df)
            
            if before_filter != after_filter:
                logger.info(f"过滤掉 {before_filter - after_filter} 行无效数据")
            
            # 3. 标准化lot_ID格式（如果需要的话）
            df['lot_ID'] = df['lot_ID'].astype(str)
            
            # 4. 处理数值列的精度
            # 对于数值列，保持原始精度
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            logger.debug(f"数值列: {list(numeric_columns)}")
            
            # 5. 重新排序列：NUM, lot_ID, 然后是其他参数列
            cols = ['NUM', 'lot_ID']
            other_cols = [col for col in df.columns if col not in cols]
            df = df[cols + other_cols]
            
            logger.info(f"数据清洗完成，最终行数: {len(df)}")
            logger.info(f"最终列数: {len(df.columns)}")
            
            return df
            
        except Exception as e:
            logger.error(f"数据清洗时出错: {str(e)}")
            return df
    
    def save_dc_result(self, df: pd.DataFrame) -> bool:
        """
        保存最终DC结果
        
        Args:
            df: 清洗后的数据
            
        Returns:
            保存是否成功
        """
        if df.empty:
            logger.warning("没有数据可保存")
            return False
        
        try:
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"DC_{timestamp}.xlsx"
            
            # 保存到Excel文件
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='DC_Data')
            
            logger.info(f"DC数据保存成功: {output_file}")
            logger.info(f"总共处理 {len(df)} 行数据")
            return True
            
        except Exception as e:
            logger.error(f"保存DC结果时出错: {str(e)}")
            return False
    
    def process_all_dc_files(self) -> bool:
        """
        处理所有DC文件的主函数
        
        Returns:
            处理是否成功
        """
        logger.info("=" * 50)
        logger.info("开始DC数据清洗处理")
        logger.info("=" * 50)
        
        try:
            # 1. 扫描所有DC文件
            dc_files = self.scan_dc_files()
            if not dc_files:
                logger.error("没有找到DC文件")
                return False
            
            # 2. 提取每个文件的数据
            all_data_frames = []
            for file_path in dc_files:
                df = self.extract_dc_data(file_path)
                if df is not None and not df.empty:
                    all_data_frames.append(df)
            
            if not all_data_frames:
                logger.error("没有成功提取到任何数据")
                return False
            
            # 3. 合并所有数据
            merged_df = self.merge_all_dc_data(all_data_frames)
            if merged_df.empty:
                logger.error("数据合并失败")
                return False
            
            # 4. 数据清洗和格式化
            cleaned_df = self.clean_and_format_dc(merged_df)
            if cleaned_df.empty:
                logger.error("数据清洗失败")
                return False
            
            # 5. 保存结果
            success = self.save_dc_result(cleaned_df)
            
            if success:
                logger.info("=" * 50)
                logger.info("DC数据清洗处理完成")
                logger.info("=" * 50)
            
            return success
            
        except Exception as e:
            logger.error(f"处理DC文件时出现错误: {str(e)}")
            return False


def main():
    """主函数"""
    try:
        # 创建DC数据清洗器实例
        cleaner = DCDataCleaner()
        
        # 处理所有DC文件
        success = cleaner.process_all_dc_files()
        
        if success:
            print("DC数据清洗完成！")
        else:
            print("DC数据清洗失败，请查看日志文件获取详细信息。")
            
    except Exception as e:
        logger.error(f"主程序执行错误: {str(e)}")
        print(f"程序执行出错: {str(e)}")


if __name__ == "__main__":
    main() 
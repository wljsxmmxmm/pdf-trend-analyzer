#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF文本提取和趋势强度分析工具

功能:
1. 从PDF文件中提取文本内容
2. 从PDF文件中提取趋势强度信息并生成透视表格式的CSV
3. 支持单文件和批量处理
4. 提供图形界面和命令行接口

作者: AI Assistant
日期: 2025-01-20
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from datetime import datetime
import threading
import re
import csv
import pandas as pd

try:
    import fitz  # PyMuPDF
except ImportError:
    print("错误: 缺少必要的依赖库 PyMuPDF")
    print("请使用以下命令安装: pip install PyMuPDF")
    sys.exit(1)


def extract_text_from_pdf(pdf_path, max_pages=None, start_page=0):
    """
    从PDF文件中提取文本内容
    
    Args:
        pdf_path: PDF文件路径
        max_pages: 最大提取页数，None表示提取所有页
        start_page: 起始页码（从0开始）
        
    Returns:
        tuple: (提取的文本内容, 页数信息)
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        # 计算实际提取的页数范围
        start_page = max(0, start_page)
        if max_pages:
            end_page = min(total_pages, start_page + max_pages)
        else:
            end_page = total_pages
            
        pages_to_extract = end_page - start_page
        
        print(f"开始提取 {pdf_path}")
        print(f"总页数: {total_pages}, 提取页数: {start_page+1}-{end_page} (共{pages_to_extract}页)")
        
        # 提取文本
        text_content = []
        for page_num in range(start_page, end_page):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            
            # 添加页码标记
            page_header = f"\n\n=== 第 {page_num + 1} 页 ===\n"
            text_content.append(page_header + text)
            
        doc.close()
        
        extracted_text = "\n".join(text_content)
        page_info = {
            'total_pages': total_pages,
            'extracted_pages': pages_to_extract,
            'start_page': start_page + 1,
            'end_page': end_page
        }
        
        return extracted_text, page_info
    
    except Exception as e:
        error_msg = f"提取PDF文本时出错: {str(e)}"
        print(error_msg)
        return "", {'error': error_msg}


def save_text_to_file(text, output_path, pdf_filename):
    """
    将提取的文本保存到文件
    
    Args:
        text: 提取的文本内容
        output_path: 输出文件路径
        pdf_filename: 原PDF文件名
    """
    try:
        # 生成输出文件名
        base_name = os.path.splitext(pdf_filename)[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{base_name}_extracted_{timestamp}.txt"
        full_output_path = os.path.join(output_path, output_filename)
        
        # 保存文本
        with open(full_output_path, 'w', encoding='utf-8') as f:
            f.write(f"PDF文本提取结果\n")
            f.write(f"原文件: {pdf_filename}\n")
            f.write(f"提取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*50}\n\n")
            f.write(text)
        
        print(f"文本已保存到: {full_output_path}")
        return full_output_path
        
    except Exception as e:
        error_msg = f"保存文本文件时出错: {str(e)}"
        print(error_msg)
        return None


def batch_extract_pdfs(pdf_directory, output_directory, max_pages=None):
    """
    批量提取PDF文件的文本
    
    Args:
        pdf_directory: PDF文件目录
        output_directory: 输出目录
        max_pages: 每个PDF最大提取页数
        
    Returns:
        处理结果统计
    """
    if not os.path.exists(pdf_directory):
        print(f"PDF目录不存在: {pdf_directory}")
        return None
        
    # 确保输出目录存在
    os.makedirs(output_directory, exist_ok=True)
    
    # 查找所有PDF文件
    pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"在目录 {pdf_directory} 中未找到PDF文件")
        return None
    
    print(f"找到 {len(pdf_files)} 个PDF文件，开始批量处理...")
    
    results = {
        'total_files': len(pdf_files),
        'success_count': 0,
        'failed_count': 0,
        'failed_files': []
    }
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n处理第 {i}/{len(pdf_files)} 个文件: {pdf_file}")
        
        pdf_path = os.path.join(pdf_directory, pdf_file)
        text, page_info = extract_text_from_pdf(pdf_path, max_pages)
        
        if text and 'error' not in page_info:
            # 保存提取的文本
            saved_path = save_text_to_file(text, output_directory, pdf_file)
            if saved_path:
                results['success_count'] += 1
                print(f"✓ 成功处理: {pdf_file}")
            else:
                results['failed_count'] += 1
                results['failed_files'].append(pdf_file)
                print(f"✗ 保存失败: {pdf_file}")
        else:
            results['failed_count'] += 1
            results['failed_files'].append(pdf_file)
            print(f"✗ 提取失败: {pdf_file}")
    
    print(f"\n批量处理完成:")
    print(f"总文件数: {results['total_files']}")
    print(f"成功: {results['success_count']}")
    print(f"失败: {results['failed_count']}")
    if results['failed_files']:
        print(f"失败文件: {', '.join(results['failed_files'])}")
    
    return results


def extract_trend_strength_from_text(text, report_date=None):
    """
    从文本中提取趋势强度信息
    
    Args:
        text: PDF提取的文本内容
        report_date: 报告日期
    
    Returns:
        list: 提取的趋势强度数据列表
    """
    trend_data = []
    
    # 尝试从文件名或内容中提取日期
    if not report_date:
        date_patterns = [
            r'(\d{4})(\d{2})(\d{2})',
            r'(\d{4})-(\d{2})-(\d{2})',
            r'(\d{4})/(\d{2})/(\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                year, month, day = match.groups()
                report_date = f"{year}-{month}-{day}"
                break
    
    if not report_date:
        report_date = datetime.now().strftime("%Y-%m-%d")
    
    # 查找趋势强度信息 - 匹配"趋势强度："前面的品种名（支持中文、英文、数字、括号等，允许空格）
    patterns = [
        r'([\u4e00-\u9fa5A-Za-z0-9（）()]+)\s*趋势强度[：:]\s*([+-]?\d+(?:\.\d+)?)',
    ]
    
    found_data = set()  # 用于去重
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) == 2:
                variety, strength = match
                variety = variety.strip()
                
                # 过滤掉一些无效的品种名和重复的品种
                # 移除品种名中的"趋势强度"后缀（如"不锈钢趋势强度"变为"不锈钢"）
                if variety.endswith('趋势强度'):
                    variety = variety[:-4]  # 移除"趋势强度"4个字符
                
                # 过滤条件：
                # 1. 品种名长度大于0
                # 2. 不包含无效关键词
                # 3. 不是纯数字
                # 4. 包含中文字符、英文字符、数字、括号等合法字符
                invalid_keywords = ['趋势', '强度', '注释', '东莞', '达孚', '公司', '有限', '集团']
                if (len(variety) > 0 and 
                    not any(keyword in variety for keyword in invalid_keywords) and
                    not variety.isdigit() and
                    re.match(r'^[\u4e00-\u9fa5A-Za-z0-9（）()]+$', variety)):
                    try:
                        strength_value = float(strength)
                        # 确保趋势强度在合理范围内
                        if -10 <= strength_value <= 10:
                            key = (variety, strength_value)
                            if key not in found_data:
                                found_data.add(key)
                                trend_data.append({
                                    '品种': variety,
                                    '趋势强度': strength_value,
                                    '日期': report_date
                                })
                    except ValueError:
                        continue
    
    return trend_data

def save_trend_strength_pivot_csv(all_trend_data, output_dir, incremental=True):
    """
    将趋势强度数据保存为透视表格式的CSV文件，并标记发生变化的品种
    支持增量更新，可以将新数据合并到已有数据中
    
    Args:
        all_trend_data: 所有趋势强度数据列表
        output_dir: 输出目录
        incremental: 是否启用增量更新模式，默认为True
    
    Returns:
        str: 保存的文件路径
    """
    if not all_trend_data:
        return None
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 定义文件路径
    output_file = os.path.join(output_dir, 'trend_strength_pivot.csv')
    change_output_file = os.path.join(output_dir, 'trend_strength_pivot_with_changes.csv')
    
    # 创建新数据的DataFrame
    new_df = pd.DataFrame(all_trend_data)
    
    # 创建新数据的透视表
    new_pivot_df = new_df.pivot_table(
        index='日期', 
        columns='品种', 
        values='趋势强度', 
        fill_value=0.0
    )
    
    # 如果启用增量更新且已有文件存在，则合并数据
    if incremental and os.path.exists(output_file):
        try:
            # 读取已有数据
            existing_pivot_df = pd.read_csv(output_file, index_col=0, encoding='utf-8-sig')
            
            # 确保索引为字符串类型以便比较
            existing_pivot_df.index = existing_pivot_df.index.astype(str)
            new_pivot_df.index = new_pivot_df.index.astype(str)
            
            # 合并数据：使用concat合并，然后处理重复
            combined_df = pd.concat([existing_pivot_df, new_pivot_df])
            
            # 去重：对于相同日期的数据，保留最新的（后面的）
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
            
            # 填充缺失值
            combined_df = combined_df.fillna(0.0)
            
            # 按日期排序
            pivot_df = combined_df.sort_index()
            
            print(f"增量更新模式：合并了已有数据和新数据")
            print(f"已有数据: {existing_pivot_df.shape[0]} 个日期, {existing_pivot_df.shape[1]} 个品种")
            print(f"新数据: {new_pivot_df.shape[0]} 个日期, {new_pivot_df.shape[1]} 个品种")
            
        except Exception as e:
            print(f"读取已有数据时出错，将使用新数据覆盖: {e}")
            pivot_df = new_pivot_df.sort_index()
    else:
        # 不使用增量更新或文件不存在，直接使用新数据
        pivot_df = new_pivot_df.sort_index()
    
    # 检测趋势强度变化并创建变化标记表
    change_df = pivot_df.astype(str).copy()
    
    for col in pivot_df.columns:
        for i in range(len(pivot_df)):
            current_value = pivot_df.iloc[i][col]
            
            if i == 0:
                # 第一行直接显示所有数值（包括0）
                change_df.iloc[i, change_df.columns.get_loc(col)] = str(current_value)
            else:
                previous_value = pivot_df.iloc[i-1][col]
                
                # 如果趋势强度发生变化，用★标记
                if current_value != previous_value:
                    change_df.iloc[i, change_df.columns.get_loc(col)] = f'★{current_value}'
                else:
                    # 没有变化，正常显示数值
                    change_df.iloc[i, change_df.columns.get_loc(col)] = str(current_value)
    
    # 保存原始透视表
    pivot_df.to_csv(output_file, encoding='utf-8-sig')
    
    # 保存带变化标记的透视表
    change_df.to_csv(change_output_file, encoding='utf-8-sig')
    
    print(f"\n趋势强度透视表已保存到: {output_file}")
    print(f"带变化标记的透视表已保存到: {change_output_file}")
    print(f"数据维度: {pivot_df.shape[0]} 个日期, {pivot_df.shape[1]} 个品种")
    
    # 统计变化情况
    total_changes = 0
    for col in pivot_df.columns:
        for i in range(1, len(pivot_df)):
            current_value = pivot_df.iloc[i][col]
            previous_value = pivot_df.iloc[i-1][col]
            if (current_value != previous_value and 
                current_value != 0 and previous_value != 0):
                total_changes += 1
    
    print(f"检测到 {total_changes} 次趋势强度变化（用★标记）")
    
    return output_file

def analyze_pdf_trend_strength(pdf_path, output_dir=None):
    """
    分析PDF文件中的趋势强度信息
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
    
    Returns:
        list: 提取的趋势强度数据
    """
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)
    
    print(f"正在分析PDF文件: {pdf_path}")
    
    # 提取PDF文本
    text_content, page_info = extract_text_from_pdf(pdf_path)
    
    if not text_content or 'error' in page_info:
        print(f"PDF文本提取失败: {page_info.get('error', '未知错误')}")
        return []
    
    # 尝试从文件名提取日期
    filename = os.path.basename(pdf_path)
    date_match = re.search(r'(\d{8})', filename)
    report_date = None
    if date_match:
        date_str = date_match.group(1)
        report_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    
    # 提取趋势强度信息
    trend_data = extract_trend_strength_from_text(text_content, report_date)
    
    if trend_data:
        print(f"成功提取到 {len(trend_data)} 个品种的趋势强度信息")
        for data in trend_data:
            print(f"  {data['品种']}: {data['趋势强度']} (日期: {data['日期']})")
    else:
        print("未找到趋势强度信息")
        # 调试信息：显示包含"趋势强度"的文本行
        lines_with_trend = [line.strip() for line in text_content.split('\n') 
                           if '趋势强度' in line and line.strip()]
        if lines_with_trend:
            print("\n包含'趋势强度'的文本行:")
            for line in lines_with_trend[:5]:  # 只显示前5行
                print(f"  {line}")
    
    return trend_data

def batch_analyze_trend_strength(pdf_directory, output_directory):
    """
    批量分析PDF文件中的趋势强度信息
    
    Args:
        pdf_directory: PDF文件目录
        output_directory: 输出目录
    
    Returns:
        dict: 处理结果统计
    """
    pdf_files = list(Path(pdf_directory).glob("*.pdf"))
    
    if not pdf_files:
        print(f"在目录 {pdf_directory} 中未找到PDF文件")
        return {'success_count': 0, 'failed_count': 0, 'trend_data': []}
    
    print(f"找到 {len(pdf_files)} 个PDF文件")
    
    all_trend_data = []
    success_count = 0
    failed_count = 0
    
    for pdf_file in pdf_files:
        try:
            trend_data = analyze_pdf_trend_strength(str(pdf_file), output_directory)
            if trend_data:
                all_trend_data.extend(trend_data)
                success_count += 1
                print(f"✓ {pdf_file.name} - 提取到 {len(trend_data)} 个品种")
            else:
                failed_count += 1
                print(f"✗ {pdf_file.name} - 未找到趋势强度信息")
        except Exception as e:
            failed_count += 1
            print(f"✗ {pdf_file.name} - 处理失败: {str(e)}")
    
    # 保存汇总的透视表
    if all_trend_data:
        pivot_file = save_trend_strength_pivot_csv(all_trend_data, output_directory)
        print(f"\n批量处理完成！")
        print(f"成功处理: {success_count} 个文件")
        print(f"失败: {failed_count} 个文件")
        print(f"总共提取: {len(all_trend_data)} 条趋势强度记录")
        if pivot_file:
            print(f"透视表文件: {pivot_file}")
    
    return {
        'success_count': success_count,
        'failed_count': failed_count,
        'trend_data': all_trend_data,
        'pivot_file': pivot_file if all_trend_data else None
    }


class PDFTextExtractorGUI:
    """PDF文本提取工具的图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        self.root.title("PDF文本提取和趋势强度分析工具")
        self.root.geometry("800x700")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 功能选择
        function_frame = ttk.LabelFrame(main_frame, text="功能选择", padding="10")
        function_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.function_var = tk.StringVar(value="text")
        ttk.Radiobutton(function_frame, text="文本提取", variable=self.function_var, 
                       value="text", command=self.on_function_change).grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(function_frame, text="趋势强度提取", variable=self.function_var, 
                       value="trend", command=self.on_function_change).grid(row=0, column=1, sticky=tk.W)
        
        # 模式选择
        mode_frame = ttk.LabelFrame(main_frame, text="处理模式", padding="10")
        mode_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.mode_var = tk.StringVar(value="single")
        ttk.Radiobutton(mode_frame, text="单个PDF文件", variable=self.mode_var, 
                       value="single", command=self.on_mode_change).grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="批量处理", variable=self.mode_var, 
                       value="batch", command=self.on_mode_change).grid(row=0, column=1, sticky=tk.W)
        
        # 文件/目录选择
        self.file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
        self.file_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.file_var = tk.StringVar()
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_var, width=60)
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.file_button = ttk.Button(self.file_frame, text="选择文件", command=self.select_file)
        self.file_button.grid(row=0, column=1)
        
        # 输出目录选择
        output_frame = ttk.LabelFrame(main_frame, text="输出目录", padding="10")
        output_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.output_var = tk.StringVar()
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_var, width=60)
        self.output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(output_frame, text="选择目录", command=self.select_output_dir).grid(row=0, column=1)
        
        # 提取选项（仅文本提取时显示）
        self.options_frame = ttk.LabelFrame(main_frame, text="提取选项", padding="10")
        self.options_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 页数限制
        ttk.Label(self.options_frame, text="最大页数:").grid(row=0, column=0, sticky=tk.W)
        self.max_pages_var = tk.StringVar()
        ttk.Entry(self.options_frame, textvariable=self.max_pages_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(self.options_frame, text="(留空表示提取所有页)").grid(row=0, column=2, sticky=tk.W)
        
        # 起始页
        ttk.Label(self.options_frame, text="起始页:").grid(row=1, column=0, sticky=tk.W, pady=(5,0))
        self.start_page_var = tk.StringVar(value="1")
        ttk.Entry(self.options_frame, textvariable=self.start_page_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=(5,0))
        ttk.Label(self.options_frame, text="(从第几页开始提取)").grid(row=1, column=2, sticky=tk.W, pady=(5,0))
        
        # 操作按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        self.extract_button = ttk.Button(button_frame, text="开始处理", command=self.start_extraction)
        self.extract_button.grid(row=0, column=0, padx=5)
        
        ttk.Button(button_frame, text="清空结果", command=self.clear_results).grid(row=0, column=1, padx=5)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # 结果显示
        result_frame = ttk.LabelFrame(main_frame, text="处理结果", padding="10")
        result_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 创建文本框和滚动条
        text_frame = ttk.Frame(result_frame)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.result_text = tk.Text(text_frame, height=20, width=80, wrap=tk.WORD)
        scrollbar_y = ttk.Scrollbar(text_frame, orient="vertical", command=self.result_text.yview)
        scrollbar_x = ttk.Scrollbar(text_frame, orient="horizontal", command=self.result_text.xview)
        
        self.result_text.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        scrollbar_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 配置网格权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
        self.file_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        # 初始化界面状态
        self.on_function_change()
    
    def on_function_change(self):
        """功能切换时更新界面"""
        function = self.function_var.get()
        if function == "text":
            self.options_frame.grid()
            self.extract_button.config(text="开始提取")
        else:
            self.options_frame.grid_remove()
            self.extract_button.config(text="开始分析")
    
    def on_mode_change(self):
        """模式切换时更新界面"""
        mode = self.mode_var.get()
        if mode == "single":
            self.file_frame.config(text="PDF文件选择")
            self.file_button.config(text="选择文件")
        else:
            self.file_frame.config(text="PDF目录选择")
            self.file_button.config(text="选择目录")
    
    def select_file(self):
        """选择文件或目录"""
        mode = self.mode_var.get()
        if mode == "single":
            filename = filedialog.askopenfilename(
                title="选择PDF文件",
                filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
            )
            if filename:
                self.file_var.set(filename)
                # 自动设置输出目录
                if not self.output_var.get():
                    self.output_var.set(os.path.dirname(filename))
        else:
            directory = filedialog.askdirectory(title="选择PDF文件目录")
            if directory:
                self.file_var.set(directory)
                # 自动设置输出目录
                if not self.output_var.get():
                    self.output_var.set(directory)
    
    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_var.set(directory)
    
    def start_extraction(self):
        """开始处理"""
        file_path = self.file_var.get().strip()
        output_dir = self.output_var.get().strip()
        mode = self.mode_var.get()
        function = self.function_var.get()
        
        if not file_path:
            messagebox.showerror("错误", "请选择PDF文件或目录")
            return
        
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            return
        
        # 获取页数设置（仅文本提取时使用）
        max_pages = None
        start_page = 0
        
        if function == "text":
            try:
                if self.max_pages_var.get().strip():
                    max_pages = int(self.max_pages_var.get())
                if self.start_page_var.get().strip():
                    start_page = int(self.start_page_var.get()) - 1  # 转换为0基索引
                    start_page = max(0, start_page)
            except ValueError:
                messagebox.showerror("错误", "页数设置必须是数字")
                return
        
        # 在后台线程中执行处理
        self.extract_button.config(state='disabled')
        self.progress.start()
        self.result_text.delete(1.0, tk.END)
        
        if function == "text":
            self.result_text.insert(tk.END, "正在提取PDF文本，请稍候...\n")
        else:
            self.result_text.insert(tk.END, "正在分析趋势强度，请稍候...\n")
        
        thread = threading.Thread(target=self.run_extraction, 
                                 args=(file_path, output_dir, mode, function, max_pages, start_page))
        thread.daemon = True
        thread.start()
    
    def run_extraction(self, file_path, output_dir, mode, function, max_pages, start_page):
        """在后台运行处理"""
        try:
            import io
            from contextlib import redirect_stdout
            
            output_buffer = io.StringIO()
            
            with redirect_stdout(output_buffer):
                if function == "text":
                    # 文本提取
                    if mode == "single":
                        text, page_info = extract_text_from_pdf(file_path, max_pages, start_page)
                        if text and 'error' not in page_info:
                            filename = os.path.basename(file_path)
                            saved_path = save_text_to_file(text, output_dir, filename)
                            result = {'success': True, 'text': text, 'page_info': page_info, 'saved_path': saved_path}
                        else:
                            result = {'success': False, 'error': page_info.get('error', '未知错误')}
                    else:
                        result = batch_extract_pdfs(file_path, output_dir, max_pages)
                else:
                    # 趋势强度分析
                    if mode == "single":
                        trend_data = analyze_pdf_trend_strength(file_path, output_dir)
                        if trend_data:
                            pivot_file = save_trend_strength_pivot_csv(trend_data, output_dir)
                            result = {'success': True, 'trend_data': trend_data, 'pivot_file': pivot_file}
                        else:
                            result = {'success': False, 'error': '未找到趋势强度信息'}
                    else:
                        result = batch_analyze_trend_strength(file_path, output_dir)
                        result['success'] = result['success_count'] > 0
            
            # 获取输出内容
            output_content = output_buffer.getvalue()
            
            # 在主线程中更新GUI
            self.root.after(0, self.extraction_complete, output_content, result, mode, function)
            
        except Exception as e:
            error_msg = f"处理过程中出现错误: {str(e)}"
            self.root.after(0, self.extraction_error, error_msg)
    
    def extraction_complete(self, output_content, result, mode, function):
        """处理完成"""
        self.progress.stop()
        self.extract_button.config(state='normal')
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, output_content)
        
        if function == "text":
            # 文本提取结果
            if mode == "single":
                if result['success']:
                    self.result_text.insert(tk.END, f"\n提取完成！\n")
                    self.result_text.insert(tk.END, f"页数信息: {result['page_info']}\n")
                    if result['saved_path']:
                        self.result_text.insert(tk.END, f"文件已保存到: {result['saved_path']}\n")
                    
                    # 显示部分提取的文本
                    if len(result['text']) > 1000:
                        preview_text = result['text'][:1000] + "\n\n... (文本过长，仅显示前1000字符) ..."
                    else:
                        preview_text = result['text']
                    
                    self.result_text.insert(tk.END, f"\n提取的文本内容:\n{'-'*50}\n{preview_text}")
                    messagebox.showinfo("完成", "PDF文本提取完成！")
                else:
                    self.result_text.insert(tk.END, f"\n提取失败: {result['error']}\n")
                    messagebox.showerror("错误", f"提取失败: {result['error']}")
            else:
                if result:
                    self.result_text.insert(tk.END, f"\n批量处理完成！\n")
                    messagebox.showinfo("完成", f"批量处理完成！成功: {result['success_count']}, 失败: {result['failed_count']}")
                else:
                    messagebox.showerror("错误", "批量处理失败")
        else:
            # 趋势强度分析结果
            if mode == "single":
                if result['success']:
                    self.result_text.insert(tk.END, f"\n分析完成！共提取到 {len(result['trend_data'])} 个品种的趋势强度信息。\n")
                    if result['pivot_file']:
                        self.result_text.insert(tk.END, f"透视表文件已保存到: {result['pivot_file']}\n")
                    messagebox.showinfo("完成", f"分析完成！共提取到 {len(result['trend_data'])} 个品种的趋势强度信息。")
                else:
                    self.result_text.insert(tk.END, f"\n分析失败: {result['error']}\n")
                    messagebox.showerror("错误", f"分析失败: {result['error']}")
            else:
                if result['success']:
                    self.result_text.insert(tk.END, f"\n批量分析完成！\n")
                    if result.get('pivot_file'):
                        self.result_text.insert(tk.END, f"透视表文件已保存到: {result['pivot_file']}\n")
                    messagebox.showinfo("完成", f"批量分析完成！成功: {result['success_count']}, 失败: {result['failed_count']}")
                else:
                    messagebox.showerror("错误", "批量分析失败")
    
    def extraction_error(self, error_msg):
        """处理出错"""
        self.progress.stop()
        self.extract_button.config(state='normal')
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, error_msg)
        
        messagebox.showerror("错误", error_msg)
    
    def clear_results(self):
        """清空结果"""
        self.result_text.delete(1.0, tk.END)


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        # 命令行模式
        pdf_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(pdf_path)
        max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else None
        start_page = int(sys.argv[4]) - 1 if len(sys.argv) > 4 else 0
        
        if os.path.isfile(pdf_path):
            # 单文件处理
            text, page_info = extract_text_from_pdf(pdf_path, max_pages, start_page)
            if text and 'error' not in page_info:
                filename = os.path.basename(pdf_path)
                save_text_to_file(text, output_dir, filename)
                print(f"\n提取完成！页数信息: {page_info}")
            else:
                print(f"提取失败: {page_info.get('error', '未知错误')}")
        elif os.path.isdir(pdf_path):
            # 批量处理
            batch_extract_pdfs(pdf_path, output_dir, max_pages)
        else:
            print(f"错误: 路径不存在 - {pdf_path}")
    else:
        # GUI模式
        root = tk.Tk()
        app = PDFTextExtractorGUI(root)
        root.mainloop()


if __name__ == "__main__":
    main()
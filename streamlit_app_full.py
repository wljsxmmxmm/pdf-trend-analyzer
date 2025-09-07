#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF趋势强度提取工具 - Streamlit版本

功能：
1. 直接从PDF文件中提取文本内容
2. 识别并提取【趋势强度】部分的品种信息
3. 输出按品种和按日期分类的CSV文件
4. 支持Web界面文件上传
"""

import os
import re
import csv
import io
from pathlib import Path
from datetime import datetime
from io import BytesIO
import pandas as pd
import streamlit as st

try:
    import fitz  # PyMuPDF
except ImportError:
    st.error("错误: 缺少必要的依赖库 PyMuPDF")
    st.error("请使用以下命令安装: pip install PyMuPDF")
    st.stop()


def extract_text_from_pdf(pdf_file, max_pages=None):
    """
    从PDF文件中提取文本内容
    
    Args:
        pdf_file: PDF文件对象或路径
        max_pages: 最大提取页数，None表示提取所有页
        
    Returns:
        提取的文本内容
    """
    try:
        # 如果是文件对象，读取字节数据
        if hasattr(pdf_file, 'read'):
            pdf_bytes = pdf_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        else:
            doc = fitz.open(pdf_file)
            
        total_pages = len(doc)
        pages_to_extract = min(total_pages, max_pages) if max_pages else total_pages
        
        st.info(f"开始提取PDF文件 (共 {total_pages} 页，将提取 {pages_to_extract} 页)")
        
        # 提取文本
        text_content = []
        for page_num in range(pages_to_extract):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            text_content.append(text)
            
        doc.close()
        return "\n\n".join(text_content)
    
    except Exception as e:
        st.error(f"提取PDF文本时出错: {str(e)}")
        return ""


def extract_trend_strength_from_text(text, report_date=None):
    """
    从文本中提取趋势强度信息
    
    Args:
        text: 文本内容
        report_date: 报告日期
        
    Returns:
        提取的趋势强度数据列表
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
    
    st.info("正在查找趋势强度信息...")
    
    # 查找趋势强度信息 - 匹配"趋势强度："前面的品种名（支持中文、英文、数字、括号等，允许空格）
    patterns = [
        r'([\u4e00-\u9fa5A-Za-z0-9（）()]+)\s*趋势强度[：:]\s*([+-]?\d+(?:\.\d+)?)',
    ]
    
    found_data = set()  # 用于去重
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        st.info(f"使用模式 {pattern} 找到 {len(matches)} 个匹配项")
        
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
                        # 先转换为浮点数进行范围验证，但保存原始字符串
                        strength_float = float(strength)
                        # 确保趋势强度在合理范围内
                        if -10 <= strength_float <= 10:
                            # 使用原始字符串作为趋势值
                            key = (variety, strength)
                            if key not in found_data:
                                found_data.add(key)
                                trend_data.append({
                                    '品种': variety,
                                    '趋势强度': strength,  # 保存原始字符串
                                    '趋势强度_float': strength_float,  # 保存浮点数用于计算
                                    '日期': report_date
                                })
                                st.success(f"提取: {variety} = {strength}")
                    except ValueError:
                        st.warning(f"跳过无效数值: {variety} = {strength}")
                        continue
    
    # 如果没有找到数据，尝试查找【趋势强度】部分的格式
    if not trend_data:
        st.warning("未找到标准格式的趋势强度信息，尝试查找【趋势强度】部分...")
        
        # 查找【趋势强度】部分 - 更宽松的匹配
        trend_patterns = [
            r'【趋势强度】([\s\S]*?)(?=【|$)',
            r'趋势强度([\s\S]*?)(?=【|$)',
            r'\[趋势强度\]([\s\S]*?)(?=\[|$)'
        ]
        
        trend_content = None
        for pattern in trend_patterns:
            trend_match = re.search(pattern, text, re.IGNORECASE)
            if trend_match:
                trend_content = trend_match.group(1)
                st.success(f"找到趋势强度内容，使用模式: {pattern}")
                break
        
        if trend_content:
            st.info(f"趋势强度内容长度: {len(trend_content)} 字符")
            
            # 提取偏强、中性、偏弱品种
            categories = {
                '偏强': 1,
                '中性': 0, 
                '偏弱': -1
            }
            
            for category, strength_value in categories.items():
                st.info(f"正在查找{category}品种...")
                
                # 多种匹配模式
                patterns = [
                    rf'{category}[：:](.*?)(?=(?:偏强|中性|偏弱)[：:]|$)',
                    rf'{category}\s*[：:]\s*(.*?)(?=(?:偏强|中性|偏弱)|$)',
                    rf'{category}\s*[:：]\s*(.*?)(?=\n\n|\n[^\u4e00-\u9fff]|$)'
                ]
                
                content = None
                for pattern in patterns:
                    match = re.search(pattern, trend_content, re.DOTALL | re.IGNORECASE)
                    if match:
                        content = match.group(1).strip()
                        st.success(f"找到{category}内容，使用模式: {pattern}")
                        break
                
                if content:
                    # 提取品种和数字 - 支持多种格式
                    variety_patterns = [
                        r'([\u4e00-\u9fff]+)\s*[（(]([+-]?\d+(?:\.\d+)?)[）)]',  # 品种名(数字)
                        r'([\u4e00-\u9fff]+)\s*[：:]\s*([+-]?\d+(?:\.\d+)?)',    # 品种名: 数字
                        r'([\u4e00-\u9fff]+)\s+([+-]?\d+(?:\.\d+)?)',          # 品种名 数字
                    ]
                    
                    varieties = []
                    for var_pattern in variety_patterns:
                        found = re.findall(var_pattern, content)
                        if found:
                            varieties.extend(found)
                    
                    # 去重
                    seen = set()
                    unique_varieties = []
                    for variety, number in varieties:
                        key = variety.strip()
                        if key not in seen:
                            seen.add(key)
                            unique_varieties.append((variety, number))
                    
                    for i, (variety, number) in enumerate(unique_varieties, 1):
                        try:
                            # 先转换为浮点数进行验证，但保存原始字符串
                            number_float = float(number)
                            # 确保趋势强度在合理范围内
                            if -10 <= number_float <= 10:
                                trend_data.append({
                                    '品种': variety.strip(),
                                    '趋势强度': number,  # 保存原始字符串
                                    '趋势强度_float': number_float,  # 保存浮点数用于计算
                                    '序号': i,
                                    '类别': category,
                                    '日期': report_date
                                })
                                st.success(f"提取: {variety.strip()} = {number}")
                        except ValueError:
                            st.warning(f"跳过无效数值: {variety} = {number}")
                            continue
                else:
                    st.warning(f"未找到{category}品种内容")
    
    if trend_data:
        st.success(f"共提取到 {len(trend_data)} 个品种的趋势强度信息")
    else:
        st.error("未找到任何趋势强度信息")
        # 显示调试信息
        lines_with_trend = [line.strip() for line in text.split('\n') 
                           if '趋势强度' in line and line.strip()]
        if lines_with_trend:
            st.info("包含'趋势强度'的文本行:")
            for line in lines_with_trend[:5]:  # 只显示前5行
                st.text(f"  {line}")
        else:
            st.warning("文档中未找到包含'趋势强度'的文本行")
    
    return trend_data


def save_trend_strength_pivot_csv(all_trend_data, output_dir=None, incremental=True):
    """
    将趋势强度数据保存为透视表格式的CSV文件，并标记发生变化的品种
    支持增量更新，可以将新数据合并到已有数据中
    
    Args:
        all_trend_data: 所有趋势强度数据列表
        output_dir: 输出目录（在Streamlit中不使用）
        incremental: 是否启用增量更新模式，默认为True
    
    Returns:
        tuple: (pivot_df, change_df) 透视表和变化标记表
    """
    if not all_trend_data:
        return None, None
    
    # 创建新数据的DataFrame
    new_df = pd.DataFrame(all_trend_data)
    
    # 如果启用增量更新且存在历史数据，则合并
    if incremental and 'historical_data' in st.session_state:
        st.info("检测到历史数据，正在进行增量更新...")
        historical_df = pd.DataFrame(st.session_state.historical_data)
        
        # 合并历史数据和新数据
        combined_df = pd.concat([historical_df, new_df], ignore_index=True)
        
        # 去重：同一日期同一品种只保留最新的记录
        combined_df = combined_df.drop_duplicates(subset=['日期', '品种'], keep='last')
        
        st.info(f"合并后数据量: {len(combined_df)} 条记录")
    else:
        combined_df = new_df
        st.info(f"使用新数据: {len(combined_df)} 条记录")
    
    # 更新session_state中的历史数据
    st.session_state.historical_data = combined_df.to_dict('records')
    
    # 保存到CSV文件以实现持久化
    try:
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)
        csv_file_path = data_dir / "trend_strength_data.csv"
        combined_df.to_csv(csv_file_path, index=False)
        st.success(f"已将 {len(combined_df)} 条数据保存到CSV文件")
    except Exception as e:
        st.error(f"保存CSV文件时出错: {str(e)}")
    
    # 创建透视表 - 使用浮点数字段进行计算
    if '趋势强度_float' in combined_df.columns:
        # 使用浮点数字段创建计算用的透视表
        pivot_calc_df = combined_df.pivot_table(
            index='日期', 
            columns='品种', 
            values='趋势强度_float', 
            fill_value=0.0
        )
        
        # 使用原始字符串创建显示用的透视表
        pivot_df = combined_df.pivot_table(
            index='日期', 
            columns='品种', 
            values='趋势强度', 
            aggfunc='first',  # 使用第一个值，因为字符串不能求平均
            fill_value='0'
        )
    else:
        # 向后兼容，如果没有浮点数字段，则使用原始字段
        pivot_df = combined_df.pivot_table(
            index='日期', 
            columns='品种', 
            values='趋势强度', 
            fill_value='0'
        )
    
    # 按日期排序
    pivot_df = pivot_df.sort_index()
    
    # 检测趋势强度变化并创建变化标记表
    change_df = pivot_df.copy()
    
    # 使用计算用的透视表进行比较（如果存在）
    compare_df = pivot_calc_df if '趋势强度_float' in combined_df.columns else pivot_df
    
    for col in pivot_df.columns:
        for i in range(len(pivot_df)):
            current_value = pivot_df.iloc[i][col]  # 显示用的原始字符串值
            
            if i == 0:
                # 第一行直接显示所有数值
                change_df.iloc[i, change_df.columns.get_loc(col)] = current_value
            else:
                # 使用计算用的值进行比较
                current_compare = compare_df.iloc[i][col]
                previous_compare = compare_df.iloc[i-1][col]
                
                # 如果趋势强度发生变化，用★标记
                if current_compare != previous_compare:
                    change_df.iloc[i, change_df.columns.get_loc(col)] = f'★{current_value}'
                else:
                    # 没有变化，正常显示数值
                    change_df.iloc[i, change_df.columns.get_loc(col)] = current_value
    
    # 统计变化情况
    total_changes = 0
    # 使用计算用的透视表进行比较（如果存在）
    stats_df = pivot_calc_df if '趋势强度_float' in combined_df.columns else pivot_df
    
    for col in stats_df.columns:
        for i in range(1, len(stats_df)):
            current_value = stats_df.iloc[i][col]
            previous_value = stats_df.iloc[i-1][col]
            # 对于浮点数比较，使用不等于；对于字符串，需要先确保不是'0'再比较
            if isinstance(current_value, (int, float)):
                if (current_value != previous_value and 
                    current_value != 0 and previous_value != 0):
                    total_changes += 1
            else:  # 字符串情况
                if (current_value != previous_value and 
                    current_value != '0' and previous_value != '0'):
                    total_changes += 1
    
    st.info(f"数据维度: {pivot_df.shape[0]} 个日期, {pivot_df.shape[1]} 个品种")
    st.info(f"检测到 {total_changes} 次趋势强度变化（用★标记）")
    
    return pivot_df, change_df

def create_download_files(trend_data):
    """
    创建可下载的文件
    
    Args:
        trend_data: 趋势强度数据列表
        
    Returns:
        包含文件内容的字典
    """
    if not trend_data:
        return {}
    
    files = {}
    
    # 确定字段名（根据数据中是否包含文件名字段）
    sample_item = trend_data[0]
    base_fields = ['品种', '趋势强度', '日期']
    optional_fields = []
    
    if '序号' in sample_item:
        optional_fields.append('序号')
    if '类别' in sample_item:
        optional_fields.append('类别')
    if '文件名' in sample_item:
        optional_fields.append('文件名')
    
    # 排除趋势强度_float字段，这个字段只用于内部计算
    all_fields = base_fields + optional_fields
    
    # 按品种分组的CSV
    by_variety_csv = io.StringIO()
    writer = csv.DictWriter(by_variety_csv, fieldnames=all_fields)
    writer.writeheader()
    sorted_data = sorted(trend_data, key=lambda x: x['品种'])
    
    # 过滤掉趋势强度_float字段
    filtered_data = []
    for item in sorted_data:
        filtered_item = {k: v for k, v in item.items() if k != '趋势强度_float'}
        filtered_data.append(filtered_item)
    
    writer.writerows(filtered_data)
    files['trend_strength_by_variety.csv'] = by_variety_csv.getvalue()
    
    # 按日期排序的CSV
    by_date_csv = io.StringIO()
    date_fields = ['日期'] + [f for f in all_fields if f != '日期']
    writer = csv.DictWriter(by_date_csv, fieldnames=date_fields)
    writer.writeheader()
    sorted_data = sorted(trend_data, key=lambda x: x['日期'])
    
    # 过滤掉趋势强度_float字段
    filtered_data = []
    for item in sorted_data:
        filtered_item = {k: v for k, v in item.items() if k != '趋势强度_float'}
        filtered_data.append(filtered_item)
    
    writer.writerows(filtered_data)
    files['trend_strength_by_date.csv'] = by_date_csv.getvalue()
    
    # 按文件名分组的CSV（如果有文件名信息）
    if '文件名' in sample_item:
        by_file_csv = io.StringIO()
        file_fields = ['文件名'] + [f for f in all_fields if f != '文件名']
        writer = csv.DictWriter(by_file_csv, fieldnames=file_fields)
        writer.writeheader()
        sorted_data = sorted(trend_data, key=lambda x: (x.get('文件名', ''), x['品种']))
        
        # 过滤掉趋势强度_float字段
        filtered_data = []
        for item in sorted_data:
            filtered_item = {k: v for k, v in item.items() if k != '趋势强度_float'}
            filtered_data.append(filtered_item)
        
        writer.writerows(filtered_data)
        files['trend_strength_by_file.csv'] = by_file_csv.getvalue()
    
    # Excel格式
    # 过滤掉趋势强度_float字段
    filtered_data = []
    for item in trend_data:
        filtered_item = {k: v for k, v in item.items() if k != '趋势强度_float'}
        filtered_data.append(filtered_item)
    
    df = pd.DataFrame(filtered_data)
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    files['trend_strength_summary.xlsx'] = excel_buffer.getvalue()
    
    return files


def analyze_pdf_trend_strength(pdf_file, filename=None):
    """
    分析PDF文件中的趋势强度信息
    
    Args:
        pdf_file: PDF文件对象
        filename: 文件名
        
    Returns:
        提取的趋势强度数据和统计信息
    """
    st.info(f"开始分析PDF文件: {filename or 'uploaded file'}")
    
    # 从PDF提取文本
    text_content = extract_text_from_pdf(pdf_file)
    if not text_content:
        st.error("无法从PDF提取文本内容")
        return [], {}
    
    st.info(f"提取的文本长度: {len(text_content)} 字符")
    
    # 尝试从文件名提取日期（优先使用8位数字格式）
    report_date = None
    if filename:
        st.info(f"正在从文件名提取日期: {filename}")
        # 优先匹配8位连续数字（YYYYMMDD格式）
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            date_str = date_match.group(1)
            try:
                # 验证日期格式并转换
                year, month, day = date_str[:4], date_str[4:6], date_str[6:8]
                report_date = f"{year}-{month}-{day}"
                # 验证日期有效性
                datetime.strptime(report_date, '%Y-%m-%d')
                st.success(f"从文件名提取到日期: {report_date}")
            except ValueError:
                st.warning(f"文件名中的日期格式无效: {date_str}")
                report_date = None
        else:
            st.warning("文件名中未找到8位数字日期格式（YYYYMMDD）")
    
    # 如果文件名中没有找到日期，尝试从内容中提取
    if not report_date:
        st.info("尝试从PDF内容中提取日期...")
        date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{4})-(\d{2})-(\d{2})',
            r'(\d{4})/(\d{2})/(\d{2})',
            r'(\d{4})(\d{2})(\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text_content)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    year, month, day = groups
                    report_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    try:
                        datetime.strptime(report_date, '%Y-%m-%d')
                        st.success(f"从内容中提取到日期: {report_date}")
                        break
                    except ValueError:
                        continue
    
    # 如果仍然没有日期，使用当前日期
    if not report_date:
        report_date = datetime.now().strftime("%Y-%m-%d")
        st.warning(f"未找到有效日期，使用当前日期: {report_date}")
    
    # 提取趋势强度信息
    trend_data = extract_trend_strength_from_text(text_content, report_date)
    
    # 为每条数据添加文件名信息
    if trend_data and filename:
        for item in trend_data:
            item['文件名'] = filename
    
    # 统计信息
    stats = {}
    if trend_data:
        for item in trend_data:
            category = item.get('类别', '未分类')
            stats[category] = stats.get(category, 0) + 1
    
    return trend_data, stats


def main():
    """
    Streamlit主应用
    """
    st.set_page_config(
        page_title="PDF趋势强度提取工具",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 PDF趋势强度提取工具")
    st.markdown("---")
    
    # 创建数据目录（如果不存在）
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    
    # CSV文件路径
    csv_file_path = data_dir / "trend_strength_data.csv"
    
    # 初始化session state
    if 'historical_data' not in st.session_state:
        # 尝试从CSV文件加载历史数据
        if csv_file_path.exists():
            try:
                df = pd.read_csv(csv_file_path)
                st.session_state.historical_data = df.to_dict('records')
                st.success(f"已从CSV文件加载 {len(df)} 条历史数据")
            except Exception as e:
                st.error(f"加载CSV文件时出错: {str(e)}")
                st.session_state.historical_data = []
        else:
            st.session_state.historical_data = []
    
    # 显示历史数据统计
    if st.session_state.historical_data:
        historical_df = pd.DataFrame(st.session_state.historical_data)
        unique_dates = historical_df['日期'].nunique()
        unique_varieties = historical_df['品种'].nunique()
        st.info(f"📈 历史数据: {len(st.session_state.historical_data)} 条记录，{unique_dates} 个日期，{unique_varieties} 个品种")
        
        # 生成透视表（使用历史数据）
        st.subheader("📊 历史数据变化分析")
        pivot_df, change_df = save_trend_strength_pivot_csv(st.session_state.historical_data, incremental=False)
        
        if pivot_df is not None:
            # 只显示变化标记表
            st.write("**变化标记表（★表示变化）:**")
            # 确保所有列都是字符串类型，避免Arrow转换错误
            change_df_str = change_df.astype(str)
            st.dataframe(change_df_str, use_container_width=True)
        
        # 清除历史数据按钮
        if st.button("🗑️ 清除历史数据", help="清除所有已保存的历史数据"):
            st.session_state.historical_data = []
            
            # 同时删除CSV文件
            try:
                data_dir = Path("./data")
                csv_file_path = data_dir / "trend_strength_data.csv"
                if csv_file_path.exists():
                    csv_file_path.unlink()  # 删除文件
                    st.success("历史数据已清除，CSV文件已删除")
                else:
                    st.success("历史数据已清除")
            except Exception as e:
                st.error(f"删除CSV文件时出错: {str(e)}")
                st.success("历史数据已清除，但CSV文件删除失败")
            
            st.experimental_rerun()
    
    st.markdown("""
    ### 功能说明
    - 📄 **批量上传**: 支持同时上传多个PDF文件进行批量分析
    - 🔍 **智能提取**: 从PDF文件中提取趋势强度信息
    - 📊 **分类识别**: 识别并提取【趋势强度】部分的品种信息
    - 🏷️ **类别支持**: 支持偏强、中性、偏弱三种类别
    - 📈 **增量更新**: 自动合并历史数据，支持数据累积
    - 💾 **多格式导出**: 生成CSV和Excel格式的分析结果
    - 📁 **文件追踪**: 记录每条数据的来源文件
    """)
    
    # 文件上传
    uploaded_files = st.file_uploader(
        "选择PDF文件",
        type=['pdf'],
        accept_multiple_files=True,
        help="请上传包含趋势强度信息的PDF文件，支持批量上传"
    )
    
    if uploaded_files:
        if len(uploaded_files) == 1:
            st.success(f"已上传文件: {uploaded_files[0].name}")
        else:
            st.success(f"已上传 {len(uploaded_files)} 个文件")
            with st.expander("查看上传的文件列表", expanded=False):
                for i, file in enumerate(uploaded_files, 1):
                    st.write(f"{i}. {file.name}")
        
        # 分析按钮
        if st.button("开始分析", type="primary"):
            with st.spinner(f"正在分析 {len(uploaded_files)} 个PDF文件，请稍候..."):
                all_trend_data = []
                all_stats = {}
                
                # 处理每个上传的文件
                for i, uploaded_file in enumerate(uploaded_files, 1):
                    # 分析PDF
                    trend_data, stats = analyze_pdf_trend_strength(uploaded_file, uploaded_file.name)
                    
                    if trend_data:
                        all_trend_data.extend(trend_data)
                        
                        # 合并统计信息
                        for category, count in stats.items():
                            all_stats[category] = all_stats.get(category, 0) + count
                    else:
                        st.warning(f"⚠️ {uploaded_file.name}: 未能提取到数据")
                
                # 显示汇总结果
                if all_trend_data:
                    st.success(f"✅ 分析完成：{len(all_trend_data)} 条趋势强度信息")
                    
                    # 使用合并后的数据进行后续处理
                    trend_data = all_trend_data
                    stats = all_stats
                else:
                    st.error("未能提取到趋势强度信息")
                    st.stop()
                
                if trend_data:
                    # 显示简化的统计信息
                    successful_files = sum(1 for file in uploaded_files if any(item.get('文件名', '').startswith(file.name.split('.')[0]) for item in trend_data))
                    
                    # 显示统计信息
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("偏强品种", stats.get('偏强', 0))
                    with col2:
                        st.metric("中性品种", stats.get('中性', 0))
                    with col3:
                        st.metric("偏弱品种", stats.get('偏弱', 0))
                    
                    # 显示数据表格
                    st.subheader("📋 提取结果")
                    df = pd.DataFrame(trend_data)
                    st.dataframe(df, use_container_width=True)
                    
                    # 按类别分组显示（如果有类别信息）
                    if trend_data and '类别' in trend_data[0]:
                        st.subheader("📈 按类别分组")
                        for category in ['偏强', '中性', '偏弱']:
                            category_data = [item for item in trend_data if item.get('类别') == category]
                            if category_data:
                                with st.expander(f"{category} ({len(category_data)} 个品种)"):
                                    category_df = pd.DataFrame(category_data)
                                    st.dataframe(category_df, use_container_width=True)
                    
                    # 生成透视表（启用增量更新）
                    st.subheader("📊 透视表分析")
                    pivot_df, change_df = save_trend_strength_pivot_csv(trend_data, incremental=True)
                    
                    if pivot_df is not None:
                        # 显示透视表
                        st.write("**原始透视表:**")
                        st.dataframe(pivot_df, use_container_width=True)
                        
                        # 显示变化标记表
                        st.write("**变化标记表（★表示变化）:**")
                        # 确保所有列都是字符串类型，避免Arrow转换错误
                        change_df_str = change_df.astype(str)
                        st.dataframe(change_df_str, use_container_width=True)
                    
                    # 生成下载文件
                    files = create_download_files(trend_data)
                    
                    # 下载按钮
                    st.subheader("💾 下载结果")
                    
                    # 根据是否有文件名信息调整列数
                    if 'trend_strength_by_file.csv' in files:
                        col1, col2, col3, col4 = st.columns(4)
                    else:
                        col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.download_button(
                            label="📄 按品种排序CSV",
                            data=files['trend_strength_by_variety.csv'],
                            file_name='trend_strength_by_variety.csv',
                            mime='text/csv'
                        )
                    
                    with col2:
                        st.download_button(
                            label="📅 按日期排序CSV",
                            data=files['trend_strength_by_date.csv'],
                            file_name='trend_strength_by_date.csv',
                            mime='text/csv'
                        )
                    
                    with col3:
                        if 'trend_strength_by_file.csv' in files:
                            st.download_button(
                                label="📁 按文件分组CSV",
                                data=files['trend_strength_by_file.csv'],
                                file_name='trend_strength_by_file.csv',
                                mime='text/csv'
                            )
                        else:
                            # 透视表CSV下载
                            if pivot_df is not None:
                                pivot_csv = pivot_df.to_csv(encoding='utf-8-sig')
                                st.download_button(
                                label="📊 下载透视表CSV",
                                data=pivot_csv,
                                file_name=f"trend_strength_pivot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime='text/csv'
                            )
                    
                    with col4:
                        if 'trend_strength_by_file.csv' in files:
                            # 完整Excel下载（包含透视表）
                            excel_buffer = io.BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                                # 原始数据
                                df = pd.DataFrame(trend_data)
                                df.to_excel(writer, sheet_name='原始数据', index=False)
                                
                                # 透视表
                                if pivot_df is not None:
                                    pivot_df.to_excel(writer, sheet_name='透视表')
                                    change_df.to_excel(writer, sheet_name='变化标记表')
                            
                            st.download_button(
                                label="📊 下载完整Excel",
                                data=excel_buffer.getvalue(),
                                file_name=f"trend_strength_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            )
                        else:
                            # 单个Excel下载
                            st.download_button(
                                label="📊 下载Excel",
                                data=files['trend_strength_summary.xlsx'],
                                file_name='trend_strength_summary.xlsx',
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            )
                    
                else:
                    st.warning("未找到趋势强度信息")
                    st.info("请确保PDF文件包含【趋势强度】部分的内容")
    
    # 侧边栏信息
    with st.sidebar:
        st.header("使用说明")
        st.markdown("""
        ### 📋 操作步骤
        1. **批量上传**: 选择一个或多个PDF文件
        2. **开始分析**: 点击"开始分析"按钮
        3. **查看结果**: 浏览提取的数据和统计信息
        4. **下载文件**: 选择需要的格式下载结果
        
        ### 📄 支持的格式
        - 【趋势强度】部分内容
        - 偏强、中性、偏弱分类
        - 品种名(数字)格式
        - 品种名: 数字格式
        - 文件名日期格式: YYYYMMDD
        
        ### 💡 批量处理优势
        - 一次性处理多个文件
        - 自动合并所有数据
        - 按文件名分组导出
        - 历史数据累积功能
        """)
        
        st.header("技术信息")
        st.markdown("""
        - 基于PyMuPDF提取PDF文本
        - 使用正则表达式解析趋势强度
        - 支持多种数据格式输出
        """)


if __name__ == "__main__":
    main()
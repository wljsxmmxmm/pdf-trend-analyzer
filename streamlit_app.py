#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF趋势强度提取工具 - Streamlit-lite版本

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
    
    使用PyMuPDF库提取PDF文本，支持文件对象和文件路径两种输入方式
    
    Args:
        pdf_file: PDF文件对象或文件路径
        max_pages: 最大提取页数，None表示提取所有页
        
    Returns:
        str: 提取的文本内容，如果失败返回空字符串
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
    从文本中提取趋势强度信息（仅使用正则表达式）
    
    使用正则表达式匹配"品种名 趋势强度: 数值"的格式，提取趋势强度数据
    支持中文、英文、数字、括号等字符的品种名
    
    Args:
        text: PDF提取的文本内容
        report_date: 报告日期，如果为None则使用当前日期
        
    Returns:
        list: 包含趋势强度数据的字典列表，每个字典包含品种、趋势强度、日期等信息
    """
    trend_data = []
    
    if not report_date:
        report_date = datetime.now().strftime("%Y-%m-%d")
    
    st.info("正在查找趋势强度信息...")
    
    # 正则表达式模式：匹配"品种名 趋势强度: 数值"格式
    # 支持中文、英文、数字、括号等字符的品种名
    patterns = [
        r'([\u4e00-\u9fa5A-Za-z0-9（）()]+)\s*趋势强度[：:]\s*([+-]?\d+(?:\.\d+)?)',
    ]
    
    found_data = set()  # 用于去重，避免重复提取相同品种
    extraction_details = []  # 存储提取详情用于折叠显示
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        st.info(f"使用模式 {pattern} 找到 {len(matches)} 个匹配项")
        
        for match in matches:
            if len(match) == 2:
                variety, strength = match
                variety = variety.strip()
                
                # 数据清洗：移除品种名中的"趋势强度"后缀
                if variety.endswith('趋势强度'):
                    variety = variety[:-4]  # 移除"趋势强度"4个字符
                
                # 数据验证：过滤无效的品种名
                invalid_keywords = ['趋势', '强度', '注释', '东莞', '达孚', '公司', '有限', '集团']
                if (len(variety) > 0 and 
                    not any(keyword in variety for keyword in invalid_keywords) and
                    not variety.isdigit() and
                    re.match(r'^[\u4e00-\u9fa5A-Za-z0-9（）()]+$', variety)):
                    try:
                        # 数值验证：确保趋势强度在合理范围内(-10到10)
                        strength_float = float(strength)
                        if -10 <= strength_float <= 10:
                            # 转换为整数
                            strength_int = int(round(strength_float))
                            strength_str = str(strength_int)
                            
                            # 去重检查：避免重复提取相同品种
                            key = (variety, strength_str)
                            if key not in found_data:
                                found_data.add(key)
                                trend_data.append({
                                    '品种': variety,
                                    '趋势强度': strength_str,  # 保存整数字符串
                                    '日期': report_date
                                })
                                extraction_details.append(f"提取: {variety} = {strength_str}")
                    except ValueError:
                        extraction_details.append(f"跳过无效数值: {variety} = {strength}")
                        continue
    
    # 折叠显示提取详情
    if extraction_details:
        with st.expander(f"📋 提取详情 ({len(extraction_details)} 条)", expanded=False):
            for detail in extraction_details:
                if "提取:" in detail:
                    st.success(detail)
                else:
                    st.warning(detail)
    
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
    将趋势强度数据保存为透视表格式，并标记发生变化的品种
    
    核心功能：
    1. 合并历史数据和新数据（增量更新）
    2. 创建透视表（日期为行，品种为列）
    3. 按最新日期的趋势值排序列（有值在前，无值在后）
    4. 保存数据到CSV文件实现持久化
    
    Args:
        all_trend_data: 当前提取的趋势强度数据列表
        output_dir: 输出目录（在Streamlit中不使用）
        incremental: 是否启用增量更新模式，默认为True
    
    Returns:
        DataFrame: 透视表（日期为行，品种为列）
    """
    if not all_trend_data:
        return None
    
    # 创建新数据的DataFrame
    new_df = pd.DataFrame(all_trend_data)
    
    # 如果启用增量更新且存在历史数据，则合并
    if incremental and 'historical_data' in st.session_state and st.session_state.historical_data:
        # 静默增量更新，避免页面顶部出现提示
        historical_df = pd.DataFrame(st.session_state.historical_data)
        
        # 合并历史数据和新数据
        combined_df = pd.concat([historical_df, new_df], ignore_index=True)
        
        # 去重：同一日期同一品种只保留最新的记录
        combined_df = combined_df.drop_duplicates(subset=['日期', '品种'], keep='last')
        
        # 合并后数据量日志省略
    else:
        combined_df = new_df
        # 使用新数据日志省略
    
    # 更新session_state中的历史数据
    st.session_state.historical_data = combined_df.to_dict('records')
    
    # 保存到CSV文件以实现持久化
    try:
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)
        csv_file_path = data_dir / "trend_strength_data.csv"
        combined_df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
        # 保存CSV的提示省略
    except Exception as e:
        st.error(f"保存CSV文件时出错: {str(e)}")
    
    # 创建透视表 - 统一使用字符串字段，确保显示一致性
    # 确保只使用必要的字段，排除可能存在的趋势强度_float字段
    if '趋势强度_float' in combined_df.columns:
        # 如果存在趋势强度_float字段，先删除它
        combined_df = combined_df.drop(columns=['趋势强度_float'])
    
    # 确保趋势强度字段都是整数格式的字符串
    if '趋势强度' in combined_df.columns:
        # 将趋势强度字段转换为整数格式
        combined_df['趋势强度'] = combined_df['趋势强度'].astype(str).apply(
            lambda x: str(int(float(x))) if x.replace('.', '').replace('-', '').isdigit() else x
        )
    
    pivot_df = combined_df.pivot_table(
        index='日期', 
        columns='品种', 
        values='趋势强度', 
        aggfunc='first',  # 使用第一个值，因为字符串不能求平均
        fill_value='--'  # 使用--表示无数据，便于辨识
    )
    
    # 确保所有值都是字符串类型，避免Arrow转换错误
    pivot_df = pivot_df.astype(str)
    # 按日期排序（从新到旧）
    pivot_df = pivot_df.sort_index(ascending=False)
    
    # 列排序优化：按最新日期分组排序
    # 从左到右顺序：趋势>0，趋势<0，趋势=0，未提取到（--）
    if not pivot_df.empty:
        latest_row = pivot_df.iloc[0]

        def classify_value(v: str) -> str:
            try:
                n = float(v)
            except Exception:
                return 'missing'
            if n > 0:
                return 'pos'
            if n < 0:
                return 'neg'
            return 'zero'

        groups = {'pos': [], 'neg': [], 'zero': [], 'missing': []}
        for col in pivot_df.columns:
            grp = classify_value(latest_row.get(col, '--'))
            groups[grp].append(col)

        ordered_cols = groups['pos'] + groups['neg'] + groups['zero'] + groups['missing']
        # 仅在列集一致时重排，避免潜在缺失
        if set(ordered_cols) == set(pivot_df.columns):
            pivot_df = pivot_df[ordered_cols]
    
    # 维度信息提示省略
    
    return pivot_df


# 样式辅助：仅为“最新日期”一行添加颜色（正数红，负数绿）
def style_latest_date_row(df: pd.DataFrame) -> pd.DataFrame:
    """返回与df同形状的样式DataFrame，仅为第一行（最新日期）着色。
    - 正数：红色
    - 负数：绿色
    其余单元格不着色。
    支持单元格中带有↑/↓箭头或非数字占位符（如--）。
    """
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    if df.empty:
        return styles

    latest_idx = df.index[0]

    def parse_number(val: str):
        if val is None:
            return None
        try:
            s = str(val)
            # 去掉箭头和空格
            s = s.replace('↑', '').replace('↓', '').strip()
            if s in ('', '--'):
                return None
            return float(s)
        except Exception:
            return None

    for col in df.columns:
        num = parse_number(df.loc[latest_idx, col])
        if num is None:
            continue
        if num > 0:
            styles.loc[latest_idx, col] = 'color: red'
        elif num < 0:
            styles.loc[latest_idx, col] = 'color: green'
        # 等于0不着色

    return styles



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
    
    # 只从文件名提取日期
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
    
    # 如果文件名中没有找到日期，使用当前日期
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
    
    # 取消页面主标题展示
    
    # 创建数据目录（如果不存在）
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    
    # CSV文件路径
    csv_file_path = data_dir / "trend_strength_data.csv"
    
    # 初始
    # 化session state
    if 'historical_data' not in st.session_state:
        # 尝试从CSV文件加载历史数据
        if csv_file_path.exists():
            try:
                df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
                
                # 清理历史数据，移除趋势强度_float字段
                if '趋势强度_float' in df.columns:
                    df = df.drop(columns=['趋势强度_float'])
                    st.info("已清理历史数据中的趋势强度_float字段")
                
                st.session_state.historical_data = df.to_dict('records')
                # 取消CSV加载成功提示
            except Exception as e:
                st.error(f"加载CSV文件时出错: {str(e)}")
                st.session_state.historical_data = []
        else:
            st.session_state.historical_data = []
    
    # 将文件上传功能放在最上方
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
                    # 显示统计信息
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("总品种数", len(trend_data))
                    with col2:
                        st.metric("成功文件数", len(uploaded_files))
                    with col3:
                        st.metric("最新日期", trend_data[0]['日期'] if trend_data else "无")
                    
                    # 显示提取结果
                    st.subheader("📋 提取结果")
                    df = pd.DataFrame(trend_data)
                    st.dataframe(df, width='stretch')
                    
                    # 生成透视表（启用增量更新）
                    st.subheader("📊 透视表分析")
                    pivot_df = save_trend_strength_pivot_csv(trend_data, incremental=True)
                    
                    if pivot_df is not None:
                        st.write("**趋势强度透视表:**")
                        # 为最新日期一行加色：正数红、负数绿
                        styled = pivot_df.astype(str).style.apply(style_latest_date_row, axis=None)
                        st.dataframe(styled, width='stretch')
                    
                    
                else:
                    st.warning("未找到趋势强度信息")
                    st.info("请确保PDF文件包含【趋势强度】部分的内容")

    # 显示历史数据统计
    if st.session_state.historical_data:
        historical_df = pd.DataFrame(st.session_state.historical_data)
        unique_dates = historical_df['日期'].nunique()
        unique_varieties = historical_df['品种'].nunique()
        
        # 获取最新日期
        latest_date = historical_df['日期'].max()
        # 取消页面上方的统计提示
        
        # 生成透视表（使用历史数据）
        # st.subheader("📊 历史数据分析")
        pivot_df = save_trend_strength_pivot_csv(st.session_state.historical_data, incremental=False)
        
        if pivot_df is not None:
            # 是否显示完整历史数据
            show_full = st.checkbox("显示完整历史数据表格", value=False)
            if not show_full:
                pivot_df = pivot_df.head(10)
            title_txt = "历史数据透视表（完整）" if show_full else "历史数据透视表（最新10个日期）"
            st.write(f"**{title_txt}:**")
            # 构造变化标记：与上一日比较，变动用箭头标记
            pivot_str = pivot_df.astype(str)
            # 数值化用于比较，'--' 转为空
            pivot_num = pivot_str.replace('--', pd.NA).apply(pd.to_numeric, errors='coerce')
            prev_num = pivot_num.shift(-1)  # 上一日（因日期从新到旧排序）

            up_mask = pivot_num.notna() & prev_num.notna() & (pivot_num > prev_num)
            down_mask = pivot_num.notna() & prev_num.notna() & (pivot_num < prev_num)
            marker = pd.DataFrame('', index=pivot_str.index, columns=pivot_str.columns)
            # 仅标注上升/下降，不对缺失变化标记
            marker = marker.mask(up_mask, '↑').mask(down_mask, '↓')

            pivot_with_marks = pivot_str + marker
            # 为最新日期一行加色：正数红、负数绿
            styled = (pivot_with_marks
                      .style
                      .apply(style_latest_date_row, axis=None))
            st.dataframe(styled, width='stretch')

        # 删除指定日期的数据
        with st.expander("删除指定日期的数据", expanded=False):
            try:
                available_dates = sorted(historical_df['日期'].unique().tolist(), reverse=True)
            except Exception:
                available_dates = []
            if available_dates:
                selected_date = st.selectbox("选择要删除的日期", options=available_dates, index=0)
                if st.button("🗑️ 删除所选日期数据", help="将从历史记录与CSV中移除该日期的所有数据"):
                    remaining = [item for item in st.session_state.historical_data if item.get('日期') != selected_date]
                    removed_count = len(st.session_state.historical_data) - len(remaining)
                    st.session_state.historical_data = remaining
                    # 同步更新CSV文件
                    try:
                        if remaining:
                            pd.DataFrame(remaining).to_csv(csv_file_path, index=False, encoding='utf-8-sig')
                        else:
                            if csv_file_path.exists():
                                csv_file_path.unlink()
                        st.success(f"已删除 {selected_date} 的 {removed_count} 条记录")
                    except Exception as e:
                        st.error(f"更新CSV文件时出错: {str(e)}")
                    st.rerun()
            else:
                st.info("当前无可删除的日期")
        
        # 按需移除清除历史数据功能（已取消）
    
    
    


if __name__ == "__main__":
    main()

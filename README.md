# PDF趋势强度提取工具 - Streamlit版本

这是一个基于Streamlit的Web应用，用于从PDF文件中提取趋势强度信息。

## 功能特点

- 📊 从PDF文件中提取趋势强度信息
- 🔍 识别并提取【趋势强度】部分的品种信息
- 📈 支持偏强、中性、偏弱三种类别分析
- 📁 生成CSV和Excel格式的分析结果
- 🌐 Web界面，支持文件上传和在线分析

## 本地运行

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行应用：
```bash
streamlit run streamlit_app.py
```

## Streamlit Cloud部署

### 方法一：通过GitHub部署

1. 将代码推送到GitHub仓库
2. 访问 [Streamlit Cloud](https://streamlit.io/cloud)
3. 使用GitHub账号登录
4. 点击"New app"创建新应用
5. 选择你的GitHub仓库和分支
6. 设置主文件路径为 `streamlit_app.py`
7. 点击"Deploy"开始部署

### 方法二：直接上传文件

1. 访问 [Streamlit Cloud](https://streamlit.io/cloud)
2. 登录后选择"Create app from existing repo"
3. 上传以下文件：
   - `streamlit_app.py`
   - `requirements.txt`
   - `README.md`
4. 设置主文件为 `streamlit_app.py`
5. 部署应用

## 文件说明

- `streamlit_app.py` - 主应用文件，包含Streamlit界面和PDF处理逻辑
- `requirements.txt` - Python依赖包列表
- `app.py` - 原始的tkinter GUI版本（已弃用）
- `README.md` - 项目说明文档

## 使用方法

1. 打开Web应用
2. 上传包含趋势强度信息的PDF文件
3. 点击"开始分析"按钮
4. 查看提取结果和统计信息
5. 下载CSV或Excel格式的结果文件

## 支持的PDF格式

应用支持包含以下格式的PDF文件：
- 【趋势强度】部分标题
- 偏强、中性、偏弱分类
- 品种名(数字)格式，如：玉米(+2.5)
- 品种名: 数字格式，如：大豆: -1.2

## 技术栈

- **Streamlit** - Web应用框架
- **PyMuPDF** - PDF文本提取
- **Pandas** - 数据处理
- **正则表达式** - 文本解析

## 注意事项

- 确保PDF文件包含可提取的文本（非扫描图片）
- 文件大小建议不超过10MB
- 支持中文品种名称识别
- 自动从文件名提取日期信息

## 更新日志

### v2.0.0 (Streamlit版本)
- 移除tkinter GUI界面
- 添加Streamlit Web界面
- 支持在线文件上传
- 优化用户体验
- 添加实时分析进度显示

### v1.0.0 (原始版本)
- 基于tkinter的桌面GUI
- PDF文本提取功能
- 趋势强度信息解析
- CSV和Excel输出
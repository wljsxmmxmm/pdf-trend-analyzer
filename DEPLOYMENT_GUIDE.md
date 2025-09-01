# Streamlit Cloud 部署指南

## 快速部署步骤

### 1. 准备文件
确保你的项目包含以下文件：
- `streamlit_app.py` - 主应用文件
- `requirements.txt` - 依赖包列表
- `README.md` - 项目说明

### 2. 上传到GitHub

```bash
# 初始化Git仓库
git init

# 添加文件
git add .

# 提交
git commit -m "Initial commit: PDF趋势强度提取工具"

# 添加远程仓库（替换为你的GitHub仓库地址）
git remote add origin https://github.com/yourusername/pdf-parser-app.git

# 推送到GitHub
git push -u origin main
```

### 3. 在Streamlit Cloud部署

1. 访问 [https://streamlit.io/cloud](https://streamlit.io/cloud)
2. 使用GitHub账号登录
3. 点击 "New app"
4. 选择你的GitHub仓库
5. 设置以下参数：
   - **Repository**: 你的GitHub仓库
   - **Branch**: main
   - **Main file path**: streamlit_app.py
6. 点击 "Deploy!"

### 4. 等待部署完成

部署通常需要2-5分钟，Streamlit Cloud会：
- 自动安装 `requirements.txt` 中的依赖
- 启动你的应用
- 提供一个公开的URL

## 部署配置

### requirements.txt 说明
```
streamlit>=1.28.0    # Web应用框架
PyMuPDF>=1.23.0     # PDF文本提取
pandas>=1.5.0       # 数据处理
openpyxl>=3.1.0     # Excel文件支持
```

### 应用配置（可选）

如果需要自定义配置，可以创建 `.streamlit/config.toml` 文件：

```toml
[server]
maxUploadSize = 200  # 最大上传文件大小（MB）

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

## 常见问题

### Q: 部署失败怎么办？
A: 检查以下几点：
1. `requirements.txt` 格式是否正确
2. `streamlit_app.py` 是否有语法错误
3. 查看部署日志中的错误信息

### Q: 如何更新应用？
A: 只需要推送新代码到GitHub，Streamlit Cloud会自动重新部署

```bash
git add .
git commit -m "更新功能"
git push
```

### Q: 应用运行缓慢怎么办？
A: Streamlit Cloud免费版有资源限制，可以考虑：
1. 优化代码性能
2. 减少依赖包
3. 升级到付费版本

### Q: 如何设置环境变量？
A: 在Streamlit Cloud的应用设置中可以添加环境变量

## 本地测试

在部署前，建议先在本地测试：

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
streamlit run streamlit_app.py
```

## 监控和维护

- 定期检查应用运行状态
- 监控用户反馈
- 及时更新依赖包版本
- 备份重要数据

## 安全注意事项

- 不要在代码中硬编码敏感信息
- 使用环境变量存储API密钥
- 定期更新依赖包以修复安全漏洞
- 限制文件上传大小和类型

## 支持的文件格式

当前版本支持：
- PDF文件（文本格式，非扫描图片）
- 最大文件大小：200MB（可配置）
- 支持中文内容

## 联系支持

如果遇到问题，可以：
1. 查看Streamlit官方文档
2. 在GitHub Issues中报告问题
3. 联系开发者
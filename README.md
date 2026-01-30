---
title: CiteScan
emoji: 📚
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
---

# CiteScan: Check References, Confirm Truth.

**CiteScan** is an open-source and free tool designed to detect hallucinated references in academic writing. As AI coding assistants and writing tools become more prevalent, they sometimes generate plausible-sounding citations that do not actually exist. **CiteScan** addresses this issue by validating every bibliography entry against multiple authoritative academic databases—including arXiv, CrossRef, DBLP, Semantic Scholar, OpenAlex, and Google Scholar—to confirm their authenticity.

Going beyond simple verification, **CiteScan** uses rule-based algorithms to analyze whether the cited papers genuinely support the claims made in your text. Thanks to the free accessibility for academic databases across CS and AI areas, our system will **cost $0 for maintenance after development**.

## 🚀 Quick Start

### Option 1: Web Interface (Gradio)

```bash
# Install dependencies
pip install -r requirements.txt

# Run Gradio interface
python app.py
```

Access at `http://localhost:7860`

### Option 2: API Service (FastAPI)

```bash
# Install dependencies
pip install -r requirements.txt

# Run API service
python main.py
```

Access API at `http://localhost:8000`
API Documentation at `http://localhost:8000/docs`

### Option 3: Docker

```bash
# Run both services with Docker Compose
docker-compose up -d

# Gradio: http://localhost:7860
# API: http://localhost:8000
```

## 📚 Documentation

- **[API Documentation](API_DOCS.md)** - Complete API reference and examples
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment instructions

## 🛡 Why CiteScan?

- **🚫 NO Hallucinations**: Annotate citations that don't exist or have mismatched metadata across year, authors, and title.

- **📋 Ground Truth Reference**: Provide the link if the citations are flagged to *issued entry*. You can click the **Open paper** or **DOI** button to access the real-world metadata, and then cite the BibTeX from the press website.

![Functions](assets/screenshot_performance_zh.png)

- **🏠 Top-tier Research Organizations**: Cooperate with National University of Singapore (NUS) and Shanghai Jiao Tong University (SJTU).

- **🔌 RESTful API**: Production-ready API for integration with other tools and services.

## ✨ Features

### Web Interface (Gradio)
- User-friendly interface for manual verification
- Real-time progress tracking
- Interactive filtering by verification status
- Visual presentation of results

### API Service (FastAPI)
- RESTful API for programmatic access
- Automatic OpenAPI documentation
- JSON responses for easy integration
- Health checks and monitoring endpoints
- Structured logging
- Caching for improved performance

## 🔍 References Validation

- **Multi-Source Verification**: Validates metadata against arXiv, CrossRef, DBLP, Semantic Scholar, OpenAlex, and Google Scholar.

- **Covert citation from pre-print version to official version**: After clicking the blue button (`Open paper` or `DOI`), the official website will display. Click the `cite` button, you can copy the official BibTex.

![Citation](assets/screenshot_semantic_scholar.png)

### Verification Workflow

1. **Parse BibTeX**: Extract entries and metadata
2. **Priority-based Search**: Query databases in priority order
3. **Metadata Comparison**: Compare title, authors, year, venue
4. **Duplicate Detection**: Identify duplicate entries
5. **Result Generation**: Provide detailed verification report

## 📖 API Usage Examples

### Python

```python
import requests

url = "http://localhost:8000/api/v1/verify"
bibtex = """
@article{vaswani2017attention,
  title={Attention is all you need},
  author={Vaswani, Ashish and Shazeer, Noam},
  year={2017}
}
"""

response = requests.post(url, json={"bibtex_content": bibtex})
result = response.json()

print(f"Verified: {result['verified_count']}/{result['total_count']}")
```

### cURL

```bash
curl -X POST "http://localhost:8000/api/v1/verify" \
  -H "Content-Type: application/json" \
  -d '{"bibtex_content": "@article{example,title={Test},year={2023}}"}'
```

See [API_DOCS.md](API_DOCS.md) for complete API documentation.

## ⚙️ Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Key configuration options:

```bash
# Server ports
API_PORT=8000
GRADIO_PORT=7860

# Performance
MAX_WORKERS=10
CACHE_ENABLED=true
CACHE_TTL=3600

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete configuration guide.

## 🏗️ Architecture

```
CiteScan/
├── src/
│   ├── api/              # FastAPI routes and schemas
│   ├── services/         # Business logic layer
│   ├── core/             # Configuration, logging, cache
│   ├── fetchers/         # Database API clients
│   ├── analyzers/        # Metadata comparison
│   ├── parsers/          # BibTeX parsing
│   └── utils/            # Utilities
├── app.py                # Gradio interface
├── main.py               # FastAPI application
├── Dockerfile            # Container configuration
└── docker-compose.yml    # Multi-service setup
```

## 🔧 Development

### Setup Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run in development mode
ENVIRONMENT=development python main.py
```

### Project Structure

- **Services Layer**: Reusable business logic
- **API Layer**: RESTful endpoints with FastAPI
- **UI Layer**: Gradio interface
- **Core**: Configuration, logging, caching
- **Fetchers**: Database API integrations

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Statistics

```bash
curl http://localhost:8000/api/v1/stats
```

### Logs

Logs are stored in `logs/citescan.log` in JSON format:

```bash
tail -f logs/citescan.log | jq '.'
```

## ⚠️ Case Study for False Positives

1. **Authors Mismatch**:
   - *Reason*: Different databases deal with a longer list of authors with different strategies, like truncation.
   - *Action*: Verify if main authors match

2. **Venues Mismatch**:
   - *Reason*: Abbreviations vs. full names, such as "ICLR" vs. "International Conference on Learning Representations"
   - *Action*: Both are correct.

3. **Year GAP (±1 Year)**:
   - *Reason*: Delay between preprint (arXiv) and final version publication
   - *Action*: Verify which version you intend to cite. We recommend citing the version from the official press website. Lower pre-print version bib will make your submission more convincing.

4. **Non-academic Sources**:
   - *Reason*: Blogs and APIs are not indexed in academic databases.
   - *Action*: Verify URL, year, and title manually.

## 🙏 Acknowledgments

CiteScan uses multiple data sources:
- arXiv API
- CrossRef API
- Semantic Scholar API
- DBLP API
- OpenAlex API
- Google Scholar (web scraping)

## 📝 License

[Add your license here]

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions and support:
- Email: e1143641@u.nus.edu
- GitHub Issues: [Repository URL]

---

## 🚀 ModelScope Deployment

To deploy on ModelScope 创空间:

```bash
# Add ModelScope remote
git remote add modelscope "http://oauth2:YOUR_TOKEN@www.modelscope.cn/studios/YOUR_USERNAME/CiteScan.git"

# Push to ModelScope
git push modelscope main

# Or force push if needed
git push modelscope main --force
```

After pushing, visit your ModelScope studio and click "上线空间展示" or "立即发布" to deploy the Gradio application.

---

## 🚀 Hugging Face Spaces 部署

将代码推送到 [Hugging Face Spaces](https://huggingface.co/spaces/yancan/CiteScan/)：

1. **安装 Hugging Face CLI 并登录**（如未安装）：
   ```bash
   pip install huggingface_hub
   huggingface-cli login
   ```

2. **添加 Hugging Face 远程仓库**：
   ```bash
   git remote add hf https://huggingface.co/spaces/yancan/CiteScan
   ```

3. **推送到 Spaces**（HF 不允许普通 git 推送二进制文件，需用无图片分支 `hf-main`）：
   - **重要**：HF 上显示的是 **已提交到 main 的代码**。若本地有未提交的修改（如 `main.py`、`src/` 等），需先提交到 `main`，再更新并推送 `hf-main`。
   - 一键脚本：`./scripts/push_to_hf.sh`（会提示先提交未提交的修改，再重建 `hf-main` 并推送）。
   - 或手动：先 `git add -A && git commit -m "说明"`，再运行脚本或按脚本内步骤重建 `hf-main` 并 `git push hf hf-main:main --force`。

4. 推送完成后，在 [Space 页面](https://huggingface.co/spaces/yancan/CiteScan) 等待构建结束即可访问 Gradio 应用。

**注意**：README 顶部的 YAML 配置（`title`、`sdk`、`app_file` 等）为 Spaces 必需，请勿删除。
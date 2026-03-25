# 1. 进入后端目录
cd /Users/lfx/Documents/006_code/stock_analyzer/backend

# 2. 激活虚拟环境
source ../venv/bin/activate

# 3. 启动服务
python main.py


# 1. 启动后端（终端1）
cd /Users/lfx/Documents/006_code/stock_analyzer
source venv/bin/activate
python backend/main.py

# 2. 启动前端（直接在浏览器打开）
open frontend/index.html
# 或使用简单HTTP服务器
cd frontend && python -m http.server 8080
后端API地址：http://localhost:8000
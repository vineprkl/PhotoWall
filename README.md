# 照片墙项目

一个简单的、易于部署的照片墙应用程序，使用 Flask 和 SQLite。

## 功能

- 主页展示可见照片的缩略图网格，支持按分类筛选。
- 新增分类：游戏, 活动。
- **分类逻辑**: 
    - 文件名以 `Sky` 开头且以 `.png` 结尾 (如 `Sky12345.png`) -> 归类为 `活动`。
    - 其他所有文件 -> 归类为 `游戏` (默认)。
- **排序逻辑**: 
    - `游戏` 分类按时间戳降序排列（优先EXIF，其次尝试解析文件名 `屏幕截图 YYYY-MM-DD HHMMSS` 或 `*_YYYYMMDD_HHMMSS.*`，最后文件修改时间）。
    - `活动` 按文件名中的数字升序排列。
    - **默认视图**: 首页默认显示 `游戏` 分类。
- 点击缩略图可在 Lightbox 中查看原图并下载。
- 后台管理页面 (`/super-admin-panel`)：
    - 批量上传照片 (jpg, jpeg, png, gif)。
    - 自动生成缩略图。
    - 尝试提取照片的原始拍摄时间。
    - 查看所有已上传照片列表。
    - 切换照片的可见性（在主页显示或隐藏）。
    - 删除照片。

## 技术栈

- 后端: Python, Flask, Flask-SQLAlchemy
- 数据库: SQLite
- 图片处理: Pillow
- 前端: HTML, CSS, JavaScript

## 设置与运行

1.  **克隆或下载项目**

2.  **确保已安装 Python 3**

3.  **创建虚拟环境 (推荐)**:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

4.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

    **重要: 如果从旧版本升级，请先删除项目根目录下的 `database.db` 文件，因为数据库结构已更改！旧版本中分类为 "屏幕截图", "游戏截图", 或 "游戏内滤镜" 的数据需要重新上传才能正确归类为 "游戏" 或 "活动"。**

5.  **初始化数据库 (首次运行或升级后必须执行)**:
    ```bash
    # 确保你的终端在项目根目录下，并且虚拟环境已激活
    flask init-db 
    ```
    这将创建 `database.db` 文件和所需的表。

6.  **运行开发服务器**:
    ```bash
    python app.py
    ```
    访问 `http://127.0.0.1:5000/` 查看主页。
    访问 `http://127.0.0.1:5000/super-admin-panel` 访问管理后台。

7.  **运行生产服务器 (使用 Waitress)**:
    ```bash
    waitress-serve --host 0.0.0.0 --port 5000 app:app
    ```
    将 `0.0.0.0` 替换为特定 IP 地址（如果需要），或保持 `0.0.0.0` 以监听所有接口。

## 其他命令

### 清空所有数据 (危险!)

有一个命令可以删除数据库中的所有照片记录以及 `uploads` 目录下的所有图片文件。这是一个不可逆的操作，请谨慎使用！

```bash
# 在项目根目录下，激活虚拟环境后运行
flask clear-all 
```
系统会要求你输入 `yes` 进行确认。

## 文件结构

```
/
├── app.py             # Flask 应用主文件
├── requirements.txt   # Python 依赖
├── static/            # 静态文件 (CSS, JS)
│   ├── css/style.css
│   └── js/script.js
├── templates/         # HTML 模板
│   ├── index.html     # 主页
│   └── admin.html     # 后台管理页
├── uploads/           # 用户上传的图片 (应用运行时创建)
│   ├── originals/     # 存储原图
│   └── thumbnails/    # 存储缩略图
├── database.db        # SQLite 数据库文件 (应用运行时创建)
└── README.md          # 本文件
``` 

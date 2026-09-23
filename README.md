# 万能视频下载器（安卓版）

一个运行在安卓手机上的视频下载器 APK，Kivy 开发，通过 GitHub Actions 自动构建。

## 功能

- **连接电脑模式（推荐）**：调用电脑端下载服务（网页版 web_server），抖音无水印 / YouTube / Facebook 全功能下载，文件直接保存到手机「下载」目录
- **本机直连模式**：无需电脑，内置 yt-dlp 直接下载（抖音可能受登录态限制，其他平台可用）
- MP4 视频 / 仅 MP3 音频 可选

## 本地构建

依赖：Python 3.10+、buildozer

```bash
pip install buildozer cython
buildozer -v android debug
```

APK 输出在 `bin/` 目录。

## GitHub Actions 自动构建

每次 push 到 `main` 分支（或手动触发 Workflow）会自动构建 APK：

1. 打开仓库 Actions 页面
2. 选择最新的构建任务
3. 在「Artifacts」里下载 `apk`
4. 把 APK 传到手机安装（需要在设置里允许「未知来源」）

## 使用

1. 手机安装 APK
2. **连接电脑模式**：电脑上运行 `web_server.py`（端口 8000），手机填电脑局域网地址（如 `http://192.168.1.100:8000`）
3. 粘贴抖音/YouTube 等分享链接，选择格式，开始下载

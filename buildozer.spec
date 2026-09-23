[app]
# 应用信息
title = 万能视频下载器
package.name = videodownloader
package.domain = com.doubao
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1.0
requirements = python3,kivy,yt-dlp,requests

# 界面
orientation = portrait
fullscreen = 0

# Android 配置
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.private_storage = True
android.enable_androidx = True
android.ndk_api = 21

# 图标（可选，无则用默认）
# icon.filename = %(source.dir)s/icon.png

[buildozer]
log_level = 2
warn_on_root = 1
accept_root = True

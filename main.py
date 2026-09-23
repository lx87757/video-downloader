# -*- coding: utf-8 -*-
"""万能视频下载器 · 安卓版（Kivy）
双模式：
  连接电脑 —— 调用电脑端 web_server 下载（抖音无水印/YouTube 等全功能）
  本机直连 —— 内置 yt-dlp 直接下载（抖音可能需登录态，其他平台可用）
"""
import json
import os
import re
import sys
import threading
import time
import urllib.parse

import requests

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView

# ---------- 存储权限（Android） ----------
SAVE_DIR = "/storage/emulated/0/Download"
try:
    from android.permissions import Permission, request_permissions
    request_permissions([Permission.READ_EXTERNAL_STORAGE,
                         Permission.WRITE_EXTERNAL_STORAGE,
                         Permission.MANAGE_EXTERNAL_STORAGE])
except Exception:
    pass

try:
    import android  # noqa
    IS_ANDROID = True
except Exception:
    IS_ANDROID = False


def default_save_dir():
    if IS_ANDROID:
        try:
            from android.storage import primary_external_storage_path
            return os.path.join(primary_external_storage_path(), "Download")
        except Exception:
            return SAVE_DIR
    return os.path.expanduser("~/Downloads")


KV = """
<RootLayout>:
    orientation: 'vertical'
    spacing: '8dp'
    padding: ['12dp', '12dp', '12dp', '12dp']

    BoxLayout:
        size_hint_y: None
        height: '50dp'
        Label:
            text: '万能视频下载器'
            font_size: '20sp'
            bold: True
            color: 0.12, 0.30, 0.70, 1
            halign: 'center'

    Spinner:
        id: mode
        size_hint_y: None
        height: '46dp'
        text: '连接电脑（推荐，无水印）'
        values: ['连接电脑（推荐，无水印）', '本机直连（无需电脑）']

    BoxLayout:
        size_hint_y: None
        height: '44dp'
        Label:
            text: '电脑地址:'
            size_hint_x: 0.34
            halign: 'right'
        TextInput:
            id: server
            text: 'http://192.168.1.100:8000'
            hint_text: '电脑上显示的地址'
            multiline: False

    Label:
        size_hint_y: None
        height: '24dp'
        text: '视频链接 / 分享文案'
        font_size: '14sp'
        color: 0.2, 0.2, 0.2, 1
        halign: 'left'

    TextInput:
        id: url
        hint_text: '粘贴抖音/YouTube/Facebook 等链接...'
        multiline: True
        size_hint_y: 0.32

    BoxLayout:
        size_hint_y: None
        height: '46dp'
        Label:
            text: '格式:'
            size_hint_x: 0.3
            halign: 'right'
        Spinner:
            id: fmt
            text: 'MP4 视频'
            values: ['MP4 视频', '仅 MP3 音频']
            size_hint_x: 0.7

    Button:
        id: go
        size_hint_y: None
        height: '52dp'
        text: '▶ 开始下载'
        background_color: 0.15, 0.40, 0.92, 1
        on_release: root.on_download()

    ProgressBar:
        id: bar
        size_hint_y: None
        height: '10dp'
        max: 1.0

    Label:
        id: status
        size_hint_y: None
        height: '30dp'
        text: '准备就绪'
        font_size: '13sp'
        color: 0.3, 0.3, 0.3, 1
        text_size: self.width, None

    Label:
        id: saved
        size_hint_y: None
        height: '34dp'
        text: ''
        font_size: '12sp'
        color: 0.02, 0.55, 0.30, 1
        text_size: self.width, None
"""


class RootLayout(BoxLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.dl_thread = None
        self.stop_poll = False
        self.save_dir = default_save_dir()
        try:
            os.makedirs(self.save_dir, exist_ok=True)
        except Exception:
            pass
        Clock.schedule_once(lambda dt: self._init())

    def _init(self):
        pass

    def _set_status(self, text, color=(0.3, 0.3, 0.3, 1)):
        Clock.schedule_once(lambda dt: self._apply_status(text, color))

    def _apply_status(self, text, color):
        self.ids.status.text = text
        self.ids.status.color = color

    def _set_progress(self, p):
        Clock.schedule_once(lambda dt: setattr(self.ids.bar, "value", p))

    def _set_saved(self, text):
        Clock.schedule_once(lambda dt: setattr(self.ids.saved, "text", text))

    def on_download(self):
        if self.dl_thread and self.dl_thread.is_alive():
            return
        mode = self.ids.mode.text
        url_raw = self.ids.url.text.strip()
        m = re.search(r"https?://[^\s\"'<>]+", url_raw)
        if not m:
            self._set_status("未找到有效链接", (0.8, 0.2, 0.2, 1))
            return
        url = m.group(0)
        fmt = "MP3" if self.ids.fmt.text == "仅 MP3 音频" else "MP4"
        self._set_saved("")
        self._set_progress(0)
        self.dl_thread = threading.Thread(
            target=self._download_worker, args=(mode, url, fmt), daemon=True
        )
        self.dl_thread.start()

    # ---------- 模式1：连接电脑 ----------
    def _server_download(self, base, url, fmt):
        try:
            r = requests.post(
                base.rstrip("/") + "/api/download",
                json={"url": url, "format": fmt},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                self._set_status("提交失败: " + str(data.get("error", "")), (0.8, 0.2, 0.2, 1))
                return
            self._set_status("已提交，等待电脑解析...")
            while not self.stop_poll:
                time.sleep(1.2)
                try:
                    s = requests.get(base.rstrip("/") + "/api/status", timeout=10).json()
                except Exception:
                    continue
                if s.get("busy"):
                    self._set_progress(float(s.get("progress") or 0))
                    st = s.get("status") or "下载中..."
                    self._set_status(st[:60])
                elif s.get("done"):
                    if s.get("success") and s.get("file"):
                        self._set_progress(1)
                        self._set_status("下载完成，正在保存到手机...")
                        fname = urllib.parse.unquote(s["file"])
                        out = os.path.join(self.save_dir, fname)
                        self._download_file(base.rstrip("/") + "/files/" + s["file"], out)
                        self._set_status("已保存")
                        self._set_saved(out)
                    else:
                        self._set_status("下载失败: " + str(s.get("error", ""))[:80],
                                         (0.8, 0.2, 0.2, 1))
                    return
        except Exception as e:
            self._set_status("连接电脑失败: " + str(e)[:60], (0.8, 0.2, 0.2, 1))

    def _download_file(self, url, out_path):
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length") or 0)
                got = 0
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(1024 * 128):
                        if chunk:
                            f.write(chunk)
                            got += len(chunk)
                            if total > 0:
                                self._set_progress(got / total)
        except Exception as e:
            self._set_status("保存到手机失败: " + str(e)[:60], (0.8, 0.2, 0.2, 1))

    # ---------- 模式2：本机直连 ----------
    def _local_download(self, url, fmt):
        try:
            import yt_dlp
        except Exception as e:
            self._set_status("本机模式缺少 yt-dlp 组件", (0.8, 0.2, 0.2, 1))
            return

        def hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                got = d.get("downloaded_bytes") or 0
                if total > 0:
                    self._set_progress(got / total)
                self._set_status("下载中... " + ("%.1f%%" % (got * 100.0 / total)) if total > 0 else "下载中...")
            elif d["status"] == "finished":
                self._set_status("下载完成，正在处理...")

        try:
            opts = {
                "outtmpl": os.path.join(self.save_dir, "%(title)s.%(ext)s"),
                "progress_hooks": [hook],
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "socket_timeout": 25,
                "retries": 2,
            }
            if fmt == "MP3":
                opts["format"] = "bestaudio/best"
                opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            else:
                opts["format"] = "best"
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                fname = ydl.prepare_filename(info)
                self._set_progress(1)
                self._set_status("下载完成")
                self._set_saved(fname)
        except Exception as e:
            self._set_status("本机下载失败: " + str(e)[:80], (0.8, 0.2, 0.2, 1))

    def _download_worker(self, mode, url, fmt):
        self._set_status("正在处理...")
        if mode.startswith("连接电脑"):
            base = self.ids.server.text.strip().rstrip("/")
            if not base.startswith("http"):
                self._set_status("请填写正确的电脑地址（http://...）", (0.8, 0.2, 0.2, 1))
                return
            self._server_download(base, url, fmt)
        else:
            self._local_download(url, fmt)


class VideoDownloaderApp(App):
    def build(self):
        Window.softinput_mode = "pan"
        return Builder.load_string(KV)


if __name__ == "__main__":
    VideoDownloaderApp().run()

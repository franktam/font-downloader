# -*- coding: utf-8 -*-
"""
font_downloader.py - 字体识别与下载工具主程序
GUI 主界面
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import requests
import sys

from font_parser import parse_fonts
from font_preview import show_preview_window

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

APP_TITLE = '网页字体识别下载工具 v1.0'
APP_BG = '#f0f0f5'
TABLE_BG = '#ffffff'
ACCENT = '#4a5ee0'
ACCENT_DARK = '#3a4ec0'


class FontDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry('900x620')
        self.root.minsize(750, 500)
        self.root.configure(bg=APP_BG)

        # 设置图标（若有）
        try:
            # 打包后图标在 sys._MEIPASS
            base = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
            icon_path = os.path.join(base, 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self.font_data = []       # 存储当前解析到的字体列表
        self.parse_thread = None  # 解析线程引用

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        """配置 ttk 样式"""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=APP_BG)
        style.configure('Card.TFrame', background='white', relief='flat')

        style.configure('Title.TLabel', background=APP_BG,
                        font=('微软雅黑', 11), foreground='#333')
        style.configure('Status.TLabel', background=APP_BG,
                        font=('微软雅黑', 9), foreground='#666')

        # 主按钮
        style.configure('Primary.TButton',
                        background=ACCENT, foreground='white',
                        font=('微软雅黑', 10, 'bold'),
                        borderwidth=0, relief='flat', padding=(12, 6))
        style.map('Primary.TButton',
                  background=[('active', ACCENT_DARK), ('pressed', ACCENT_DARK)])

        # 普通按钮
        style.configure('TButton',
                        font=('微软雅黑', 9),
                        padding=(8, 4))

        # 表格
        style.configure('Treeview',
                        font=('微软雅黑', 9),
                        rowheight=32,
                        background='white',
                        fieldbackground='white',
                        borderwidth=0)
        style.configure('Treeview.Heading',
                        font=('微软雅黑', 9, 'bold'),
                        background='#e8e8f0',
                        foreground='#333',
                        relief='flat')
        style.map('Treeview',
                  background=[('selected', '#dde3ff')],
                  foreground=[('selected', '#222')])

    def _build_ui(self):
        """构建主界面"""
        # ── 顶部标题栏 ──
        title_bar = tk.Frame(self.root, bg=ACCENT, height=52)
        title_bar.pack(fill='x')
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text='🔤  网页字体识别下载工具',
                 bg=ACCENT, fg='white',
                 font=('微软雅黑', 14, 'bold')).pack(side='left', padx=16, pady=10)

        tk.Label(title_bar, text='自动识别网页中使用的所有字体文件',
                 bg=ACCENT, fg='#ccd3ff',
                 font=('微软雅黑', 9)).pack(side='left', padx=0, pady=10)

        # ── 输入区域 ──
        input_frame = tk.Frame(self.root, bg=APP_BG, pady=12)
        input_frame.pack(fill='x', padx=20)

        tk.Label(input_frame, text='网址：', bg=APP_BG,
                 font=('微软雅黑', 10)).pack(side='left')

        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(input_frame, textvariable=self.url_var,
                              font=('微软雅黑', 10), width=55)
        url_entry.pack(side='left', padx=(4, 8), ipady=4)
        url_entry.bind('<Return>', lambda e: self._start_parse())

        self.parse_btn = ttk.Button(input_frame, text='🔍 解析',
                                    style='Primary.TButton',
                                    command=self._start_parse)
        self.parse_btn.pack(side='left', padx=(0, 6))

        ttk.Button(input_frame, text='清空',
                   command=self._clear).pack(side='left')

        # 示例链接
        example_frame = tk.Frame(self.root, bg=APP_BG)
        example_frame.pack(fill='x', padx=20)
        tk.Label(example_frame, text='示例：', bg=APP_BG,
                 font=('微软雅黑', 8), fg='#999').pack(side='left')
        examples = [
            'https://fonts.googleapis.com',
            'https://www.adobe.com',
            'https://cn.vuejs.org',
        ]
        for ex in examples:
            lbl = tk.Label(example_frame, text=ex, bg=APP_BG,
                           font=('微软雅黑', 8), fg='#4a5ee0', cursor='hand2')
            lbl.pack(side='left', padx=(4, 0))
            lbl.bind('<Button-1>', lambda e, url=ex: self._set_example(url))

        # ── 状态栏 ──
        self.status_var = tk.StringVar(value='请输入网址后点击【解析】按钮')
        status_bar = tk.Frame(self.root, bg='#e8e8f0', pady=5)
        status_bar.pack(fill='x', padx=20)

        self.progress = ttk.Progressbar(status_bar, mode='indeterminate', length=140)
        self.progress.pack(side='left', padx=(0, 8))
        self.progress.stop()
        self.progress.pack_forget()

        ttk.Label(status_bar, textvariable=self.status_var,
                  style='Status.TLabel',
                  background='#e8e8f0').pack(side='left')

        self.count_var = tk.StringVar(value='')
        ttk.Label(status_bar, textvariable=self.count_var,
                  background='#e8e8f0',
                  font=('微软雅黑', 9, 'bold'),
                  foreground=ACCENT).pack(side='right', padx=8)

        # ── 表格区域 ──
        table_frame = tk.Frame(self.root, bg=APP_BG)
        table_frame.pack(fill='both', expand=True, padx=20, pady=(8, 0))

        # 表格列定义
        columns = ('sel', 'idx', 'name', 'format', 'size', 'preview', 'download')
        self.tree = ttk.Treeview(table_frame, columns=columns,
                                 show='headings', selectmode='browse')

        col_config = [
            ('sel',      '☑',        40,  'center'),
            ('idx',      '#',         40,  'center'),
            ('name',     '字体名称',  260, 'w'),
            ('format',   '格式',       70, 'center'),
            ('size',     '文件大小',   90, 'center'),
            ('preview',  '预览',       70, 'center'),
            ('download', '下载',       70, 'center'),
        ]
        for col, heading, width, anchor in col_config:
            self.tree.heading(col, text=heading,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=width, anchor=anchor, stretch=(col == 'name'))

        # 滚动条
        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        # 绑定点击事件
        self.tree.bind('<ButtonRelease-1>', self._on_table_click)
        self.tree.bind('<Double-1>', self._on_double_click)

        # 表格行颜色
        self.tree.tag_configure('odd', background='#fafafd')
        self.tree.tag_configure('even', background='white')
        self.tree.tag_configure('checked', background='#eef0ff')

        # ── 底部操作栏 ──
        bottom_frame = tk.Frame(self.root, bg=APP_BG, pady=10)
        bottom_frame.pack(fill='x', padx=20)

        self.select_all_var = tk.BooleanVar(value=False)
        self.chk_all = ttk.Checkbutton(
            bottom_frame, text='全选',
            variable=self.select_all_var,
            command=self._toggle_select_all
        )
        self.chk_all.pack(side='left')

        self.selected_count_var = tk.StringVar(value='已选：0 个')
        ttk.Label(bottom_frame, textvariable=self.selected_count_var,
                  background=APP_BG,
                  font=('微软雅黑', 9), foreground='#666').pack(side='left', padx=8)

        ttk.Button(bottom_frame, text='📂 选择保存路径',
                   command=self._choose_save_dir).pack(side='left', padx=(0, 6))

        self.save_dir_var = tk.StringVar(value=os.path.join(os.path.expanduser('~'), 'Desktop'))
        self.save_dir_label = ttk.Label(bottom_frame, textvariable=self.save_dir_var,
                                        background=APP_BG,
                                        font=('微软雅黑', 8), foreground='#888',
                                        width=30, anchor='w')
        self.save_dir_label.pack(side='left')

        self.download_btn = ttk.Button(bottom_frame, text='⬇ 下载选中字体',
                                       style='Primary.TButton',
                                       command=self._download_selected,
                                       state='disabled')
        self.download_btn.pack(side='right', padx=(8, 0))

        self.download_all_btn = ttk.Button(bottom_frame, text='⬇ 全部下载',
                                           command=self._download_all,
                                           state='disabled')
        self.download_all_btn.pack(side='right')

        # 选中集合
        self.checked_items = set()

    # ── 事件处理 ──

    def _set_example(self, url):
        self.url_var.set(url)

    def _clear(self):
        self.url_var.set('')
        self._clear_table()
        self.status_var.set('已清空，请重新输入网址')
        self.count_var.set('')
        self.checked_items.clear()
        self._update_selected_count()

    def _clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.font_data = []
        self.download_btn.config(state='disabled')
        self.download_all_btn.config(state='disabled')

    def _start_parse(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning('提示', '请先输入要解析的网址！')
            return

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            self.url_var.set(url)

        # 禁用解析按钮，防止重复点击
        self.parse_btn.config(state='disabled')
        self._clear_table()
        self.checked_items.clear()
        self._update_selected_count()

        # 显示进度条
        self.progress.pack(side='left', padx=(0, 8))
        self.progress.start(10)
        self.status_var.set('正在解析中...')
        self.count_var.set('')

        # 后台线程执行解析
        self.parse_thread = threading.Thread(
            target=self._parse_worker, args=(url,), daemon=True)
        self.parse_thread.start()

    def _parse_worker(self, url):
        """后台解析线程"""
        try:
            def on_progress(msg):
                self.root.after(0, lambda: self.status_var.set(msg))

            font_list = parse_fonts(url, progress_callback=on_progress)
            self.root.after(0, lambda: self._on_parse_done(font_list))
        except Exception as e:
            self.root.after(0, lambda: self._on_parse_error(str(e)))

    def _on_parse_done(self, font_list):
        """解析完成后的 UI 更新（主线程）"""
        self.progress.stop()
        self.progress.pack_forget()
        self.parse_btn.config(state='normal')

        self.font_data = font_list
        self._populate_table(font_list)

        if font_list:
            count = len(font_list)
            self.status_var.set(f'✅ 解析完成，共找到 {count} 个字体文件')
            self.count_var.set(f'共 {count} 个字体')
            self.download_btn.config(state='normal')
            self.download_all_btn.config(state='normal')
        else:
            self.status_var.set('⚠️ 未找到任何字体文件，该网页可能未使用自定义字体或字体通过 JS 动态加载')
            self.count_var.set('')

    def _on_parse_error(self, error_msg):
        """解析出错（主线程）"""
        self.progress.stop()
        self.progress.pack_forget()
        self.parse_btn.config(state='normal')
        self.status_var.set(f'❌ 解析失败：{error_msg}')
        messagebox.showerror('解析失败', f'无法解析该网址：\n{error_msg}')

    def _populate_table(self, font_list):
        """填充表格数据"""
        for i, font in enumerate(font_list):
            tag = 'odd' if i % 2 == 0 else 'even'
            item_id = self.tree.insert('', 'end', iid=str(i),
                                       values=('☐', i + 1,
                                               font['name'],
                                               font['format'].upper(),
                                               font['size_str'],
                                               '🔍 预览',
                                               '⬇ 下载'),
                                       tags=(tag,))

    def _on_table_click(self, event):
        """处理表格单击事件"""
        region = self.tree.identify_region(event.x, event.y)
        if region != 'cell':
            return

        col = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if not item:
            return

        col_num = int(col.replace('#', '')) - 1
        col_names = ('sel', 'idx', 'name', 'format', 'size', 'preview', 'download')
        if col_num < 0 or col_num >= len(col_names):
            return

        col_name = col_names[col_num]
        idx = int(item)

        if col_name == 'sel':
            self._toggle_check(item)
        elif col_name == 'preview':
            self._preview_font(idx)
        elif col_name == 'download':
            self._download_single(idx)

    def _on_double_click(self, event):
        """双击字体名称行触发预览"""
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if item and int(col.replace('#', '')) - 1 == 2:  # name 列
            self._preview_font(int(item))

    def _toggle_check(self, item):
        """切换选中状态"""
        idx = int(item)
        values = list(self.tree.item(item, 'values'))
        if item in self.checked_items:
            self.checked_items.discard(item)
            values[0] = '☐'
            cur_tag = 'odd' if idx % 2 == 0 else 'even'
        else:
            self.checked_items.add(item)
            values[0] = '☑'
            cur_tag = 'checked'

        self.tree.item(item, values=values, tags=(cur_tag,))
        self._update_selected_count()

    def _toggle_select_all(self):
        """全选/取消全选"""
        select = self.select_all_var.get()
        self.checked_items.clear()

        for i, item in enumerate(self.tree.get_children()):
            values = list(self.tree.item(item, 'values'))
            if select:
                self.checked_items.add(item)
                values[0] = '☑'
                tag = 'checked'
            else:
                values[0] = '☐'
                tag = 'odd' if i % 2 == 0 else 'even'
            self.tree.item(item, values=values, tags=(tag,))

        self._update_selected_count()

    def _update_selected_count(self):
        n = len(self.checked_items)
        self.selected_count_var.set(f'已选：{n} 个')

    def _choose_save_dir(self):
        """弹出目录选择对话框"""
        d = filedialog.askdirectory(
            title='选择字体文件保存目录',
            initialdir=self.save_dir_var.get()
        )
        if d:
            self.save_dir_var.set(d)

    def _preview_font(self, idx):
        """弹出字体预览窗口"""
        if 0 <= idx < len(self.font_data):
            font_info = self.font_data[idx]
            show_preview_window(self.root, font_info)

    def _download_single(self, idx):
        """下载单个字体"""
        if 0 <= idx < len(self.font_data):
            font_info = self.font_data[idx]
            save_dir = self.save_dir_var.get()
            if not os.path.isdir(save_dir):
                os.makedirs(save_dir, exist_ok=True)
            threading.Thread(
                target=self._do_download,
                args=([font_info], save_dir, False),
                daemon=True
            ).start()

    def _download_selected(self):
        """下载选中的字体"""
        if not self.checked_items:
            messagebox.showinfo('提示', '请先勾选要下载的字体！')
            return
        selected_fonts = [self.font_data[int(i)] for i in self.checked_items
                          if int(i) < len(self.font_data)]
        if not selected_fonts:
            return
        save_dir = self.save_dir_var.get()
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        self._start_download(selected_fonts, save_dir)

    def _download_all(self):
        """下载全部字体"""
        if not self.font_data:
            return
        if not messagebox.askyesno('确认', f'确认下载全部 {len(self.font_data)} 个字体文件？'):
            return
        save_dir = self.save_dir_var.get()
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        self._start_download(self.font_data, save_dir)

    def _start_download(self, fonts, save_dir):
        """启动下载线程"""
        self.download_btn.config(state='disabled')
        self.download_all_btn.config(state='disabled')
        self.status_var.set(f'开始下载 {len(fonts)} 个字体文件...')

        threading.Thread(
            target=self._do_download,
            args=(fonts, save_dir, True),
            daemon=True
        ).start()

    def _do_download(self, fonts, save_dir, restore_buttons):
        """实际执行下载（后台线程）"""
        success = 0
        fail = 0
        for i, font in enumerate(fonts):
            self.root.after(0, lambda i=i, n=len(fonts), name=font['name']:
                            self.status_var.set(f'下载中 ({i+1}/{n})：{name}'))
            try:
                resp = requests.get(font['url'], headers=HEADERS, timeout=30, stream=True)
                resp.raise_for_status()

                # 构造保存文件名
                from urllib.parse import urlparse
                import os
                filename = os.path.basename(urlparse(font['url']).path)
                if not filename:
                    filename = f"{font['name']}.{font['format']}"
                save_path = os.path.join(save_dir, filename)

                # 避免同名覆盖
                base, ext = os.path.splitext(save_path)
                counter = 1
                while os.path.exists(save_path):
                    save_path = f'{base}_{counter}{ext}'
                    counter += 1

                with open(save_path, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                success += 1
            except Exception as e:
                fail += 1

        def finish():
            msg = f'✅ 下载完成！成功 {success} 个'
            if fail:
                msg += f'，失败 {fail} 个'
            msg += f'  →  保存至：{save_dir}'
            self.status_var.set(msg)
            if restore_buttons:
                self.download_btn.config(state='normal')
                self.download_all_btn.config(state='normal')
            if success:
                if messagebox.askyesno('下载完成',
                                       f'{msg}\n\n是否立即打开保存目录？'):
                    os.startfile(save_dir)

        self.root.after(0, finish)

    def _sort_by(self, col):
        """点击表头排序"""
        if col not in ('name', 'format', 'size'):
            return
        if col == 'size':
            key = lambda x: self.font_data[int(x)]['size']
        else:
            key = lambda x: self.font_data[int(x)][col].lower()

        items = list(self.tree.get_children())
        items.sort(key=key)
        for idx, item in enumerate(items):
            self.tree.move(item, '', idx)
            values = list(self.tree.item(item, 'values'))
            values[1] = idx + 1
            tag = 'odd' if idx % 2 == 0 else 'even'
            if item in self.checked_items:
                tag = 'checked'
            self.tree.item(item, values=values, tags=(tag,))


def main():
    root = tk.Tk()
    app = FontDownloaderApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()

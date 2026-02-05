import sys
import uuid
import os
import ctypes
import json
from datetime import datetime, timedelta, timezone
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel, QColorDialog, QSystemTrayIcon,
                             QMenu, QTableWidget, QTableWidgetItem, QHeaderView,
                             QInputDialog, QMessageBox, QFrame, QScrollArea,
                             QGraphicsDropShadowEffect, QListWidget, QListWidgetItem)
from PyQt6.QtGui import (QIcon, QColor, QAction, QPainter, QPixmap, QFont,
                         QShortcut, QKeySequence, QBrush, QPen, QCursor)
from PyQt6.QtCore import (Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve,
                          QPoint, QRect, QThread, pyqtSignal, QVariantAnimation, QPointF)

# 导入 wintypes 用于 Windows API 调用
if sys.platform == 'win32':
    from ctypes import wintypes


# --- 资源路径适配函数 (核心：适配 PyInstaller 打包) ---
def resource_path(relative_path):
    """ 获取文件的绝对路径，兼容开发环境与打包后的环境 """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        return os.path.join(sys._MEIPASS, relative_path)
    # 开发环境下的当前目录
    return os.path.join(os.path.abspath("."), relative_path)


try:
    from supabase import create_client, Client
except ImportError:
    print("错误: 请先运行 'pip install supabase' 安装数据库库")
    sys.exit(1)

# 数据库配置
SUPABASE_URL = "https://fjupgsvslahmuwirtooc.supabase.co"
SUPABASE_KEY = "sb_publishable_WePlyU5U7HI2RloP-VQG_A_ANh6_Ajl"

# --- 现代毛玻璃 QSS 样式表 ---
STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI";
    color: #2d3436;
}
#MainContainer {
    background-color: rgba(245, 246, 250, 0.95); 
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.4);
}
QListWidget#Sidebar {
    background-color: rgba(255, 255, 255, 0.4);
    border: none;
    border-right: 1px solid rgba(0, 0, 0, 0.05);
    border-top-left-radius: 20px;
    border-bottom-left-radius: 20px;
    outline: none;
}
QListWidget#Sidebar::item {
    padding: 12px;
    border-radius: 10px;
    margin: 4px 8px;
    color: #636e72;
}
QListWidget#Sidebar::item:selected {
    background-color: #6c5ce7;
    color: white;
}
QFrame#Card {
    background-color: rgba(255, 255, 255, 0.7);
    border-radius: 15px;
    border: 1px solid rgba(255, 255, 255, 0.9);
}
QLabel#Title {
    font-size: 15px;
    font-weight: bold;
    color: #6c5ce7;
}
QPushButton.TrafficBtn {
    border: none;
    border-radius: 6px;
    font-size: 9px;
    font-weight: bold;
    font-family: "Arial";
    color: transparent;
}
QPushButton.TrafficBtn:hover { color: rgba(0, 0, 0, 0.5); }
#BtnClose { background-color: #FF5F56; }
#BtnMin { background-color: #FFBD2E; }
#BtnMax { background-color: #27C93F; }

QFrame#EmojiBar {
    background: rgba(255, 255, 255, 0.5);
    border-radius: 8px;
    border: 1px solid rgba(0, 0, 0, 0.05);
}
QPushButton#EmojiBtn {
    background-color: transparent;
    border: none;
    font-size: 18px;
    border-radius: 5px;
}
QPushButton#EmojiBtn:hover { background-color: rgba(108, 92, 231, 0.15); }

QPushButton#PrimaryBtn {
    background-color: #6c5ce7;
    color: white;
    border-radius: 10px;
    font-weight: bold;
}
QPushButton#PrimaryBtn:hover { background-color: #5b4cc4; }

QPushButton#MeditationBtn {
    background-color: #00b894;
    color: white;
    border-radius: 10px;
}
QTableWidget {
    border: none;
    gridline-color: transparent;
    background-color: transparent;
}
QHeaderView::section {
    background-color: transparent;
    border: none;
    color: #b2bec3;
    font-size: 11px;
    padding-bottom: 5px;
}
"""


# --- 呼吸光点控件 ---
class BreathingDot(QWidget):
    def __init__(self, color_str, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.base_color = QColor(color_str)
        self.glow_radius = 5.0
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(4.0)
        self.anim.setEndValue(10.0)
        self.anim.setDuration(2000)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self.update_glow)
        self.anim.start()

    def update_glow(self, value):
        self.glow_radius = float(value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.rect().center())
        glow_color = QColor(self.base_color)
        alpha = int(max(0, 150 - self.glow_radius * 12))
        glow_color.setAlpha(alpha)
        painter.setBrush(glow_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, self.glow_radius, self.glow_radius)
        painter.setBrush(self.base_color)
        painter.drawEllipse(center, 5.0, 5.0)


# --- 全局热键监听线程 ---
class HotkeyThread(QThread):
    hotkey_pressed = pyqtSignal()

    def run(self):
        if sys.platform != 'win32': return
        user32 = ctypes.windll.user32
        # Alt(0x0001) + Ctrl(0x0002) + M(77)
        if not user32.RegisterHotKey(None, 1, 0x0001 | 0x0002, 77):
            return
        try:
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312:
                    self.hotkey_pressed.emit()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnregisterHotKey(None, 1)


# --- 冥想沉浸窗体 ---
class MeditationWindow(QWidget):
    def __init__(self, moods_data):
        super().__init__()
        self.moods = moods_data
        self.dots = []
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.showFullScreen()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        for mood in self.moods:
            self.dots.append({
                "pos": QPoint(500, 500),
                "speed": QPoint((uuid.getnode() % 10 - 5), (uuid.getnode() % 8 - 4)),
                "color": QColor(mood.get('color', '#6c5ce7')),
                "msg": mood.get('message', '')
            })
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)

    def update_animation(self):
        rect = self.rect()
        for dot in self.dots:
            dot["pos"] += dot["speed"]
            if dot["pos"].x() < 0 or dot["pos"].x() > rect.width(): dot["speed"].setX(-dot["speed"].x())
            if dot["pos"].y() < 0 or dot["pos"].y() > rect.height(): dot["speed"].setY(-dot["speed"].y())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 225))
        for dot in self.dots:
            color = QColor(dot["color"])
            color.setAlpha(180)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(dot["pos"], 15, 15)
            painter.setPen(QColor(255, 255, 255, 180))
            painter.drawText(dot["pos"] + QPoint(20, 5), dot["msg"])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


# --- 主管理面板 ---
class SettingsWindow(QWidget):
    def __init__(self, supabase_client: Client, user_id: str, app_icon: QIcon):
        super().__init__()
        self.supabase = supabase_client
        self.user_id = user_id
        self.selected_color = "#6c5ce7"
        self.current_group = None
        self.recent_groups = []
        self.last_data_hash = ""

        self.setWindowIcon(app_icon)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(300)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_moods)

        self.init_ui()
        self.check_user_status()

    def init_ui(self):
        self.setFixedSize(650, 780)
        self.setStyleSheet(STYLESHEET)
        self.container = QFrame(self)
        self.container.setObjectName("MainContainer")
        self.container.setFixedSize(650, 780)

        main_layout = QHBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(160)
        self.sidebar.itemClicked.connect(self.switch_group)
        main_layout.addWidget(self.sidebar)

        content_wrapper = QVBoxLayout()
        content_wrapper.setContentsMargins(20, 0, 20, 20)
        content_wrapper.setSpacing(15)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 15, 0, 5)
        traffic_lights = QHBoxLayout()
        traffic_lights.setSpacing(8)
        self.btn_close = QPushButton("×")
        self.btn_min = QPushButton("−")
        self.btn_max = QPushButton("+")
        for btn, name, func in [(self.btn_close, "BtnClose", self.hide_animated),
                                (self.btn_min, "BtnMin", self.showMinimized),
                                (self.btn_max, "BtnMax", self.toggle_size)]:
            btn.setObjectName(name)
            btn.setFixedSize(12, 12)
            btn.setProperty("class", "TrafficBtn")
            btn.clicked.connect(func)
            traffic_lights.addWidget(btn)
        top_bar.addLayout(traffic_lights)
        top_bar.addSpacing(20)
        self.group_label = QLabel("共鸣频段: 未连接")
        self.group_label.setObjectName("Title")
        top_bar.addWidget(self.group_label)
        top_bar.addStretch()
        content_wrapper.addLayout(top_bar)

        header_card = QFrame();
        header_card.setObjectName("Card");
        self.add_shadow(header_card)
        header_layout = QVBoxLayout(header_card)
        self.refresh_status_label = QLabel("等待连接共鸣网络...")
        header_layout.addWidget(self.refresh_status_label)
        btn_row = QHBoxLayout()
        self.join_btn = QPushButton("接入");
        self.create_btn = QPushButton("新建")
        self.leave_btn = QPushButton("切断");
        self.meditation_btn = QPushButton("冥想模式")
        self.meditation_btn.setObjectName("MeditationBtn")
        for b in [self.join_btn, self.create_btn, self.leave_btn, self.meditation_btn]: btn_row.addWidget(b)
        header_layout.addLayout(btn_row)
        content_wrapper.addWidget(header_card)

        input_card = QFrame();
        input_card.setObjectName("Card");
        self.add_shadow(input_card)
        input_layout = QVBoxLayout(input_card)
        self.message_input = QLineEdit();
        self.message_input.setPlaceholderText("此刻的想法是...")
        input_layout.addWidget(self.message_input)
        emoji_bar = QFrame();
        emoji_bar.setObjectName("EmojiBar")
        emoji_row = QHBoxLayout(emoji_bar);
        emojis = ["😊", "🌈", "✨", "🌊", "🌙", "🔥", "🐱", "☁️", "🍀"]
        for e in emojis:
            btn = QPushButton(e);
            btn.setObjectName("EmojiBtn");
            btn.setFixedSize(32, 32)
            btn.clicked.connect(lambda checked, char=e: self.message_input.insert(char))
            emoji_row.addWidget(btn)
        emoji_row.addStretch();
        input_layout.addWidget(emoji_bar)
        color_row = QHBoxLayout()
        self.color_preview = QFrame();
        self.color_preview.setFixedSize(20, 20)
        self.color_preview.setStyleSheet(
            f"background-color: {self.selected_color}; border-radius: 10px; border: 2px solid white;")
        self.color_btn = QPushButton("色彩");
        self.save_btn = QPushButton("同步共鸣")
        self.save_btn.setObjectName("PrimaryBtn");
        self.save_btn.setFixedSize(100, 35)
        color_row.addWidget(self.color_preview);
        color_row.addWidget(self.color_btn)
        color_row.addStretch();
        color_row.addWidget(self.save_btn)
        input_layout.addLayout(color_row)
        content_wrapper.addWidget(input_card)

        list_card = QFrame();
        list_card.setObjectName("Card");
        self.add_shadow(list_card)
        list_layout = QVBoxLayout(list_card)
        self.mood_table = QTableWidget();
        self.mood_table.setColumnCount(2)
        self.mood_table.setHorizontalHeaderLabels(["状态", "心声内容"])
        self.mood_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.mood_table.setColumnWidth(0, 60)
        self.mood_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.mood_table.verticalHeader().setVisible(False);
        self.mood_table.setShowGrid(False)
        list_layout.addWidget(self.mood_table)
        content_wrapper.addWidget(list_card)
        main_layout.addLayout(content_wrapper)

        self.save_btn.clicked.connect(self.save_settings)
        self.color_btn.clicked.connect(self.pick_color)
        self.create_btn.clicked.connect(self.handle_create_group)
        self.join_btn.clicked.connect(self.handle_join_group)
        self.leave_btn.clicked.connect(self.handle_leave_group)
        self.meditation_btn.clicked.connect(self.open_meditation)

    def add_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect();
        shadow.setBlurRadius(15)
        shadow.setXOffset(0);
        shadow.setYOffset(4);
        shadow.setColor(QColor(0, 0, 0, 25))
        widget.setGraphicsEffect(shadow)

    def toggle_size(self):
        new_w = 900 if self.width() == 650 else 650
        self.setFixedWidth(new_w);
        self.container.setFixedWidth(new_w)

    def show_animated(self):
        self.show()
        self.setWindowOpacity(0.0)
        self.anim.stop();
        self.anim.setStartValue(0.0);
        self.anim.setEndValue(1.0)
        try:
            self.anim.finished.disconnect()
        except:
            pass
        self.anim.start()
        self.activateWindow()

    def hide_animated(self):
        self.anim.stop();
        self.anim.setStartValue(self.windowOpacity());
        self.anim.setEndValue(0.0)
        try:
            self.anim.finished.disconnect()
        except:
            pass
        self.anim.finished.connect(self.hide);
        self.anim.start()

    def check_user_status(self):
        try:
            res = self.supabase.table("moods").select("group_code").eq("user_uuid", self.user_id).execute()
            if res.data and res.data[0]['group_code']:
                self.current_group = res.data[0]['group_code']
                if self.current_group not in self.recent_groups: self.recent_groups.append(self.current_group)
                self.update_sidebar();
                self.update_group_ui(True)
            else:
                self.update_group_ui(False)
        except:
            pass

    def update_sidebar(self):
        self.sidebar.clear()
        for g in self.recent_groups:
            item = QListWidgetItem(f"📡 {g}")
            self.sidebar.addItem(item)
            if g == self.current_group: self.sidebar.setCurrentItem(item)

    def switch_group(self, item):
        group_name = item.text().replace("📡 ", "")
        if group_name != self.current_group:
            self.current_group = group_name;
            self.save_settings();
            self.update_group_ui(True)

    def update_group_ui(self, in_group):
        self.group_label.setText(f"频段: {self.current_group}" if in_group else "未连接频段")
        self.save_btn.setEnabled(in_group)
        if in_group:
            if not self.refresh_timer.isActive(): self.refresh_timer.start(8000)
            self.refresh_moods()
        else:
            self.refresh_timer.stop();
            self.mood_table.setRowCount(0);
            self.last_data_hash = ""

    def handle_create_group(self):
        n, ok1 = QInputDialog.getText(self, "创建频段", "请输入频段名称：")
        if not ok1 or not n: return
        p, ok2 = QInputDialog.getText(self, "访问密码", "设置接入密码：", QLineEdit.EchoMode.Password)
        if ok1 and ok2 and n:
            try:
                self.supabase.table("groups").insert({"name": n, "password": p, "creator_uuid": self.user_id}).execute()
                self.current_group = n
                if n not in self.recent_groups: self.recent_groups.append(n)
                self.update_sidebar();
                self.save_settings();
                self.update_group_ui(True)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建失败: {str(e)}")

    def handle_join_group(self):
        n, ok1 = QInputDialog.getText(self, "接入频段", "频段名称：")
        if not ok1 or not n: return
        p, ok2 = QInputDialog.getText(self, "接入密码", "密码：", QLineEdit.EchoMode.Password)
        if ok1 and ok2:
            res = self.supabase.table("groups").select("*").eq("name", n).eq("password", p).execute()
            if res.data:
                self.current_group = n
                if n not in self.recent_groups: self.recent_groups.append(n)
                self.update_sidebar();
                self.save_settings();
                self.update_group_ui(True)
            else:
                QMessageBox.warning(self, "接入失败", "名称或密码错误")

    def handle_leave_group(self):
        self.supabase.table("moods").update({"group_code": None}).eq("user_uuid", self.user_id).execute()
        self.current_group = None;
        self.update_group_ui(False)

    def pick_color(self):
        c = QColorDialog.getColor()
        if c.isValid():
            self.selected_color = c.name()
            self.color_preview.setStyleSheet(
                f"background-color: {c.name()}; border-radius: 10px; border: 2px solid white;")

    def save_settings(self):
        if not self.current_group: return
        data = {
            "user_uuid": self.user_id, "group_code": self.current_group,
            "color": self.selected_color, "message": self.message_input.text() or "🌈 保持共鸣",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        self.supabase.table("moods").upsert(data, on_conflict="user_uuid").execute()
        self.refresh_moods()

    def refresh_moods(self):
        if not self.current_group: return
        try:
            time_limit = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            self.supabase.table("moods").delete().lt("updated_at", time_limit).execute()
            res = self.supabase.table("moods").select("*").eq("group_code", self.current_group).order("updated_at",
                                                                                                      desc=True).execute()
            h = json.dumps(res.data, sort_keys=True)
            if h == self.last_data_hash: return
            self.last_data_hash, self.last_data = h, res.data
            self.mood_table.setRowCount(len(res.data))
            for r, item in enumerate(res.data):
                dot_widget = BreathingDot(item['color'])
                container = QWidget();
                l = QHBoxLayout(container);
                l.addWidget(dot_widget)
                l.setAlignment(Qt.AlignmentFlag.AlignCenter);
                l.setContentsMargins(0, 0, 0, 0)
                self.mood_table.setCellWidget(r, 0, container)
                txt = f"{item['message']}" + (" (我)" if item['user_uuid'] == self.user_id else "")
                ti = QTableWidgetItem(txt);
                ti.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.mood_table.setItem(r, 1, ti)
            self.refresh_status_label.setText(f"当前共鸣人数: {len(res.data)}")
        except:
            self.refresh_status_label.setText("同步中...")

    def open_meditation(self):
        if hasattr(self, 'last_data') and self.last_data:
            self.med_win = MeditationWindow(self.last_data)
        else:
            QMessageBox.information(self, "提示", "先加入一个有共鸣的频段吧")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft();
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos);
            event.accept()


# --- 应用主控类 (v0.3.0 重点修复区) ---
class MoodBeamApp:
    def __init__(self):
        if sys.platform == 'win32':
            my_appid = u'com.moodbeam.resonance.v030'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_appid)

        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # 资源图标加载
        self.icon_path = resource_path("icon.png")
        if os.path.exists(self.icon_path):
            self.app_icon = QIcon(self.icon_path)
        else:
            self.app_icon = self.create_fallback_icon()

        self.app.setWindowIcon(self.app_icon)
        self.user_id = str(uuid.getnode())
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.settings_window = SettingsWindow(self.supabase, self.user_id, self.app_icon)

        # 热键监听
        self.hotkey_thread = HotkeyThread()
        self.hotkey_thread.hotkey_pressed.connect(self.toggle_window)
        self.hotkey_thread.start()

        self.setup_tray()
        self.settings_window.show_animated()

    def create_fallback_icon(self):
        pix = QPixmap(64, 64);
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix);
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor("#6c5ce7"));
        p.setPen(Qt.PenStyle.NoPen);
        p.drawEllipse(8, 8, 48, 48);
        p.end()
        return QIcon(pix)

    def setup_tray(self):
        """ 重新构建托盘逻辑 """
        self.tray_icon = QSystemTrayIcon(self.app_icon, self.app)
        self.tray_icon.setToolTip("共鸣之光 (MoodBeam)")

        # 创建自定义右键菜单
        self.tray_menu = QMenu()
        self.tray_menu.setWindowFlags(self.tray_menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.tray_menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.tray_menu.setStyleSheet("""
            QMenu { background-color: white; border: 1px solid #6c5ce7; border-radius: 10px; padding: 5px; }
            QMenu::item { padding: 8px 25px; border-radius: 5px; }
            QMenu::item:selected { background-color: #6c5ce7; color: white; }
        """)

        a_show = QAction("✨ 呼唤面板", self.tray_menu)
        a_show.triggered.connect(self.settings_window.show_animated)

        a_quit = QAction("🚪 退出共鸣", self.tray_menu)
        a_quit.triggered.connect(self.app.quit)

        self.tray_menu.addAction(a_show)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(a_quit)

        # 核心：将菜单直接绑定到托盘，但不通过 setContextMenu(self.tray_menu)
        # 而是通过 activated 信号全权接管，解决左键点击无效的问题
        self.tray_icon.activated.connect(self.handle_tray_activation)
        self.tray_icon.show()

    def handle_tray_activation(self, reason):
        """ 接管所有点击事件 """
        # Trigger 是左键，Context 是右键，DoubleClick 是双击
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.Context,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            # 获取当前鼠标位置并弹出菜单
            self.tray_menu.exec(QCursor.pos())

    def toggle_window(self):
        if self.settings_window.isVisible():
            self.settings_window.hide_animated()
        else:
            self.settings_window.show_animated()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    MoodBeamApp().run()

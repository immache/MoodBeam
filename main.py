import sys
import uuid
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLineEdit, QLabel, QColorDialog, QSystemTrayIcon,
                             QMenu, QTableWidget, QTableWidgetItem, QHeaderView,
                             QInputDialog, QMessageBox)
from PyQt6.QtGui import QIcon, QColor, QAction, QPainter, QPixmap
from PyQt6.QtCore import Qt, QTimer


# --- 资源路径适配函数 (打包必备) ---
def resource_path(relative_path):
    """ 获取文件的绝对路径，兼容 PyInstaller 打包后的环境 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


try:
    from supabase import create_client, Client
except ImportError:
    print("错误: 请先运行 'pip install supabase' 安装数据库库")
    sys.exit(1)

# 注意：在实际发布前，建议将 Key 混淆或通过更安全的方式管理，目前维持原样以便你直接运行
SUPABASE_URL = "YOUR_URL"
SUPABASE_KEY = "YOUR_KEY"


class SettingsWindow(QWidget):
    def __init__(self, supabase_client: Client, user_id: str):
        super().__init__()
        self.supabase = supabase_client
        self.user_id = user_id
        self.selected_color = "#a29bfe"
        self.current_group = None
        self.is_creator = False
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_moods)
        self.init_ui()
        self.check_user_status()

    def init_ui(self):
        self.setWindowTitle("共鸣之光 - 管理者模式")
        self.setFixedSize(400, 600)
        # 设置窗口图标（如果存在 icon.png）
        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout()
        header_layout = QHBoxLayout()
        self.group_label = QLabel("<b>当前群组：未加入</b>")
        self.refresh_status_label = QLabel("")
        self.refresh_status_label.setStyleSheet("color: #b2bec3; font-size: 10px;")
        header_layout.addWidget(self.group_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_status_label)
        layout.addLayout(header_layout)

        btn_layout = QHBoxLayout()
        self.join_btn = QPushButton("加入群组")
        self.create_btn = QPushButton("创建新群组")
        self.leave_btn = QPushButton("退出群组")
        self.delete_btn = QPushButton("解散群组")
        self.delete_btn.setStyleSheet("background-color: #ff7675; color: white;")
        for b in [self.join_btn, self.create_btn, self.leave_btn, self.delete_btn]:
            b.setFixedHeight(30)
            btn_layout.addWidget(b)
        layout.addLayout(btn_layout)

        layout.addWidget(QLabel("<hr>"))
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("在群组里想说什么？")
        layout.addWidget(QLabel("<b>此刻心声：</b>"))
        layout.addWidget(self.message_input)

        self.color_btn = QPushButton("修改代表色")
        self.color_btn.clicked.connect(self.pick_color)
        layout.addWidget(self.color_btn)

        self.save_btn = QPushButton("同步我的共鸣")
        self.save_btn.setFixedHeight(40)
        self.save_btn.setStyleSheet("background-color: #6c5ce7; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)

        layout.addWidget(QLabel("<hr>"))
        self.mood_table = QTableWidget()
        self.mood_table.setColumnCount(2)
        self.mood_table.setHorizontalHeaderLabels(["色块", "心声"])
        self.mood_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.mood_table)

        self.setLayout(layout)

        # 信号连接
        self.create_btn.clicked.connect(self.handle_create_group)
        self.join_btn.clicked.connect(self.handle_join_group)
        self.leave_btn.clicked.connect(self.handle_leave_group)
        self.delete_btn.clicked.connect(self.handle_delete_group)

    def check_user_status(self):
        try:
            res = self.supabase.table("moods").select("group_code").eq("user_uuid", self.user_id).execute()
            if res.data and res.data[0]['group_code']:
                self.current_group = res.data[0]['group_code']
                g_res = self.supabase.table("groups").select("creator_uuid").eq("name", self.current_group).execute()
                self.is_creator = (g_res.data[0]['creator_uuid'] == self.user_id) if g_res.data else False
                self.update_group_ui(True)
            else:
                self.update_group_ui(False)
        except:
            pass

    def update_group_ui(self, in_group):
        self.group_label.setText(f"<b>当前：{self.current_group if in_group else '未加入'}</b>")
        self.join_btn.setVisible(not in_group)
        self.create_btn.setVisible(not in_group)
        self.leave_btn.setVisible(in_group)
        self.delete_btn.setVisible(in_group and self.is_creator)
        self.save_btn.setEnabled(in_group)
        if in_group:
            self.refresh_timer.start(30000)
            self.refresh_moods()
        else:
            self.refresh_timer.stop()
            self.mood_table.setRowCount(0)

    def handle_create_group(self):
        n, ok1 = QInputDialog.getText(self, "创建", "名称：")
        p, ok2 = QInputDialog.getText(self, "密码", "密码：", QLineEdit.EchoMode.Password)
        if ok1 and ok2 and n and p:
            try:
                self.supabase.table("groups").insert({"name": n, "password": p, "creator_uuid": self.user_id}).execute()
                self.current_group, self.is_creator = n, True
                self.save_settings()
                self.update_group_ui(True)
            except:
                QMessageBox.critical(self, "错误", "名称已存在或网络连接失败")

    def handle_join_group(self):
        n, ok1 = QInputDialog.getText(self, "加入", "名称：")
        p, ok2 = QInputDialog.getText(self, "验证", "密码：", QLineEdit.EchoMode.Password)
        if ok1 and ok2:
            res = self.supabase.table("groups").select("*").eq("name", n).eq("password", p).execute()
            if res.data:
                self.current_group = n
                self.is_creator = (res.data[0]['creator_uuid'] == self.user_id)
                self.save_settings()
                self.update_group_ui(True)
            else:
                QMessageBox.warning(self, "失败", "群组名或密码错误")

    def handle_leave_group(self):
        if QMessageBox.question(self, "确认", "确定退出当前群组吗？") == QMessageBox.StandardButton.Yes:
            self.supabase.table("moods").update({"group_code": None}).eq("user_uuid", self.user_id).execute()
            self.current_group = None
            self.update_group_ui(False)

    def handle_delete_group(self):
        p, ok = QInputDialog.getText(self, "解散", "请输入群组密码以确认解散：", QLineEdit.EchoMode.Password)
        if ok:
            res = self.supabase.table("groups").select("*").eq("name", self.current_group).eq("password", p).execute()
            if res.data:
                self.supabase.table("groups").delete().eq("name", self.current_group).execute()
                self.supabase.table("moods").update({"group_code": None}).eq("group_code", self.current_group).execute()
                self.current_group = None
                self.update_group_ui(False)
            else:
                QMessageBox.warning(self, "错误", "密码错误")

    def pick_color(self):
        c = QColorDialog.getColor()
        if c.isValid():
            self.selected_color = c.name()
            self.color_btn.setStyleSheet(f"background-color: {c.name()}; color: white;")

    def save_settings(self):
        if not self.current_group: return
        data = {
            "user_uuid": self.user_id,
            "group_code": self.current_group,
            "color": self.selected_color,
            "message": self.message_input.text() or "Hello"
        }
        self.supabase.table("moods").upsert(data, on_conflict="user_uuid").execute()
        self.refresh_moods()

    def refresh_moods(self):
        if not self.current_group: return
        try:
            res = self.supabase.table("moods").select("*").eq("group_code", self.current_group).execute()
            self.mood_table.setRowCount(len(res.data))
            for r, item in enumerate(res.data):
                lbl = QLabel()
                lbl.setStyleSheet(f"background-color: {item['color']}; margin: 5px; border-radius: 5px;")
                self.mood_table.setCellWidget(r, 0, lbl)
                txt = f"{item['message']} (我)" if item['user_uuid'] == self.user_id else item['message']
                self.mood_table.setItem(r, 1, QTableWidgetItem(txt))
            self.refresh_status_label.setText(f"成员: {len(res.data)} | 已实时同步")
        except:
            self.refresh_status_label.setText("同步失败，检查网络")

    def showEvent(self, e):
        super().showEvent(e)
        if self.current_group: self.refresh_timer.start(30000)

    def hideEvent(self, e):
        super().hideEvent(e)
        self.refresh_timer.stop()


class MoodBeamApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.user_id = str(uuid.getnode())
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.settings_window = SettingsWindow(self.supabase, self.user_id)
        self.setup_tray()
        self.settings_window.show()

    def setup_tray(self):
        # 尝试加载 icon.png，如果没有则生成默认圆点
        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            tray_icon_img = QIcon(icon_path)
        else:
            pix = QPixmap(64, 64)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setBrush(QColor("#6c5ce7"))
            p.drawEllipse(8, 8, 48, 48)
            p.end()
            tray_icon_img = QIcon(pix)

        self.tray_icon = QSystemTrayIcon(tray_icon_img, self.app)
        menu = QMenu()
        open_action = menu.addAction("打开面板")
        open_action.triggered.connect(self.settings_window.show)
        exit_action = menu.addAction("退出程序")
        exit_action.triggered.connect(self.app.quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def run(self):
        sys.exit(self.app.exec())


if __name__ == "__main__":
    MoodBeamApp().run()

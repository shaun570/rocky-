import sys
import os
import random
import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QMenu, QSystemTrayIcon
)
from PySide6.QtGui import QIcon, QMovie, QAction, QPixmap, QFontDatabase, QFont
from PySide6.QtCore import Qt, QTimer, QSize, QUrl
from PySide6.QtMultimedia import QSoundEffect


def resource_path(rel_path: str) -> str:
    """
    兼容开发环境与 PyInstaller 打包后的资源路径。
    """
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, rel_path)


def first_existing(paths: list[str]) -> str | None:
    """
    从候选路径里找出第一个存在的路径，找不到返回 None。
    """
    for p in paths:
        rp = resource_path(p)
        if os.path.exists(rp):
            return rp
    return None


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()

        # 无边框 + 置顶 + 透明背景：仅显示图像与气泡
        self.setWindowFlags(Qt.FramelessWindowHint |
                            Qt.Tool |
                            Qt.NoDropShadowWindowHint |
                            Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setWindowIcon(QIcon(resource_path("assets/app.ico")))
        self.setWindowTitle("桌宠")

        # 右键菜单的统一样式（修复黑底看不清的问题）
        self.menu_style = """
        QMenu {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid rgba(0,0,0,0.15);
            padding: 4px;
        }
        QMenu::item {
            padding: 6px 14px;
            background: transparent;
        }
        QMenu::item:selected {
            background: #e6f0ff;
            color: #000000;
        }
        """

        # 尺寸与模式
        self.min_side = 100
        self.max_side = 400
        self._resizing_guard = False
        self.side = 240
        self.resize_mode = False  # “调整大小”开关

        # 精灵区域（按比例缩放，完整可见）
        self.sprite = QLabel(self)
        self.sprite.setScaledContents(False)     # 不直接拉伸
        self.sprite.setAlignment(Qt.AlignCenter) # 内容居中
        self.sprite.setFixedSize(self.side, self.side)
        self.sprite.move(0, 0)

        # 气泡（居中）
        self.bubble = QLabel(self)
        self.bubble.setWordWrap(True)
        self.bubble.setFixedWidth(230)
        self.bubble.setAlignment(Qt.AlignCenter)  # 文字水平+垂直居中
        self.bubble.setStyleSheet(
            "QLabel {"
            " background: rgba(255, 204, 229, 0.92);"
            " color: #444444;"
            " border-radius: 12px;"
            " padding: 8px;"
            "}"
        )
        self.bubble.hide()
        self.bubble_timer = QTimer(self)
        self.bubble_timer.setSingleShot(True)
        self.bubble_timer.timeout.connect(self.bubble.hide)

        # 资源与文案
        self.assets = {
            "morning": "assets/morning.gif",
            "day":     "assets/day.gif",
            "evening": "assets/evening.gif",
            "night":   "assets/night.gif",
        }
        self.phrases = {
            "morning": [
                "GOOD!GOOD!GOOD!",
                "AMAZE!AMAZE!AMAZE!",
                "GOOD!!!",
                "HAPPY!HAPPY!HAPPY!",
            ],
            "day": [
                "GOOD!GOOD!GOOD!",
                "AMAZE!AMAZE!AMAZE!",
                "GOOD!!!",
                "HAPPY!HAPPY!HAPPY!",
            ],
            "evening": [
                "GOOD!GOOD!GOOD!",
                "AMAZE!AMAZE!AMAZE!",
                "GOOD!!!",
                "HAPPY!HAPPY!HAPPY!",
            ],
            "night": [
                "GOOD!GOOD!GOOD!",
                "AMAZE!AMAZE!AMAZE!",
                "GOOD!!!",
                "HAPPY!HAPPY!HAPPY!",
            ],
        }

        # 当前主题/GIF控制
        self.current_period = None
        self.movie: QMovie | None = None
        # 跟踪当前显示资源（用于在窗口大小变化时按比例重绘）
        # 形式为：("movie", 路径) 或 ("pixmap", 路径)
        self.current_visual: tuple[str, str] | None = None

        # 声音效果：从 assets/sfx 下加载 .wav/.ogg，点击时随机播放
        self.sfx_effects: list[QSoundEffect] = []
        self._init_sounds()

        # 托盘菜单（应用浅色样式）
        self.tray = QSystemTrayIcon(QIcon(resource_path("assets/app.ico")), self)
        tray_menu = QMenu()
        tray_menu.setStyleSheet(self.menu_style)

        act_phrase = QAction("来一句", self)
        act_phrase.triggered.connect(self.show_random_phrase)

        self.act_resize = QAction("调整大小", self)
        self.act_resize.setCheckable(True)
        self.act_resize.toggled.connect(self.set_resize_mode)

        act_toggle = QAction("显示/隐藏", self)
        act_toggle.triggered.connect(self.toggle_visible)

        act_exit = QAction("退出", self)
        act_exit.triggered.connect(QApplication.instance().quit)

        tray_menu.addAction(act_phrase)
        tray_menu.addAction(self.act_resize)
        tray_menu.addSeparator()
        tray_menu.addAction(act_toggle)
        tray_menu.addAction(act_exit)
        self.tray.setContextMenu(tray_menu)
        self.tray.show()

        # 初始：正方形、居右下角、主题
        self.setFixedSize(self.side, self.side)
        self.update_theme()
        self.position_bottom_right()

        # 定时检查时间段（每 5 分钟）
        self.theme_timer = QTimer(self)
        self.theme_timer.timeout.connect(self.update_theme)
        self.theme_timer.start(5 * 60 * 1000)

        # 拖拽移动
        self.drag_offset = None

        # 自定义字体用法（任选一种，按需取消注释）
        # 方式一：使用系统已安装字体
        # self._apply_label_font("等距更纱黑体 SC", 12, bold=True)
        # 方式二：从 assets 加载字体文件（打包可用）
        family = self._load_font_from_assets("assets/HFShinySunday-2.ttf")
        if family: self._apply_label_font(family, 12, bold=True)

    # ========== 初始化与播放音效 ==========
    def _init_sounds(self):
        """
        扫描 assets/sfx 目录，加载 .wav/.ogg 音效为 QSoundEffect。
        点击时会随机挑一个播放。
        """
        sfx_dir = resource_path("assets/sfx")
        if not os.path.isdir(sfx_dir):
            return
        for name in os.listdir(sfx_dir):
            if not name.lower().endswith((".wav", ".ogg")):
                continue
            path = os.path.join(sfx_dir, name)
            eff = QSoundEffect(self)
            eff.setSource(QUrl.fromLocalFile(path))
            eff.setVolume(0.8)  # 0.0-1.0
            # eff.setLoopCount(1)  # 默认一次
            self.sfx_effects.append(eff)

    def play_random_sfx(self):
        if not self.sfx_effects:
            return
        eff = random.choice(self.sfx_effects)
        # 若已在播，先停再播，让点击能“立刻触发”
        if eff.isPlaying():
            eff.stop()
        eff.play()

    # ========== 位置/主题/气泡 ==========
    def position_bottom_right(self):
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.move(screen_geo.right() - self.width() - 20,
                  screen_geo.bottom() - self.height() - 20)

    def time_period(self, t: datetime.time | None = None) -> str:
        if t is None:
            t = datetime.datetime.now().time()
        if datetime.time(5, 0) <= t < datetime.time(9, 0):
            return "morning"
        elif datetime.time(9, 0) <= t < datetime.time(16, 0):
            return "day"
        elif datetime.time(16, 0) <= t < datetime.time(21, 0):
            return "evening"
        else:
            return "night"

    def update_theme(self):
        period = self.time_period()
        if period != self.current_period:
            self.current_period = period
            path = resource_path(self.assets[period])
            self._set_movie(path)
            self.setToolTip(f"桌宠 - {period}")

    def show_random_phrase(self):
        period = self.current_period or self.time_period()
        pool = self.phrases.get(period, ["嗨～"])
        text = random.choice(pool)
        self._show_bubble(text, 4000)

    # ========== 调整大小模式（正方形、100-400）==========
    def set_resize_mode(self, on: bool):
        """
        进入调整大小模式：
        - 显示系统窗口边框，允许拖拽改变大小
        - 强制正方形，边长限制 [100, 400]
        退出时：
        - 恢复无边框，并把当前大小锁定为固定大小
        """
        self.resize_mode = on
        pos_before = self.pos()

        if on:
            # 显示系统边框（可拖拽）
            self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
            self.setMinimumSize(self.min_side, self.min_side)
            self.setMaximumSize(self.max_side, self.max_side)
            self.show()
            self.move(pos_before)
        else:
            # 退出：锁定当前为正方形固定大小，恢复无边框
            fixed_side = max(self.min_side, min(self.max_side, min(self.width(), self.height())))
            self.setWindowFlags(Qt.FramelessWindowHint |
                                Qt.Tool |
                                Qt.NoDropShadowWindowHint |
                                Qt.WindowStaysOnTopHint)
            self.setFixedSize(fixed_side, fixed_side)
            self.show()
            self.move(pos_before)

        # 精灵区域大小贴合窗口并重绘
        self.sprite.setFixedSize(self.width(), self.height())
        self._refresh_sprite_frame()

    # ========== 统一的短提示（气泡）=========
    def _show_bubble(self, text: str, ms: int = 1500):
        self.bubble.setText(text)
        self.bubble.adjustSize()
        bx = max(6, (self.width() - self.bubble.width()) // 2)
        by = max(6, self.sprite.y() - self.bubble.height() - 8)
        self.bubble.move(bx, by)
        self.bubble.show()
        self.bubble_timer.start(ms)

    # ========== GIF/图片按比例完整显示的核心实现 ==========
    def _set_movie(self, path: str):
        """设置并播放 GIF，缩放策略：按窗口大小等比缩放，完整可见。"""
        if self.movie:
            self.movie.stop()
            self.movie.deleteLater()
            self.movie = None
        self.current_visual = ("movie", path)
        m = QMovie(path)
        self.movie = m
        # 每帧回调：取当前帧等比缩放，setPixmap 到标签
        m.frameChanged.connect(self._on_movie_frame)
        m.start()
        self._on_movie_frame(-1)  # 立即绘制首帧

    def _on_movie_frame(self, _index: int):
        if not self.movie:
            return
        frame = self.movie.currentPixmap()
        if frame.isNull():
            return
        self._set_sprite_pixmap(frame)

    def _set_pixmap(self, path: str):
        """设置静态图片，缩放策略同上。"""
        self.current_visual = ("pixmap", path)
        pm = QPixmap(path)
        self._set_sprite_pixmap(pm)

    def _set_sprite_pixmap(self, pm: QPixmap):
        # 按窗口的正方形尺寸，保持比例缩放，完整显示
        if pm.isNull():
            return
        target = pm.scaled(self.sprite.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.sprite.setPixmap(target)

    def _refresh_sprite_frame(self):
        """窗口尺寸变化后，按当前资源重绘（保证始终完整显示）。"""
        if not self.current_visual:
            return
        kind, path = self.current_visual
        if kind == "movie" and self.movie:
            self._on_movie_frame(-1)
        elif kind == "pixmap":
            self._set_pixmap(path)

    # ========== 字体相关 ==========
    def _load_font_from_assets(self, rel_path: str) -> str | None:
        """
        从 assets 加载 ttf/otf 字体并注册，返回首选字体族名，失败返回 None。
        打包时记得 --add-data "assets;assets"
        """
        path = resource_path(rel_path)
        if not os.path.exists(path):
            return None
        fid = QFontDatabase.addApplicationFont(path)
        if fid == -1:
            return None
        fams = QFontDatabase.applicationFontFamilies(fid)
        return fams[0] if fams else None

    def _apply_label_font(self, family: str, pt_size: int = 12, bold: bool = False):
        """
        将字体应用到气泡（也可应用到全局或其他控件）。
        """
        font = QFont(family, pt_size)
        font.setBold(bold)
        self.bubble.setFont(font)
        # 如需全局统一：
        # QApplication.instance().setFont(font)

    # ========== 鼠标与事件 ==========
    def _global_pos(self, e):
        if hasattr(e, "globalPosition"):
            return e.globalPosition().toPoint()
        return e.globalPos()

    def _local_pos(self, e):
        if hasattr(e, "position"):
            return e.position().toPoint()
        return e.pos()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drag_offset = self._global_pos(e) - self.frameGeometry().topLeft()
            self.show_random_phrase()
            self.play_random_sfx()  # 点击时随机播放一个音效
            e.accept()

    def mouseMoveEvent(self, e):
        # 非调整大小模式下，支持拖拽整体移动
        if not self.resize_mode and self.drag_offset and (e.buttons() & Qt.LeftButton):
            self.move(self._global_pos(e) - self.drag_offset)
            e.accept()

    def mouseReleaseEvent(self, e):
        self.drag_offset = None

    def contextMenuEvent(self, e):
        # 右键菜单（与托盘共享动作），应用统一浅色样式
        m = QMenu(self)
        m.setStyleSheet(self.menu_style)
        m.addAction("来一句", self.show_random_phrase)
        m.addAction(self.act_resize)
        m.addSeparator()
        m.addAction("退出", QApplication.instance().quit)
        m.exec(e.globalPos())

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

    def resizeEvent(self, event):
        """
        调整大小模式：强制正方形 + 限制范围 [100,400]。
        任何情况下，sprite 都按比例完整显示当前资源。
        """
        super().resizeEvent(event)

        if self.resize_mode and not self._resizing_guard:
            w, h = event.size().width(), event.size().height()
            target = max(w, h)
            target = max(self.min_side, min(self.max_side, target))
            if target != w or target != h:
                self._resizing_guard = True
                self.resize(QSize(target, target))
                self._resizing_guard = False

        # 精灵随窗口填充（label 大小等于窗口，但内容等比缩放）
        self.sprite.setFixedSize(self.width(), self.height())
        self._refresh_sprite_frame()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec())
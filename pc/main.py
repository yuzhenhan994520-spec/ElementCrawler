import json
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import sys

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QSplitter, QTreeWidget, QTreeWidgetItem, QLabel, QPushButton,
        QTextEdit, QLineEdit, QGroupBox, QFrame, QMessageBox,
        QComboBox, QScrollArea, QMenuBar, QMenu, QStatusBar,
        QDialog, QDialogButtonBox, QTabWidget, QTableWidget,
        QTableWidgetItem, QHeaderView
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
    from PyQt6.QtGui import QAction, QFont, QClipboard, QTextCursor
except ImportError:
    print("PyQt6 not installed. Please run: pip install PyQt6")
    sys.exit(1)


@dataclass
class Element:
    resource_id: str = ""
    text: str = ""
    content_desc: str = ""
    class_name: str = ""
    bounds: str = ""
    depth: int = 0
    is_clickable: bool = False
    is_scrollable: bool = False
    is_focusable: bool = False
    is_editable: bool = False
    package_name: str = ""
    view_id: str = ""
    x: int = 0
    y: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> 'Element':
        return cls(
            resource_id=data.get('resourceId', ''),
            text=data.get('text', ''),
            content_desc=data.get('contentDesc', ''),
            class_name=data.get('className', ''),
            bounds=data.get('bounds', ''),
            depth=data.get('depth', 0),
            is_clickable=data.get('isClickable', False),
            is_scrollable=data.get('isScrollable', False),
            is_focusable=data.get('isFocusable', False),
            is_editable=data.get('isEditable', False),
            package_name=data.get('packageName', ''),
            view_id=data.get('viewId', ''),
            x=data.get('x', 0),
            y=data.get('y', 0)
        )

    def get_best_locator(self) -> Dict[str, str]:
        locators = []

        if self.resource_id and self.resource_id != "null":
            locators.append({
                'type': 'resource-id',
                'value': self.resource_id,
                'priority': 1,
                'code': f'driver.find_element(AppiumBy.ID, "{self.resource_id}")'
            })

        if self.text and self.text != "null":
            locators.append({
                'type': 'text',
                'value': self.text,
                'priority': 2,
                'code': f'driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().text(\\"{self.text}\\")")'
            })

        if self.content_desc and self.content_desc != "null":
            locators.append({
                'type': 'content-desc',
                'value': self.content_desc,
                'priority': 3,
                'code': f'driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().description(\\"{self.content_desc}\\")")'
            })

        if self.class_name and self.class_name != "null":
            locators.append({
                'type': 'className',
                'value': self.class_name,
                'priority': 4,
                'code': f'driver.find_element(AppiumBy.CLASS_NAME, "{self.class_name}")'
            })

        locators.append({
            'type': 'coordinates',
            'value': f'({self.x}, {self.y})',
            'priority': 5,
            'code': f'driver.tap([({self.x}, {self.y})])'
        })

        locators.sort(key=lambda x: x['priority'])
        return locators[0] if locators else {}


class AndroidConnection:
    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.connected = False

    def connect(self, ip: str, port: int = 16688) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((ip, port))
            self.connected = True
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            return False

    def send_command(self, command: str) -> str:
        if not self.connected or not self.socket:
            return "ERROR: Not connected"

        try:
            self.socket.sendall(f"{command}\n".encode())
            self.socket.settimeout(10)
            response = self.socket.recv(65536).decode()
            return response.strip()
        except Exception as e:
            print(f"Command failed: {e}")
            return f"ERROR: {e}"

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False

    def get_elements(self) -> List[Element]:
        response = self.send_command("GET_ELEMENTS")
        try:
            data = json.loads(response)
            return [Element.from_dict(item) for item in data]
        except:
            return []

    def click_by_coords(self, x: int, y: int) -> bool:
        response = self.send_command(f"CLICK_BY_COORDS:{x},{y}")
        return response == "OK"

    def click_by_id(self, element_id: str) -> bool:
        response = self.send_command(f"CLICK_BY_ID:{element_id}")
        return response == "OK"

    def click_by_text(self, text: str) -> bool:
        response = self.send_command(f"CLICK_BY_TEXT:{text}")
        return response == "OK"

    def click_by_content_desc(self, content_desc: str) -> bool:
        response = self.send_command(f"CLICK_BY_CONTENT_DESC:{content_desc}")
        return response == "OK"

    def input_text(self, text: str) -> bool:
        response = self.send_command(f"INPUT_TEXT:{text}")
        return response == "OK"

    def scroll_down(self) -> bool:
        response = self.send_command("SCROLL_DOWN")
        return response == "OK"

    def scroll_up(self) -> bool:
        response = self.send_command("SCROLL_UP")
        return response == "OK"


class ADBHelper:
    @staticmethod
    def run_command(args: List[str]) -> str:
        try:
            result = subprocess.run(
                ['adb'] + args,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.strip()
        except Exception as e:
            return str(e)

    @staticmethod
    def get_devices() -> List[str]:
        output = ADBHelper.run_command(['devices'])
        devices = []
        for line in output.split('\n')[1:]:
            if line.strip() and 'device' in line:
                device = line.split()[0]
                devices.append(device)
        return devices

    @staticmethod
    def get_device_ip(device: str = "") -> str:
        cmd = ['shell', 'ip', 'route']
        if device:
            cmd = ['-s', device] + cmd

        output = ADBHelper.run_command(cmd)
        for line in output.split('\n'):
            if 'src' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'src':
                        return parts[i + 1]
        return "127.0.0.1"

    @staticmethod
    def forward_port(port: int) -> bool:
        result = ADBHelper.run_command(['forward', f'tcp:{port}', 'tcp:16688'])
        return result == ""

    @staticmethod
    def reverse_port(port: int) -> bool:
        result = ADBHelper.run_command(['reverse', f'tcp:{port}', 'tcp:16688'])
        return result == ""


class ElementDetailDialog(QDialog):
    def __init__(self, element: Element, parent=None):
        super().__init__(parent)
        self.element = element
        self.setWindowTitle("元素详情")
        self.setMinimumSize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        basic_tab = QWidget()
        basic_layout = QVBoxLayout()

        fields = [
            ("Resource ID", self.element.resource_id),
            ("Text", self.element.text),
            ("Content Desc", self.element.content_desc),
            ("Class Name", self.element.class_name),
            ("Package Name", self.element.package_name),
            ("View ID", self.element.view_id),
            ("Bounds", self.element.bounds),
            ("Position", f"({self.element.x}, {self.element.y})"),
            ("Depth", str(self.element.depth)),
        ]

        for label, value in fields:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{label}:"))
            row.addWidget(QLabel(value if value else "-"))
            row.addStretch()
            basic_layout.addLayout(row)

        basic_tab.setLayout(basic_layout)
        tabs.addTab(basic_tab, "基本属性")

        properties_tab = QWidget()
        properties_layout = QVBoxLayout()

        props = [
            ("可点击 (Clickable)", self.element.is_clickable),
            ("可滚动 (Scrollable)", self.element.is_scrollable),
            ("可聚焦 (Focusable)", self.element.is_focusable),
            ("可编辑 (Editable)", self.element.is_editable),
        ]

        for label, value in props:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{label}:"))
            row.addWidget(QLabel("是" if value else "否"))
            row.addStretch()
            properties_layout.addLayout(row)

        properties_tab.setLayout(properties_layout)
        tabs.addTab(properties_tab, "属性")

        locator_tab = QWidget()
        locator_layout = QVBoxLayout()

        best_locator = self.element.get_best_locator()
        if best_locator:
            row = QHBoxLayout()
            row.addWidget(QLabel("推荐定位方式:"))
            row.addWidget(QLabel(best_locator.get('type', '')))
            row.addStretch()
            locator_layout.addLayout(row)

            row = QHBoxLayout()
            row.addWidget(QLabel("定位值:"))
            row.addWidget(QLabel(best_locator.get('value', '')))
            row.addStretch()
            locator_layout.addLayout(row)

            code_group = QGroupBox("Appium 代码")
            code_layout = QVBoxLayout()
            code_edit = QTextEdit()
            code_edit.setPlainText(best_locator.get('code', ''))
            code_edit.setReadOnly(True)
            code_layout.addWidget(code_edit)
            code_group.setLayout(code_layout)
            locator_layout.addWidget(code_group)

        locator_tab.setLayout(locator_layout)
        tabs.addTab(locator_tab, "定位推荐")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
        )
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.connection = AndroidConnection()
        self.elements: List[Element] = []
        self.selected_element: Optional[Element] = None
        self.device_serial = ""
        self.scrcpy_process = None

        self.setWindowTitle("元素捕手 - Element Crawler PC")
        self.setMinimumSize(1400, 800)

        self.setup_ui()
        self.setup_menu()

    def setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")

        connect_action = QAction("连接设备", self)
        connect_action.triggered.connect(self.show_connect_dialog)
        file_menu.addAction(connect_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        device_menu = menubar.addMenu("设备")

        refresh_action = QAction("刷新元素", self)
        refresh_action.triggered.connect(self.refresh_elements)
        device_menu.addAction(refresh_action)

        start_scrcpy_action = QAction("启动 scrcpy", self)
        start_scrcpy_action.triggered.connect(self.start_scrcpy)
        device_menu.addAction(start_scrcpy_action)

        stop_scrcpy_action = QAction("停止 scrcpy", self)
        stop_scrcpy_action.triggered.connect(self.stop_scrcpy)
        device_menu.addAction(stop_scrcpy_action)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)

        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([350, 600, 350])

        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("未连接")

    def create_left_panel(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)

        title = QLabel("元素列表")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        control_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_elements)
        control_layout.addWidget(self.refresh_btn)

        self.auto_refresh_check = QComboBox()
        self.auto_refresh_check.addItems(["手动刷新", "1秒", "2秒", "3秒", "5秒"])
        self.auto_refresh_check.currentTextChanged.connect(self.on_auto_refresh_changed)
        control_layout.addWidget(self.auto_refresh_check)

        layout.addLayout(control_layout)

        self.element_tree = QTreeWidget()
        self.element_tree.setHeaderLabels(["元素", "类型", "文本"])
        self.element_tree.setColumnWidth(0, 200)
        self.element_tree.itemClicked.connect(self.on_element_selected)
        layout.addWidget(self.element_tree)

        return frame

    def create_center_panel(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)

        title = QLabel("scrcpy 投屏区域")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        scrcpy_info = QLabel("请先连接设备，然后点击'启动 scrcpy'开始投屏")
        scrcpy_info.setStyleSheet("color: gray; padding: 10px;")
        layout.addWidget(scrcpy_info)

        layout.addStretch()

        return frame

    def create_right_panel(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)

        title = QLabel("元素详情")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(300)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self.detail_group = QGroupBox("详细信息")
        detail_layout = QVBoxLayout()

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(200)
        detail_layout.addWidget(self.detail_text)

        self.detail_group.setLayout(detail_layout)
        scroll_layout.addWidget(self.detail_group)

        locator_group = QGroupBox("定位推荐")
        locator_layout = QVBoxLayout()

        self.locator_combo = QComboBox()
        self.locator_combo.currentIndexChanged.connect(self.on_locator_changed)
        locator_layout.addWidget(self.locator_combo)

        self.locator_value = QLineEdit()
        self.locator_value.setReadOnly(True)
        locator_layout.addWidget(self.locator_value)

        self.locator_code = QTextEdit()
        self.locator_code.setReadOnly(True)
        self.locator_code.setMaximumHeight(80)
        locator_layout.addWidget(self.locator_code)

        locator_group.setLayout(locator_layout)
        scroll_layout.addWidget(locator_group)

        action_group = QGroupBox("操作")
        action_layout = QVBoxLayout()

        self.click_test_btn = QPushButton("点击测试")
        self.click_test_btn.clicked.connect(self.click_test)
        self.click_test_btn.setEnabled(False)
        action_layout.addWidget(self.click_test_btn)

        copy_layout = QHBoxLayout()

        self.copy_locator_btn = QPushButton("复制定位")
        self.copy_locator_btn.clicked.connect(self.copy_locator)
        self.copy_locator_btn.setEnabled(False)
        copy_layout.addWidget(self.copy_locator_btn)

        self.copy_code_btn = QPushButton("复制代码")
        self.copy_code_btn.clicked.connect(self.copy_code)
        self.copy_code_btn.setEnabled(False)
        copy_layout.addWidget(self.copy_code_btn)

        action_layout.addLayout(copy_layout)

        action_group.setLayout(action_layout)
        scroll_layout.addWidget(action_group)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        return frame

    def show_connect_dialog(self):
        devices = ADBHelper.get_devices()
        if not devices:
            QMessageBox.warning(self, "警告", "未检测到ADB设备，请确保手机已连接电脑并开启USB调试")
            return

        device = devices[0]
        self.device_serial = device

        ip = ADBHelper.get_device_ip(device)
        if ip == "127.0.0.1":
            ip = "192.168.1.100"

        port = 16688
        ADBHelper.forward_port(port)

        if self.connection.connect(ip, port):
            self.status_bar.showMessage(f"已连接: {ip}:{port}")
            self.refresh_elements()
            QMessageBox.information(self, "成功", f"已连接到设备 {ip}:{port}")
        else:
            QMessageBox.warning(self, "连接失败", "无法连接到Android设备，请确保手机端应用已启动无障碍服务")

    def refresh_elements(self):
        if not self.connection.connected:
            QMessageBox.warning(self, "未连接", "请先连接设备")
            return

        self.elements = self.connection.get_elements()
        self.update_element_tree()
        self.status_bar.showMessage(f"已加载 {len(self.elements)} 个元素")

    def update_element_tree(self):
        self.element_tree.clear()

        elements_by_depth: Dict[int, List[Element]] = {}
        for element in self.elements:
            if element.depth not in elements_by_depth:
                elements_by_depth[element.depth] = []
            elements_by_depth[element.depth].append(element)

        def create_items(elements: List[Element], parent: QTreeWidgetItem = None):
            for element in elements:
                if element.class_name:
                    display_text = element.class_name.split('.')[-1]
                else:
                    display_text = "Element"

                if element.text:
                    display_text = f"{display_text}: {element.text[:20]}"
                elif element.resource_id:
                    display_text = f"{display_text}: {element.resource_id.split('/')[-1]}"

                if parent:
                    item = QTreeWidgetItem(parent, [display_text, element.class_name.split('.')[-1] if element.class_name else "", element.text[:30] if element.text else ""])
                else:
                    item = QTreeWidgetItem(self.element_tree, [display_text, element.class_name.split('.')[-1] if element.class_name else "", element.text[:30] if element.text else ""])

                item.setData(0, Qt.ItemDataRole.UserRole, element)

        for depth in sorted(elements_by_depth.keys()):
            create_items(elements_by_depth[depth])

    def on_element_selected(self, item: QTreeWidgetItem, column: int):
        element = item.data(0, Qt.ItemDataRole.UserRole)
        if element:
            self.selected_element = element
            self.show_element_details(element)

    def show_element_details(self, element: Element):
        self.detail_text.clear()
        self.detail_text.append(f"Resource ID: {element.resource_id or '-'}")
        self.detail_text.append(f"Text: {element.text or '-'}")
        self.detail_text.append(f"Content Desc: {element.content_desc or '-'}")
        self.detail_text.append(f"Class Name: {element.class_name or '-'}")
        self.detail_text.append(f"Package: {element.package_name or '-'}")
        self.detail_text.append(f"Bounds: {element.bounds or '-'}")
        self.detail_text.append(f"Position: ({element.x}, {element.y})")
        self.detail_text.append(f"Depth: {element.depth}")
        self.detail_text.append(f"Clickable: {'是' if element.is_clickable else '否'}")
        self.detail_text.append(f"Scrollable: {'是' if element.is_scrollable else '否'}")
        self.detail_text.append(f"Editable: {'是' if element.is_editable else '否'}")

        locators = self.get_all_locators(element)
        self.locator_combo.clear()
        for loc in locators:
            self.locator_combo.addItem(f"{loc['type']}: {loc['value']}", loc)

        if locators:
            self.locator_combo.setCurrentIndex(0)
            self.on_locator_changed(0)

        self.click_test_btn.setEnabled(True)
        self.copy_locator_btn.setEnabled(True)
        self.copy_code_btn.setEnabled(True)

    def get_all_locators(self, element: Element) -> List[Dict]:
        locators = []

        if element.resource_id and element.resource_id != "null":
            locators.append({
                'type': 'resource-id',
                'value': element.resource_id,
                'code': f'driver.find_element(AppiumBy.ID, "{element.resource_id}")'
            })

        if element.text and element.text != "null":
            locators.append({
                'type': 'text',
                'value': element.text,
                'code': f'driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().text(\\"{element.text}\\")")'
            })

        if element.content_desc and element.content_desc != "null":
            locators.append({
                'type': 'content-desc',
                'value': element.content_desc,
                'code': f'driver.find_element(AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().description(\\"{element.content_desc}\\")")'
            })

        if element.class_name and element.class_name != "null":
            locators.append({
                'type': 'className',
                'value': element.class_name,
                'code': f'driver.find_element(AppiumBy.CLASS_NAME, "{element.class_name}")'
            })

        locators.append({
            'type': 'coordinates',
            'value': f'({element.x}, {element.y})',
            'code': f'driver.tap([({element.x}, {element.y})])'
        })

        return locators

    def on_locator_changed(self, index):
        if index < 0:
            return

        loc = self.locator_combo.currentData()
        if loc:
            self.locator_value.setText(loc.get('value', ''))
            self.locator_code.setPlainText(loc.get('code', ''))

    def click_test(self):
        if not self.selected_element:
            return

        element = self.selected_element

        if element.resource_id and element.resource_id != "null":
            if self.connection.click_by_id(element.resource_id):
                self.status_bar.showMessage(f"点击成功 (ID: {element.resource_id})")
                return

        if element.text and element.text != "null":
            if self.connection.click_by_text(element.text):
                self.status_bar.showMessage(f"点击成功 (Text: {element.text})")
                return

        if element.content_desc and element.content_desc != "null":
            if self.connection.click_by_content_desc(element.content_desc):
                self.status_bar.showMessage(f"点击成功 (ContentDesc: {element.content_desc})")
                return

        self.status_bar.showMessage("无法点击: 元素无可用定位方式")

    def copy_locator(self):
        value = self.locator_value.text()
        if value:
            clipboard = QApplication.clipboard()
            clipboard.setText(value)
            self.status_bar.showMessage("已复制定位值")

    def copy_code(self):
        code = self.locator_code.toPlainText()
        if code:
            clipboard = QApplication.clipboard()
            clipboard.setText(code)
            self.status_bar.showMessage("已复制代码")

    def start_scrcpy(self):
        if not self.device_serial:
            QMessageBox.warning(self, "警告", "请先连接设备")
            return

        try:
            self.scrcpy_process = subprocess.Popen(
                ['scrcpy', '-s', self.device_serial, '--window-title', '元素捕手 - scrcpy'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.status_bar.showMessage("scrcpy 已启动")
        except FileNotFoundError:
            QMessageBox.warning(self, "错误", "未找到 scrcpy，请确保已安装 scrcpy 并添加到环境变量")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"启动 scrcpy 失败: {e}")

    def stop_scrcpy(self):
        if self.scrcpy_process:
            self.scrcpy_process.terminate()
            self.scrcpy_process = None
            self.status_bar.showMessage("scrcpy 已停止")

    def on_auto_refresh_changed(self, text):
        pass

    def closeEvent(self, event):
        self.connection.disconnect()
        self.stop_scrcpy()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

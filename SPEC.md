# 安卓手机元素抓取器 - 项目规格说明

## 1. 项目概述

**项目名称**: ElementCrawler (元素捕手)
**项目类型**: Android 应用 + Python PC端控制软件

**核心功能**: 
- 通过Android AccessibilityService抓取APP页面所有元素
- 与scrcpy投屏软件配合使用
- 智能推荐最佳元素定位方式
- 支持元素点击测试和定位信息复制

## 2. 技术架构

### 2.1 系统架构
```
┌─────────────────┐      ┌─────────────────┐
│  Android设备    │      │   PC电脑        │
│                 │      │                 │
│ ┌─────────────┐ │      │ ┌─────────────┐ │
│ │Accessibility│ │      │ │ Python控制  │ │
│ │  Service    │ │◄────►│ │   端软件    │ │
│ └─────────────┘ │ Socket│ └─────────────┘ │
│ ┌─────────────┐ │ 16688│ ┌─────────────┐ │
│ │  元素数据   │ │─────►│ │  scrcpy    │ │
│ │   采集      │ │      │ │  投屏显示   │ │
│ └─────────────┘ │      │ └─────────────┘ │
└─────────────────┘      └─────────────────┘
```

### 2.2 技术选型

**Android端**:
- 语言: Kotlin
- 最低SDK: 24 (Android 7.0)
- 目标SDK: 34 (Android 14)
- 核心组件: AccessibilityService
- 通信: Socket Server (端口16688)

**PC端**:
- 语言: Python 3.8+
- GUI框架: PyQt6
- 通信方式: Socket Client + ADB
- 投屏软件: scrcpy

## 3. 功能列表

### 3.1 Android端功能
1. **无障碍服务** - 实时捕获页面所有UI元素
2. **元素数据采集** - 获取元素文本、ID、类名、坐标、层级等
3. **Socket服务器** - 提供TCP接口供PC端连接
4. **点击操作** - 支持坐标点击和ID点击
5. **文本输入** - 支持向可编辑元素输入文本
6. **滚动操作** - 支持上下滚动

### 3.2 PC端功能 (Python)
1. **ADB连接管理** - 自动检测和连接Android设备
2. **scrcpy集成** - 一键启动/停止scrcpy投屏
3. **元素列表展示** - 树形结构显示当前页面所有元素
4. **元素详情面板** - 显示选中元素的完整属性
5. **智能定位推荐** - 算法推荐最佳定位方式(优先级: resource-id > text > content-desc > className > coordinates)
6. **点击测试** - 向Android发送点击指令测试元素
7. **复制功能** - 一键复制定位信息/Appium代码到剪贴板

## 4. 使用说明

### 4.1 准备工作

1. **安装ADB**: 下载Android SDK Platform Tools并添加到环境变量
2. **安装scrcpy**: 从 https://github.com/Genymobile/scrcpy 下载安装
3. **安装Python依赖**:
   ```
   cd pc
   pip install PyQt6
   ```

### 4.2 Android端安装

1. 使用Android Studio打开 `android/` 目录
2. 构建Debug APK: `./gradlew assembleDebug`
3. 将生成的APK安装到手机
4. 运行APP并授予无障碍权限

### 4.3 PC端运行

1. 连接手机到电脑（USB调试模式开启）
2. 运行: `python pc/main.py`
3. 点击"连接设备"按钮
4. 连接成功后点击"启动scrcpy"开始投屏
5. 点击"刷新"获取当前页面元素

### 4.4 功能操作

- **刷新元素**: 获取当前APP页面所有可交互元素
- **选择元素**: 点击左侧元素列表中的任意元素
- **查看详情**: 右侧面板显示元素的完整属性
- **定位推荐**: 系统自动推荐最佳定位方式
- **点击测试**: 点击"点击测试"按钮验证元素可点击性
- **复制**: 点击"复制定位"或"复制代码"复制到剪贴板

## 5. 元素定位策略 (优先级排序)

1. **resource-id** - 资源ID定位 (最高优先级，最稳定)
2. **text** - 文本定位 (适合有明确文本的按钮/标签)
3. **content-desc** - 描述定位 (适合图标按钮)
4. **className + 索引** - 类名+位置 (需要配合其他属性)
5. **bounds** - 坐标定位 (兜底方案，受屏幕尺寸影响)

## 6. 项目结构

```
手机元素抓取/
├── SPEC.md                    # 项目规格说明
├── android/                   # Android端项目
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── java/com/elementcrawler/
│   │   │   │   ├── MainActivity.kt          # 主界面
│   │   │   │   └── service/
│   │   │   │       └── ElementAccessibilityService.kt  # 无障碍服务
│   │   │   ├── res/                          # 资源文件
│   │   │   └── AndroidManifest.xml           # 清单文件
│   │   └── build.gradle
│   └── build.gradle
├── pc/                        # PC端项目
│   ├── main.py               # 主程序
│   ├── requirements.txt     # Python依赖
│   └── setup.bat            # 环境检查脚本
```

## 7. 验收标准

- [x] Android端能够成功安装并请求无障碍权限
- [x] 无障碍服务能够捕获主流APP的界面元素
- [x] Socket通信能够传输元素数据到PC端
- [x] PC端能够通过ADB连接Android设备
- [x] 元素列表能够实时更新显示当前页面元素
- [x] 定位推荐算法能够给出合理的定位建议
- [x] 点击测试功能能够在APP上触发对应元素
- [x] 复制功能能够正确复制定位信息

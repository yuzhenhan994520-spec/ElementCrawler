package com.elementcrawler.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Intent
import android.graphics.Rect
import android.os.Build
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import com.elementcrawler.MainActivity
import org.json.JSONArray
import org.json.JSONObject
import java.io.PrintWriter
import java.io.ServerSocket
import java.io.Socket
import java.net.NetworkInterface

class ElementAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "ElementCrawler"
        const val ACTION_START = "com.elementcrawler.ACTION_START"
        const val ACTION_STOP = "com.elementcrawler.ACTION_STOP"
        const val ACTION_CLICK = "com.elementcrawler.ACTION_CLICK"
        const val ACTION_CLICK_BY_COORDS = "com.elementcrawler.ACTION_CLICK_BY_COORDS"
        const val EXTRA_X = "extra_x"
        const val EXTRA_Y = "extra_y"

        private var instance: ElementAccessibilityService? = null
        private var elementCount = 0

        fun getInstance(): ElementAccessibilityService? = instance
        fun getElementCount(): Int = elementCount
    }

    private var serverSocket: ServerSocket? = null
    private var isServerRunning = false
    private var currentElements: MutableList<ElementInfo> = mutableListOf()

    data class ElementInfo(
        val node: AccessibilityNodeInfo,
        val resourceId: String,
        val text: String,
        val contentDesc: String,
        val className: String,
        val bounds: Rect,
        val depth: Int,
        val isClickable: Boolean,
        val isScrollable: Boolean,
        val isFocusable: Boolean,
        val isEditable: Boolean,
        val packageName: String,
        val viewId: String
    )

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        Log.d(TAG, "Service connected")

        serviceInfo = AccessibilityServiceInfo().apply {
            eventTypes = AccessibilityEvent.TYPE_ALL_TYPES
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS or
                    AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS or
                    AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS
            notificationTimeout = 100
        }

        startSocketServer()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopSelf()
            }
            ACTION_CLICK_BY_COORDS -> {
                val x = intent.getIntExtra(EXTRA_X, 0)
                val y = intent.getIntExtra(EXTRA_Y, 0)
                performGlobalAction(GLOBAL_ACTION_CLONE)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                    val gestureResult = dispatchGesture(
                        android.view.MotionEvent.obtain(
                            System.currentTimeMillis(),
                            System.currentTimeMillis(),
                            android.view.MotionEvent.ACTION_DOWN,
                            x.toFloat(),
                            y.toFloat(),
                            0
                        ),
                        null,
                        null
                    )
                }
            }
        }
        return super.onStartCommand(intent, flags, startId)
    }

    private fun startSocketServer() {
        Thread {
            try {
                serverSocket = ServerSocket(16688)
                isServerRunning = true
                Log.d(TAG, "Socket server started on port 16688")

                while (isServerRunning) {
                    try {
                        val clientSocket = serverSocket?.accept()
                        clientSocket?.let { handleClient(it) }
                    } catch (e: Exception) {
                        if (isServerRunning) {
                            Log.e(TAG, "Error accepting connection", e)
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error starting socket server", e)
            }
        }.start()
    }

    private fun handleClient(socket: Socket) {
        try {
            val reader = socket.getInputStream().bufferedReader()
            val writer = PrintWriter(socket.getOutputStream(), true)

            val request = reader.readLine()
            Log.d(TAG, "Received request: $request")

            val response = when {
                request.startsWith("GET_ELEMENTS") -> {
                    getElementsJson()
                }
                request.startsWith("CLICK_BY_ID:") -> {
                    val elementId = request.substringAfter("CLICK_BY_ID:")
                    if (clickElementById(elementId)) "OK" else "ERROR: Element not found"
                }
                request.startsWith("CLICK_BY_TEXT:") -> {
                    val text = request.substringAfter("CLICK_BY_TEXT:")
                    if (clickElementByText(text)) "OK" else "ERROR: Element not found"
                }
                request.startsWith("CLICK_BY_CONTENT_DESC:") -> {
                    val contentDesc = request.substringAfter("CLICK_BY_CONTENT_DESC:")
                    if (clickElementByContentDesc(contentDesc)) "OK" else "ERROR: Element not found"
                }
                request.startsWith("CLICK_BY_COORDS:") -> {
                    val coords = request.substringAfter("CLICK_BY_COORDS:")
                    val parts = coords.split(",")
                    if (parts.size == 2) {
                        val x = parts[0].toIntOrNull() ?: 0
                        val y = parts[1].toIntOrNull() ?: 0
                        clickByCoordinates(x, y)
                        "OK"
                    } else {
                        "ERROR: Invalid coordinates"
                    }
                }
                request.startsWith("INPUT_TEXT:") -> {
                    val text = request.substringAfter("INPUT_TEXT:")
                    inputText(text)
                    "OK"
                }
                request == "SCROLL_DOWN" -> {
                    performGlobalAction(GLOBAL_ACTION_SCROLL_FORWARD)
                    "OK"
                }
                request == "SCROLL_UP" -> {
                    performGlobalAction(GLOBAL_ACTION_SCROLL_BACKWARD)
                    "OK"
                }
                else -> {
                    "ERROR: Unknown command"
                }
            }

            writer.println(response)
            socket.close()
        } catch (e: Exception) {
            Log.e(TAG, "Error handling client", e)
        }
    }

    private fun getElementsJson(): String {
        val rootNode = rootInActiveWindow
        if (rootNode == null) {
            return JSONArray().toString()
        }

        currentElements.clear()
        extractElementsRecursive(rootNode, 0)
        elementCount = currentElements.size

        val jsonArray = JSONArray()
        for (element in currentElements) {
            val jsonObject = JSONObject().apply {
                put("resourceId", element.resourceId)
                put("text", element.text)
                put("contentDesc", element.contentDesc)
                put("className", element.className)
                put("bounds", "${element.bounds.left},${element.bounds.top},${element.bounds.right},${element.bounds.bottom}")
                put("depth", element.depth)
                put("isClickable", element.isClickable)
                put("isScrollable", element.isScrollable)
                put("isFocusable", element.isFocusable)
                put("isEditable", element.isEditable)
                put("packageName", element.packageName)
                put("viewId", element.viewId)
                put("x", (element.bounds.left + element.bounds.right) / 2)
                put("y", (element.bounds.top + element.bounds.bottom) / 2)
            }
            jsonArray.put(jsonObject)
        }

        rootNode.recycle()
        return jsonArray.toString()
    }

    private fun extractElementsRecursive(node: AccessibilityNodeInfo, depth: Int) {
        if (node == null) return

        val bounds = Rect()
        node.getBoundsInScreen(bounds)

        val resourceId = node.viewIdResourceName ?: ""
        val text = node.text?.toString() ?: ""
        val contentDesc = node.contentDescription?.toString() ?: ""
        val className = node.className?.toString() ?: ""
        val packageName = node.packageName?.toString() ?: ""

        if (bounds.width() > 0 && bounds.height() > 0) {
            val element = ElementInfo(
                node = node,
                resourceId = resourceId,
                text = text,
                contentDesc = contentDesc,
                className = className,
                bounds = bounds,
                depth = depth,
                isClickable = node.isClickable,
                isScrollable = node.isScrollable,
                isFocusable = node.isFocusable,
                isEditable = node.isEditable,
                packageName = packageName,
                viewId = resourceId.substringAfterLast("/")
            )
            currentElements.add(element)
        }

        for (i in 0 until node.childCount) {
            val child = node.getChild(i)
            if (child != null) {
                extractElementsRecursive(child, depth + 1)
                child.recycle()
            }
        }
    }

    private fun clickElementById(elementId: String): Boolean {
        val rootNode = rootInActiveWindow ?: return false

        fun findAndClick(node: AccessibilityNodeInfo): Boolean {
            if (node.viewIdResourceName == elementId) {
                return performClick(node)
            }

            for (i in 0 until node.childCount) {
                val child = node.getChild(i)
                if (child != null) {
                    if (findAndClick(child)) {
                        child.recycle()
                        return true
                    }
                    child.recycle()
                }
            }
            return false
        }

        val result = findAndClick(rootNode)
        rootNode.recycle()
        return result
    }

    private fun clickElementByText(text: String): Boolean {
        val rootNode = rootInActiveWindow ?: return false

        fun findAndClick(node: AccessibilityNodeInfo): Boolean {
            val nodeText = node.text?.toString() ?: ""
            if (nodeText == text) {
                return performClick(node)
            }

            for (i in 0 until node.childCount) {
                val child = node.getChild(i)
                if (child != null) {
                    if (findAndClick(child)) {
                        child.recycle()
                        return true
                    }
                    child.recycle()
                }
            }
            return false
        }

        val result = findAndClick(rootNode)
        rootNode.recycle()
        return result
    }

    private fun clickElementByContentDesc(contentDesc: String): Boolean {
        val rootNode = rootInActiveWindow ?: return false

        fun findAndClick(node: AccessibilityNodeInfo): Boolean {
            val nodeDesc = node.contentDescription?.toString() ?: ""
            if (nodeDesc == contentDesc) {
                return performClick(node)
            }

            for (i in 0 until node.childCount) {
                val child = node.getChild(i)
                if (child != null) {
                    if (findAndClick(child)) {
                        child.recycle()
                        return true
                    }
                    child.recycle()
                }
            }
            return false
        }

        val result = findAndClick(rootNode)
        rootNode.recycle()
        return result
    }

    private fun performClick(node: AccessibilityNodeInfo): Boolean {
        if (node.isClickable) {
            return node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
        }

        var parent = node.parent
        while (parent != null) {
            if (parent.isClickable) {
                val result = parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                parent.recycle()
                return result
            }
            val temp = parent.parent
            parent.recycle()
            parent = temp
        }
        return false
    }

    private fun clickByCoordinates(x: Int, y: Int): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            val builder = android.view.GestureDescription.Builder()
            val path = android.graphics.Path()
            path.moveTo(x.toFloat(), y.toFloat())
            builder.addStroke(android.view.GestureDescription.StrokeDescription(path, 0, 100))
            dispatchGesture(builder.build(), null, null)
            true
        } else {
            false
        }
    }

    private fun inputText(text: String): Boolean {
        val rootNode = rootInActiveWindow ?: return false

        fun findAndInput(node: AccessibilityNodeInfo): Boolean {
            if (node.isEditable) {
                val arguments = android.os.Bundle()
                arguments.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text)
                val result = node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments)
                node.recycle()
                return result
            }

            for (i in 0 until node.childCount) {
                val child = node.getChild(i)
                if (child != null) {
                    if (findAndInput(child)) {
                        child.recycle()
                        return true
                    }
                    child.recycle()
                }
            }
            return false
        }

        val result = findAndInput(rootNode)
        rootNode.recycle()
        return result
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event?.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||
            event?.eventType == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED) {
            Log.d(TAG, "Window changed: ${event.packageName}")
        }
    }

    override fun onInterrupt() {
        Log.d(TAG, "Service interrupted")
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        isServerRunning = false
        serverSocket?.close()
        Log.d(TAG, "Service destroyed")
    }
}

package com.elementcrawler

import android.accessibilityservice.AccessibilityServiceInfo
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.format.Formatter
import android.view.accessibility.AccessibilityManager
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.elementcrawler.databinding.ActivityMainBinding
import com.elementcrawler.service.ElementAccessibilityService
import java.net.NetworkInterface

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val SERVICE_PORT = 16688

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        displayIpAddress()
        setupListeners()
        updateServiceStatus()
    }

    override fun onResume() {
        super.onResume()
        updateServiceStatus()
    }

    private fun setupListeners() {
        binding.btnToggleService.setOnClickListener {
            if (isAccessibilityServiceEnabled()) {
                toggleAccessibilityService()
            } else {
                requestAccessibilityPermission()
            }
        }

        binding.btnCopyIp.setOnClickListener {
            copyIpAddress()
        }
    }

    private fun displayIpAddress() {
        val ipAddress = getLocalIpAddress()
        binding.tvIpAddress.text = ipAddress
        binding.tvPort.text = getString(R.string.port, SERVICE_PORT)
    }

    private fun getLocalIpAddress(): String {
        try {
            val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            val wifiInfo = wifiManager.connectionInfo
            val ipInt = wifiInfo.ipAddress
            if (ipInt != 0) {
                return Formatter.formatIpAddress(ipInt)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        try {
            val interfaces = NetworkInterface.getNetworkInterfaces()
            while (interfaces.hasMoreElements()) {
                val networkInterface = interfaces.nextElement()
                val addresses = networkInterface.inetAddresses
                while (addresses.hasMoreElements()) {
                    val address = addresses.nextElement()
                    if (!address.isLoopbackAddress && address.hostAddress?.contains(":") == false) {
                        return address.hostAddress ?: ""
                    }
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        return "127.0.0.1"
    }

    private fun copyIpAddress() {
        val ip = "${binding.tvIpAddress.text}:$SERVICE_PORT"
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val clip = ClipData.newPlainText("ElementCrawler IP", ip)
        clipboard.setPrimaryClip(clip)
        Toast.makeText(this, R.string.ip_copied, Toast.LENGTH_SHORT).show()
    }

    private fun isAccessibilityServiceEnabled(): Boolean {
        val accessibilityManager = getSystemService(Context.ACCESSIBILITY_SERVICE) as AccessibilityManager
        val enabledServices = accessibilityManager.getEnabledAccessibilityServiceList(
            AccessibilityServiceInfo.FEEDBACK_GENERAL
        )

        for (service in enabledServices) {
            if (service.resolveInfo.serviceInfo.packageName == packageName &&
                service.resolveInfo.serviceInfo.name == ElementAccessibilityService::class.java.name) {
                return true
            }
        }
        return false
    }

    private fun requestAccessibilityPermission() {
        val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        startActivity(intent)
        Toast.makeText(this, R.string.permission_required, Toast.LENGTH_LONG).show()
    }

    private fun toggleAccessibilityService() {
        val intent = Intent(this, ElementAccessibilityService::class.java)
        if (isAccessibilityServiceEnabled()) {
            intent.action = ElementAccessibilityService.ACTION_STOP
        } else {
            intent.action = ElementAccessibilityService.ACTION_START
        }
        startService(intent)
    }

    private fun updateServiceStatus() {
        val isEnabled = isAccessibilityServiceEnabled()
        if (isEnabled) {
            binding.tvStatus.text = getString(R.string.service_status_running)
            binding.tvStatus.setTextColor(getColor(R.color.green_running))
            binding.btnToggleService.text = getString(R.string.stop_service)
        } else {
            binding.tvStatus.text = getString(R.string.service_status_stopped)
            binding.tvStatus.setTextColor(getColor(R.color.red_stopped))
            binding.btnToggleService.text = getString(R.string.start_service)
        }

        val elementCount = ElementAccessibilityService.getElementCount()
        binding.tvElementCount.text = getString(R.string.element_count, elementCount)
    }

    fun updateElementCount(count: Int) {
        runOnUiThread {
            binding.tvElementCount.text = getString(R.string.element_count, count)
        }
    }
}

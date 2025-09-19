#include <windows.h>
#include <psapi.h>
#include <string>
#include <chrono>
#include <thread>
#include <iostream>
#include <tlhelp32.h>
#include <mmdeviceapi.h>
#include <endpointvolume.h>
#include <sstream>
#include <iomanip>

#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "ole32.lib")

// 全局变量
HANDLE hPipe = INVALID_HANDLE_VALUE;
bool isRunning = true;
DWORD lastKeyboardEvents = 0;
DWORD lastMouseEvents = 0;

// 音量控制接口
class AudioMeter {
private:
    IMMDeviceEnumerator* pEnumerator;
    IMMDevice* pDevice;
    IAudioEndpointVolume* pEndpointVolume;

public:
    AudioMeter() : pEnumerator(nullptr), pDevice(nullptr), pEndpointVolume(nullptr) {
        CoInitialize(nullptr);
        CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_INPROC_SERVER,
            __uuidof(IMMDeviceEnumerator), (void**)&pEnumerator);

        pEnumerator->GetDefaultAudioEndpoint(eRender, eConsole, &pDevice);
        pDevice->Activate(__uuidof(IAudioEndpointVolume), CLSCTX_INPROC_SERVER,
            nullptr, (void**)&pEndpointVolume);
    }

    ~AudioMeter() {
        if (pEndpointVolume) pEndpointVolume->Release();
        if (pDevice) pDevice->Release();
        if (pEnumerator) pEnumerator->Release();
        CoUninitialize();
    }

    float GetMasterVolume() {
        float level;
        pEndpointVolume->GetMasterVolumeLevelScalar(&level);
        return level * 100.0f; // 转换为百分比
    }
};

// 键盘和鼠标事件计数
void UpdateInputCounters(DWORD& keyboardCount, DWORD& mouseCount) {
    LASTINPUTINFO lii = { 0 };
    lii.cbSize = sizeof(LASTINPUTINFO);
    
    // 简单的事件计数方法 - 实际应用中可能需要使用钩子
    static DWORD lastTickCount = GetTickCount();
    DWORD currentTick = GetTickCount();
    
    // 这里只是模拟，实际应用中应该使用低级别钩子
    // 为了演示，我们检测是否有输入活动
    if (GetLastInputInfo(&lii)) {
        if (lii.dwTime > lastTickCount) {
            // 简单区分鼠标和键盘（实际需要更复杂的检测）
            mouseCount++;
        }
    }
    
    lastTickCount = currentTick;
}

// 获取进程CPU使用率
float GetProcessCpuUsage(DWORD pid) {
    static FILETIME lastKernelTime = { 0 }, lastUserTime = { 0 };
    static DWORD lastTickCount = 0;
    
    HANDLE hProc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (!hProc) return 0.0f;
    
    FILETIME creationTime, exitTime, kernelTime, userTime;
    if (!GetProcessTimes(hProc, &creationTime, &exitTime, &kernelTime, &userTime)) {
        CloseHandle(hProc);
        return 0.0f;
    }
    
    DWORD currentTick = GetTickCount();
    
    if (lastTickCount == 0) {
        lastKernelTime = kernelTime;
        lastUserTime = userTime;
        lastTickCount = currentTick;
        CloseHandle(hProc);
        return 0.0f;
    }
    
    // 计算时间差
    ULARGE_INTEGER kernelDiff, userDiff, totalDiff;
    kernelDiff.LowPart = kernelTime.dwLowDateTime - lastKernelTime.dwLowDateTime;
    kernelDiff.HighPart = kernelTime.dwHighDateTime - lastKernelTime.dwHighDateTime;
    
    userDiff.LowPart = userTime.dwLowDateTime - lastUserTime.dwLowDateTime;
    userDiff.HighPart = userTime.dwHighDateTime - lastUserTime.dwHighDateTime;
    
    totalDiff.QuadPart = kernelDiff.QuadPart + userDiff.QuadPart;
    
    // 转换为毫秒
    DWORD tickDiff = currentTick - lastTickCount;
    
    // 计算CPU使用率
    float cpuUsage = 0.0f;
    if (tickDiff > 0) {
        cpuUsage = (float)(totalDiff.QuadPart / 10000.0) / (float)tickDiff * 100.0f;
    }
    
    // 更新最后时间
    lastKernelTime = kernelTime;
    lastUserTime = userTime;
    lastTickCount = currentTick;
    
    CloseHandle(hProc);
    return cpuUsage;
}

// 获取进程内存使用量(MB)
float GetProcessMemoryUsage(DWORD pid) {
    HANDLE hProc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (!hProc) return 0.0f;
    
    PROCESS_MEMORY_COUNTERS_EX pmc;
    pmc.cb = sizeof(pmc);
    
    if (GetProcessMemoryInfo(hProc, (PROCESS_MEMORY_COUNTERS*)&pmc, sizeof(pmc))) {
        CloseHandle(hProc);
        // 转换为MB
        return (float)pmc.PrivateUsage / (1024 * 1024);
    }
    
    CloseHandle(hProc);
    return 0.0f;
}

// 发送数据到管道
void SendToPipe(const std::string& data) {
    if (hPipe == INVALID_HANDLE_VALUE) {
        hPipe = CreateFileA("\\\\.\\pipe\\ActivityAnalytics",
            GENERIC_WRITE, 0, nullptr, OPEN_EXISTING, 0, nullptr);
    }
    
    if (hPipe != INVALID_HANDLE_VALUE) {
        DWORD bytesWritten;
        WriteFile(hPipe, data.c_str(), (DWORD)data.size(), &bytesWritten, nullptr);
        
        // 写入换行符作为分隔符
        const char newline = '\n';
        WriteFile(hPipe, &newline, 1, &bytesWritten, nullptr);
    } else {
        // 管道连接失败，下次重试
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
}

// 获取活动窗口信息
std::string GetActiveWindowInfo() {
    HWND hWnd = GetForegroundWindow();
    if (!hWnd) return "{}";
    
    DWORD pid;
    GetWindowThreadProcessId(hWnd, &pid);
    
    // 获取窗口标题
    char title[256] = { 0 };
    GetWindowTextA(hWnd, title, sizeof(title));
    
    // 获取进程路径
    char exePath[MAX_PATH] = { 0 };
    HANDLE hProc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
    if (hProc) {
        GetModuleFileNameExA(hProc, nullptr, exePath, MAX_PATH);
        CloseHandle(hProc);
    }
    
    // 获取系统信息
    float cpuUsage = GetProcessCpuUsage(pid);
    float memUsage = GetProcessMemoryUsage(pid);
    
    // 获取输入事件计数
    DWORD currentKeyboard = 0, currentMouse = 0;
    UpdateInputCounters(currentKeyboard, currentMouse);
    
    DWORD kbEvents = currentKeyboard - lastKeyboardEvents;
    DWORD mouseEvents = currentMouse - lastMouseEvents;
    
    lastKeyboardEvents = currentKeyboard;
    lastMouseEvents = currentMouse;
    
    // 获取音量
    AudioMeter audioMeter;
    float volume = audioMeter.GetMasterVolume();
    
    // 构建JSON
    std::stringstream ss;
    ss << "{"
       << "\"pid\":" << pid << ","
       << "\"title\":\"" << title << "\","
       << "\"exe\":\"" << exePath << "\","
       << "\"cpu\":" << std::fixed << std::setprecision(1) << cpuUsage << ","
       << "\"mem\":" << std::fixed << std::setprecision(1) << memUsage << ","
       << "\"kb\":" << kbEvents << ","
       << "\"mouse\":" << mouseEvents << ","
       << "\"dB\":" << std::fixed << std::setprecision(1) << volume
       << "}";
    
    return ss.str();
}

// 处理控制台关闭事件
BOOL WINAPI ConsoleCtrlHandler(DWORD ctrlType) {
    if (ctrlType == CTRL_CLOSE_EVENT || ctrlType == CTRL_C_EVENT) {
        isRunning = false;
        return TRUE;
    }
    return FALSE;
}

int main() {
    // 设置控制台关闭处理
    SetConsoleCtrlHandler(ConsoleCtrlHandler, TRUE);
    
    std::cout << "Activity Monitor started. Press Ctrl+C to exit." << std::endl;
    
    // 主循环
    while (isRunning) {
        std::string data = GetActiveWindowInfo();
        SendToPipe(data);
        
        // 每秒采集一次
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    
    // 清理
    if (hPipe != INVALID_HANDLE_VALUE) {
        CloseHandle(hPipe);
    }
    
    std::cout << "Activity Monitor stopped." << std::endl;
    return 0;
}

#include <windows.h>
#include <psapi.h>
#include <tlhelp32.h>
#include <mmdeviceapi.h>
#include <endpointvolume.h>
#include <audioclient.h>
#include <mmsystem.h>
#include <string>
#include <sstream>
#include <iomanip>
#include <locale>
#include <chrono>
#include <thread>
#include <iostream>
#include "monitor_hook.hpp"

#pragma comment(lib, "winmm.lib")
#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "ole32.lib")

HANDLE hPipe = INVALID_HANDLE_VALUE;
bool   isRunning = true;
std::chrono::steady_clock::time_point lastPipeAttempt;

/* ---------- 工具 ---------- */
static std::string escapeJson(const std::string& s)
{
	std::string r;
	r.reserve(s.size() + 10);
	for (unsigned char c : s) {
		switch (c) {
			case '\"': r += "\\\""; break;
			case '\\': r += "\\\\"; break;
			case '\b': r += "\\b";  break;
			case '\f': r += "\\f";  break;
			case '\n': r += "\\n";  break;
			case '\r': r += "\\r";  break;
			case '\t': r += "\\t";  break;
		default:
			if (c < 0x20) { char b[8]; sprintf(b, "\\u%04x", c); r += b; }
			else          { r += c; }
		}
	}
	return r;
}

/* ---------- 麦克风峰值 ---------- */
class MicMeter {
public:
	MicMeter() {
		CoInitialize(nullptr);
		CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_INPROC_SERVER,
			__uuidof(IMMDeviceEnumerator), (void**)&pEnumerator);
		if (pEnumerator)
			pEnumerator->GetDefaultAudioEndpoint(eCapture, eConsole, &pDevice);
		if (pDevice)
			pDevice->Activate(__uuidof(IAudioMeterInformation), CLSCTX_INPROC_SERVER,
				nullptr, (void**)&pMeter);
	}
	~MicMeter() {
		if (pMeter)      pMeter->Release();
		if (pDevice)     pDevice->Release();
		if (pEnumerator) pEnumerator->Release();
		CoUninitialize();
	}
	float GetPeakDb() {
		float peak = 0.0f;
		if (pMeter) pMeter->GetPeakValue(&peak);
		return 20.0f * log10f(peak + 1e-5f);
	}
private:
	IMMDeviceEnumerator*    pEnumerator = nullptr;
	IMMDevice*              pDevice     = nullptr;
	IAudioMeterInformation* pMeter      = nullptr;
};

/* ---------- 整机 CPU ---------- */
static float GetSystemCpu()
{
	static ULARGE_INTEGER lastIdle{}, lastKernel{}, lastUser{};
	ULARGE_INTEGER idle, kernel, user;
	if (!GetSystemTimes((PFILETIME)&idle, (PFILETIME)&kernel, (PFILETIME)&user))
		return 0.0f;
	if (lastIdle.QuadPart == 0) {
		lastIdle = idle; lastKernel = kernel; lastUser = user;
		return 0.0f;
	}
	auto idleDiff   = idle.QuadPart   - lastIdle.QuadPart;
	auto kernelDiff = kernel.QuadPart - lastKernel.QuadPart;
	auto userDiff   = user.QuadPart   - lastUser.QuadPart;
	lastIdle = idle; lastKernel = kernel; lastUser = user;
	auto sysDiff = kernelDiff + userDiff;
	return sysDiff == 0 ? 0.0f :
	100.0f * (1.0 - (double)idleDiff / sysDiff);
}

/* ---------- 整机内存 % ---------- */
static float GetSystemMem()
{
	MEMORYSTATUSEX ms{ sizeof(ms) };
	GlobalMemoryStatusEx(&ms);
	return 100.0f * (1.0 - (double)ms.ullAvailPhys / ms.ullTotalPhys);
}

/* ---------- 进程私有内存 ---------- */
static float GetProcessMem(DWORD pid)
{
	HANDLE hProc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
	if (!hProc) return 0.0f;
	PROCESS_MEMORY_COUNTERS_EX pmc{ sizeof(pmc) };
	float mem = 0.0f;
	if (GetProcessMemoryInfo(hProc, (PROCESS_MEMORY_COUNTERS*)&pmc, sizeof(pmc)))
		mem = (float)pmc.PrivateUsage / (1024.0f * 1024.0f);
	CloseHandle(hProc);
	return mem;
}

/* ---------- 管道发送 ---------- */
void SendToPipe(const std::string& data)
{
	auto now = std::chrono::steady_clock::now();
	if (hPipe == INVALID_HANDLE_VALUE &&
		now - lastPipeAttempt < std::chrono::seconds(5))
		return;
	lastPipeAttempt = now;
	
	hPipe = CreateFileA("\\\\.\\pipe\\ActivityAnalytics",
		GENERIC_WRITE, 0, nullptr, OPEN_EXISTING,
		FILE_FLAG_OVERLAPPED, nullptr);
	if (hPipe == INVALID_HANDLE_VALUE) return;
	
	std::string line = data + '\n';
	DWORD bw = 0;
	OVERLAPPED ov{};
	ov.hEvent = CreateEvent(nullptr, TRUE, FALSE, nullptr);
	WriteFile(hPipe, line.data(), (DWORD)line.size(), &bw, &ov);
	CloseHandle(ov.hEvent);
}

/* ---------- 拼 JSON ---------- */
std::string GetActiveWindowInfo()
{
	HWND hWnd = GetForegroundWindow();
	if (!hWnd) return "{}";
	DWORD pid = 0;
	GetWindowThreadProcessId(hWnd, &pid);
	
	WCHAR exePathW[MAX_PATH]{}, titleW[256]{};
	GetWindowTextW(hWnd, titleW, 256);
	char title[512]{};
	WideCharToMultiByte(CP_UTF8, 0, titleW, -1, title, sizeof(title), nullptr, nullptr);
	
	HANDLE hProc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, FALSE, pid);
	if (hProc) {
		GetModuleFileNameExW(hProc, nullptr, exePathW, MAX_PATH);
		CloseHandle(hProc);
	}
	char exePath[MAX_PATH]{};
	WideCharToMultiByte(CP_UTF8, 0, exePathW, -1, exePath, sizeof(exePath), nullptr, nullptr);
	
	static MicMeter mic;
	std::ostringstream ss;
	ss.imbue(std::locale("C"));
	ss << std::fixed << std::setprecision(1);
	ss << '{'
	<< "\"pid\":" << pid << ','
	<< "\"title\":\"" << escapeJson(title) << "\","
	<< "\"exe\":\""  << escapeJson(exePath) << "\","
	<< "\"cpu\":"  << GetSystemCpu()  << ','
	<< "\"mem\":"  << GetSystemMem()  << ','
	<< "\"pvtMB\":"<< GetProcessMem(pid) << ','
	<< "\"kb\":"   << InputHook::kb   << ','

	<< "\"dB\":"   << mic.GetPeakDb()
	<< '}';
	return ss.str();
}

/* ---------- 控制台信号 ---------- */
BOOL WINAPI Handler(DWORD ctrl)
{
	if (ctrl == CTRL_C_EVENT || ctrl == CTRL_CLOSE_EVENT) {
		isRunning = false;
		return TRUE;
	}
	return FALSE;
}

/* ---------- 后台消息泵 ---------- */
void MessagePumpWorker()
{
	while (isRunning) {
		MSG msg;
		while (PeekMessage(&msg, nullptr, 0, 0, PM_REMOVE)) {
			TranslateMessage(&msg);
			DispatchMessage(&msg);
		}
		std::this_thread::yield(); // 让出时间片，但不阻塞
	}
}

/* ---------- 入口 ---------- */
int main()
{
	InputHook::Install();
	SetConsoleCtrlHandler(Handler, TRUE);
	std::cout << "Monitor started. Ctrl-C to exit.\n";
	
	std::thread msgThread(MessagePumpWorker); 
	
	while (isRunning) {
		std::string json = GetActiveWindowInfo();
		std::cout << json << std::endl;
		SendToPipe(json);
		std::this_thread::sleep_for(std::chrono::milliseconds(1000)); 
	}
	
	msgThread.join(); 
	InputHook::Uninstall();
	if (hPipe != INVALID_HANDLE_VALUE) CloseHandle(hPipe);
	std::cout << "Monitor stopped.\n";
	return 0;
}

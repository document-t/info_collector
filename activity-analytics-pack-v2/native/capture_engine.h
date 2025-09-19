#pragma once

#include <windows.h>
#include <d3d11.h>
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <vector>
#include <string>
#include <memory>
#include <chrono>

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "mf.lib")
#pragma comment(lib, "mfplat.lib")
#pragma comment(lib, "mfreadwrite.lib")
#pragma comment(lib, "mfuuid.lib")

// 录屏配置
struct RecordingConfig {
    int fps = 30;
    int bitrate = 1000000; // 1 Mbps
    float quality = 0.8f;
    bool audioEnabled = true;
    int maxFileDurationMinutes = 10;
    std::wstring outputDirectory;
};

// 录屏引擎类
class CaptureEngine {
private:
    ID3D11Device* d3dDevice = nullptr;
    ID3D11DeviceContext* d3dContext = nullptr;
    IDXGIOutputDuplication* deskDupl = nullptr;
    DXGI_OUTDUPL_DESC deskDesc = {};
    
    // 媒体基础相关
    IMFMediaSink* pMediaSink = nullptr;
    IMFSinkWriter* pSinkWriter = nullptr;
    DWORD videoStreamIndex = MFVIDEO_FORMAT_H264;
    DWORD audioStreamIndex = 0;
    
    // 录屏状态
    bool isRecording = false;
    RecordingConfig config;
    std::wstring currentOutputFile;
    std::chrono::system_clock::time_point recordingStartTime;
    
    // 初始化D3D设备
    HRESULT InitD3D();
    
    // 初始化桌面复制
    HRESULT InitDesktopDuplication();
    
    // 初始化媒体基础
    HRESULT InitMediaFoundation();
    
    // 创建媒体接收器
    HRESULT CreateMediaSink(const std::wstring& filePath);
    
    // 初始化视频编码器
    HRESULT InitVideoEncoder();
    
    // 初始化音频捕获
    HRESULT InitAudioCapture();
    
    // 生成输出文件名
    std::wstring GenerateOutputFileName();
    
    // 检查是否需要分割文件
    bool NeedSplitFile();
    
    // 分割文件并开始新的录制
    HRESULT SplitRecording();

public:
    CaptureEngine(const RecordingConfig& config);
    ~CaptureEngine();
    
    // 开始录制
    HRESULT StartRecording();
    
    // 停止录制
    HRESULT StopRecording();
    
    // 捕获一帧并编码
    HRESULT CaptureFrame();
    
    // 获取录制状态
    bool IsRecording() const { return isRecording; }
};
    
#pragma once

#include <windows.h>
#include <winrt/Windows.AI.Ocr.h>
#include <winrt/Windows.Storage.Streams.h>
#include <winrt/Windows.Graphics.Imaging.h>
#include <string>
#include <memory>

using namespace winrt;
using namespace Windows::AI::Ocr;
using namespace Windows::Storage::Streams;
using namespace Windows::Graphics::Imaging;

// OCR配置
struct OcrConfig {
    std::wstring language = L"zh-CN";
    int intervalSec = 5;
    float cropRatio = 0.3f;
    bool enableAutoLanguage = false;
};

// OCR引擎类
class OcrEngine {
private:
    OcrConfig config;
    winrt::Windows::AI::Ocr::OcrEngine ocrEngine = nullptr;
    bool isInitialized = false;
    
    // 初始化OCR引擎
    HRESULT InitEngine();
    
    // 捕获窗口内容为SoftwareBitmap
    HRESULT CaptureWindowBitmap(HWND hwnd, SoftwareBitmap& softwareBitmap);
    
    // 裁剪图像
    SoftwareBitmap CropBitmap(const SoftwareBitmap& source);
    
    // 转换为UTF-8字符串
    std::string WstringToUtf8(const std::wstring& wstr);

public:
    OcrEngine(const OcrConfig& config);
    
    // 对指定窗口进行OCR识别
    HRESULT RecognizeWindow(HWND hwnd, std::string& resultText);
    
    // 获取配置
    const OcrConfig& GetConfig() const { return config; }
};
    
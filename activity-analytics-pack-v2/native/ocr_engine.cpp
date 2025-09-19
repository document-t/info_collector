#include "ocr_engine.h"
#include <d3d11.h>
#include <dxgi1_2.h>
#include <wincodec.h>
#include <string>
#include <vector>
#include <codecvt>
#include <locale>

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "windowscodecs.lib")

// 初始化OCR引擎
HRESULT OcrEngine::InitEngine() {
    if (isInitialized) return S_OK;
    
    try {
        if (config.enableAutoLanguage) {
            // 自动检测语言
            ocrEngine = winrt::Windows::AI::Ocr::OcrEngine::TryCreateFromUserProfileLanguages();
        } else {
            // 使用指定语言
            Language language(config.language);
            ocrEngine = winrt::Windows::AI::Ocr::OcrEngine::TryCreateFromLanguage(language);
        }
        
        isInitialized = ocrEngine != nullptr;
        return isInitialized ? S_OK : E_FAIL;
    } catch (...) {
        return E_FAIL;
    }
}

// 捕获窗口内容为SoftwareBitmap
HRESULT OcrEngine::CaptureWindowBitmap(HWND hwnd, SoftwareBitmap& softwareBitmap) {
    HRESULT hr = S_OK;
    
    // 获取窗口客户区矩形
    RECT rcClient;
    if (!GetClientRect(hwnd, &rcClient)) return E_FAIL;
    
    // 获取窗口DC
    HDC hdcWindow = GetDC(hwnd);
    if (!hdcWindow) return E_FAIL;
    
    // 创建兼容DC
    HDC hdcMem = CreateCompatibleDC(hdcWindow);
    if (!hdcMem) {
        ReleaseDC(hwnd, hdcWindow);
        return E_FAIL;
    }
    
    // 创建位图
    int width = rcClient.right - rcClient.left;
    int height = rcClient.bottom - rcClient.top;
    
    HBITMAP hbmScreen = CreateCompatibleBitmap(hdcWindow, width, height);
    if (!hbmScreen) {
        DeleteDC(hdcMem);
        ReleaseDC(hwnd, hdcWindow);
        return E_FAIL;
    }
    
    // 选择位图到DC
    HGDIOBJ hOld = SelectObject(hdcMem, hbmScreen);
    
    // 复制窗口内容
    BitBlt(hdcMem, 0, 0, width, height, hdcWindow, 0, 0, SRCCOPY);
    
    // 获取位图信息
    BITMAPINFOHEADER bmpInfoHeader = {0};
    bmpInfoHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmpInfoHeader.biWidth = width;
    bmpInfoHeader.biHeight = -height; // 负值表示从上到下
    bmpInfoHeader.biPlanes = 1;
    bmpInfoHeader.biBitCount = 32;
    bmpInfoHeader.biCompression = BI_RGB;
    
    // 分配内存并获取位图数据
    std::vector<BYTE> pixelData(width * height * 4);
    GetDIBits(hdcMem, hbmScreen, 0, height, pixelData.data(), 
              reinterpret_cast<BITMAPINFO*>(&bmpInfoHeader), DIB_RGB_COLORS);
    
    // 释放GDI资源
    SelectObject(hdcMem, hOld);
    DeleteObject(hbmScreen);
    DeleteDC(hdcMem);
    ReleaseDC(hwnd, hdcWindow);
    
    // 创建SoftwareBitmap
    try {
        softwareBitmap = SoftwareBitmap::CreateCopyFromBuffer(
            Windows::Storage::Streams::Buffer(pixelData),
            BitmapPixelFormat::Bgra8,
            width,
            height
        );
        
        // 转换为灰度图以提高OCR准确性
        if (softwareBitmap.BitmapPixelFormat() != BitmapPixelFormat::Gray8) {
            auto converted = SoftwareBitmap::Convert(
                softwareBitmap, 
                BitmapPixelFormat::Gray8
            );
            softwareBitmap = converted;
        }
    } catch (...) {
        return E_FAIL;
    }
    
    return S_OK;
}

// 裁剪图像
SoftwareBitmap OcrEngine::CropBitmap(const SoftwareBitmap& source) {
    int originalWidth = source.PixelWidth();
    int originalHeight = source.PixelHeight();
    
    // 计算裁剪区域（上半部分）
    int cropHeight = static_cast<int>(originalHeight * config.cropRatio);
    
    // 创建裁剪后的位图
    SoftwareBitmap cropped(
        source.BitmapPixelFormat(),
        originalWidth,
        cropHeight
    );
    
    // 复制像素数据
    auto sourceBuffer = source.LockBuffer(BitmapBufferAccessMode::Read);
    auto croppedBuffer = cropped.LockBuffer(BitmapBufferAccessMode::Write);
    
    auto sourceReference = sourceBuffer.CreateReference();
    auto croppedReference = croppedBuffer.CreateReference();
    
    BYTE* sourceData = nullptr;
    UINT32 sourceCapacity = 0;
    COMPointer<IBufferByteAccess> sourceByteAccess;
    sourceReference.as(sourceByteAccess);
    sourceByteAccess->Buffer(&sourceData, &sourceCapacity);
    
    BYTE* croppedData = nullptr;
    UINT32 croppedCapacity = 0;
    COMPointer<IBufferByteAccess> croppedByteAccess;
    croppedReference.as(croppedByteAccess);
    croppedByteAccess->Buffer(&croppedData, &croppedCapacity);
    
    // 计算每行字节数
    int bytesPerPixel = 1; // 假设是灰度图
    if (source.BitmapPixelFormat() == BitmapPixelFormat::Bgra8) {
        bytesPerPixel = 4;
    }
    
    int rowPitch = originalWidth * bytesPerPixel;
    
    // 复制裁剪区域数据
    for (int y = 0; y < cropHeight; y++) {
        memcpy(
            croppedData + y * rowPitch,
            sourceData + y * rowPitch,
            rowPitch
        );
    }
    
    return cropped;
}

// 转换为UTF-8字符串
std::string OcrEngine::WstringToUtf8(const std::wstring& wstr) {
    std::wstring_convert<std::codecvt_utf8<wchar_t>> converter;
    return converter.to_bytes(wstr);
}

// 构造函数
OcrEngine::OcrEngine(const OcrConfig& config) : config(config) {
    InitEngine();
}

// 对指定窗口进行OCR识别
HRESULT OcrEngine::RecognizeWindow(HWND hwnd, std::string& resultText) {
    if (!isInitialized) {
        if (FAILED(InitEngine())) {
            resultText = "OCR引擎初始化失败";
            return E_FAIL;
        }
    }
    
    // 捕获窗口图像
    SoftwareBitmap softwareBitmap;
    HRESULT hr = CaptureWindowBitmap(hwnd, softwareBitmap);
    if (FAILED(hr)) {
        resultText = "窗口捕获失败";
        return hr;
    }
    
    // 裁剪图像
    SoftwareBitmap croppedBitmap = CropBitmap(softwareBitmap);
    
    try {
        // 执行OCR识别
        auto ocrResult = ocrEngine.RecognizeAsync(croppedBitmap).get();
        
        // 获取识别结果
        resultText = WstringToUtf8(ocrResult.Text());
        
        // 替换引号以避免JSON格式问题
        size_t pos = 0;
        while ((pos = resultText.find('"', pos)) != std::string::npos) {
            resultText.replace(pos, 1, "\\\"");
            pos += 2;
        }
        
        return S_OK;
    } catch (...) {
        resultText = "OCR识别失败";
        return E_FAIL;
    }
}
    
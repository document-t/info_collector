#include "capture_engine.h"
#include <dxgi1_2.h>
#include <mfapi.h>
#include <mferror.h>
#include <shlwapi.h>
#include <sstream>
#include <iomanip>

#pragma comment(lib, "shlwapi.lib")

// 初始化D3D设备
HRESULT CaptureEngine::InitD3D() {
    HRESULT hr = S_OK;
    
    // 创建D3D设备
    D3D_FEATURE_LEVEL featureLevel;
    hr = D3D11CreateDevice(
        nullptr,
        D3D_DRIVER_TYPE_HARDWARE,
        nullptr,
        0,
        nullptr,
        0,
        D3D11_SDK_VERSION,
        &d3dDevice,
        &featureLevel,
        &d3dContext
    );
    
    if (FAILED(hr)) {
        // 如果硬件设备创建失败，尝试使用WARP软件设备
        hr = D3D11CreateDevice(
            nullptr,
            D3D_DRIVER_TYPE_WARP,
            nullptr,
            0,
            nullptr,
            0,
            D3D11_SDK_VERSION,
            &d3dDevice,
            &featureLevel,
            &d3dContext
        );
    }
    
    return hr;
}

// 初始化桌面复制
HRESULT CaptureEngine::InitDesktopDuplication() {
    HRESULT hr = S_OK;
    
    IDXGIDevice* dxgiDevice = nullptr;
    hr = d3dDevice->QueryInterface(__uuidof(IDXGIDevice), reinterpret_cast<void**>(&dxgiDevice));
    if (FAILED(hr)) return hr;
    
    IDXGIAdapter* dxgiAdapter = nullptr;
    hr = dxgiDevice->GetParent(__uuidof(IDXGIAdapter), reinterpret_cast<void**>(&dxgiAdapter));
    dxgiDevice->Release();
    if (FAILED(hr)) return hr;
    
    IDXGIOutput* dxgiOutput = nullptr;
    hr = dxgiAdapter->EnumOutputs(0, &dxgiOutput);
    dxgiAdapter->Release();
    if (FAILED(hr)) return hr;
    
    IDXGIOutput1* dxgiOutput1 = nullptr;
    hr = dxgiOutput->QueryInterface(__uuidof(IDXGIOutput1), reinterpret_cast<void**>(&dxgiOutput1));
    dxgiOutput->Release();
    if (FAILED(hr)) return hr;
    
    // 复制桌面
    hr = dxgiOutput1->DuplicateOutput(d3dDevice, &deskDupl);
    if (FAILED(hr)) {
        dxgiOutput1->Release();
        return hr;
    }
    
    // 获取桌面描述
    deskDupl->GetDesc(&deskDesc);
    dxgiOutput1->Release();
    
    return hr;
}

// 初始化媒体基础
HRESULT CaptureEngine::InitMediaFoundation() {
    return MFStartup(MF_VERSION);
}

// 创建媒体接收器
HRESULT CaptureEngine::CreateMediaSink(const std::wstring& filePath) {
    HRESULT hr = S_OK;
    
    // 创建文件接收器
    IMFByteStream* pByteStream = nullptr;
    hr = MFCreateFile(
        MF_ACCESSMODE_WRITE,
        MF_OPENMODE_CREATE_ALWAYS,
        MF_FILEFLAGS_NONE,
        filePath.c_str(),
        &pByteStream
    );
    if (FAILED(hr)) return hr;
    
    // 创建媒体接收器
    hr = MFCreateSinkWriterFromByteStream(pByteStream, nullptr, nullptr, &pSinkWriter);
    pByteStream->Release();
    
    return hr;
}

// 初始化视频编码器
HRESULT CaptureEngine::InitVideoEncoder() {
    HRESULT hr = S_OK;
    
    // 设置视频输出格式
    IMFMediaType* pVideoMediaTypeOut = nullptr;
    hr = MFCreateMediaType(&pVideoMediaTypeOut);
    if (FAILED(hr)) return hr;
    
    hr = pVideoMediaTypeOut->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Video);
    if (FAILED(hr)) goto done;
    
    hr = pVideoMediaTypeOut->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_H264);
    if (FAILED(hr)) goto done;
    
    hr = pVideoMediaTypeOut->SetUINT32(MF_MT_AVG_BITRATE, config.bitrate);
    if (FAILED(hr)) goto done;
    
    hr = pVideoMediaTypeOut->SetUINT32(MF_MT_INTERLACE_MODE, MFVideoInterlace_Progressive);
    if (FAILED(hr)) goto done;
    
    hr = MFSetAttributeSize(pVideoMediaTypeOut, MF_MT_FRAME_SIZE, deskDesc.ModeDesc.Width, deskDesc.ModeDesc.Height);
    if (FAILED(hr)) goto done;
    
    hr = MFSetAttributeRatio(pVideoMediaTypeOut, MF_MT_FRAME_RATE, config.fps, 1);
    if (FAILED(hr)) goto done;
    
    hr = MFSetAttributeRatio(pVideoMediaTypeOut, MF_MT_PIXEL_ASPECT_RATIO, 1, 1);
    if (FAILED(hr)) goto done;
    
    // 设置输入格式
    IMFMediaType* pVideoMediaTypeIn = nullptr;
    hr = MFCreateMediaType(&pVideoMediaTypeIn);
    if (FAILED(hr)) goto done;
    
    hr = pVideoMediaTypeIn->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Video);
    if (FAILED(hr)) goto done;
    
    hr = pVideoMediaTypeIn->SetGUID(MF_MT_SUBTYPE, MFVideoFormat_ARGB32);
    if (FAILED(hr)) goto done;
    
    hr = pVideoMediaTypeIn->SetUINT32(MF_MT_INTERLACE_MODE, MFVideoInterlace_Progressive);
    if (FAILED(hr)) goto done;
    
    hr = MFSetAttributeSize(pVideoMediaTypeIn, MF_MT_FRAME_SIZE, deskDesc.ModeDesc.Width, deskDesc.ModeDesc.Height);
    if (FAILED(hr)) goto done;
    
    hr = MFSetAttributeRatio(pVideoMediaTypeIn, MF_MT_FRAME_RATE, config.fps, 1);
    if (FAILED(hr)) goto done;
    
    hr = MFSetAttributeRatio(pVideoMediaTypeIn, MF_MT_PIXEL_ASPECT_RATIO, 1, 1);
    if (FAILED(hr)) goto done;
    
    // 添加视频流
    hr = pSinkWriter->AddStream(pVideoMediaTypeOut, &videoStreamIndex);
    if (FAILED(hr)) goto done;
    
    // 设置输入格式
    hr = pSinkWriter->SetInputMediaType(videoStreamIndex, pVideoMediaTypeIn, nullptr);
    if (FAILED(hr)) goto done;
    
    // 开始编写
    hr = pSinkWriter->BeginWriting();
    
done:
    if (pVideoMediaTypeOut) pVideoMediaTypeOut->Release();
    if (pVideoMediaTypeIn) pVideoMediaTypeIn->Release();
    return hr;
}

// 初始化音频捕获
HRESULT CaptureEngine::InitAudioCapture() {
    // 如果不启用音频，直接返回成功
    if (!config.audioEnabled) return S_OK;
    
    HRESULT hr = S_OK;
    
    // 设置音频输出格式
    IMFMediaType* pAudioMediaTypeOut = nullptr;
    hr = MFCreateMediaType(&pAudioMediaTypeOut);
    if (FAILED(hr)) return hr;
    
    hr = pAudioMediaTypeOut->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio);
    if (FAILED(hr)) goto done;
    
    hr = pAudioMediaTypeOut->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_AAC);
    if (FAILED(hr)) goto done;
    
    hr = pAudioMediaTypeOut->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND, 44100);
    if (FAILED(hr)) goto done;
    
    hr = pAudioMediaTypeOut->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS, 2);
    if (FAILED(hr)) goto done;
    
    hr = pAudioMediaTypeOut->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE, 16);
    if (FAILED(hr)) goto done;
    
    // 设置输入格式
    IMFMediaType* pAudioMediaTypeIn = nullptr;
    hr = MFCreateMediaType(&pAudioMediaTypeIn);
    if (FAILED(hr)) goto done;
    
    hr = pAudioMediaTypeIn->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio);
    if (FAILED(hr)) goto done;
    
    hr = pAudioMediaTypeIn->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_PCM);
    if (FAILED(hr)) goto done;
    
    hr = pAudioMediaTypeIn->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND, 44100);
    if (FAILED(hr)) goto done;
    
    hr = pAudioMediaTypeIn->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS, 2);
    if (FAILED(hr)) goto done;
    
    hr = pAudioMediaTypeIn->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE, 16);
    if (FAILED(hr)) goto done;
    
    // 计算块对齐
    UINT32 blockAlign = 2 * 2; // 2 channels * 2 bytes per sample
    hr = pAudioMediaTypeIn->SetUINT32(MF_MT_AUDIO_BLOCK_ALIGNMENT, blockAlign);
    if (FAILED(hr)) goto done;
    
    // 计算比特率
    UINT32 bitRate = 44100 * blockAlign * 8;
    hr = pAudioMediaTypeIn->SetUINT32(MF_MT_AVG_BITRATE, bitRate);
    if (FAILED(hr)) goto done;
    
    // 添加音频流
    hr = pSinkWriter->AddStream(pAudioMediaTypeOut, &audioStreamIndex);
    if (FAILED(hr)) goto done;
    
    // 设置输入格式
    hr = pSinkWriter->SetInputMediaType(audioStreamIndex, pAudioMediaTypeIn, nullptr);
    
done:
    if (pAudioMediaTypeOut) pAudioMediaTypeOut->Release();
    if (pAudioMediaTypeIn) pAudioMediaTypeIn->Release();
    return hr;
}

// 生成输出文件名
std::wstring CaptureEngine::GenerateOutputFileName() {
    // 创建目录（如果不存在）
    if (!PathIsDirectoryW(config.outputDirectory.c_str())) {
        CreateDirectoryW(config.outputDirectory.c_str(), nullptr);
    }
    
    // 生成带时间戳的文件名
    auto now = std::chrono::system_clock::now();
    std::time_t now_time = std::chrono::system_clock::to_time_t(now);
    struct tm timeinfo;
    localtime_s(&timeinfo, &now_time);
    
    std::wstringstream wss;
    wss << config.outputDirectory << L"/screen_";
    wss << std::put_time(&timeinfo, L"%Y%m%d_%H%M%S") << L".mp4";
    
    return wss.str();
}

// 检查是否需要分割文件
bool CaptureEngine::NeedSplitFile() {
    auto now = std::chrono::system_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::minutes>(now - recordingStartTime);
    return duration.count() >= config.maxFileDurationMinutes;
}

// 分割文件并开始新的录制
HRESULT CaptureEngine::SplitRecording() {
    // 停止当前录制
    HRESULT hr = pSinkWriter->Finalize();
    if (FAILED(hr)) return hr;
    
    // 释放当前资源
    if (pSinkWriter) {
        pSinkWriter->Release();
        pSinkWriter = nullptr;
    }
    
    // 创建新文件
    currentOutputFile = GenerateOutputFileName();
    hr = CreateMediaSink(currentOutputFile);
    if (FAILED(hr)) return hr;
    
    // 重新初始化编码器
    hr = InitVideoEncoder();
    if (FAILED(hr)) return hr;
    
    if (config.audioEnabled) {
        hr = InitAudioCapture();
        if (FAILED(hr)) return hr;
    }
    
    // 更新录制开始时间
    recordingStartTime = std::chrono::system_clock::now();
    
    return S_OK;
}

// 构造函数
CaptureEngine::CaptureEngine(const RecordingConfig& config) : config(config) {
    // 初始化组件
    InitD3D();
    InitDesktopDuplication();
    InitMediaFoundation();
}

// 析构函数
CaptureEngine::~CaptureEngine() {
    StopRecording();
    
    // 释放资源
    if (deskDupl) deskDupl->Release();
    if (d3dContext) d3dContext->Release();
    if (d3dDevice) d3dDevice->Release();
    if (pSinkWriter) pSinkWriter->Release();
    
    MFShutdown();
}

// 开始录制
HRESULT CaptureEngine::StartRecording() {
    if (isRecording) return S_OK;
    
    // 生成输出文件名
    currentOutputFile = GenerateOutputFileName();
    
    // 创建媒体接收器
    HRESULT hr = CreateMediaSink(currentOutputFile);
    if (FAILED(hr)) return hr;
    
    // 初始化编码器
    hr = InitVideoEncoder();
    if (FAILED(hr)) return hr;
    
    if (config.audioEnabled) {
        hr = InitAudioCapture();
        if (FAILED(hr)) return hr;
    }
    
    // 记录开始时间
    recordingStartTime = std::chrono::system_clock::now();
    
    isRecording = true;
    return S_OK;
}

// 停止录制
HRESULT CaptureEngine::StopRecording() {
    if (!isRecording) return S_OK;
    
    HRESULT hr = S_OK;
    
    if (pSinkWriter) {
        hr = pSinkWriter->Finalize();
        pSinkWriter->Release();
        pSinkWriter = nullptr;
    }
    
    isRecording = false;
    return hr;
}

// 捕获一帧并编码
HRESULT CaptureEngine::CaptureFrame() {
    if (!isRecording) return E_FAIL;
    
    // 检查是否需要分割文件
    if (NeedSplitFile()) {
        HRESULT hr = SplitRecording();
        if (FAILED(hr)) return hr;
    }
    
    HRESULT hr = S_OK;
    IDXGIResource* desktopResource = nullptr;
    DXGI_OUTDUPL_FRAME_INFO frameInfo;
    
    // 获取下一帧
    hr = deskDupl->AcquireNextFrame(500, &frameInfo, &desktopResource);
    if (hr == DXGI_ERROR_WAIT_TIMEOUT) {
        // 超时，没有新帧
        return S_OK;
    }
    if (FAILED(hr)) return hr;
    
    // 获取桌面纹理
    ID3D11Texture2D* desktopTexture = nullptr;
    hr = desktopResource->QueryInterface(__uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&desktopTexture));
    desktopResource->Release();
    if (FAILED(hr)) return hr;
    
    // 创建用于编码的纹理
    D3D11_TEXTURE2D_DESC textureDesc;
    desktopTexture->GetDesc(&textureDesc);
    textureDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    textureDesc.Usage = D3D11_USAGE_STAGING;
    textureDesc.BindFlags = 0;
    textureDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    textureDesc.MiscFlags = 0;
    
    ID3D11Texture2D* stagingTexture = nullptr;
    hr = d3dDevice->CreateTexture2D(&textureDesc, nullptr, &stagingTexture);
    if (FAILED(hr)) {
        desktopTexture->Release();
        return hr;
    }
    
    // 复制纹理
    d3dContext->CopyResource(stagingTexture, desktopTexture);
    desktopTexture->Release();
    
    // 映射纹理
    D3D11_MAPPED_SUBRESOURCE mappedResource;
    hr = d3dContext->Map(stagingTexture, 0, D3D11_MAP_READ, 0, &mappedResource);
    if (FAILED(hr)) {
        stagingTexture->Release();
        return hr;
    }
    
    // 创建媒体示例
    IMFSample* pSample = nullptr;
    hr = MFCreateSample(&pSample);
    if (FAILED(hr)) goto done;
    
    IMFMediaBuffer* pBuffer = nullptr;
    hr = MFCreateMemoryBuffer(textureDesc.Width * textureDesc.Height * 4, &pBuffer);
    if (FAILED(hr)) goto done;
    
    // 锁定缓冲区并复制数据
    BYTE* pBufferData = nullptr;
    DWORD bufferMaxLength = 0, bufferCurrentLength = 0;
    hr = pBuffer->Lock(&pBufferData, &bufferMaxLength, &bufferCurrentLength);
    if (FAILED(hr)) goto done;
    
    // 复制图像数据（注意行对齐）
    BYTE* pSource = reinterpret_cast<BYTE*>(mappedResource.pData);
    BYTE* pDest = pBufferData;
    
    for (UINT y = 0; y < textureDesc.Height; y++) {
        memcpy(pDest, pSource, textureDesc.Width * 4);
        pSource += mappedResource.RowPitch;
        pDest += textureDesc.Width * 4;
    }
    
    // 解锁缓冲区
    hr = pBuffer->Unlock();
    if (FAILED(hr)) goto done;
    
    hr = pBuffer->SetCurrentLength(textureDesc.Width * textureDesc.Height * 4);
    if (FAILED(hr)) goto done;
    
    // 将缓冲区添加到示例
    hr = pSample->AddBuffer(pBuffer);
    if (FAILED(hr)) goto done;
    
    // 设置时间戳
    LONGLONG hnsTime = MFGetSystemTime();
    hr = pSample->SetSampleTime(hnsTime);
    if (FAILED(hr)) goto done;
    
    // 计算帧持续时间 (100ns单位)
    LONGLONG hnsDuration = 10000000 / config.fps; // 1秒 = 10,000,000 100ns单位
    hr = pSample->SetSampleDuration(hnsDuration);
    if (FAILED(hr)) goto done;
    
    // 写入视频帧
    hr = pSinkWriter->WriteSample(videoStreamIndex, pSample);
    
done:
    // 释放资源
    if (pSample) pSample->Release();
    if (pBuffer) pBuffer->Release();
    d3dContext->Unmap(stagingTexture, 0);
    stagingTexture->Release();
    
    // 释放帧
    deskDupl->ReleaseFrame();
    
    return hr;
}
    
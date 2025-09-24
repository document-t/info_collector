#pragma once
#include <windows.h>
#include <atomic>

class InputHook {
public:
    static std::atomic<DWORD> kb;
    static HHOOK kbHook;
    static void Install();
    static void Uninstall();
private:
    static LRESULT CALLBACK KBProc(int, WPARAM, LPARAM);
};
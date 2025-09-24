
#include "monitor_hook.hpp"
#include <atomic>

std::atomic<DWORD> InputHook::kb{0};
HHOOK InputHook::kbHook = nullptr;

void InputHook::Install() {
    kbHook = SetWindowsHookExW(WH_KEYBOARD_LL, KBProc, GetModuleHandleW(nullptr), 0);
}

void InputHook::Uninstall() {
    if (kbHook) UnhookWindowsHookEx(kbHook);
}

LRESULT CALLBACK InputHook::KBProc(int n, WPARAM w, LPARAM l) {
    if (n == HC_ACTION && (w == WM_KEYDOWN || w == WM_SYSKEYDOWN)) ++kb;
    return CallNextHookEx(kbHook, n, w, l);
}

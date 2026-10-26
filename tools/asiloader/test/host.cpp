// Test host, built as MassEffect2.exe: loads bink2w64.dll (the loader) like the game does, opens a window, and waits
// for test.asi to report. Exit code 0 means every check passed. Run by test\run_test.ps1.
#include <windows.h>

#include <cstdio>
#include <cstring>

extern "C" __declspec(dllexport) __declspec(noinline) int Target(int a, int b)
{
    volatile int sum = 0;
    for (int i = 0; i < b; ++i)
        sum += a;
    return sum;
}

// Hand-written code the plugin hooks: RipLoad = mov rax,[rip+data]; add rax,1; ret.
// ShortJump = jmp +3; nop x3; mov eax,7; ret.
extern "C" __declspec(dllexport) void* g_ripLoad = nullptr;
extern "C" __declspec(dllexport) void* g_shortJump = nullptr;
extern "C" __declspec(dllexport) volatile int g_done = 0;
extern "C" __declspec(dllexport) volatile int g_failures = -1;

int main()
{
    auto* code = static_cast<unsigned char*>(VirtualAlloc(nullptr, 4096, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE));
    const unsigned char rip[] = {0x48, 0x8B, 0x05, 0x00, 0x00, 0x00, 0x00, 0x48, 0x83, 0xC0, 0x01, 0xC3};
    std::memcpy(code, rip, sizeof(rip));
    *reinterpret_cast<long long*>(code + 256) = 41;
    const int disp = 256 - 7;
    std::memcpy(code + 3, &disp, 4);
    const unsigned char jump[] = {0xEB, 0x03, 0x90, 0x90, 0x90, 0xB8, 0x07, 0x00, 0x00, 0x00, 0xC3};
    std::memcpy(code + 64, jump, sizeof(jump));
    g_ripLoad = code;
    g_shortJump = code + 64;

    if (!LoadLibraryW(L"bink2w64.dll"))
    {
        std::printf("could not load bink2w64.dll (%lu)\n", GetLastError());
        return 2;
    }
    CreateWindowExW(0, L"STATIC", L"loader test", WS_OVERLAPPEDWINDOW, 0, 0, 100, 100, nullptr, nullptr, nullptr, nullptr);
    for (int i = 0; i < 400 && !g_done; ++i)
    {
        MSG msg;
        while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE))
            DispatchMessageW(&msg);
        Target(1, 1);  // keep a caller busy in another thread's view while the hook goes in
        Sleep(25);
    }
    std::printf("done=%d failures=%d\n", g_done, g_failures);
    return g_done && g_failures == 0 ? 0 : 1;
}

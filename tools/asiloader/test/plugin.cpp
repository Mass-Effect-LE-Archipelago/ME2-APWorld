// Test SPI plugin (test.asi): checks the loader's SPI calls against the test host and reports through its exports.
#include <windows.h>

#include <cstdio>

enum class SPIReturn : short { Success = 1 };
enum class SPIGameVersion { Launcher, LE1, LE2, LE3 };
class ISharedProxyInterface
{
public:
    virtual SPIReturn GetVersion(unsigned long*) = 0;
    virtual SPIReturn GetBuildMode(bool*) = 0;
    virtual SPIReturn GetHostGame(SPIGameVersion*) = 0;
    virtual SPIReturn FindPattern(void**, char*) = 0;
    virtual SPIReturn InstallHook(const char*, void*, void*, void**) = 0;
    virtual SPIReturn UninstallHook(const char*) = 0;
};

using TargetFn = int (*)(int, int);
using NoArgFn = long long (*)();
static TargetFn g_targetOrig;
static NoArgFn g_ripOrig, g_jumpOrig;
static int HookTarget(int a, int b) { return g_targetOrig(a, b) + 1000; }
static long long HookRip() { return g_ripOrig() + 100; }
static long long HookJump() { return g_jumpOrig() + 100; }

extern "C" __declspec(dllexport) void SpiSupportDecl(wchar_t** name, wchar_t** author, wchar_t** version, int* games, int* minVersion)
{
    *name = const_cast<wchar_t*>(L"LoaderTest");
    *author = const_cast<wchar_t*>(L"AP");
    *version = const_cast<wchar_t*>(L"1");
    *games = 1 << 2;
    *minVersion = 3;
}
extern "C" __declspec(dllexport) bool SpiShouldPreload() { return false; }
extern "C" __declspec(dllexport) bool SpiShouldSpawnThread() { return true; }

extern "C" __declspec(dllexport) bool SpiOnAttach(ISharedProxyInterface* spi)
{
    HMODULE host = GetModuleHandleW(nullptr);
    auto target = reinterpret_cast<TargetFn>(GetProcAddress(host, "Target"));
    auto rip = *reinterpret_cast<NoArgFn*>(GetProcAddress(host, "g_ripLoad"));
    auto jump = *reinterpret_cast<NoArgFn*>(GetProcAddress(host, "g_shortJump"));
    auto* failures = reinterpret_cast<volatile int*>(GetProcAddress(host, "g_failures"));
    auto* done = reinterpret_cast<volatile int*>(GetProcAddress(host, "g_done"));
    int bad = 0;
    const auto check = [&](bool ok, const char* what) {
        std::printf("%s %s\n", ok ? "PASS" : "FAIL", what);
        bad += ok ? 0 : 1;
    };

    unsigned long version = 0;
    check(spi->GetVersion(&version) == SPIReturn::Success && version == 3, "GetVersion == 3");
    SPIGameVersion game{};
    check(spi->GetHostGame(&game) == SPIReturn::Success && game == SPIGameVersion::LE2, "GetHostGame == LE2");

    char pattern[64];
    auto* bytes = reinterpret_cast<unsigned char*>(target);
    std::snprintf(pattern, sizeof(pattern), "%02X %02X ?? %02X %02X %02X", bytes[0], bytes[1], bytes[3], bytes[4], bytes[5]);
    void* found = nullptr;
    check(spi->FindPattern(&found, pattern) == SPIReturn::Success && found != nullptr, "FindPattern finds Target's prologue");
    char badPattern[] = "4G 8B";
    check(spi->FindPattern(&found, badPattern) != SPIReturn::Success, "FindPattern rejects a bad pattern");

    const int before = target(3, 4);
    check(spi->InstallHook("target", reinterpret_cast<void*>(target), reinterpret_cast<void*>(HookTarget),
                           reinterpret_cast<void**>(&g_targetOrig)) == SPIReturn::Success, "InstallHook Target");
    check(target(3, 4) == before + 1000, "hooked Target runs the detour and the original");
    check(spi->InstallHook("target", reinterpret_cast<void*>(target), reinterpret_cast<void*>(HookTarget),
                           reinterpret_cast<void**>(&g_targetOrig)) != SPIReturn::Success, "duplicate hook name refused");
    check(spi->UninstallHook("target") == SPIReturn::Success && target(3, 4) == before, "UninstallHook restores Target");

    check(spi->InstallHook("rip", reinterpret_cast<void*>(rip), reinterpret_cast<void*>(HookRip),
                           reinterpret_cast<void**>(&g_ripOrig)) == SPIReturn::Success && rip() == 142,
          "RIP-relative prologue relocated (41 + 1 + 100)");
    check(spi->InstallHook("jump", reinterpret_cast<void*>(jump), reinterpret_cast<void*>(HookJump),
                           reinterpret_cast<void**>(&g_jumpOrig)) == SPIReturn::Success && jump() == 107,
          "short-jump prologue widened (7 + 100)");

    *failures = bad;
    *done = 1;
    return bad == 0;
}

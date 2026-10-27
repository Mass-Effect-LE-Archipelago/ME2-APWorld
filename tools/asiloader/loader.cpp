// AP ASI Loader: a bink2w64.dll proxy for Mass Effect Legendary Edition. Every Bink export is forwarded to the real DLL
// (renamed bink2w64_original.dll, see exports.h). On load it starts a thread that loads Binaries\Win64\ASI\*.asi and
// runs their SPI entry points (SpiSupportDecl / SpiShouldPreload / SpiShouldSpawnThread / SpiOnAttach), offering the
// SPI v3 interface those plugins expect: version, build mode, host game, FindPattern, InstallHook, UninstallHook.
// Pre-load plugins attach at once; post-load plugins wait until the game has created its window (its code is unpacked
// and running by then).

#include <windows.h>

#include <algorithm>
#include <cctype>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <share.h>
#include <mutex>
#include <string>
#include <vector>

#include "exports.h"
#include "hook.h"

#define AP_LOADER_VERSION L"1.0.0"

// ---- SPI (the plugin-facing interface; the vtable layout must match what plugins are compiled against) ----

enum class SPIReturn : short
{
    Success = 1,
    FailureGeneric = 10,
    FailureDuplicacy = 11,
    FailureHooking = 12,
    FailureInvalidParam = 13,
    FailurePatternInvalid = 16,
    FailurePatternTooLong = 17,
};

enum class SPIGameVersion
{
    Launcher = 0,
    LE1 = 1,
    LE2 = 2,
    LE3 = 3
};

class ISharedProxyInterface
{
public:
    virtual SPIReturn GetVersion(unsigned long* outVersion) = 0;
    virtual SPIReturn GetBuildMode(bool* outIsRelease) = 0;
    virtual SPIReturn GetHostGame(SPIGameVersion* outGame) = 0;
    virtual SPIReturn FindPattern(void** outAddress, char* combinedPattern) = 0;
    virtual SPIReturn InstallHook(const char* name, void* target, void* detour, void** original) = 0;
    virtual SPIReturn UninstallHook(const char* name) = 0;
};

constexpr unsigned long kSpiVersion = 3;
constexpr size_t kMaxPatternBytes = 100;

namespace
{
    SPIGameVersion g_game = SPIGameVersion::Launcher;
    std::wstring g_exeDir;
    FILE* g_log = nullptr;
    std::mutex g_logLock;

    void Log(const wchar_t* format, ...)
    {
        std::lock_guard guard(g_logLock);
        if (!g_log)
            return;
        SYSTEMTIME now;
        GetLocalTime(&now);
        fwprintf(g_log, L"[%02d:%02d:%02d.%03d] ", now.wHour, now.wMinute, now.wSecond, now.wMilliseconds);
        va_list args;
        va_start(args, format);
        vfwprintf(g_log, format, args);
        va_end(args);
        fputwc(L'\n', g_log);
        fflush(g_log);
    }

    bool ParsePattern(const char* text, std::vector<int>& out)
    {
        // PEiD style: "48 8B 05 ?? ?? ?? ??" (a byte is two hex digits; ? or ?? is a wildcard).
        out.clear();
        const char* p = text;
        while (*p)
        {
            while (*p == ' ')
                ++p;
            if (!*p)
                break;
            const char* start = p;
            while (*p && *p != ' ')
                ++p;
            const std::string token(start, p);
            if (token == "?" || token == "??")
                out.push_back(-1);
            else if (token.size() == 2 && std::isxdigit(static_cast<unsigned char>(token[0])) &&
                     std::isxdigit(static_cast<unsigned char>(token[1])))
                out.push_back(static_cast<int>(std::strtol(token.c_str(), nullptr, 16)));
            else
                return false;
        }
        return !out.empty();
    }

    void* ScanMainModule(const std::vector<int>& pattern)
    {
        auto* base = reinterpret_cast<uint8_t*>(GetModuleHandleW(nullptr));
        auto* dos = reinterpret_cast<IMAGE_DOS_HEADER*>(base);
        auto* nt = reinterpret_cast<IMAGE_NT_HEADERS*>(base + dos->e_lfanew);
        uint8_t* const end = base + nt->OptionalHeader.SizeOfImage;
        const size_t n = pattern.size();
        for (uint8_t* region = base; region < end;)
        {
            MEMORY_BASIC_INFORMATION mbi{};
            if (!VirtualQuery(region, &mbi, sizeof(mbi)))
                break;
            uint8_t* const regionEnd = std::min(static_cast<uint8_t*>(mbi.BaseAddress) + mbi.RegionSize, end);
            const DWORD readable = PAGE_READONLY | PAGE_READWRITE | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE |
                                   PAGE_WRITECOPY | PAGE_EXECUTE_WRITECOPY;
            if (mbi.State == MEM_COMMIT && (mbi.Protect & readable) && !(mbi.Protect & PAGE_GUARD) &&
                regionEnd - region >= static_cast<ptrdiff_t>(n))
            {
                for (uint8_t* p = region; p + n <= regionEnd; ++p)
                {
                    size_t i = 0;
                    while (i < n && (pattern[i] < 0 || p[i] == pattern[i]))
                        ++i;
                    if (i == n)
                        return p;
                }
            }
            region = regionEnd;
        }
        return nullptr;
    }

    class SharedProxy final : public ISharedProxyInterface
    {
    public:
        SPIReturn GetVersion(unsigned long* outVersion) override
        {
            if (!outVersion)
                return SPIReturn::FailureInvalidParam;
            *outVersion = kSpiVersion;
            return SPIReturn::Success;
        }

        SPIReturn GetBuildMode(bool* outIsRelease) override
        {
            if (!outIsRelease)
                return SPIReturn::FailureInvalidParam;
            *outIsRelease = true;
            return SPIReturn::Success;
        }

        SPIReturn GetHostGame(SPIGameVersion* outGame) override
        {
            if (!outGame)
                return SPIReturn::FailureInvalidParam;
            *outGame = g_game;
            return SPIReturn::Success;
        }

        SPIReturn FindPattern(void** outAddress, char* combinedPattern) override
        {
            if (!outAddress || !combinedPattern)
                return SPIReturn::FailureInvalidParam;
            *outAddress = nullptr;
            std::vector<int> pattern;
            if (!ParsePattern(combinedPattern, pattern))
                return SPIReturn::FailurePatternInvalid;
            if (pattern.size() > kMaxPatternBytes)
                return SPIReturn::FailurePatternTooLong;
            *outAddress = ScanMainModule(pattern);
            if (!*outAddress)
            {
                Log(L"FindPattern: no match for %S", combinedPattern);
                return SPIReturn::FailureGeneric;
            }
            return SPIReturn::Success;
        }

        SPIReturn InstallHook(const char* name, void* target, void* detour, void** original) override
        {
            const Hooks::Result result = Hooks::Install(name, target, detour, original);
            Log(L"InstallHook %S at %p: %d", name ? name : "(null)", target, static_cast<int>(result));
            switch (result)
            {
            case Hooks::Result::Ok: return SPIReturn::Success;
            case Hooks::Result::Duplicate: return SPIReturn::FailureDuplicacy;
            case Hooks::Result::BadTarget: return SPIReturn::FailureInvalidParam;
            default: return SPIReturn::FailureHooking;
            }
        }

        SPIReturn UninstallHook(const char* name) override
        {
            const Hooks::Result result = Hooks::Uninstall(name);
            Log(L"UninstallHook %S: %d", name ? name : "(null)", static_cast<int>(result));
            if (result == Hooks::Result::Ok)
                return SPIReturn::Success;
            return result == Hooks::Result::NotFound ? SPIReturn::FailureDuplicacy : SPIReturn::FailureHooking;
        }
    };

    SharedProxy g_spi;

    using SupportDecl = void (*)(wchar_t**, wchar_t**, wchar_t**, int*, int*);
    using BoolQuery = bool (*)();
    using Attach = bool (*)(ISharedProxyInterface*);

    struct Plugin
    {
        std::wstring file;
        Attach attach = nullptr;
        bool preload = false;
        bool spawnThread = false;
    };

    DWORD WINAPI AttachThread(LPVOID param)
    {
        auto* plugin = static_cast<Plugin*>(param);
        const bool ok = plugin->attach(&g_spi);
        Log(L"%s: SpiOnAttach returned %s", plugin->file.c_str(), ok ? L"true" : L"false");
        return 0;
    }

    void AttachPlugin(Plugin& plugin)
    {
        if (plugin.spawnThread)
        {
            HANDLE thread = CreateThread(nullptr, 0, AttachThread, &plugin, 0, nullptr);
            if (thread)
                CloseHandle(thread);
            else
                Log(L"%s: could not start its attach thread", plugin.file.c_str());
        }
        else
        {
            AttachThread(&plugin);
        }
    }

    BOOL CALLBACK FindOwnWindow(HWND window, LPARAM found)
    {
        DWORD pid = 0;
        GetWindowThreadProcessId(window, &pid);
        if (pid != GetCurrentProcessId())
            return TRUE;
        *reinterpret_cast<bool*>(found) = true;
        return FALSE;
    }

    void WaitForGameWindow()
    {
        for (int i = 0; i < 1200; ++i)  // 60 s, then carry on anyway
        {
            bool found = false;
            EnumWindows(FindOwnWindow, reinterpret_cast<LPARAM>(&found));
            if (found)
            {
                Log(L"game window is up after %d ms", i * 50);
                return;
            }
            Sleep(50);
        }
        Log(L"no game window after 60 s; loading post-load plugins anyway");
    }

    std::vector<Plugin>* g_plugins = nullptr;  // lives for the whole process; plugin threads hold pointers into it

    DWORD WINAPI Main(LPVOID)
    {
        const std::wstring asiDir = g_exeDir + L"\\ASI";
        std::vector<std::wstring> files;
        WIN32_FIND_DATAW data;
        HANDLE find = FindFirstFileW((asiDir + L"\\*.asi").c_str(), &data);
        if (find != INVALID_HANDLE_VALUE)
        {
            do
            {
                if (!(data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY))
                    files.emplace_back(data.cFileName);
            } while (FindNextFileW(find, &data));
            FindClose(find);
        }
        std::sort(files.begin(), files.end());
        Log(L"%zu ASI file(s) in %s", files.size(), asiDir.c_str());

        g_plugins = new std::vector<Plugin>();
        g_plugins->reserve(files.size());
        const int gameFlag = 1 << static_cast<int>(g_game);
        for (const auto& file : files)
        {
            HMODULE module = LoadLibraryW((asiDir + L"\\" + file).c_str());
            if (!module)
            {
                Log(L"%s: LoadLibrary failed (error %lu)", file.c_str(), GetLastError());
                continue;
            }
            auto decl = reinterpret_cast<SupportDecl>(GetProcAddress(module, "SpiSupportDecl"));
            auto attach = reinterpret_cast<Attach>(GetProcAddress(module, "SpiOnAttach"));
            if (!decl || !attach)
            {
                Log(L"%s: loaded (plain ASI)", file.c_str());
                continue;
            }
            wchar_t *name = nullptr, *author = nullptr, *version = nullptr;
            int games = 0, minVersion = 0;
            decl(&name, &author, &version, &games, &minVersion);
            if (!(games & gameFlag) || static_cast<unsigned long>(minVersion) > kSpiVersion)
            {
                Log(L"%s: SPI plugin %s is not for this game or needs SPI %d; not attached", file.c_str(),
                    name ? name : L"?", minVersion);
                continue;
            }
            auto preload = reinterpret_cast<BoolQuery>(GetProcAddress(module, "SpiShouldPreload"));
            auto spawn = reinterpret_cast<BoolQuery>(GetProcAddress(module, "SpiShouldSpawnThread"));
            Plugin plugin{file, attach, preload && preload(), spawn && spawn()};
            Log(L"%s: SPI plugin %s %s by %s (%s, %s)", file.c_str(), name ? name : L"?", version ? version : L"?",
                author ? author : L"?", plugin.preload ? L"pre-load" : L"post-load",
                plugin.spawnThread ? L"own thread" : L"in sequence");
            g_plugins->push_back(plugin);
        }

        for (auto& plugin : *g_plugins)
            if (plugin.preload)
                AttachPlugin(plugin);
        WaitForGameWindow();
        for (auto& plugin : *g_plugins)
            if (!plugin.preload)
                AttachPlugin(plugin);
        return 0;
    }

    void Start()
    {
        wchar_t path[MAX_PATH];
        const DWORD length = GetModuleFileNameW(nullptr, path, MAX_PATH);
        std::wstring exe(path, length);
        const size_t slash = exe.find_last_of(L"\\/");
        g_exeDir = exe.substr(0, slash);
        std::wstring name = exe.substr(slash + 1);
        std::transform(name.begin(), name.end(), name.begin(), ::towlower);
        if (name == L"masseffect1.exe") g_game = SPIGameVersion::LE1;
        else if (name == L"masseffect2.exe") g_game = SPIGameVersion::LE2;
        else if (name == L"masseffect3.exe") g_game = SPIGameVersion::LE3;
        else return;  // the launcher (or anything else): forward Bink only

        g_log = _wfsopen((g_exeDir + L"\\APAsiLoader.log").c_str(), L"w, ccs=UTF-8", _SH_DENYWR);  // readable while the game runs
        Log(L"AP ASI Loader " AP_LOADER_VERSION L" in %s (LE%d)", name.c_str(), static_cast<int>(g_game));
        HANDLE thread = CreateThread(nullptr, 0, Main, nullptr, 0, nullptr);
        if (thread)
            CloseHandle(thread);
    }
}

// Lets the setup app tell this loader from others without parsing version resources.
extern "C" __declspec(dllexport) const wchar_t* APAsiLoaderVersion() { return AP_LOADER_VERSION; }

BOOL WINAPI DllMain(HMODULE module, DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        DisableThreadLibraryCalls(module);
        Start();
    }
    return TRUE;
}

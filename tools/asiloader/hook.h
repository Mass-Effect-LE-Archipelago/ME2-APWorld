#pragma once
// Minimal x64 detours for the loader's SPI InstallHook/UninstallHook.
// A hook overwrites the target's first instructions with a 5-byte jmp to a relay near the target; the relay jumps to
// the detour, and a trampoline (the copied instructions, relocated, plus a jmp back) is returned as the original.

namespace Hooks
{
    enum class Result { Ok, Duplicate, NotFound, BadTarget, NoMemory, Busy };

    Result Install(const char* name, void* target, void* detour, void** original);
    Result Uninstall(const char* name);
}

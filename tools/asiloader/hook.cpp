#include "hook.h"

#include <windows.h>
#include <tlhelp32.h>

#include <cstdint>
#include <cstring>
#include <map>
#include <mutex>
#include <string>
#include <vector>

extern "C" {
#include "hde/hde64.h"
}

namespace Hooks
{
namespace
{
    constexpr size_t kPatchSize = 5;            // E9 rel32
    constexpr size_t kSlotSize = 64;            // relay (14 bytes) at 0, trampoline at 16
    constexpr size_t kTrampolineOffset = 16;
    constexpr size_t kPageSize = 4096;
    constexpr intptr_t kReach = 0x7FF00000;     // stay inside rel32 range of the target

    struct Hook
    {
        uint8_t* target;
        uint8_t saved[kPatchSize];
    };

    std::mutex g_lock;
    std::map<std::string, Hook> g_hooks;
    std::vector<std::pair<uint8_t*, size_t>> g_pages;  // page base, slots used

    bool Fits32(intptr_t value) { return value == static_cast<int32_t>(value); }

    uint8_t* AllocPageNear(uint8_t* target)
    {
        SYSTEM_INFO info;
        GetSystemInfo(&info);
        const uintptr_t granularity = info.dwAllocationGranularity;
        const uintptr_t origin = reinterpret_cast<uintptr_t>(target);
        const uintptr_t low = origin > static_cast<uintptr_t>(kReach) ? origin - kReach : granularity;
        const uintptr_t high = origin + kReach;
        // Walk outwards from the target, alternating below and above, one allocation granule at a time.
        for (uintptr_t step = granularity; step < static_cast<uintptr_t>(kReach); step += granularity)
        {
            for (int side = 0; side < 2; ++side)
            {
                uintptr_t candidate = side == 0 ? (origin - step) : (origin + step);
                candidate -= candidate % granularity;
                if (candidate < low || candidate > high)
                    continue;
                MEMORY_BASIC_INFORMATION mbi{};
                if (!VirtualQuery(reinterpret_cast<void*>(candidate), &mbi, sizeof(mbi)) || mbi.State != MEM_FREE)
                    continue;
                void* page = VirtualAlloc(reinterpret_cast<void*>(candidate), kPageSize, MEM_RESERVE | MEM_COMMIT,
                                          PAGE_EXECUTE_READWRITE);
                if (page)
                    return static_cast<uint8_t*>(page);
            }
        }
        return nullptr;
    }

    uint8_t* AllocSlotNear(uint8_t* target)
    {
        for (auto& [page, used] : g_pages)
        {
            if (used < kPageSize / kSlotSize && Fits32(page - target) && Fits32(page + kPageSize - target))
                return page + kSlotSize * used++;
        }
        uint8_t* page = AllocPageNear(target);
        if (!page)
            return nullptr;
        g_pages.emplace_back(page, 1);
        return page;
    }

    // Copies whole instructions from target until kPatchSize bytes are covered, fixing anything RIP-relative, then
    // appends a jmp back. Returns false for prologues it can't relocate safely.
    bool BuildTrampoline(uint8_t* target, uint8_t* out, size_t capacity)
    {
        size_t copied = 0, written = 0;
        const auto inPatch = [&](intptr_t address) {
            return address > reinterpret_cast<intptr_t>(target) &&
                   address < reinterpret_cast<intptr_t>(target + kPatchSize);
        };
        while (copied < kPatchSize)
        {
            uint8_t* src = target + copied;
            hde64s hs;
            const unsigned len = hde64_disasm(src, &hs);
            if ((hs.flags & F_ERROR) || len == 0)
                return false;
            const intptr_t next = reinterpret_cast<intptr_t>(src + len);
            uint8_t* dst = out + written;
            uint8_t buf[16];
            size_t outLen = len;
            std::memcpy(buf, src, len);

            if (hs.opcode == 0xE8 || hs.opcode == 0xE9)  // call/jmp rel32
            {
                if (len != 5)
                    return false;
                const intptr_t to = next + static_cast<int32_t>(hs.imm.imm32);
                if (inPatch(to) || !Fits32(to - reinterpret_cast<intptr_t>(dst + 5)))
                    return false;
                const int32_t rel = static_cast<int32_t>(to - reinterpret_cast<intptr_t>(dst + 5));
                std::memcpy(buf + 1, &rel, 4);
            }
            else if (hs.opcode == 0x0F && (hs.opcode2 & 0xF0) == 0x80)  // jcc rel32
            {
                if (len != 6)
                    return false;
                const intptr_t to = next + static_cast<int32_t>(hs.imm.imm32);
                if (inPatch(to) || !Fits32(to - reinterpret_cast<intptr_t>(dst + 6)))
                    return false;
                const int32_t rel = static_cast<int32_t>(to - reinterpret_cast<intptr_t>(dst + 6));
                std::memcpy(buf + 2, &rel, 4);
            }
            else if (hs.opcode == 0xEB || (hs.opcode & 0xF0) == 0x70)  // jmp/jcc rel8, widened to rel32
            {
                if (len != 2)
                    return false;
                const intptr_t to = next + static_cast<int8_t>(hs.imm.imm8);
                if (inPatch(to))
                    return false;
                if (hs.opcode == 0xEB)
                {
                    outLen = 5;
                    buf[0] = 0xE9;
                }
                else
                {
                    outLen = 6;
                    buf[1] = static_cast<uint8_t>(0x80 | (hs.opcode & 0x0F));
                    buf[0] = 0x0F;
                }
                if (!Fits32(to - reinterpret_cast<intptr_t>(dst + outLen)))
                    return false;
                const int32_t rel = static_cast<int32_t>(to - reinterpret_cast<intptr_t>(dst + outLen));
                std::memcpy(buf + outLen - 4, &rel, 4);
            }
            else if (hs.opcode >= 0xE0 && hs.opcode <= 0xE3)  // loop/jrcxz: no rel32 form
            {
                return false;
            }
            else if ((hs.flags & F_MODRM) && hs.modrm_mod == 0 && hs.modrm_rm == 5)  // [rip+disp32]
            {
                size_t immSize = 0;
                if (hs.flags & F_IMM8) immSize = 1;
                else if (hs.flags & F_IMM16) immSize = 2;
                else if (hs.flags & F_IMM32) immSize = 4;
                else if (hs.flags & F_IMM64) immSize = 8;
                const intptr_t to = next + static_cast<int32_t>(hs.disp.disp32);
                const intptr_t disp = to - reinterpret_cast<intptr_t>(dst + len);
                if (!Fits32(disp))
                    return false;
                const int32_t disp32 = static_cast<int32_t>(disp);
                std::memcpy(buf + len - immSize - 4, &disp32, 4);
            }
            else if (hs.flags & F_RELATIVE)
            {
                return false;
            }
            else if ((hs.opcode == 0xC3 || hs.opcode == 0xC2 || hs.opcode == 0xCC) && copied + len < kPatchSize)
            {
                return false;  // function is shorter than the patch
            }

            if (written + outLen + 5 > capacity)
                return false;
            std::memcpy(dst, buf, outLen);
            written += outLen;
            copied += len;
        }
        uint8_t* back = out + written;
        const intptr_t rel = reinterpret_cast<intptr_t>(target + copied) - reinterpret_cast<intptr_t>(back + 5);
        if (!Fits32(rel))
            return false;
        back[0] = 0xE9;
        const int32_t rel32 = static_cast<int32_t>(rel);
        std::memcpy(back + 1, &rel32, 4);
        return true;
    }

    // Writes bytes over code while every other thread is suspended and none is executing inside the range.
    bool PatchCode(uint8_t* at, const uint8_t* bytes, size_t count)
    {
        for (int attempt = 0; attempt < 200; ++attempt)
        {
            std::vector<DWORD> ids;
            HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
            if (snapshot == INVALID_HANDLE_VALUE)
                return false;
            THREADENTRY32 entry{sizeof(entry)};
            const DWORD self = GetCurrentThreadId(), pid = GetCurrentProcessId();
            for (BOOL ok = Thread32First(snapshot, &entry); ok; ok = Thread32Next(snapshot, &entry))
                if (entry.th32OwnerProcessID == pid && entry.th32ThreadID != self)
                    ids.push_back(entry.th32ThreadID);
            CloseHandle(snapshot);

            std::vector<HANDLE> threads;
            threads.reserve(ids.size());  // no heap use while threads are frozen
            bool busy = false;
            for (DWORD id : ids)
            {
                HANDLE thread = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT, FALSE, id);
                if (!thread)
                    continue;
                if (SuspendThread(thread) == static_cast<DWORD>(-1))
                {
                    CloseHandle(thread);
                    continue;
                }
                threads.push_back(thread);
                CONTEXT context{};
                context.ContextFlags = CONTEXT_CONTROL;
                if (GetThreadContext(thread, &context) && context.Rip >= reinterpret_cast<DWORD64>(at) &&
                    context.Rip < reinterpret_cast<DWORD64>(at + count))
                    busy = true;
            }
            bool written = false;
            if (!busy)
            {
                DWORD old;
                if (VirtualProtect(at, count, PAGE_EXECUTE_READWRITE, &old))
                {
                    std::memcpy(at, bytes, count);
                    VirtualProtect(at, count, old, &old);
                    FlushInstructionCache(GetCurrentProcess(), at, count);
                    written = true;
                }
            }
            for (HANDLE thread : threads)
            {
                ResumeThread(thread);
                CloseHandle(thread);
            }
            if (!busy)
                return written;
            Sleep(1);
        }
        return false;
    }
}

Result Install(const char* name, void* target, void* detour, void** original)
{
    if (!name || !target || !detour || !original)
        return Result::BadTarget;
    std::lock_guard guard(g_lock);
    if (g_hooks.count(name))
        return Result::Duplicate;
    auto* code = static_cast<uint8_t*>(target);
    uint8_t* slot = AllocSlotNear(code);
    if (!slot)
        return Result::NoMemory;
    // relay: jmp qword ptr [rip+0] ; <detour>
    static const uint8_t relay[6] = {0xFF, 0x25, 0, 0, 0, 0};
    std::memcpy(slot, relay, sizeof(relay));
    std::memcpy(slot + 6, &detour, sizeof(detour));
    uint8_t* trampoline = slot + kTrampolineOffset;
    if (!BuildTrampoline(code, trampoline, kSlotSize - kTrampolineOffset))
        return Result::BadTarget;
    FlushInstructionCache(GetCurrentProcess(), slot, kSlotSize);

    Hook hook{code, {}};
    std::memcpy(hook.saved, code, kPatchSize);
    uint8_t patch[kPatchSize] = {0xE9};
    const int32_t rel = static_cast<int32_t>(slot - (code + kPatchSize));
    std::memcpy(patch + 1, &rel, 4);
    *original = trampoline;  // set before the patch goes live, so the detour can call through at once
    if (!PatchCode(code, patch, kPatchSize))
    {
        *original = nullptr;
        return Result::Busy;
    }
    g_hooks.emplace(name, hook);
    return Result::Ok;
}

Result Uninstall(const char* name)
{
    if (!name)
        return Result::NotFound;
    std::lock_guard guard(g_lock);
    auto it = g_hooks.find(name);
    if (it == g_hooks.end())
        return Result::NotFound;
    if (!PatchCode(it->second.target, it->second.saved, kPatchSize))
        return Result::Busy;
    g_hooks.erase(it);  // the slot is left allocated: a thread may still be inside the trampoline
    return Result::Ok;
}
}

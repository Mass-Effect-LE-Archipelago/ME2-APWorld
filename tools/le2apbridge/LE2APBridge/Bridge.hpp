#pragma once
#include <LESDK/Headers.hpp>
#include <LESDK/Init.hpp>
#include "Common/Base.hpp"

// Named pipe \\.\pipe\LE2APBridge; the request/reply contract is tools/le2apbridge/PROTOCOL.md.
// Plot and inventory access happens on the game thread (ProcessEvent hook); the pipe thread only parses, queues and
// waits, so one TXN (grant + received-index update) can never be split by a save.
namespace LE2APBridge
{
    void StartPipeServer();
    void StopPipeServer();           // on ASI detach: ask the pipe thread to stop (module is pinned, see Bridge.cpp)
    void ProcessPendingRequests();   // call on the game thread

    using t_UObject_ProcessEvent = void(UObject* Context, UFunction* Function, void* Parms, void* Result);
    extern t_UObject_ProcessEvent* UObject_ProcessEvent_orig;
    void UObject_ProcessEvent_hook(UObject* Context, UFunction* Function, void* Parms, void* Result);
}

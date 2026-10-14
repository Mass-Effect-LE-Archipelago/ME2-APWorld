#include "Common/Base.hpp"
#include "Common/DefaultLogger.hpp"
#include "LE2APBridge/Bridge.hpp"
#include "LE2APBridge/SharedVersion.h"
#include <SPI.h>


SPI_PLUGINSIDE_SUPPORT(SDK_TARGET_NAME_W ASI_NAME_NO_SPACE_W, DEVELOPER_W, L"" VERSION_STRING_W, SPI_GAME_SDK_TARGET, SPI_VERSION_ANY);
SPI_PLUGINSIDE_POSTLOAD;
SPI_PLUGINSIDE_ASYNCATTACH;


SPI_IMPLEMENT_ATTACH
{
    ::LESDK::Initializer Init{ InterfacePtr, SDK_TARGET_NAME_A ASI_NAME_NO_SPACE_A };
    Common::SetupDefaultLogger(SDK_TARGET_NAME_A, ASI_NAME_NO_SPACE_A);
    Common::InitializeRequiredGlobals(Init);

    // Same ProcessEvent hook pattern as LE1APBridge and LExASIs' 2DAPrinter/LEXInterop.
    auto const ProcessEvent_target = Init.ResolveTyped<LE2APBridge::t_UObject_ProcessEvent>(BUILTIN_PROCESSEVENT_RVA);
    CHECK_RESOLVED(ProcessEvent_target);
    LE2APBridge::UObject_ProcessEvent_orig = (LE2APBridge::t_UObject_ProcessEvent*)Init.InstallHook(
        "UObject::ProcessEvent", ProcessEvent_target, LE2APBridge::UObject_ProcessEvent_hook);
    CHECK_RESOLVED(LE2APBridge::UObject_ProcessEvent_orig);

    LE2APBridge::StartPipeServer();
    LEASI_INFO("LE2APBridge attached");
    return true;
}

SPI_IMPLEMENT_DETACH
{
    LEASI_UNUSED(InterfacePtr);
    LE2APBridge::StopPipeServer();
    ::Common::ShutdownLogger();
    return true;
}

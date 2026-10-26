#include "LE2APBridge/Bridge.hpp"
#include "LE2APBridge/SharedVersion.h"
#include "Common/Objects.hpp"

#include <Windows.h>
#include <concurrent_queue.h>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <future>
#include <string>
#include <thread>

// Ported from LE1APBridge v11 (pipe thread, game-thread queue, startup guard). New for LE2 (feasibility plan, "Runtime
// contract improvements"): HELLO handshake, save identity (ID/IDSET), batched reads (GETBS) and indexed transactions
// (TXN). LE1's inventory, shop, container, sprint and message-box features are not ported: LE2 has no UBioInventory,
// and resources live on the player's ASFXInventoryManager.
namespace LE2APBridge
{
    namespace
    {
        constexpr wchar_t PipeName[] = L"\\\\.\\pipe\\LE2APBridge";
        constexpr DWORD BufferSize = 4096;
        // AP-owned plot block (docs/DECISIONS.md D2, pending the collision audit).
        constexpr int BoolMin = 21000, BoolMax = 21999;
        constexpr int IntMin = 2100, IntMax = 2199;
        constexpr int ReceivedIndexInt = 2100;   // written only inside TXN
        constexpr int IdentitySeedInt = 2101, IdentitySlotInt = 2102;
        constexpr int GetBsMax = 64;
        constexpr int TxnArgsMax = 3;

        // Vanilla targets a TXN may write (never cleared): ship upgrades (applied bool, research unlocked bool) and the
        // armory's weapon ints (me2_plot_db "research_upgrades"). Anything else is refused, never silently consumed.
        constexpr int ShipBools[][2] = { { 237, 5642 }, { 236, 5648 }, { 238, 5645 } };
        constexpr int WeaponInts[] = { 149, 854, 124, 725, 152, 852, 495, 88, 847, 853, 177, 855, 151, 460, 663, 461, 496 };
        constexpr int ResourceAmountMax = 1000000;

        // SDK enum SFXGame.EInventoryResourceTypes (LExSDKv2 LE2 SFXGame_classes.hpp): 0 credits, 1 medigel, 2 salvage,
        // 3 grenades, 4 eezo, 5 iridium, 6 palladium, 7 platinum, 8 probes, 9 fuel. Only the ME2 resources are granted.
        // ME1 history (protocol 2): the plot bools of the Genesis comic's six choices (tools/le2mod/research/
        // genesis_choices.tsv), written by the client only before it binds a fresh save.
        constexpr int HistoryBools[] = { 1528, 1529, 1530, 1926, 1540, 1541, 1553, 1554, 1555, 1556, 3151, 3752, 7447, 7448 };

        // Dossier journal bools (protocol 3; me2_plot_db Journals.SquadMember_Acquisition.*): the state TIM's dossier
        // transitions 2371/2372 set, which the hub recruit starts check. The client sets them (never clears) for each
        // received dossier whose recruitment is not done.
        constexpr int DossierJournalBools[] = { 551, 548, 545, 552, 549, 553, 550 };

        // Missed-checks salvage (protocol 4, D22): purchase counters the research terminal raises (the client takes them,
        // read and zeroed at once) and the caps the client sets (le2mod 0.0.7 research entries show while counter < cap).
        constexpr int SalvageBoughtMin = 2110, SalvageBoughtMax = 2149;
        constexpr int SalvageCapMin = 2150, SalvageCapMax = 2199, SalvageCapValueMax = 1000;

        bool IsDossierJournalBool(int const Index)
        {
            for (int const Allowed : DossierJournalBools)
                if (Allowed == Index) return true;
            return false;
        }

        bool IsHistoryBool(int const Index)
        {
            for (int const Allowed : HistoryBools)
                if (Allowed == Index) return true;
            return false;
        }

        bool IsResourceType(int const Type)
        {
            return Type == 0 || Type == 1 || (Type >= 4 && Type <= 8);
        }

        bool IsShipPair(int const Applied, int const Unlocked)
        {
            for (auto const& Pair : ShipBools)
                if (Pair[0] == Applied && Pair[1] == Unlocked) return true;
            return false;
        }

        bool IsWeaponInt(int const Index)
        {
            for (int const Allowed : WeaponInts)
                if (Allowed == Index) return true;
            return false;
        }

        struct Request
        {
            char Op[8]{};
            char TxnOp[8]{};
            int Index = 0;
            int Value = 0;
            int Args[TxnArgsMax]{};
            int Count = 0;              // GETBS indices used in Many
            int Many[GetBsMax]{};
            std::wstring Text{};        // NOTE
            std::promise<std::string> Reply;
        };

        concurrency::concurrent_queue<Request*> g_Pending{};
        std::atomic<bool> g_Stop{ false };
        thread_local bool t_InProcess = false;

        // First live (not default, not being destroyed) object of type T (bounded scan, as LE1APBridge).
        template<typename T>
        T* FirstLive()
        {
            constexpr uint64_t Dead = static_cast<uint64_t>(EObjectFlags::ClassDefaultObject)
                | static_cast<uint64_t>(EObjectFlags::PendingKill) | static_cast<uint64_t>(EObjectFlags::Unreachable)
                | static_cast<uint64_t>(EObjectFlags::BeginDestroyed) | static_cast<uint64_t>(EObjectFlags::FinishDestroyed);
            UObject** const Data = UObject::GObjObjects->GetData();
            int const Count = UObject::GObjObjects->Count();
            for (int i = 0; i < Count; ++i)
            {
                UObject* const Obj = Data[i];
                if (Obj == nullptr || (static_cast<uint64_t>(Obj->ObjectFlags) & Dead) != 0) continue;
                if (T* const Typed = Obj->Cast<T>()) return Typed;
            }
            return nullptr;
        }

        ABioWorldInfo* CurrentBioWorld()
        {
            // LE1 startup crash (2026-10-08): GetCurrentWorldInfo() dereferenced a null persistent level before the first
            // world existed. Only ask the engine once a live world object has been seen.
            static bool WorldSeen = false;
            static UEngine* Engine = nullptr;
            if (!WorldSeen && FirstLive<ABioWorldInfo>() == nullptr) return nullptr;
            WorldSeen = true;
            if (Engine == nullptr) Engine = FirstLive<UEngine>();
            if (Engine == nullptr) return nullptr;
            AWorldInfo* const World = Engine->GetCurrentWorldInfo();
            return World != nullptr ? World->Cast<ABioWorldInfo>() : nullptr;
        }

        UBioGlobalVariableTable* GlobalVariables()
        {
            ABioWorldInfo* const BioWorld = CurrentBioWorld();
            return BioWorld != nullptr ? BioWorld->GetGlobalVariables() : nullptr;
        }

        // The player's inventory manager (credits, eezo, minerals), or null while no player pawn exists.
        ASFXInventoryManager* PlayerInventory()
        {
            ABioWorldInfo* const BioWorld = CurrentBioWorld();
            APlayerController* const PC = BioWorld != nullptr ? BioWorld->GetLocalPlayerController() : nullptr;
            if (PC == nullptr || PC->Pawn == nullptr || PC->Pawn->InvManager == nullptr) return nullptr;
            return PC->Pawn->InvManager->Cast<ASFXInventoryManager>();
        }

        // One TXN operation; "" on success, or an error reply (the received index is then left unchanged).
        std::string ApplyTxnOp(Request const& R, UBioGlobalVariableTable* Vars)
        {
            std::string const Op{ R.TxnOp };
            if (Op == "NONE") return "";
            if (Op == "FLAG")
            {
                Vars->SetBool(R.Args[0], 1, 0);
                return "";
            }
            if (Op == "SHIP")
            {
                Vars->SetBool(R.Args[0], 1, 0);
                Vars->SetBool(R.Args[1], 1, 0);
                return "";
            }
            if (Op == "WEAPON")
            {
                if (Vars->GetInt(R.Args[0]) < 1) Vars->SetInt(R.Args[0], 1);
                return "";
            }
            if (Op == "RES")
            {
                ASFXInventoryManager* const Inv = PlayerInventory();
                if (Inv == nullptr) return "ERR noplayer";
                Inv->AdjustResource(static_cast<unsigned char>(R.Args[0]), R.Args[1], TRUE, TRUE);
                return "";
            }
            return "ERR badop";
        }

        // TXN <index> <op> <args>: apply item <index> exactly once. The grant and the received-index update run in the
        // same game-thread step, so no save can hold one without the other.
        std::string ExecuteTxn(Request const& R)
        {
            UBioGlobalVariableTable* const Vars = GlobalVariables();
            if (Vars == nullptr) return "ERR noworld";
            int const Current = Vars->GetInt(ReceivedIndexInt);
            if (R.Index < Current) return "OK done";
            if (R.Index > Current) return "ERR gap " + std::to_string(Current);
            std::string const Error = ApplyTxnOp(R, Vars);
            if (!Error.empty()) return Error;
            Vars->SetInt(ReceivedIndexInt, Current + 1);
            LEASI_INFO("TXN {} {} {} {} -> applied", R.Index, R.TxnOp, R.Args[0], R.Args[1]);
            return "OK applied";
        }

        std::string ExecuteNote(Request const& R)
        {
            // LE2's notifier signature is not yet verified in game (SCOPE R-runtime); until it is, the text goes to the
            // log only and the client turns notices off when it sees this error.
            LEASI_INFO(L"NOTE {}", R.Text.c_str());
            return "ERR unsupported";
        }

        std::string ExecuteMap()
        {
            ABioWorldInfo* const BioWorld = CurrentBioWorld();
            if (BioWorld == nullptr) return "ERR noworld";
            UObject* Outermost = BioWorld;
            for (int Depth = 0; Outermost->Outer != nullptr && Depth < 16; ++Depth) Outermost = Outermost->Outer;
            FString const Name = Outermost->GetName();
            std::string Text{};
            for (wchar_t const* C = Name.Chars(); C != nullptr && *C != L'\0' && Text.size() < 128; ++C)
                Text += (*C >= 0x20 && *C < 0x7F) ? static_cast<char>(*C) : '?';
            return Text.empty() ? "ERR noname" : "OK " + Text;
        }

        // Plot reads and writes wait for a loaded save. The main-menu and loading worlds have a blank plot table, and the
        // client bound one before the real save loaded over it (seen live 2026-10-24). A player pawn with an inventory
        // means a save or a new career is in play.
        bool SaveLoaded() { return PlayerInventory() != nullptr; }

        std::string Execute(Request const& R)
        {
            std::string const Op{ R.Op };
            if (Op == "NOTE") return ExecuteNote(R);
            if (Op == "MAP") return ExecuteMap();
            if (!SaveLoaded()) return GlobalVariables() == nullptr ? "ERR noworld" : "ERR notready";
            if (Op == "TXN") return ExecuteTxn(R);
            UBioGlobalVariableTable* const Vars = GlobalVariables();
            if (Vars == nullptr) return "ERR noworld";
            if (Op == "GETB") return std::string("OK ") + (Vars->GetBool(R.Index) ? "1" : "0");
            if (Op == "GETI") return "OK " + std::to_string(Vars->GetInt(R.Index));
            if (Op == "GETIS")
            {
                std::string Ints = "OK";
                for (int i = 0; i < R.Count; ++i) Ints += " " + std::to_string(Vars->GetInt(R.Many[i]));
                return Ints;
            }
            if (Op == "TAKEI")
            {
                int const Value = Vars->GetInt(R.Index);
                if (Value != 0) Vars->SetInt(R.Index, 0);
                if (Value != 0) LEASI_INFO("TAKEI {} -> {}", R.Index, Value);
                return "OK " + std::to_string(Value);
            }
            if (Op == "SETI")
            {
                Vars->SetInt(R.Index, R.Value);
                LEASI_INFO("SETI {} {}", R.Index, R.Value);
                return "OK";
            }
            if (Op == "GETBS")
            {
                std::string Bits = "OK ";
                for (int i = 0; i < R.Count; ++i) Bits += Vars->GetBool(R.Many[i]) ? '1' : '0';
                return Bits;
            }
            if (Op == "ID")
                return "OK " + std::to_string(Vars->GetInt(IdentitySeedInt)) + " " + std::to_string(Vars->GetInt(IdentitySlotInt));
            if (Op == "IDSET")
            {
                // Only an unbound save that has received nothing can be bound (a mismatched save is never rebound).
                if (Vars->GetInt(IdentitySeedInt) != 0 || Vars->GetInt(IdentitySlotInt) != 0 || Vars->GetInt(ReceivedIndexInt) != 0)
                    return "ERR bound";
                Vars->SetInt(IdentitySeedInt, R.Index);
                Vars->SetInt(IdentitySlotInt, R.Value);
                LEASI_INFO("IDSET {} {}", R.Index, R.Value);
                return "OK";
            }
            if (Op == "HIST")
            {
                // Same guard as IDSET: only an unbound save that has received nothing.
                if (Vars->GetInt(IdentitySeedInt) != 0 || Vars->GetInt(IdentitySlotInt) != 0 || Vars->GetInt(ReceivedIndexInt) != 0)
                    return "ERR bound";
                Vars->SetBool(R.Index, R.Value != 0 ? 1 : 0, 0);
                LEASI_INFO("HIST {} {}", R.Index, R.Value);
                return "OK";
            }
            if (Op == "SETB")
            {
                Vars->SetBool(R.Index, R.Value != 0 ? 1 : 0, 0);
                LEASI_INFO("SETB {} {}", R.Index, R.Value);
                return "OK";
            }
            if (Op == "COND")
            {
                ABioWorldInfo* const BioWorld = CurrentBioWorld();
                if (BioWorld == nullptr) return "ERR noworld";
                bool const Result = BioWorld->CheckConditional(R.Index, 0);
                LEASI_INFO("COND {} -> {}", R.Index, Result ? 1 : 0);
                return std::string("OK ") + (Result ? "1" : "0");
            }
            if (Op == "CONDCLS")
            {
                ABioWorldInfo* const BioWorld = CurrentBioWorld();
                if (BioWorld == nullptr) return "ERR noworld";
                std::string Text = "OK";
                for (decltype(BioWorld->ConditionalClasses.Count()) i = 0; i < BioWorld->ConditionalClasses.Count() && Text.size() < 3000; ++i)
                {
                    Text += ' ';
                    for (wchar_t const* C = BioWorld->ConditionalClasses(i).Chars(); C != nullptr && *C != L'\0'; ++C)
                        Text += (*C > 0x20 && *C < 0x7F) ? static_cast<char>(*C) : '?';
                }
                return Text;
            }
            return "ERR badop";
        }

        // Parses and validates on the pipe thread; returns an error reply, or "" if the request must run in game.
        std::string Parse(char const* Text, Request& R)
        {
            if (std::strncmp(Text, "NOTE ", 5) == 0)
            {
                std::strcpy(R.Op, "NOTE");
                char const* const Body = Text + 5;
                int const Bytes = static_cast<int>(std::strlen(Body));
                if (Bytes < 1 || Bytes > 300) return "ERR notallowed";
                for (int i = 0; i < Bytes; ++i)
                    if (static_cast<unsigned char>(Body[i]) < 0x20 || static_cast<unsigned char>(Body[i]) > 0x7E) return "ERR notallowed";
                R.Text.assign(Body, Body + Bytes);
                return "";
            }
            if (std::strncmp(Text, "GETBS ", 6) == 0)
            {
                std::strcpy(R.Op, "GETBS");
                char const* Cursor = Text + 6;
                int Value = 0, Consumed = 0;
                while (std::sscanf(Cursor, "%d%n", &Value, &Consumed) == 1)
                {
                    if (R.Count >= GetBsMax || Value < 0) return "ERR notallowed";
                    R.Many[R.Count++] = Value;
                    Cursor += Consumed;
                }
                return R.Count > 0 ? "" : "ERR badrequest";
            }
            if (std::strncmp(Text, "GETIS ", 6) == 0)
            {
                std::strcpy(R.Op, "GETIS");
                char const* Cursor = Text + 6;
                int Value = 0, Consumed = 0;
                while (std::sscanf(Cursor, "%d%n", &Value, &Consumed) == 1)
                {
                    if (R.Count >= GetBsMax || Value < 0) return "ERR notallowed";
                    R.Many[R.Count++] = Value;
                    Cursor += Consumed;
                }
                return R.Count > 0 ? "" : "ERR badrequest";
            }
            if (std::strncmp(Text, "TXN ", 4) == 0)
            {
                std::strcpy(R.Op, "TXN");
                int const Fields = std::sscanf(Text + 4, "%d %7s %d %d %d", &R.Index, R.TxnOp, &R.Args[0], &R.Args[1], &R.Args[2]);
                if (Fields < 2 || R.Index < 0) return "ERR badrequest";
                std::string const TxnOp{ R.TxnOp };
                int const Args = Fields - 2;
                if (TxnOp == "NONE" && Args == 0) return "";
                if (TxnOp == "FLAG" && Args == 1) return (R.Args[0] >= BoolMin && R.Args[0] <= BoolMax) ? "" : "ERR notallowed";
                if (TxnOp == "SHIP" && Args == 2) return IsShipPair(R.Args[0], R.Args[1]) ? "" : "ERR notallowed";
                if (TxnOp == "WEAPON" && Args == 1) return IsWeaponInt(R.Args[0]) ? "" : "ERR notallowed";
                if (TxnOp == "RES" && Args == 2)
                    return (IsResourceType(R.Args[0]) && R.Args[1] >= 1 && R.Args[1] <= ResourceAmountMax)
                        ? "" : "ERR notallowed";
                return "ERR badrequest";
            }
            int const Fields = std::sscanf(Text, "%7s %d %d", R.Op, &R.Index, &R.Value);
            std::string const Op{ R.Op };
            if (Fields >= 1 && Op == "PING") return "OK pong";
            if (Fields == 2 && Op == "HELLO")   // the client names its protocol; the bridge answers with its own
                return "OK " TOSTRING(ASI_PROTOCOL) " LE2";
            if (Fields == 1 && Op == "VER") return "OK " TOSTRING(ASI_VERSION);
            if (Fields == 1 && (Op == "MAP" || Op == "ID")) return "";
            if ((Op == "GETB" || Op == "GETI") && Fields == 2) return R.Index >= 0 ? "" : "ERR notallowed";
            if (Op == "IDSET" && Fields == 3) return (R.Index > 0 && R.Value > 0) ? "" : "ERR notallowed";
            if (Op == "HIST" && Fields == 3) return (IsHistoryBool(R.Index) && (R.Value == 0 || R.Value == 1)) ? "" : "ERR notallowed";
            if (Op == "SETB" && Fields == 3)   // derived state the client recomputes each poll (e.g. 21100 IFF open)
                return ((R.Index >= BoolMin && R.Index <= BoolMax && (R.Value == 0 || R.Value == 1))
                        || (IsDossierJournalBool(R.Index) && R.Value == 1)) ? "" : "ERR notallowed";
            if (Op == "TAKEI" && Fields == 2) return (R.Index >= SalvageBoughtMin && R.Index <= SalvageBoughtMax) ? "" : "ERR notallowed";
            if (Op == "SETI" && Fields == 3)
                return (R.Index >= SalvageCapMin && R.Index <= SalvageCapMax && R.Value >= 0 && R.Value <= SalvageCapValueMax) ? "" : "ERR notallowed";
            // Diagnostics (read-only): evaluate a plot conditional, list the registered conditional classes.
            if (Op == "COND" && Fields == 2) return R.Index >= 0 ? "" : "ERR notallowed";
            if (Fields == 1 && Op == "CONDCLS") return "";
            return "ERR badrequest";
        }

        void Reply(HANDLE Pipe, std::string const& Text)
        {
            DWORD Written = 0;
            WriteFile(Pipe, Text.c_str(), static_cast<DWORD>(Text.size()), &Written, nullptr);
        }

        void PipeThread()
        {
            while (!g_Stop.load())
            {
                HANDLE Pipe = CreateNamedPipeW(PipeName, PIPE_ACCESS_DUPLEX,
                    PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT, 1, BufferSize, BufferSize, 0, nullptr);
                if (Pipe == INVALID_HANDLE_VALUE)
                {
                    LEASI_ERROR("CreateNamedPipe failed: {}", GetLastError());
                    return;
                }
                if (ConnectNamedPipe(Pipe, nullptr) != FALSE || GetLastError() == ERROR_PIPE_CONNECTED)
                {
                    LEASI_INFO("Client connected");
                    char Buffer[BufferSize]{};
                    DWORD Read = 0;
                    while (!g_Stop.load() && ReadFile(Pipe, Buffer, BufferSize - 1, &Read, nullptr) != FALSE)
                    {
                        Buffer[Read] = '\0';
                        auto* R = new Request{};
                        std::string Error = Parse(Buffer, *R);
                        if (!Error.empty())
                        {
                            delete R;
                            Reply(Pipe, Error);
                            continue;
                        }
                        std::future<std::string> Result = R->Reply.get_future();
                        g_Pending.push(R);   // ownership passes to the game thread
                        // A timed-out TXN may still apply later; the client's retry then gets "OK done", never a
                        // second grant, because the bridge compares the index on the game thread.
                        if (Result.wait_for(std::chrono::seconds(5)) == std::future_status::ready)
                            Reply(Pipe, Result.get());
                        else
                            Reply(Pipe, "ERR timeout");
                    }
                    LEASI_INFO("Client disconnected");
                }
                DisconnectNamedPipe(Pipe);
                CloseHandle(Pipe);
            }
        }
    }

    void StartPipeServer()
    {
        // Pin this module: the pipe thread lives for the whole process, so the ASI must never be unloaded under it.
        HMODULE Self = nullptr;
        GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
            reinterpret_cast<LPCWSTR>(&StartPipeServer), &Self);
        std::thread(PipeThread).detach();
        LEASI_INFO("Pipe server started (module pinned)");
    }

    void StopPipeServer()
    {
        g_Stop.store(true);
    }

    void ProcessPendingRequests()
    {
        if (t_InProcess) return;   // SDK calls re-enter ProcessEvent; do not nest
        t_InProcess = true;
        Request* R = nullptr;
        while (g_Pending.try_pop(R))
        {
            R->Reply.set_value(Execute(*R));
            delete R;
        }
        t_InProcess = false;
    }

    t_UObject_ProcessEvent* UObject_ProcessEvent_orig = nullptr;
    void UObject_ProcessEvent_hook(UObject* Context, UFunction* Function, void* Parms, void* Result)
    {
        ProcessPendingRequests();
        UObject_ProcessEvent_orig(Context, Function, Parms, Result);
    }
}

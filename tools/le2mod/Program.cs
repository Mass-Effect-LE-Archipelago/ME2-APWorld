// le2mod openstart <LE2 BioGame dir> <staging dir> [transition,transition..]
// Test build of the LE2 open start (owner request 2026-10-16): new career -> SR-2 at the galaxy map.
// Reads the runtime winner of BioP_Char.pcc (DLC_METR_Patch01 over the base game), and in its Main_Sequence:
//   ShowCharacterCreation "Finished" -> PMExecuteTransition x N -> BlackScreen -> loading movie -> AreaTransition,
//   with the AreaTransition retargeted from Biop_Procer to BioP_Nor / start_galaxyMap.
// Unless --keep-prologue, also overrides EntryMenu.pcc so a new career skips the SR-1 prologue (see SkipPrologue).
// Writes only under <staging dir>: a Mod Manager mod folder (moddesc.ini + DLC_MOD_ArchipelagoME2 with Mount.dlc,
// BIOEngine.ini, the DLC TLK and the edited BioP_Char.pcc). Never writes under the game or backup folder.
// Fails closed: the package is built in a temp folder, reopened and validated, then moved into place.
using LegendaryExplorerCore;
using LegendaryExplorerCore.Compression;
using LegendaryExplorerCore.GameFilesystem;
using LegendaryExplorerCore.Kismet;
using LegendaryExplorerCore.Packages;
using LegendaryExplorerCore.TLK;
using LegendaryExplorerCore.TLK.ME2ME3;
using LegendaryExplorerCore.Unreal;

static class Program
{
    const string ModFolder = "DLC_MOD_ArchipelagoME2";
    const string ModName = "ArchipelagoME2";
    const int ModuleNumber = 4100;           // DLC_4100_INT.tlk; vanilla LE2 modules seen: 10..2000
    const int NameStrRef = 41000000;         // the DLC's display name in its own TLK
    const int MountPriority = 4100;          // must sort above every vanilla DLC (checked below)
    const string Seq = "TheWorld.PersistentLevel.Main_Sequence";
    const string AreaNode = Seq + ".BioSeqAct_AreaTransition_1";
    const string CreatorNode = Seq + ".BioSeqAct_ShowCharacterCreation_0";
    const string BlackNode = Seq + ".BioSeqAct_BlackScreen_0";
    const string TargetArea = "BioP_Nor";
    const string TargetStart = "start_galaxyMap";
    // Default start state (le2.json labels; traced from BioD_ProCer_*/BioD_ProFre_*/BioD_Nor_117 on 2026-10-16):
    //   48 Henchmen/In_Party/Set_Leading_True (Jacob in party, selectable), 46 .../Set_Vixen_True (Miranda),
    //   2398 Training_Center quest complete, 2210 Talked_to_Illusive_Man, 2225 Post_Illusive_Man journal,
    //   2401 Freedom's Progress quest complete, 4813 StayingOnPlanet false, 2403 Main_quest_Begin journal.
    // Left out on purpose: 2371 dossiers (AP items), 5672 Go_To_Citadel (hub access is AP logic), XP/mission-done bools
    // 5794/5795 (they are AP checks), 4253 ProCer achievement.
    static readonly int[] DefaultTransitions = [48, 46, 2398, 2210, 2225, 2401, 4813, 2403];

    static string AreaName(ExportEntry area) =>
        area.GetProperty<NameProperty>("AreaName")?.Value.Instanced ?? area.GetProperty<StrProperty>("AreaName")?.Value ?? "";

    // EntryMenu (runtime winner DLC_METR_Patch01) has two vanilla routes out of the main menu:
    //   re_StartNewGame      -> InitLoadingMovies_1 -> AreaTransition_1 BioP_ProNor (the SR-1 prologue)
    //   re_StartCharCreation -> InitLoadingMovies_0 -> SetBool 6022 -> 5356, 5355, 5342 (starter codices, as ProNor's
    //                           Give_Starter_Codices) -> SetBool 6022 -> AreaTransition_0 Biop_Char
    // Gender is chosen in the main menu before either (RequestStartNewGame sets DefaultPlayer.bIsFemale). Skipping the
    // prologue points re_StartNewGame at the second route. Not fired: 5391 ProNor_Complete (achievement only).
    const string EntryEvent = Seq + ".SeqEvent_RemoteEvent_1";
    const string EntryProNorMovie = Seq + ".SFXSeqAct_InitLoadingMovies_1";
    const string EntryCharMovie = Seq + ".SFXSeqAct_InitLoadingMovies_0";
    static readonly int[] CharRouteTransitions = [5356, 5355, 5342];

    static ExportEntry Next(ExportEntry node) => KismetHelper.GetOutputLinksOfNode(node).FirstOrDefault()?.FirstOrDefault()?.LinkedOp as ExportEntry;

    // Follows the first output link from start to an AreaTransition; returns the transitions met and the area node.
    static (List<int> ids, ExportEntry area) Walk(ExportEntry start)
    {
        var ids = new List<int>();
        for (var node = start; node != null && ids.Count < 32; node = Next(node))
        {
            if (node.ClassName == "BioSeqAct_AreaTransition") return (ids, node);
            if (node.ClassName == "BioSeqAct_PMExecuteTransition") ids.Add(node.GetProperty<IntProperty>("m_nIndex").Value);
        }
        return (ids, null);
    }

    static int SkipPrologue(string bioGame, string cooked)
    {
        var source = new[] { Path.Combine(bioGame, "DLC", "DLC_METR_Patch01", "CookedPCConsole", "EntryMenu.pcc"),
                             Path.Combine(bioGame, "CookedPCConsole", "EntryMenu.pcc") }.FirstOrDefault(File.Exists);
        if (source == null) { Console.Error.WriteLine("refusing: no EntryMenu.pcc under " + bioGame); return 1; }
        var outPcc = Path.Combine(cooked, "EntryMenu.pcc");
        using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
        {
            var ev = pcc.FindExport(EntryEvent);
            var pronorMovie = pcc.FindExport(EntryProNorMovie);
            var charMovie = pcc.FindExport(EntryCharMovie);
            var (pronorIds, pronorArea) = pronorMovie == null ? (new List<int>(), null) : Walk(pronorMovie);
            var (charIds, charArea) = charMovie == null ? (new List<int>(), null) : Walk(charMovie);
            if (pcc.Game != MEGame.LE2 || ev == null || ev.GetProperty<NameProperty>("EventName")?.Value.Instanced != "re_StartNewGame"
                || Next(ev) != pronorMovie || pronorIds.Count != 0 || pronorArea == null || AreaName(pronorArea) != "BioP_ProNor"
                || !charIds.SequenceEqual(CharRouteTransitions) || charArea == null
                || !AreaName(charArea).Equals("BioP_Char", StringComparison.OrdinalIgnoreCase))
            {
                Console.Error.WriteLine("refusing: EntryMenu does not have the expected vanilla new-game routes");
                return 1;
            }
            var links = KismetHelper.GetOutputLinksOfNode(ev);
            links[0].Clear();
            KismetHelper.WriteOutputLinksToNode(ev, links);
            KismetHelper.CreateOutputLink(ev, "Out", charMovie);
            pcc.Save(outPcc);
        }
        using (var check = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
        {
            var ev = check.FindExport(EntryEvent);
            var first = ev == null ? null : Next(ev);
            var (ids, area) = first == null ? (new List<int>(), null) : Walk(first);
            bool ok = first?.InstancedFullPath == EntryCharMovie && KismetHelper.GetOutputLinksOfNode(ev)[0].Count == 1
                      && ids.SequenceEqual(CharRouteTransitions) && area != null && AreaName(area).Equals("BioP_Char", StringComparison.OrdinalIgnoreCase);
            Console.WriteLine($"validate: re_StartNewGame -> {first?.ObjectName.Instanced} chain=[{string.Join(",", ids)}] -> {(area == null ? "?" : AreaName(area))}");
            if (!ok) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
        }
        Console.WriteLine($"prologue skipped (source {source})");
        return 0;
    }

    static int Main(string[] args)
    {
        var oodle = Environment.GetEnvironmentVariable("LE1PROBE_OODLE");
        bool keepPrologue = args.Contains("--keep-prologue");
        args = args.Where(a => a != "--keep-prologue").ToArray();
        if (args.Length is < 3 or > 4 || args[0] != "openstart" || string.IsNullOrEmpty(oodle))
        {
            Console.Error.WriteLine("usage: le2mod openstart <LE2 BioGame dir> <staging dir> [transition,..] [--keep-prologue]  (LE1PROBE_OODLE set)");
            return 2;
        }
        var bioGame = Path.GetFullPath(args[1]);
        var staging = Path.GetFullPath(args[2]);
        var transitions = args.Length == 4 ? args[3].Split(',').Select(int.Parse).ToArray() : DefaultTransitions;
        if (staging.StartsWith(bioGame, StringComparison.OrdinalIgnoreCase) || staging.Contains(@"\BioGame", StringComparison.OrdinalIgnoreCase))
        {
            Console.Error.WriteLine("refusing: staging must be outside any BioGame folder");
            return 2;
        }
        var source = new[] { Path.Combine(bioGame, "DLC", "DLC_METR_Patch01", "CookedPCConsole", "BioP_Char.pcc"),
                             Path.Combine(bioGame, "CookedPCConsole", "BioP_Char.pcc") }.FirstOrDefault(File.Exists);
        if (source == null) { Console.Error.WriteLine("refusing: no BioP_Char.pcc under " + bioGame); return 2; }

        // Mount priority check against every vanilla DLC.
        int highest = 0;
        foreach (var mount in Directory.EnumerateFiles(Path.Combine(bioGame, "DLC"), "Mount.dlc", SearchOption.AllDirectories))
        {
            if (mount.Contains("DLC_MOD_", StringComparison.OrdinalIgnoreCase)) continue;
            int p = MountFile.GetMountPriority(mount);
            Console.WriteLine($"mount {p,5}  {Path.GetFileName(Path.GetDirectoryName(Path.GetDirectoryName(mount)))}");
            highest = Math.Max(highest, p);
        }
        if (MountPriority <= highest) { Console.Error.WriteLine($"refusing: mount priority {MountPriority} <= vanilla {highest}"); return 1; }

        OodleHelper.LoadOodleDll(oodle);
        LegendaryExplorerCoreLib.InitLib(TaskScheduler.Default);

        var modRoot = Path.Combine(staging, ModName);
        var tmp = modRoot + ".tmp";
        if (Directory.Exists(tmp)) Directory.Delete(tmp, true);
        var cooked = Path.Combine(tmp, ModFolder, "CookedPCConsole");
        Directory.CreateDirectory(cooked);
        var outPcc = Path.Combine(cooked, "BioP_Char.pcc");

        using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
        {
            if (pcc.Game != MEGame.LE2) { Console.Error.WriteLine($"refusing: {source} is {pcc.Game}"); return 1; }
            var seq = pcc.FindExport(Seq);
            var area = pcc.FindExport(AreaNode);
            var creator = pcc.FindExport(CreatorNode);
            var black = pcc.FindExport(BlackNode);
            if (seq == null || area == null || creator == null || black == null
                || !AreaName(area).Equals("Biop_Procer", StringComparison.OrdinalIgnoreCase))
            {
                Console.Error.WriteLine("refusing: BioP_Char does not have the expected vanilla creator sequence");
                return 1;
            }

            var chain = new List<ExportEntry>();
            foreach (var id in transitions)
            {
                var node = SequenceObjectCreator.CreateSequenceObject(seq, "BioSeqAct_PMExecuteTransition");
                node.WriteProperty(new IntProperty(id, "m_nIndex"));
                chain.Add(node);
            }
            // Creator "Finished" -> transitions -> black screen (the rest of the vanilla chain is unchanged).
            var links = KismetHelper.GetOutputLinksOfNode(creator);
            int finished = KismetHelper.GetOutputLinkNames(creator).IndexOf("Finished");
            if (finished < 0 || links[finished].Count != 1 || links[finished][0].LinkedOp != black)
            {
                Console.Error.WriteLine("refusing: creator Finished does not lead to the black screen");
                return 1;
            }
            links[finished].Clear();
            KismetHelper.WriteOutputLinksToNode(creator, links);
            KismetHelper.CreateOutputLink(creator, "Finished", chain[0]);
            // New nodes carry no serialized OutputLinks (the class default "Out" applies), so write the "Out" link.
            for (int i = 0; i + 1 < chain.Count; i++) KismetHelper.CreateNewOutputLink(chain[i], "Out", chain[i + 1]);
            KismetHelper.CreateNewOutputLink(chain[^1], "Out", black);

            // Same property type as the vanilla value (NameProperty in LE2, StrProperty elsewhere).
            if (area.GetProperty<NameProperty>("AreaName") != null) area.WriteProperty(new NameProperty(TargetArea, "AreaName"));
            else area.WriteProperty(new StrProperty(TargetArea, "AreaName"));
            area.WriteProperty(new NameProperty(TargetStart, "StartPoint"));
            pcc.Save(outPcc);
        }

        // Reopen and validate.
        using (var check = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
        {
            var area = check.FindExport(AreaNode);
            var creator = check.FindExport(CreatorNode);
            bool ok = area != null && AreaName(area) == TargetArea
                      && area.GetProperty<NameProperty>("StartPoint")?.Value.Instanced == TargetStart;
            var ids = new List<int>();
            var node = creator == null ? null : KismetHelper.GetOutputLinksOfNode(creator)[0].FirstOrDefault()?.LinkedOp as ExportEntry;
            while (node != null && node.ClassName == "BioSeqAct_PMExecuteTransition")
            {
                ids.Add(node.GetProperty<IntProperty>("m_nIndex").Value);
                node = KismetHelper.GetOutputLinksOfNode(node)[0].FirstOrDefault()?.LinkedOp as ExportEntry;
            }
            ok &= ids.SequenceEqual(transitions) && node?.InstancedFullPath == BlackNode;
            Console.WriteLine($"validate: area={(area == null ? "?" : AreaName(area))}/{area?.GetProperty<NameProperty>("StartPoint")?.Value.Instanced} chain=[{string.Join(",", ids)}] -> {node?.ObjectName.Instanced}");
            if (!ok) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
        }
        if (!keepPrologue && SkipPrologue(bioGame, cooked) != 0) return 1;

        // DLC metadata, as vanilla LE2 DLC folders lay it out.
        var mountFile = new MountFile(MEGame.LE2)
        {
            MountPriority = MountPriority,
            TLKID = NameStrRef,
            ME2Only_DLCFolderName = ModFolder,
            ME2Only_DLCHumanName = "Archipelago ME2 (open start test)",
            MountFlags = new MountFlag(0, true),
        };
        mountFile.WriteMountFile(Path.Combine(cooked, "Mount.dlc"));
        File.WriteAllText(Path.Combine(cooked, "BIOEngine.ini"),
            $"[Engine.DLCModules]\r\n{ModFolder}={ModuleNumber}\r\n\r\n[DLCInfo]\r\nVersion=0\r\nFlags=2\r\nName={NameStrRef}\r\n");
        HuffmanCompression.SaveToTlkFile(Path.Combine(cooked, $"DLC_{ModuleNumber}_INT.tlk"),
            [new TLKStringRef(NameStrRef, "Archipelago ME2 (open start test)")]);
        File.WriteAllText(Path.Combine(tmp, "moddesc.ini"),
            "[ModManager]\r\ncmmver = 8.0\r\n\r\n[ModInfo]\r\ngame = LE2\r\nmodname = Archipelago ME2 open start (TEST)\r\n" +
            "moddesc = Test build: a new career skips the SR-1 prologue and goes from the character creator straight to the Normandy SR-2 galaxy map.\r\n" +
            "modver = 0.0.2\r\nmoddev = Jerrod\r\n\r\n[CUSTOMDLC]\r\nsourcedirs = " + ModFolder + "\r\ndestdirs = " + ModFolder + "\r\n");

        if (Directory.Exists(modRoot)) Directory.Delete(modRoot, true);
        Directory.Move(tmp, modRoot);
        Console.WriteLine($"staged {modRoot} (source {source})");
        return 0;
    }
}

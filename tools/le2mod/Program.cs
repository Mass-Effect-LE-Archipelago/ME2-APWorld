// le2mod openstart <LE2 BioGame dir> <staging dir> [transition,transition..]
// Test build of the LE2 open start (owner request 2026-10-16): new career -> SR-2 at the galaxy map.
// Reads the runtime winner of BioP_Char.pcc (DLC_METR_Patch01 over the base game), and in its Main_Sequence:
//   ShowCharacterCreation "Finished" -> PMExecuteTransition x N -> BlackScreen -> loading movie -> AreaTransition,
//   with the AreaTransition retargeted from Biop_Procer to BioP_Nor / start_galaxyMap.
// Unless --keep-prologue, also overrides BioP_ProNor.pcc (and EntryMenu.pcc) so a new career skips the movies, the SR-1
// prologue and Genesis (see SkipProNor, SkipPrologue). Every source is the runtime winner by mount priority (Winner).
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

    // The runtime winner of a package: the copy in the highest-mounting vanilla DLC that has it, else the base game.
    // (DLC_DHME1, mount 375, ships its own BioP_ProNor with the Genesis comic; DLC_METR_Patch01, 2000, has none.)
    static string Winner(string bioGame, string file) =>
        Directory.EnumerateFiles(Path.Combine(bioGame, "DLC"), "Mount.dlc", SearchOption.AllDirectories)
            .Where(m => !m.Contains("DLC_MOD_", StringComparison.OrdinalIgnoreCase))
            .Select(m => (p: MountFile.GetMountPriority(m), f: Path.Combine(Path.GetDirectoryName(m)!, file)))
            .Where(x => File.Exists(x.f)).OrderByDescending(x => x.p).Select(x => x.f).FirstOrDefault()
        ?? new[] { Path.Combine(bioGame, "CookedPCConsole", file) }.FirstOrDefault(File.Exists);

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
        var source = Winner(bioGame, "EntryMenu.pcc");
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

    // In game (2026-10-16) the EntryMenu override did not take: the prologue still played, as EntryMenu loads before the
    // custom DLC mounts. BioP_ProNor loads after, like BioP_Char. Its persistent Main_Sequence reaches the opening only
    // through BlackScreen_0 (after the first-run options screen) -> CompareBool SaveDataImport -> ... ->
    // RE_persistent_to_levelscript, which starts BioD_ProNor's ME2_Opening. BlackScreen_0's outputs are pointed at
    // 5356, 5355, 5342 -> BioSeqAct_ActivateCharacterCreation (BioP_Char), the end of the vanilla prologue.
    const string ProNorBlack = Seq + ".BioSeqAct_BlackScreen_0";
    const string ProNorCheck = Seq + ".SeqCond_CompareBool_0";

    static int SkipProNor(string bioGame, string cooked)
    {
        var source = Winner(bioGame, "BioP_ProNor.pcc");
        if (source == null) { Console.Error.WriteLine("refusing: no BioP_ProNor.pcc under " + bioGame); return 1; }
        var outPcc = Path.Combine(cooked, "BioP_ProNor.pcc");
        using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
        {
            var seq = pcc.FindExport(Seq);
            var black = pcc.FindExport(ProNorBlack);
            var check = pcc.FindExport(ProNorCheck);
            var links = black == null ? null : KismetHelper.GetOutputLinksOfNode(black);
            if (pcc.Game != MEGame.LE2 || seq == null || check == null || links == null || links.Count != 3
                || links.Any(l => l.Count != 1 || l[0].LinkedOp != check)
                || !pcc.Exports.Any(e => e.ClassName == "SeqAct_ActivateRemoteEvent" && e.GetProperty<NameProperty>("EventName")?.Value.Instanced == "RE_persistent_to_levelscript"))
            {
                Console.Error.WriteLine("refusing: BioP_ProNor does not have the expected vanilla opening chain");
                return 1;
            }
            var chain = CharRouteTransitions.Select(id =>
            {
                var node = SequenceObjectCreator.CreateSequenceObject(seq, "BioSeqAct_PMExecuteTransition");
                node.WriteProperty(new IntProperty(id, "m_nIndex"));
                return node;
            }).ToList();
            var activate = SequenceObjectCreator.CreateSequenceObject(seq, "BioSeqAct_ActivateCharacterCreation");
            foreach (var l in links) l.Clear();
            KismetHelper.WriteOutputLinksToNode(black, links);
            foreach (var name in KismetHelper.GetOutputLinkNames(black)) KismetHelper.CreateOutputLink(black, name, chain[0]);
            for (int i = 0; i + 1 < chain.Count; i++) KismetHelper.CreateNewOutputLink(chain[i], "Out", chain[i + 1]);
            KismetHelper.CreateNewOutputLink(chain[^1], "Out", activate);
            pcc.Save(outPcc);
        }
        using (var pcc = MEPackageHandler.OpenMEPackage(outPcc, forceLoadFromDisk: true))
        {
            var black = pcc.FindExport(ProNorBlack);
            var links = black == null ? null : KismetHelper.GetOutputLinksOfNode(black);
            var first = links?.FirstOrDefault()?.FirstOrDefault()?.LinkedOp as ExportEntry;
            var ids = new List<int>();
            var node = first;
            while (node?.ClassName == "BioSeqAct_PMExecuteTransition") { ids.Add(node.GetProperty<IntProperty>("m_nIndex").Value); node = Next(node); }
            // Nothing may still lead into the SaveDataImport check, which is the only way on to the opening.
            var check = pcc.FindExport(ProNorCheck);
            bool orphaned = check != null && !pcc.Exports.Where(e => e.ClassName.Contains("Seq") && e != check && e.GetProperty<ArrayProperty<StructProperty>>("OutputLinks") != null)
                .Any(e => KismetHelper.GetOutputLinksOfNode(e).Any(l => l.Any(x => x.LinkedOp == check)));
            bool ok = links != null && links.Count == 3 && links.All(l => l.Count == 1 && l[0].LinkedOp == first)
                      && ids.SequenceEqual(CharRouteTransitions) && node?.ClassName == "BioSeqAct_ActivateCharacterCreation" && orphaned;
            Console.WriteLine($"validate: ProNor BlackScreen_0 -> [{string.Join(",", ids)}] -> {node?.ClassName} opening-orphaned={orphaned}");
            if (!ok) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
        }
        Console.WriteLine($"ProNor opening skipped (source {source})");
        return 0;
    }

    // Galaxy-map gating (research/galaxy_gating.md section 3). Our conditionals live in Startup_ArchipelagoME2_INT.pcc as
    // PlotManagerDLC_ArchipelagoME2.BioAutoConditionals, registered the way vanilla DLCs do it (BIOEngine.ini
    // StartupPackages, BIOGame.ini BioWorldInfo.ConditionalClasses). Each keeps the vanilla body and ANDs the AP bool.
    // Vanilla conditional ids are 1..2050, so ours reuse the AP bool numbers (dossier 21000+i, Reaper 21100).
    const string CondPackage = "PlotManagerDLC_ArchipelagoME2";
    const string CondAutoPackage = "PlotManagerAutoDLC_ArchipelagoME2";
    const string StartupName = "Startup_ArchipelagoME2";
    const string CondTemplateDlc = "DLC_CON_Pack01";   // smallest vanilla startup package: 3 conditionals, empty-ish maps
    // MapName -> (vanilla conditional, ours, AP bool, vanilla body)
    static readonly (string map, int vanilla, int ours, string body)[] Gates =
    [
        ("BioP_PrsCvA", 177, 21002, "gv.GetBool(35) == FALSE && gv.GetBool(197) == FALSE"),               // Jack, Purgatory
        ("BioP_JnkKgA", 182, 21003, "gv.GetBool(618) == FALSE"),                                          // Grunt, Korlus
        ("BioP_SunTlA", 181, 21006, "gv.GetBool(312) == TRUE && gv.GetBool(40) == FALSE && gv.GetBool(202) == FALSE"), // Tali, Haestrom
        ("BioP_RprGtA", 178, 21100, "gv.GetBool(313) == TRUE && gv.GetBool(1256) == FALSE"),              // Derelict Reaper
    ];
    const string GalaxyFile = "BioD_Nor_103aGalaxyMap.pcc";

    static int Gating(string bioGame, string cooked)
    {
        // 1. Conditionals: clone the template DLC's startup package, rename its packages, recompile the class.
        var template = Path.Combine(bioGame, "DLC", CondTemplateDlc, "CookedPCConsole", $"Startup_{CondTemplateDlc[4..]}_INT.pcc");
        if (!File.Exists(template)) { Console.Error.WriteLine("refusing: no template " + template); return 1; }
        var startupOut = Path.Combine(cooked, StartupName + "_INT.pcc");
        var script = "Class BioAutoConditionals extends BioConditionals;\n\n" + string.Concat(Gates.Select(g =>
            $"public function bool F{g.ours}(BioWorldInfo bioWorld, int Argument)\n{{\n    local BioGlobalVariableTable gv;\n    \n" +
            $"    gv = bioWorld.GetGlobalVariables();\n    return {g.body} && gv.GetBool({g.ours}) == TRUE;\n}}\n"));
        using (var pcc = MEPackageHandler.OpenMEPackage(template, forceLoadFromDisk: true))
        {
            var condPkg = pcc.Exports.FirstOrDefault(e => e.ClassName == "Package" && e.ObjectName.Name == "PlotManagerDLC_" + CondTemplateDlc[4..]);
            var autoPkg = pcc.Exports.FirstOrDefault(e => e.ClassName == "Package" && e.ObjectName.Name == "PlotManagerAutoDLC_" + CondTemplateDlc[4..]);
            if (pcc.Game != MEGame.LE2 || condPkg == null || autoPkg == null) { Console.Error.WriteLine("refusing: unexpected template layout"); return 1; }
            condPkg.ObjectName = new NameReference(CondPackage);
            autoPkg.ObjectName = new NameReference(CondAutoPackage);
            // The template's plot maps stay but are never registered (no +Package line for the Auto package).
            var cls = pcc.FindExport(CondPackage + ".BioAutoConditionals");
            LE2Directory.DefaultGamePath = bioGame;   // the compiler resolves SFXGame and the other base classes from here
            var lib = new LegendaryExplorerCore.UnrealScript.FileLib(pcc);
            var usop = new LegendaryExplorerCore.UnrealScript.UnrealScriptOptionsPackage();
            if (cls == null || !lib.Initialize(usop))
            {
                Console.Error.WriteLine("refusing: cannot load the script library\n" + string.Join("\n", lib.InitializationLog?.AllErrors ?? []));
                return 1;
            }
            var (_, log) = LegendaryExplorerCore.UnrealScript.UnrealScriptCompiler.CompileClass(pcc, script, lib, usop, cls, condPkg);
            if (log.HasErrors) { Console.Error.WriteLine("compile FAILED:\n" + string.Join("\n", log.AllErrors)); return 1; }
            pcc.Save(startupOut);
        }
        using (var pcc = MEPackageHandler.OpenMEPackage(startupOut, forceLoadFromDisk: true))
        {
            var fns = pcc.Exports.Where(e => e.ClassName == "Function" && e.Parent?.InstancedFullPath == CondPackage + ".BioAutoConditionals")
                .Select(e => e.ObjectName.Instanced).OrderBy(n => n).ToList();
            var want = Gates.Select(g => "F" + g.ours).OrderBy(n => n).ToList();
            bool stale = pcc.Exports.Any(e => e.InstancedFullPath.Contains(CondTemplateDlc[4..]) && e.ClassName != "ShaderCache");
            Console.WriteLine($"validate: {StartupName}_INT functions [{string.Join(",", fns)}] template-names-left={stale}");
            if (!fns.SequenceEqual(want) || stale) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
        }

        // 2. Galaxy map: the runtime winner with the four planets' land/visible conditionals repointed.
        var galaxy = Winner(bioGame, GalaxyFile);
        if (galaxy == null) { Console.Error.WriteLine("refusing: no " + GalaxyFile); return 1; }
        var galaxyOut = Path.Combine(cooked, GalaxyFile);
        string[] condProps = ["PlanetLandCondition", "VisibleConditional", "UsableConditional"];
        ExportEntry Planet(IMEPackage p, string map) => p.Exports.SingleOrDefault(e => e.ClassName == "BioPlanet"
            && string.Equals(e.GetProperty<StrProperty>("MapName")?.Value, map, StringComparison.OrdinalIgnoreCase));
        using (var pcc = MEPackageHandler.OpenMEPackage(galaxy, forceLoadFromDisk: true))
        {
            foreach (var g in Gates)
            {
                var planet = Planet(pcc, g.map);
                if (planet == null || planet.GetProperty<IntProperty>("PlanetLandCondition")?.Value != g.vanilla)
                {
                    Console.Error.WriteLine($"refusing: {g.map} is missing or its land conditional is not {g.vanilla}");
                    return 1;
                }
                foreach (var name in condProps)
                    if (planet.GetProperty<IntProperty>(name)?.Value == g.vanilla) planet.WriteProperty(new IntProperty(g.ours, name));
            }
            pcc.Save(galaxyOut);
        }
        using (var pcc = MEPackageHandler.OpenMEPackage(galaxyOut, forceLoadFromDisk: true))
        {
            foreach (var g in Gates)
            {
                var planet = Planet(pcc, g.map);
                var values = condProps.Select(n => planet?.GetProperty<IntProperty>(n)?.Value).ToList();
                Console.WriteLine($"validate: {g.map} land/visible/usable = {string.Join("/", values.Select(v => v?.ToString() ?? "-"))}");
                if (values[0] != g.ours || values.Any(v => v == g.vanilla)) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
            }
        }
        Console.WriteLine($"galaxy gating built (galaxy source {galaxy})");
        return 0;
    }

    static int Main(string[] args)
    {
        var oodle = Environment.GetEnvironmentVariable("LE1PROBE_OODLE");
        bool keepPrologue = args.Contains("--keep-prologue");
        bool noGating = args.Contains("--no-gating");
        args = args.Where(a => a != "--keep-prologue" && a != "--no-gating").ToArray();
        if (args.Length is < 3 or > 4 || args[0] != "openstart" || string.IsNullOrEmpty(oodle))
        {
            Console.Error.WriteLine("usage: le2mod openstart <LE2 BioGame dir> <staging dir> [transition,..] [--keep-prologue] [--no-gating]  (LE1PROBE_OODLE set)");
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
        var source = Winner(bioGame, "BioP_Char.pcc");
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
        if (!keepPrologue && (SkipPrologue(bioGame, cooked) != 0 || SkipProNor(bioGame, cooked) != 0)) return 1;
        if (!noGating && Gating(bioGame, cooked) != 0) return 1;

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
            $"[Engine.DLCModules]\r\n{ModFolder}={ModuleNumber}\r\n\r\n[DLCInfo]\r\nVersion=0\r\nFlags=2\r\nName={NameStrRef}\r\n" +
            (noGating ? "" : $"\r\n[Engine.StartupPackages]\r\n+DLCStartupPackage={StartupName}\r\n+Package={CondPackage}\r\n"));
        if (!noGating)
            File.WriteAllText(Path.Combine(cooked, "BIOGame.ini"), $"[SFXGame.BioWorldInfo]\r\n+ConditionalClasses={CondPackage}.BioAutoConditionals\r\n");
        HuffmanCompression.SaveToTlkFile(Path.Combine(cooked, $"DLC_{ModuleNumber}_INT.tlk"),
            [new TLKStringRef(NameStrRef, "Archipelago ME2 (open start test)")]);
        File.WriteAllText(Path.Combine(tmp, "moddesc.ini"),
            "[ModManager]\r\ncmmver = 8.0\r\n\r\n[ModInfo]\r\ngame = LE2\r\nmodname = Archipelago ME2 open start (TEST)\r\n" +
            "moddesc = Test build: a new career skips the SR-1 prologue and goes from the character creator straight to the Normandy SR-2 galaxy map.\r\n" +
            "modver = 0.0.4\r\nmoddev = Jerrod\r\n\r\n[CUSTOMDLC]\r\nsourcedirs = " + ModFolder + "\r\ndestdirs = " + ModFolder + "\r\n");

        if (Directory.Exists(modRoot)) Directory.Delete(modRoot, true);
        Directory.Move(tmp, modRoot);
        Console.WriteLine($"staged {modRoot} (source {source})");
        return 0;
    }
}

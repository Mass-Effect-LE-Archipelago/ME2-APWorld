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
    const int CareerMarkerBool = 21999;   // client: only unbound saves with this bool set may be bound (world client.py)

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
        // DLC access (D25): Overlord, Arrival; Firewalker n = copy n of the progressive item (its vanilla Landing_Open bool is
        // replaced, so the item order is the order the missions open)
        ("BioP_Unc1Base1", 1864, 21101, "gv.GetBool(6512) == FALSE"),                                      // Project Overlord
        ("BioP_ArvLvl1", 1973, 21103, "gv.GetBool(7449) == TRUE && gv.GetBool(7450) == TRUE && gv.GetBool(7451) == FALSE"), // Arrival
        ("BioP_N7Geth1", 1559, 21111, "gv.GetBool(5187) == FALSE"),                                        // Firewalker 1: Geth Incursions
        ("BioP_N7DriveBy", 1561, 21112, "gv.GetBool(3946) == FALSE"),                                      // Firewalker 2: Survey Sites
        ("BioP_N7Ruins", 1563, 21113, "gv.GetBool(6206) == FALSE"),                                        // Firewalker 3: Prothean Site
        ("BioP_N7Shipwreck", 1565, 21114, "gv.GetBool(4042) == FALSE"),                                    // Firewalker 4: Rosalie Lost
        ("BioP_N7Mmnt8", 1567, 21115, "gv.GetBool(6219) == FALSE"),                                        // Firewalker 5: Volcano Station
        // Progressive Loyalty (D26): loyalty missions that start from a galaxy-map planet; bool 21130 + loyalty index
        ("BioP_BchLmL", 1571, 21131, "gv.GetBool(3995) == TRUE && gv.GetBool(34) == TRUE && gv.GetBool(1497) == FALSE && gv.GetBool(394) == TRUE"), // Jacob
        ("BioP_JunCvL", 187, 21134, "gv.GetBool(35) == TRUE && gv.GetBool(1498) == FALSE && gv.GetBool(395) == TRUE"),   // Jack
        ("BioP_QuaTlL", 192, 21138, "gv.GetBool(40) == TRUE && gv.GetBool(1503) == FALSE && gv.GetBool(400) == TRUE"),   // Tali
        ("BioP_BlbGtl", 188, 21139, "gv.GetBool(36) == TRUE && gv.GetBool(1499) == FALSE && gv.GetBool(396) == TRUE"),   // Legion
        ("BioP_ZyaVTL", 195, 21140, "gv.GetBool(44) == TRUE && gv.GetBool(1507) == FALSE && gv.GetBool(404) == TRUE"),   // Zaeed
        ("biop_ptymtl", 189, 21141, "gv.GetBool(37) == TRUE && gv.GetBool(1500) == FALSE && gv.GetBool(397) == TRUE"),   // Kasumi
    ];
    // Hub conditionals (research/galaxy_gating.md section 6): same pattern, used by repointed PMCheckConditional nodes.
    static readonly (int vanilla, int ours, string body)[] HubConditionals =
    [
        (376, 21005, "gv.GetBool(1542) == TRUE && gv.GetBool(43) == FALSE && gv.GetBool(205) == FALSE"),   // Samara, cab console
        (185, 21130, "gv.GetBool(33) == TRUE && gv.GetBool(1496) == FALSE && gv.GetBool(393) == TRUE"),    // Miranda loyalty (Illium lounge)
        (1553, 21132, "gv.GetBool(5951) == TRUE && gv.GetBool(2051) == FALSE"),                            // Mordin loyalty (Tuchanka)
        (468, 21137, "gv.GetBool(1947) == TRUE && gv.GetBool(1506) == FALSE && gv.GetBool(43) == TRUE"),  // Samara loyalty (Omega)
    ];
    // Galaxy-map recruit labels on the hub planets (SFXPlanetFeature FEATURE_LABEL, shown in the system tooltip): each
    // gets a conditional 21200+i = its vanilla VisibleConditional body AND the dossier bool, so a locked recruit's name
    // stays hidden (Austin, 2026-10-25). Planet labels (PlanetPlotLabelCondition) reuse the Gates conditionals.
    // body is the full expression (the dossier bool is not the conditional's own number here).
    static readonly (string map, int strref, int vanilla, int ours, string body)[] HubLabels =
    [
        ("BioP_OmgHub", 348619, 172, 21200, "gv.GetBool(41) == FALSE && gv.GetBool(203) == FALSE && gv.GetBool(21000) == TRUE"),   // Recruit The Professor
        ("BioP_OmgHub", 348618, 173, 21201, "gv.GetBool(38) == FALSE && gv.GetBool(200) == FALSE && gv.GetBool(21001) == TRUE"),   // Recruit Archangel
        ("BioP_TwrHub", 348626, 180, 21204, "gv.GetBool(312) == TRUE && gv.GetBool(39) == FALSE && gv.GetBool(201) == FALSE && gv.GetBool(21004) == TRUE"), // Recruit The Assassin
        ("BioP_TwrHub", 348625, 183, 21205, "gv.GetBool(43) == FALSE && gv.GetBool(312) == TRUE && gv.GetBool(205) == FALSE && gv.GetBool(21005) == TRUE"), // Recruit The Justicar
        ("BioP_OmgHub", 352029, 184, 21207, "gv.GetBool(44) == FALSE && gv.GetBool(206) == FALSE && gv.GetBool(2289) == TRUE && gv.GetBool(21007) == TRUE"), // Recruit The Veteran
        ("BioP_CitHub", 358125, 179, 21208, "gv.GetBool(37) == FALSE && gv.GetBool(199) == FALSE && gv.GetBool(2288) == TRUE && gv.GetBool(21008) == TRUE"), // Recruit The Master Thief
        ("BioP_TwrHub", 376969, 1987, 21210, "gv.GetInt(745) >= 2 && gv.GetBool(6844) == FALSE && gv.GetBool(21102) == TRUE"), // Give Liara Intel (Shadow Broker)
        ("BioP_TwrHub", 365856, 1998, 21211, "gv.GetBool(6844) == TRUE && gv.GetBool(6815) == FALSE && gv.GetBool(21102) == TRUE"), // Take Cab to Liara's
        ("BioP_CitHub", 348624, 190, 21220, "gv.GetBool(38) == TRUE && gv.GetBool(1501) == FALSE && gv.GetBool(398) == TRUE && gv.GetBool(21133) == TRUE"), // Help Garrus
        ("BioP_CitHub", 348623, 191, 21221, "gv.GetBool(39) == TRUE && gv.GetBool(1502) == FALSE && gv.GetBool(399) == TRUE && gv.GetBool(21136) == TRUE"), // Help Thane
        ("BioP_OmgHub", 348620, 174, 21222, "gv.GetBool(312) == TRUE && gv.GetBool(43) == TRUE && gv.GetBool(1506) == FALSE && gv.GetBool(403) == TRUE && gv.GetBool(21137) == TRUE"), // Help Samara
        ("BioP_TwrHub", 348627, 185, 21223, "gv.GetBool(33) == TRUE && gv.GetBool(1496) == FALSE && gv.GetBool(393) == TRUE && gv.GetBool(21130) == TRUE"), // Help Miranda
    ];
    const string MainSeq = "TheWorld.PersistentLevel.Main_Sequence.";
    // Per-dossier hub gates. "insert": a PMCheckState on the AP bool goes in front of the node (every link into it is
    // redirected through the check; False goes nowhere). "repoint": PMCheckConditional nodes move to our conditional.
    // The mission departures are gated at plot transition 399, which runs before the black screen and loading movie
    // (gating the AreaTransition itself would leave the player on a loading screen). Expect "" skips the target check.
    static readonly (string file, string kind, string node, string expect, int vanilla, int ours)[] HubGates =
    [
        ("BioD_OmgHub_110ProfessorAcq.pcc", "insert", MainSeq + "BioSeqAct_PMExecuteTransition_0", "399", 0, 21000),                         // Mordin
        ("BioD_OmgHub_100Dock.pcc", "insert", MainSeq + "Garrus_Acquisition_Blue_Suns_Driver.BioSeqAct_PMExecuteTransition_0", "399", 0, 21001), // Garrus
        ("BioD_TwrHub_301CarPortHall.pcc", "insert", MainSeq + "Assassin_Acquisition.BioSeqAct_PMExecuteTransition_0", "399", 0, 21004),      // Thane
        ("BioD_TwrHub_302CarPort.pcc", "repoint", MainSeq + "DLC_MODIFIED_Cab_Console", "", 376, 21005),                                    // Samara: cab menu
        ("BioD_TwrHub_302CarPort.pcc", "insert", MainSeq + "DLC_MODIFIED_Cab_Console.BioSeqAct_BlackScreen_0", "", 0, 21005),              // Samara: RE_HailCab
        // Zaeed: his recruit conversation starts from OnPlayerActivate with no check (C1495 only runs after it, 2026-10-25).
        ("BioD_OmgHub_DLC_Veteran.pcc", "insert", MainSeq + "Initialization.SFXSeqAct_StartConversation_1", "zyavtl_zaeed_acq_d_dlg", 0, 21007),
        ("BioD_CitHub_DLC_500Thief.pcc", "insert", MainSeq + "SFXSeqAct_StartConversation_0", "citmtl_kasumi_acq_d_dlg", 0, 21008),         // Kasumi
        ("BioD_TwrHub_302CarPort.pcc", "insert", MainSeq + "DLC_MODIFIED_Cab_Console.SeqAct_ToggleInput_0", "", 0, 21102),                // Shadow Broker: cab to Liara's
        // Progressive Loyalty (D26): the hub-based loyalty starts
        ("BioD_TwrHub_202Lounge.pcc", "repoint", MainSeq + "Vixen_Loyalty", "", 185, 21130),                                         // Miranda
        ("BioD_KroHub_120MordinLoyalty.pcc", "repoint", MainSeq + "Mordin_Loyalty", "", 1553, 21132),                              // Mordin
        ("BioD_CitHub.pcc", "insert", MainSeq + "Transportation_Logic.BioSeqAct_PMExecuteTransition_5", "399", 0, 21133),          // Garrus
        ("BioD_KroHub_110GruntLoyalty.pcc", "insert", MainSeq + "Shaman_Conversation.To_Grunt_Loyalty.BioSeqAct_ModifyPropertyNavigation_0", "", 0, 21135), // Grunt
        ("BioD_CitHub_220AsL.pcc", "insert", MainSeq + "BioSeqAct_PMExecuteTransition_0", "1838", 0, 21136),                        // Thane
        ("BioD_OmgHub_460MwL_Victim.pcc", "repoint", "TheWorld.PersistentLevel.Main_Sequence", "", 468, 21137),                     // Samara
    ];

    static string NodeTarget(ExportEntry node) =>
        node.GetProperty<NameProperty>("AreaName")?.Value.Instanced
        ?? node.GetProperty<IntProperty>("m_nIndex")?.Value.ToString()
        ?? (node.GetProperty<ObjectProperty>("Conv") is { } c ? node.FileRef.GetEntry(c.Value)?.ObjectName.Instanced : null) ?? "";

    static IEnumerable<ExportEntry> SeqOps(IMEPackage pcc) =>
        pcc.Exports.Where(e => e.GetProperty<ArrayProperty<StructProperty>>("OutputLinks") != null);

    static int HubGating(string bioGame, string cooked)
    {
        foreach (var g in HubGates)
        {
            var outPcc = Path.Combine(cooked, g.file);
            // A second gate in the same package builds on the first one's output.
            var source = File.Exists(outPcc) ? outPcc : Winner(bioGame, g.file);
            if (source == null) { Console.Error.WriteLine("refusing: no " + g.file); return 1; }
            var tmpPcc = outPcc + ".tmp";
            using (var pcc = MEPackageHandler.OpenMEPackage(source, forceLoadFromDisk: true))
            {
                var node = pcc.FindExport(g.node);
                if (node == null) { Console.Error.WriteLine($"refusing: {g.file} has no {g.node}"); return 1; }
                if (g.kind == "insert")
                {
                    if (g.expect != "" && !NodeTarget(node).Equals(g.expect, StringComparison.OrdinalIgnoreCase))
                    {
                        Console.Error.WriteLine($"refusing: {g.node} leads to {NodeTarget(node)}, not {g.expect}");
                        return 1;
                    }
                    var feeders = SeqOps(pcc).Where(e => KismetHelper.GetOutputLinksOfNode(e).Any(l => l.Any(x => x.LinkedOp == node))).ToList();
                    if (feeders.Count == 0) { Console.Error.WriteLine($"refusing: nothing leads into {g.node}"); return 1; }
                    var gate = SequenceObjectCreator.CreateSequenceObject((ExportEntry)node.Parent, "BioSeqAct_PMCheckState");
                    gate.WriteProperty(new IntProperty(g.ours, "m_nIndex"));
                    foreach (var f in feeders)
                    {
                        var links = KismetHelper.GetOutputLinksOfNode(f);
                        foreach (var l in links)
                            for (int i = 0; i < l.Count; i++)
                                if (l[i].LinkedOp == node) l[i] = new OutputLink { LinkedOp = gate, InputLinkIdx = 0 };
                        KismetHelper.WriteOutputLinksToNode(f, links);
                    }
                    // The creator usually writes the class's True/False outputs; add them only when it did not.
                    if (KismetHelper.GetOutputLinkNames(gate).Contains("True")) KismetHelper.CreateOutputLink(gate, "True", node);
                    else { KismetHelper.CreateNewOutputLink(gate, "True", node); KismetHelper.CreateNewOutputLink(gate, "False", null); }
                }
                else
                {
                    var conds = pcc.Exports.Where(e => e.ClassName == "BioSeqAct_PMCheckConditional" && e.Parent == node
                                                       && e.GetProperty<IntProperty>("m_nIndex")?.Value == g.vanilla).ToList();
                    if (conds.Count == 0) { Console.Error.WriteLine($"refusing: no C{g.vanilla} in {g.node}"); return 1; }
                    foreach (var c in conds) c.WriteProperty(new IntProperty(g.ours, "m_nIndex"));
                }
                pcc.Save(tmpPcc);
            }
            using (var pcc = MEPackageHandler.OpenMEPackage(tmpPcc, forceLoadFromDisk: true))
            {
                var node = pcc.FindExport(g.node);
                bool ok;
                if (g.kind == "insert")
                {
                    // Every path into the node now passes a PMCheckState on our bool, whose True leads to the node.
                    var feeders = SeqOps(pcc).Where(e => KismetHelper.GetOutputLinksOfNode(e).Any(l => l.Any(x => x.LinkedOp == node))).ToList();
                    ok = feeders.Count == 1 && feeders[0].ClassName == "BioSeqAct_PMCheckState"
                         && feeders[0].GetProperty<IntProperty>("m_nIndex")?.Value == g.ours
                         && KismetHelper.GetOutputLinkNames(feeders[0]).FirstOrDefault() == "True"
                         && KismetHelper.GetOutputLinksOfNode(feeders[0])[0].Single().LinkedOp == node
                         && SeqOps(pcc).Any(e => KismetHelper.GetOutputLinksOfNode(e).Any(l => l.Any(x => x.LinkedOp == feeders[0])));
                    Console.WriteLine($"validate: {g.file} {g.node.Replace(MainSeq, "")} <- S{g.ours} ({NodeTarget(node)})");
                }
                else
                {
                    var values = pcc.Exports.Where(e => e.ClassName == "BioSeqAct_PMCheckConditional" && e.Parent == node)
                        .Select(e => e.GetProperty<IntProperty>("m_nIndex")?.Value).ToList();
                    ok = values.Contains(g.ours) && !values.Contains(g.vanilla);
                    Console.WriteLine($"validate: {g.file} {g.node.Replace(MainSeq, "")} conditionals [{string.Join(",", values)}]");
                }
                if (!ok) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
            }
            File.Move(tmpPcc, outPcc, true);
        }
        return 0;
    }

    // Missed-checks salvage (D22, research/salvage_store.md). Per mission k (tools/le2mod/salvage.json, exported from the
    // world): a multi-level tech Tec_APSalvage_k whose level is plot int bought_int_base+k and whose cap is
    // APSalvageCap_k = cap_int_base+k (both mapped in PlotManagerGameData), and one research entry per price tier t
    // (treasure row 21500+5k+t, DisableId tier_disable_base+t) at the Normandy research terminal. The client sets the
    // caps and the tier bools and takes the counters (bridge protocol 4).
    const string SalvagePackage = "BIOG_2DA_ArchipelagoME2_PlotManager_X";
    const string SalvageTemplateDlc = "DLC_HEN_VT";   // its startup package carries the three part tables we need
    const int SalvageTreasureBase = 21500, SalvageTechRowBase = 41000;
    const int SalvageTitleStrRef = 41000100, SalvageDescStrRef = 41000300, SalvageMessageStrRef = 41000301;

    record SalvageMission(int index, string area, string label, int pickups);
    record SalvageData(int bought_int_base, int cap_int_base, int tier_disable_base, int[] prices, SalvageMission[] missions);

    static SalvageData _salvage;
    static SalvageData LoadSalvage()
    {
        if (_salvage != null) return _salvage;
        for (var dir = new DirectoryInfo(AppContext.BaseDirectory); dir != null; dir = dir.Parent)
        {
            var path = Path.Combine(dir.FullName, "salvage.json");
            if (File.Exists(path)) return _salvage = System.Text.Json.JsonSerializer.Deserialize<SalvageData>(File.ReadAllText(path));
        }
        throw new FileNotFoundException("salvage.json (tools/le2mod) not found above " + AppContext.BaseDirectory);
    }

    static int SalvageTreasureId(int k, int t) => SalvageTreasureBase + 5 * k + t;

    static string SalvageResearchIni()
    {
        var s = LoadSalvage();
        var lines = new List<string> { "[SFXGame.SFXGameChoiceGUIData_Research]" };
        foreach (var m in s.missions)
            for (int t = 0; t < s.prices.Length; t++)
                lines.Add($"+Research=(PlotName=\"Tec_APSalvage_{m.index}\",TreasureId={SalvageTreasureId(m.index, t)},UnlockId=0," +
                          $"DisableId={s.tier_disable_base + t},RMode=0,ChoiceEntry=(srChoiceTitle={SalvageTitleStrRef + m.index},oChoiceImage=none," +
                          $"srChoiceImageTitle={SalvageTitleStrRef + m.index},srChoiceDescription={SalvageDescStrRef},ChoiceColor=3))");
        return string.Join("\r\n", lines) + "\r\n";
    }

    static IEnumerable<TLKStringRef> SalvageStrings()
    {
        var s = LoadSalvage();
        foreach (var m in s.missions) yield return new TLKStringRef(SalvageTitleStrRef + m.index, m.label + " Salvage");
        yield return new TLKStringRef(SalvageDescStrRef,
            "Recover one pickup you left behind on this mission. Each purchase sends one missed Archipelago check.");
        yield return new TLKStringRef(SalvageMessageStrRef, "Salvage recovered: one missed check sent.");
    }

    static int Salvage(string bioGame, string cooked)
    {
        var s = LoadSalvage();
        var startupOut = Path.Combine(cooked, StartupName + "_INT.pcc");
        var template = Path.Combine(bioGame, "DLC", SalvageTemplateDlc, "CookedPCConsole", $"Startup_{SalvageTemplateDlc[4..]}_INT.pcc");
        string srcPkg = $"BIOG_2DA_{SalvageTemplateDlc[4..]}_PlotManager_X";
        using (var src = MEPackageHandler.OpenMEPackage(template, forceLoadFromDisk: true))
        using (var pcc = MEPackageHandler.OpenMEPackage(startupOut, forceLoadFromDisk: true))
        {
            var pkg = src.Exports.FirstOrDefault(e => e.ClassName == "Package" && e.ObjectName.Name == srcPkg);
            if (pkg == null) { Console.Error.WriteLine("refusing: no " + srcPkg + " in " + template); return 1; }
            // Our package export, then each template table ported into it (the Resources table is not needed).
            var ourPkg = pcc.CreatePackageExport(new NameReference(SalvagePackage));
            ExportEntry Port(string name)
            {
                var table = src.Exports.Single(e => e.InstancedFullPath == $"{srcPkg}.{name}_part_100");
                LegendaryExplorerCore.Packages.CloningImportingAndRelinking.EntryImporter.ImportAndRelinkEntries(
                    LegendaryExplorerCore.Packages.CloningImportingAndRelinking.EntryImporter.PortingOption.CloneAllDependencies, table, pcc, ourPkg, true,
                    new LegendaryExplorerCore.Packages.CloningImportingAndRelinking.RelinkerOptionsPackage(), out var ported);
                var export = (ExportEntry)ported;
                export.ObjectName = new NameReference(name + "_part_4100");
                return export;
            }
            var treasure = Port("Plot_Treasure_Treasure");
            var tech = Port("Plot_Treasure_Tech");
            var gameData = Port("PlotManagerGameData");

            LegendaryExplorerCore.Unreal.Classes.Bio2DACell Name(string v) => new(new NameReference(v), pcc);
            LegendaryExplorerCore.Unreal.Classes.Bio2DACell Int(int v) => new(v);
            LegendaryExplorerCore.Unreal.Classes.Bio2DA Fresh(ExportEntry e)
            {
                var old = new LegendaryExplorerCore.Unreal.Classes.Bio2DA(e);
                var t = new LegendaryExplorerCore.Unreal.Classes.Bio2DA { IsIndexed = old.IsIndexed };
                t.AddColumns(old.ColumnNames.ToArray());
                return t;
            }
            void Row(LegendaryExplorerCore.Unreal.Classes.Bio2DA t, string row, params LegendaryExplorerCore.Unreal.Classes.Bio2DACell[] cells)
            {
                int r = t.AddRow(row);
                for (int c = 0; c < cells.Length; c++) if (cells[c] != null) t[r, c] = cells[c];
            }

            var techT = Fresh(tech);      // nmTech nLevels nmResearch srTitle srName srMessage srDescription UnlockId sImage sLargeImage sBonusDescription
            var treasureT = Fresh(treasure); // nmLevel nmTreasure nmTech nmResource nPrice nmRequiredTech nRequiredTechLevel nDiscoverTechLevel nNoAnimation nMultiLevel
            var gameT = Fresh(gameData);  // Index
            foreach (var m in s.missions)
            {
                Row(techT, (SalvageTechRowBase + m.index).ToString(), Name($"Tec_APSalvage_{m.index}"), Int(10), null, Int(SalvageTitleStrRef + m.index),
                    Int(SalvageTitleStrRef + m.index), Int(SalvageMessageStrRef), Int(SalvageDescStrRef), Int(-1),
                    Name("GUI_GlobalIcons.Notifications.NewTech_256"), Name("GUI_Codex_Images.ResearchProjectUpgrade_512"), null);
                for (int t = 0; t < s.prices.Length; t++)
                    Row(treasureT, SalvageTreasureId(m.index, t).ToString(), Name("Biop_Nor"), Name($"Tre_APSalvage_{m.index}_{t}"),
                        Name($"Tec_APSalvage_{m.index}"), Name("Credits"), Int(s.prices[t]), Name($"APSalvageCap_{m.index}"), Int(1), Int(0), Int(1), Int(1));
                Row(gameT, $"Tec_APSalvage_{m.index}", Int(s.bought_int_base + m.index));
                Row(gameT, $"APSalvageCap_{m.index}", Int(s.cap_int_base + m.index));
            }
            Row(gameT, "LastLineDoesntWorkWTF", Int(0));   // the vanilla part tables end with this sentinel row
            techT.Write2DAToExport(tech);
            treasureT.Write2DAToExport(treasure);
            gameT.Write2DAToExport(gameData);
            pcc.Save(startupOut + ".tmp");
        }
        using (var pcc = MEPackageHandler.OpenMEPackage(startupOut + ".tmp", forceLoadFromDisk: true))
        {
            var tables = pcc.Exports.Where(e => e.Parent?.ObjectName.Name == SalvagePackage).ToDictionary(e => e.ObjectName.Name);
            bool ok = tables.Count == 3 && !pcc.Exports.Any(e => e.InstancedFullPath.Contains(SalvageTemplateDlc[4..]) && e.ClassName != "ShaderCache");
            var treasureT = ok ? new LegendaryExplorerCore.Unreal.Classes.Bio2DA(tables["Plot_Treasure_Treasure_part_4100"]) : null;
            var techT = ok ? new LegendaryExplorerCore.Unreal.Classes.Bio2DA(tables["Plot_Treasure_Tech_part_4100"]) : null;
            var gameT = ok ? new LegendaryExplorerCore.Unreal.Classes.Bio2DA(tables["PlotManagerGameData_part_4100"]) : null;
            ok &= treasureT?.RowCount == s.missions.Length * s.prices.Length && techT?.RowCount == s.missions.Length
                  && gameT?.RowCount == 2 * s.missions.Length + 1;
            if (ok)
            {
                // spot check: Korlus at the 1000-credit tier
                var korlus = s.missions.First(m => m.area == "grunt_acq");
                var row = treasureT.RowNames.ToList().IndexOf(SalvageTreasureId(korlus.index, 2).ToString());
                ok &= row >= 0 && treasureT[row, "nPrice"].IntValue == s.prices[2] && treasureT[row, "nmTech"].NameValue.Instanced == $"Tec_APSalvage_{korlus.index}";
                Console.WriteLine($"validate: salvage tables treasure={treasureT.RowCount} tech={techT.RowCount} gamedata={gameT.RowCount}; " +
                                  $"Korlus tier 2 = {treasureT[row, "nPrice"].IntValue} credits");
            }
            if (!ok) { Console.Error.WriteLine("salvage validation FAILED; staging left unchanged"); return 1; }
        }
        File.Move(startupOut + ".tmp", startupOut, true);
        return 0;
    }

    const string GalaxyFile = "BioD_Nor_103aGalaxyMap.pcc";

    static int Gating(string bioGame, string cooked)
    {
        // 1. Conditionals: clone the template DLC's startup package, rename its packages, recompile the class.
        var template = Path.Combine(bioGame, "DLC", CondTemplateDlc, "CookedPCConsole", $"Startup_{CondTemplateDlc[4..]}_INT.pcc");
        if (!File.Exists(template)) { Console.Error.WriteLine("refusing: no template " + template); return 1; }
        var startupOut = Path.Combine(cooked, StartupName + "_INT.pcc");
        var allConds = Gates.Select(g => (g.ours, body: $"{g.body} && gv.GetBool({g.ours}) == TRUE"))
            .Concat(HubConditionals.Select(h => (h.ours, body: $"{h.body} && gv.GetBool({h.ours}) == TRUE")))
            .Concat(HubLabels.Select(l => (l.ours, l.body))).ToList();
        var script = "Class BioAutoConditionals extends BioConditionals;\n\n" + string.Concat(allConds.Select(g =>
            $"public function bool F{g.ours}(BioWorldInfo bioWorld, int Argument)\n{{\n    local BioGlobalVariableTable gv;\n    \n" +
            $"    gv = bioWorld.GetGlobalVariables();\n    return {g.body};\n}}\n"));
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
            var want = allConds.Select(g => "F" + g.ours).OrderBy(n => n).ToList();
            bool stale = pcc.Exports.Any(e => e.InstancedFullPath.Contains(CondTemplateDlc[4..]) && e.ClassName != "ShaderCache");
            Console.WriteLine($"validate: {StartupName}_INT functions [{string.Join(",", fns)}] template-names-left={stale}");
            if (!fns.SequenceEqual(want) || stale) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
        }

        // 2. Galaxy map: the runtime winner with the four planets' land/visible conditionals repointed.
        var galaxy = Winner(bioGame, GalaxyFile);
        if (galaxy == null) { Console.Error.WriteLine("refusing: no " + GalaxyFile); return 1; }
        var galaxyOut = Path.Combine(cooked, GalaxyFile);
        string[] condProps = ["PlanetLandCondition", "VisibleConditional", "UsableConditional", "PlanetPlotLabelCondition"];
        ExportEntry Label(IMEPackage p, string map, int strref) => p.Exports.SingleOrDefault(e => e.ClassName == "SFXPlanetFeature"
            && e.Parent is ExportEntry planet && string.Equals(planet.GetProperty<StrProperty>("MapName")?.Value, map, StringComparison.OrdinalIgnoreCase)
            && e.GetProperty<StringRefProperty>("DisplayName")?.Value == strref);
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
                // the planet's tooltip label follows its gate (DLC planets label on their own conditionals)
                if (planet.GetProperty<IntProperty>("PlanetPlotLabelCondition") != null) planet.WriteProperty(new IntProperty(g.ours, "PlanetPlotLabelCondition"));
            }
            foreach (var l in HubLabels)
            {
                var label = Label(pcc, l.map, l.strref);
                if (label == null || label.GetProperty<IntProperty>("VisibleConditional")?.Value != l.vanilla)
                {
                    Console.Error.WriteLine($"refusing: {l.map} label ${l.strref} is missing or not on conditional {l.vanilla}");
                    return 1;
                }
                label.WriteProperty(new IntProperty(l.ours, "VisibleConditional"));
            }
            pcc.Save(galaxyOut);
        }
        using (var pcc = MEPackageHandler.OpenMEPackage(galaxyOut, forceLoadFromDisk: true))
        {
            foreach (var g in Gates)
            {
                var planet = Planet(pcc, g.map);
                var values = condProps.Select(n => planet?.GetProperty<IntProperty>(n)?.Value).ToList();
                Console.WriteLine($"validate: {g.map} land/visible/usable/label = {string.Join("/", values.Select(v => v?.ToString() ?? "-"))}");
                if (values[0] != g.ours || (values[3] != null && values[3] != g.ours) || values.Any(v => v == g.vanilla)) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
            }
            foreach (var l in HubLabels)
            {
                var v = Label(pcc, l.map, l.strref)?.GetProperty<IntProperty>("VisibleConditional")?.Value;
                Console.WriteLine($"validate: {l.map} label ${l.strref} visible = {v}");
                if (v != l.ours) { Console.Error.WriteLine("validation FAILED; staging left unchanged"); return 1; }
            }
        }
        Console.WriteLine($"galaxy gating built (galaxy source {galaxy})");
        if (HubGating(bioGame, cooked) != 0) return 1;
        Console.WriteLine("hub recruit gating built");
        if (Salvage(bioGame, cooked) != 0) return 1;
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
            // Archipelago career marker (2026-10-26): plot bool CareerMarkerBool = TRUE, so the client binds only careers
            // started with this mod (a vanilla save loaded by mistake was bound and its progress sent as checks).
            var marker = SequenceObjectCreator.CreateSequenceObject(seq, "SeqAct_SetBool");
            var markerVar = SequenceObjectCreator.CreateSequenceObject(seq, "BioSeqVar_StoryManagerBool");
            markerVar.WriteProperty(new IntProperty(CareerMarkerBool, "m_nIndex"));
            var trueVar = SequenceObjectCreator.CreateSequenceObject(seq, "SeqVar_Bool");
            trueVar.WriteProperty(new IntProperty(1, "bValue"));
            // New nodes carry no VariableLinks either (CreateVariableLink needs them), so write both links as vanilla
            // SetBools have them (BioD_Nor_130TechLabs EDI_Tour_Lab.SeqAct_SetBool_0).
            StructProperty VarLink(ExportEntry v, string desc, string prop, int min, bool writeable) => new("SeqVarLink",
            [
                new ArrayProperty<ObjectProperty>([new ObjectProperty(v)], "LinkedVariables"), new StrProperty(desc, "LinkDesc"),
                new ObjectProperty(trueVar.Class, "ExpectedType"), new NameProperty("None", "LinkVar"), new NameProperty(prop, "PropertyName"),
                new IntProperty(min, "MinVars"), new IntProperty(255, "MaxVars"), new BoolProperty(writeable, "bWriteable"),
                new BoolProperty(false, "bModifiesLinkedObject"), new BoolProperty(false, "bAllowAnyType"),
            ]);
            marker.WriteProperty(new ArrayProperty<StructProperty>([VarLink(markerVar, "Target", "Target", 1, true), VarLink(trueVar, "Value", "None", 0, false)], "VariableLinks"));
            KismetHelper.CreateNewOutputLink(chain[^1], "Out", marker);
            KismetHelper.CreateNewOutputLink(marker, "Out", black);

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
            // then the career marker SetBool, then the black screen
            var markerOk = node?.ClassName == "SeqAct_SetBool"
                && KismetHelper.GetVariableLinksOfNode(node).Any(l => l.LinkedNodes.Any(v => v is ExportEntry e && e.ClassName == "BioSeqVar_StoryManagerBool" && e.GetProperty<IntProperty>("m_nIndex")?.Value == CareerMarkerBool));
            if (markerOk) node = KismetHelper.GetOutputLinksOfNode(node)[0].FirstOrDefault()?.LinkedOp as ExportEntry;
            ok &= markerOk && ids.SequenceEqual(transitions) && node?.InstancedFullPath == BlackNode;
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
            (noGating ? "" : $"\r\n[Engine.StartupPackages]\r\n+DLCStartupPackage={StartupName}\r\n+Package={CondPackage}\r\n+Package={SalvagePackage}\r\n"));
        if (!noGating)
        {
            File.WriteAllText(Path.Combine(cooked, "BIOGame.ini"), $"[SFXGame.BioWorldInfo]\r\n+ConditionalClasses={CondPackage}.BioAutoConditionals\r\n");
            File.WriteAllText(Path.Combine(cooked, "BIOUI.ini"), SalvageResearchIni());
        }
        HuffmanCompression.SaveToTlkFile(Path.Combine(cooked, $"DLC_{ModuleNumber}_INT.tlk"),
            [new TLKStringRef(NameStrRef, "Archipelago ME2 (open start test)"), .. (noGating ? [] : SalvageStrings())]);
        File.WriteAllText(Path.Combine(tmp, "moddesc.ini"),
            "[ModManager]\r\ncmmver = 8.0\r\n\r\n[ModInfo]\r\ngame = LE2\r\nmodname = Archipelago ME2 open start (TEST)\r\n" +
            "moddesc = Test build: a new career skips the SR-1 prologue and goes from the character creator straight to the Normandy SR-2 galaxy map.\r\n" +
            "modver = 0.0.9\r\nmoddev = Jerrod\r\n\r\n[CUSTOMDLC]\r\nsourcedirs = " + ModFolder + "\r\ndestdirs = " + ModFolder + "\r\n");

        if (Directory.Exists(modRoot)) Directory.Delete(modRoot, true);
        Directory.Move(tmp, modRoot);
        Console.WriteLine($"staged {modRoot} (source {source})");
        return 0;
    }
}

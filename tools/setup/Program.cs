// ME2 AP Setup: finds the Mass Effect LE and Archipelago folders, installs the world, bridge and mod, and writes the
// player's YAML into Archipelago's Players folder. Seeds are still generated and hosted by Archipelago.
// The payload (mass_effect_le2.apworld, LE2APBridge.asi, ArchipelagoME2\moddesc.ini) sits next to the exe.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Win32;

namespace ME2APSetup;

static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        // check mode: "ME2 AP Setup.exe --write-yaml <file> [slot] [preset]" writes that YAML without showing the window
        if (args.Length >= 2 && args[0] == "--write-yaml")
        {
            using var form = new MainForm();
            File.WriteAllText(args[1], form.DefaultYaml(args.Length > 2 ? args[2] : "Shepard", args.Length > 3 ? args[3] : "Default"), new UTF8Encoding(false));
            return;
        }
        Application.Run(new MainForm());
    }
}

sealed class OptionDef
{
    public string Key, Display, Doc, Type;
    public JsonElement Default;
    public string[] Choices = [];
    public int Min, Max;
}

sealed class MainForm : Form
{
    readonly string _here = AppContext.BaseDirectory;
    readonly TextBox _gameDir = new() { Width = 520 }, _apDir = new() { Width = 520 }, _modManager = new() { Width = 520 };
    readonly Label _status = new() { AutoSize = true, Font = new Font(FontFamily.GenericMonospace, 9) };
    readonly TextBox _help = new() { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Height = 150, Dock = DockStyle.Bottom };
    readonly TextBox _slot = new() { Width = 200, Text = "Shepard", MaxLength = 16 };
    readonly ComboBox _preset = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 200 };
    readonly CheckBox _useModManager = new() { Text = "Install the mod through ME3Tweaks Mod Manager (if found) instead of copying it", AutoSize = true };
    readonly CheckBox _launchClient = new() { Text = "also start the ME2 Archipelago client", AutoSize = true, Checked = true, Margin = new Padding(8, 6, 0, 0) };
    readonly Dictionary<string, Control> _controls = new();
    readonly List<OptionDef> _options = [];
    JsonElement _schema;
    string Backup => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ME2APSetup", "backup");

    public MainForm()
    {
        Text = "ME2 AP Setup 0.2.1 - Mass Effect Legendary Edition 2 for Archipelago";
        Width = 900; Height = 760;
        using (var stream = typeof(MainForm).Assembly.GetManifestResourceStream("options.json"))
            _schema = JsonDocument.Parse(stream).RootElement.Clone();
        var tabs = new TabControl { Dock = DockStyle.Fill };
        tabs.TabPages.Add(PathsPage());
        tabs.TabPages.Add(InstallPage());
        tabs.TabPages.Add(OptionsPage());
        tabs.SelectedIndexChanged += (_, _) => RefreshStatus();
        Controls.Add(tabs);
        DetectPaths();
        RefreshStatus();
    }

    // ---------------------------------------------------------------- paths
    TabPage PathsPage()
    {
        var page = new TabPage("1. Folders");
        var flow = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, Padding = new Padding(12), AutoScroll = true };
        flow.Controls.Add(new Label { AutoSize = true, MaximumSize = new Size(820, 0), Text =
            "Check the folders below (they are detected automatically; use Browse to change them), then go to Install.\n" +
            "Mass Effect Legendary Edition: the folder that contains Game\\ME2. Archipelago: the folder with ArchipelagoLauncher.exe.\n" +
            "ME3Tweaks Mod Manager installs the mod and refreshes the game's file table; without it you can drag ArchipelagoME2-mod.zip onto Mod Manager yourself." });
        flow.Controls.Add(PathRow("Mass Effect Legendary Edition folder", _gameDir, true));
        flow.Controls.Add(PathRow("Archipelago folder", _apDir, true));
        flow.Controls.Add(PathRow("ME3Tweaks Mod Manager (ME3TweaksModManager.exe)", _modManager, false));
        page.Controls.Add(flow);
        return page;
    }

    Control PathRow(string label, TextBox box, bool folder)
    {
        var panel = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.TopDown, Margin = new Padding(0, 10, 0, 0) };
        panel.Controls.Add(new Label { Text = label, AutoSize = true, Font = new Font(Font, FontStyle.Bold) });
        var row = new FlowLayoutPanel { AutoSize = true };
        var browse = new Button { Text = "Browse...", AutoSize = true };
        browse.Click += (_, _) =>
        {
            if (folder)
            {
                using var dialog = new FolderBrowserDialog { SelectedPath = box.Text };
                if (dialog.ShowDialog(this) == DialogResult.OK) box.Text = dialog.SelectedPath;
            }
            else
            {
                using var dialog = new OpenFileDialog { Filter = "ME3TweaksModManager.exe|ME3TweaksModManager.exe" };
                if (dialog.ShowDialog(this) == DialogResult.OK) box.Text = dialog.FileName;
            }
            RefreshStatus();
        };
        row.Controls.Add(box);
        row.Controls.Add(browse);
        panel.Controls.Add(row);
        return panel;
    }

    void DetectPaths()
    {
        var libraries = new List<string>();
        var steam = Registry.GetValue(@"HKEY_CURRENT_USER\Software\Valve\Steam", "SteamPath", null) as string;
        if (steam != null)
        {
            libraries.Add(steam);
            var vdf = Path.Combine(steam, "steamapps", "libraryfolders.vdf");
            if (File.Exists(vdf))
                foreach (var line in File.ReadAllLines(vdf))
                    if (line.Trim().StartsWith("\"path\""))
                        libraries.Add(line.Split('"')[3].Replace(@"\\", @"\"));
        }
        libraries.AddRange([@"C:\Program Files (x86)\Steam", @"C:\Steam", @"D:\Steam", @"D:\SteamLibrary", @"E:\SteamLibrary"]);
        _gameDir.Text = libraries.Select(l => Path.GetFullPath(Path.Combine(l, "steamapps", "common", "Mass Effect Legendary Edition")))
            .FirstOrDefault(p => File.Exists(Path.Combine(p, "Game", "ME2", "Binaries", "Win64", "MassEffect2.exe"))) ?? "";
        _apDir.Text = new[] { @"C:\ProgramData\Archipelago", Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Archipelago") }
            .FirstOrDefault(p => File.Exists(Path.Combine(p, "ArchipelagoLauncher.exe"))) ?? "";
        foreach (var root in new[] { Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                     Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Documents"),
                     Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads") })
        {
            var found = FindFile(root, "ME3TweaksModManager.exe", 4);
            if (found != null) { _modManager.Text = found; break; }
        }
    }

    static string FindFile(string root, string name, int depth)
    {
        try
        {
            var direct = Path.Combine(root, name);
            if (File.Exists(direct)) return direct;
            if (depth == 0) return null;
            foreach (var dir in Directory.EnumerateDirectories(root))
                if (FindFile(dir, name, depth - 1) is { } hit) return hit;
        }
        catch (UnauthorizedAccessException) { }
        catch (IOException) { }
        return null;
    }

    string Me2 => Path.Combine(_gameDir.Text, "Game", "ME2");
    string Win64 => Path.Combine(Me2, "Binaries", "Win64");
    string WorldTarget => Path.Combine(_apDir.Text, "custom_worlds", "mass_effect_le2.apworld");
    string AsiTarget => Path.Combine(Win64, "ASI", "LE2APBridge.asi");
    string ModTarget => Path.Combine(Me2, "BioGame", "DLC", "DLC_MOD_ArchipelagoME2");

    // ---------------------------------------------------------------- install
    TabPage InstallPage()
    {
        var page = new TabPage("2. Install");
        var flow = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, Padding = new Padding(12) };
        flow.Controls.Add(new Label { AutoSize = true, MaximumSize = new Size(820, 0), Text =
            "Close Mass Effect 2 and the Archipelago client first. Install (or Repair) copies the world into Archipelago, the bridge into ME2's ASI folder " +
            "and has Mod Manager install the mod. Anything replaced is backed up and Uninstall puts it back." });
        flow.Controls.Add(_status);
        var buttons = new FlowLayoutPanel { AutoSize = true };
        flow.Controls.Add(_useModManager);
        var install = new Button { Text = "Install / Repair", AutoSize = true };
        var launch = new Button { Text = "Launch ME2", AutoSize = true };
        launch.Click += (_, _) => Run(LaunchGame);
        var uninstall = new Button { Text = "Uninstall", AutoSize = true };
        install.Click += (_, _) => Run(InstallAll);
        uninstall.Click += (_, _) => Run(UninstallAll);
        buttons.Controls.Add(install);
        buttons.Controls.Add(uninstall);
        buttons.Controls.Add(launch);
        buttons.Controls.Add(_launchClient);
        flow.Controls.Add(buttons);
        page.Controls.Add(flow);
        return page;
    }

    void Run(Action action)
    {
        try
        {
            if (Process.GetProcessesByName("MassEffect2").Length > 0) throw new InvalidOperationException("Close Mass Effect 2 first.");
            action();
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "ME2 AP Setup", MessageBoxButtons.OK, MessageBoxIcon.Warning); }
        RefreshStatus();
    }

    static string Hash(string path) => File.Exists(path) ? Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))) : null;

    string State(string payload, string target) =>
        !File.Exists(target) ? "not installed" : Hash(payload) == Hash(target) ? "installed (this version)" : "installed (different version)";

    void RefreshStatus()
    {
        var lines = new StringBuilder();
        bool game = File.Exists(Path.Combine(Win64, "MassEffect2.exe")), ap = File.Exists(Path.Combine(_apDir.Text, "ArchipelagoLauncher.exe"));
        lines.AppendLine($"Mass Effect 2 LE      : {(game ? "found" : "NOT FOUND - set the folder on page 1")}");
        lines.AppendLine($"Archipelago           : {(ap ? "found" : "NOT FOUND - set the folder on page 1")}");
        lines.AppendLine($"ASI loader            : {(game && File.Exists(Path.Combine(Win64, "bink2w64_original.dll")) ? "installed" : "MISSING - install ME3Tweaks Mod Manager, pick LE2, Tools > Bink bypass (it is not ours to ship)")}");
        lines.AppendLine($"Mod Manager           : {(File.Exists(_modManager.Text) ? "found" : "not found (install the mod zip by hand)")}");
        lines.AppendLine($"Archipelago world     : {(ap ? State(Path.Combine(_here, "mass_effect_le2.apworld"), WorldTarget) : "-")}");
        lines.AppendLine($"Game bridge (ASI)     : {(game ? State(Path.Combine(_here, "LE2APBridge.asi"), AsiTarget) : "-")}");
        var meta = Path.Combine(ModTarget, "_metacmm.txt");
        lines.AppendLine($"Mod                   : {(game ? File.Exists(meta) ? "installed, version " + File.ReadLines(meta).Skip(1).FirstOrDefault() : Directory.Exists(ModTarget) ? "installed" : "not installed" : "-")}");
        _status.Text = lines.ToString();
    }

    void BackupFile(string path, string name)
    {
        Directory.CreateDirectory(Backup);
        var saved = Path.Combine(Backup, name);
        if (File.Exists(path) && !File.Exists(saved)) File.Copy(path, saved);
    }

    void InstallAll()
    {
        if (!File.Exists(Path.Combine(_apDir.Text, "ArchipelagoLauncher.exe"))) throw new InvalidOperationException("Set the Archipelago folder on page 1.");
        if (!File.Exists(Path.Combine(Win64, "MassEffect2.exe"))) throw new InvalidOperationException("Set the Mass Effect Legendary Edition folder on page 1.");
        if (!File.Exists(Path.Combine(Win64, "bink2w64_original.dll")))
            throw new InvalidOperationException("The ASI loader is missing. In ME3Tweaks Mod Manager pick the LE2 target and use Tools > ASI Mod Manager (installing any ASI adds the loader), then try again.");
        Directory.CreateDirectory(Path.GetDirectoryName(WorldTarget));
        BackupFile(WorldTarget, "mass_effect_le2.apworld");
        File.Copy(Path.Combine(_here, "mass_effect_le2.apworld"), WorldTarget, true);
        Directory.CreateDirectory(Path.GetDirectoryName(AsiTarget));
        BackupFile(AsiTarget, "LE2APBridge.asi");
        File.Copy(Path.Combine(_here, "LE2APBridge.asi"), AsiTarget, true);
        var moddesc = Path.Combine(_here, "ArchipelagoME2", "moddesc.ini");
        if (_useModManager.Checked && File.Exists(_modManager.Text))
        {
            Process.Start(new ProcessStartInfo(_modManager.Text, $"--installmod \"{moddesc}\" --game LE2") { UseShellExecute = false });
            MessageBox.Show(this, "World and bridge installed. Mod Manager is now installing the mod; confirm anything it asks.", "ME2 AP Setup");
            return;
        }
        // Without Mod Manager: copy the DLC folder in and write its file table (PCConsoleTOC.bin) ourselves.
        var source = Path.Combine(_here, "ArchipelagoME2", "DLC_MOD_ArchipelagoME2");
        if (Directory.Exists(ModTarget))
        {
            var saved = Path.Combine(Backup, "DLC_MOD_ArchipelagoME2");
            if (!Directory.Exists(saved)) CopyDirectory(ModTarget, saved);
            Directory.Delete(ModTarget, true);
        }
        CopyDirectory(source, ModTarget);
        WriteToc(ModTarget);
        MessageBox.Show(this, "World, bridge and mod installed.", "ME2 AP Setup");
    }

    void UninstallAll()
    {
        void Restore(string target, string name)
        {
            var saved = Path.Combine(Backup, name);
            if (File.Exists(saved)) File.Copy(saved, target, true);
            else if (File.Exists(target)) File.Delete(target);
        }
        if (File.Exists(Path.Combine(_apDir.Text, "ArchipelagoLauncher.exe"))) Restore(WorldTarget, "mass_effect_le2.apworld");
        if (Directory.Exists(Win64)) Restore(AsiTarget, "LE2APBridge.asi");
        if (Directory.Exists(ModTarget)) Directory.Delete(ModTarget, true);
        var savedMod = Path.Combine(Backup, "DLC_MOD_ArchipelagoME2");
        if (Directory.Exists(savedMod)) CopyDirectory(savedMod, ModTarget);
        MessageBox.Show(this, "Removed (earlier versions restored where a backup existed).", "ME2 AP Setup");
    }

    static void CopyDirectory(string from, string to)
    {
        foreach (var dir in Directory.EnumerateDirectories(from, "*", SearchOption.AllDirectories))
            Directory.CreateDirectory(Path.Combine(to, Path.GetRelativePath(from, dir)));
        Directory.CreateDirectory(to);
        foreach (var file in Directory.EnumerateFiles(from, "*", SearchOption.AllDirectories))
            File.Copy(file, Path.Combine(to, Path.GetRelativePath(from, file)), true);
    }

    // The DLC's own file table, as Mod Manager's AutoTOC writes it (LegendaryExplorerCore TOCCreator).
    static void WriteToc(string dlcFolder)
    {
        using var toc = LegendaryExplorerCore.Unreal.TOCCreator.CreateDLCTOCForDirectory(dlcFolder, LegendaryExplorerCore.Packages.MEGame.LE2);
        File.WriteAllBytes(Path.Combine(dlcFolder, "PCConsoleTOC.bin"), toc.ToArray());
    }

    void LaunchGame()
    {
        var exe = Path.Combine(Win64, "MassEffect2.exe");
        if (!File.Exists(exe)) throw new InvalidOperationException("Set the Mass Effect Legendary Edition folder on page 1.");
        // Started directly (no Legendary Edition launcher); Steam must be running, as it is for any LE launch.
        Process.Start(new ProcessStartInfo(exe) { WorkingDirectory = Win64, UseShellExecute = true });
        if (_launchClient.Checked && File.Exists(Path.Combine(_apDir.Text, "ArchipelagoLauncher.exe")))
            Process.Start(new ProcessStartInfo(Path.Combine(_apDir.Text, "ArchipelagoLauncher.exe"), "\"Mass Effect LE2 Client\"")
                { WorkingDirectory = _apDir.Text, UseShellExecute = false });
    }

    void Generate()
    {
        var generator = Path.Combine(_apDir.Text, "ArchipelagoGenerate.exe");
        if (!File.Exists(generator)) throw new InvalidOperationException("ArchipelagoGenerate.exe not found: set the Archipelago folder on page 1.");
        if (!SaveYaml(null)) return;
        var players = Path.Combine(_apDir.Text, "Players");
        var yamls = Directory.GetFiles(players, "*.yaml").Select(Path.GetFileName).ToArray();
        if (MessageBox.Show(this, $"Generate a seed from every YAML in {players}?\r\n\r\n{string.Join("\r\n", yamls)}\r\n\r\n" +
                "Then upload the AP_*.zip from the output folder at archipelago.gg/uploads to host it.", "ME2 AP Setup", MessageBoxButtons.YesNo) != DialogResult.Yes) return;
        using var run = Process.Start(new ProcessStartInfo(generator) { WorkingDirectory = _apDir.Text, UseShellExecute = true });
        run.WaitForExit();
        Process.Start(new ProcessStartInfo("explorer.exe", Path.Combine(_apDir.Text, "output")) { UseShellExecute = true });
    }

    // ---------------------------------------------------------------- options
    TabPage OptionsPage()
    {
        var page = new TabPage("3. Options");
        var top = new FlowLayoutPanel { Dock = DockStyle.Top, AutoSize = true, Padding = new Padding(8) };
        top.Controls.Add(new Label { Text = "Slot name", AutoSize = true, Margin = new Padding(0, 6, 4, 0) });
        top.Controls.Add(_slot);
        top.Controls.Add(new Label { Text = "Preset", AutoSize = true, Margin = new Padding(16, 6, 4, 0) });
        _preset.Items.Add("Default");
        foreach (var preset in _schema.GetProperty("presets").EnumerateObject()) _preset.Items.Add(preset.Name);
        _preset.SelectedIndex = 0;
        _preset.SelectedIndexChanged += (_, _) => ApplyPreset();
        top.Controls.Add(_preset);
        var save = new Button { Text = "Save to Archipelago Players", AutoSize = true, Margin = new Padding(16, 2, 0, 0) };
        var saveAs = new Button { Text = "Save As...", AutoSize = true, Margin = new Padding(4, 2, 0, 0) };
        save.Click += (_, _) => SaveYaml(null);
        var generate = new Button { Text = "Save + Generate seed", AutoSize = true, Margin = new Padding(4, 2, 0, 0) };
        generate.Click += (_, _) =>
        {
            try { Generate(); }
            catch (Exception ex) { MessageBox.Show(this, ex.Message, "ME2 AP Setup", MessageBoxButtons.OK, MessageBoxIcon.Warning); }
        };
        saveAs.Click += (_, _) =>
        {
            using var dialog = new SaveFileDialog { Filter = "YAML|*.yaml", FileName = SafeName() + ".yaml" };
            if (dialog.ShowDialog(this) == DialogResult.OK) SaveYaml(dialog.FileName);
        };
        top.Controls.Add(save);
        top.Controls.Add(saveAs);
        top.Controls.Add(generate);

        var groups = new TabControl { Dock = DockStyle.Fill };
        foreach (var group in _schema.GetProperty("groups").EnumerateArray())
        {
            var tab = new TabPage(group.GetProperty("name").GetString());
            var flow = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, AutoScroll = true, WrapContents = false, Padding = new Padding(8) };
            if (tab.Text == "ME1 History")
                flow.Controls.Add(new Label { AutoSize = true, MaximumSize = new Size(800, 0), Margin = new Padding(0, 0, 0, 8), Text =
                    "No ME1 save is needed for ME2. The mod skips the Genesis comic, and the Archipelago client writes these six choices " +
                    "into your new career the first time it connects (an impossible romance falls back to none)." });
            foreach (var o in group.GetProperty("options").EnumerateArray())
            {
                var def = new OptionDef
                {
                    Key = o.GetProperty("key").GetString(), Display = o.GetProperty("display").GetString(),
                    Doc = o.GetProperty("doc").GetString(), Type = o.GetProperty("type").GetString(), Default = o.GetProperty("default").Clone(),
                };
                if (o.TryGetProperty("choices", out var choices)) def.Choices = choices.EnumerateArray().Select(c => c.GetString()).ToArray();
                if (def.Type == "range") { def.Min = o.GetProperty("min").GetInt32(); def.Max = o.GetProperty("max").GetInt32(); }
                _options.Add(def);
                flow.Controls.Add(OptionRow(def));
            }
            tab.Controls.Add(flow);
            groups.TabPages.Add(tab);
        }
        page.Controls.Add(groups);
        page.Controls.Add(_help);
        page.Controls.Add(top);
        _help.Text = "Pick a preset or set each option; click an option to read what it does. Save writes <slot>.yaml into Archipelago's Players folder.";
        ApplyPreset();
        return page;
    }

    Control OptionRow(OptionDef def)
    {
        var row = new FlowLayoutPanel { AutoSize = true, WrapContents = false, Margin = new Padding(0, 4, 0, 4) };
        var label = new Label { Text = def.Display, Width = 230, Margin = new Padding(0, 6, 8, 0) };
        Control input = def.Type switch
        {
            "toggle" => new CheckBox { Text = "on", AutoSize = true },
            "choice" => new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 220 },
            "range" => new NumericUpDown { Minimum = def.Min, Maximum = def.Max, Width = 80 },
            _ => new CheckedListBox { Width = 260, Height = 20 * def.Choices.Length + 6, CheckOnClick = true },
        };
        if (input is CheckedListBox list) list.Items.AddRange(def.Choices);
        if (input is ComboBox combo) combo.Items.AddRange(def.Choices);
        void ShowHelp() => _help.Text = $"{def.Display}  ({def.Key})\r\n\r\n{def.Doc.Replace("\n", "\r\n")}";
        input.Enter += (_, _) => ShowHelp();
        input.Click += (_, _) => ShowHelp();
        label.Click += (_, _) => ShowHelp();
        _controls[def.Key] = input;
        row.Controls.Add(label);
        row.Controls.Add(input);
        return row;
    }

    void SetValue(OptionDef def, JsonElement value)
    {
        switch (_controls[def.Key])
        {
            case CheckBox box: box.Checked = value.ValueKind == JsonValueKind.True || (value.ValueKind == JsonValueKind.Number && value.GetInt32() != 0); break;
            case ComboBox combo: combo.SelectedItem = value.ValueKind == JsonValueKind.String ? value.GetString() : def.Choices[Math.Clamp(value.GetInt32(), 0, def.Choices.Length - 1)]; break;
            case NumericUpDown number: number.Value = Math.Clamp(value.GetInt32(), def.Min, def.Max); break;
            case CheckedListBox list:
                var on = value.EnumerateArray().Select(v => v.GetString()).ToHashSet();
                for (int i = 0; i < list.Items.Count; i++) list.SetItemChecked(i, on.Contains((string)list.Items[i]));
                break;
        }
    }

    void ApplyPreset()
    {
        foreach (var def in _options) SetValue(def, def.Default);
        if (_preset.SelectedIndex > 0 && _schema.GetProperty("presets").TryGetProperty((string)_preset.SelectedItem, out var preset))
            foreach (var entry in preset.EnumerateObject())
                if (_options.FirstOrDefault(d => d.Key == entry.Name) is { } def) SetValue(def, entry.Value);
    }

    string SafeName()
    {
        var name = string.Concat(_slot.Text.Trim().Where(c => !Path.GetInvalidFileNameChars().Contains(c)));
        return name.Length > 0 ? name : "Shepard";
    }

    static string Quote(string s) => "'" + s.Replace("'", "''") + "'";

    string BuildYaml()
    {
        var game = _schema.GetProperty("game").GetString();
        var yaml = new StringBuilder();
        yaml.AppendLine("# Written by ME2 AP Setup 0.2.1. Put it in Archipelago's Players folder and run Generate.");
        yaml.AppendLine($"name: {Quote(_slot.Text.Trim().Length > 0 ? _slot.Text.Trim() : "Shepard")}");
        yaml.AppendLine($"description: {Quote("ME2 AP Setup, preset " + _preset.SelectedItem)}");
        yaml.AppendLine($"game: {Quote(game)}");
        yaml.AppendLine("requires:");
        yaml.AppendLine($"  version: {_schema.GetProperty("minimum_ap_version").GetString()}");
        yaml.AppendLine("  game:");
        yaml.AppendLine($"    {Quote(game)}: {_schema.GetProperty("world_version").GetString()}");
        yaml.AppendLine($"{Quote(game)}:");
        foreach (var def in _options)
        {
            var value = _controls[def.Key] switch
            {
                CheckBox box => box.Checked ? "'true'" : "'false'",
                ComboBox combo => Quote((string)combo.SelectedItem),
                NumericUpDown number => ((int)number.Value).ToString(),
                CheckedListBox list => "[" + string.Join(", ", list.CheckedItems.Cast<string>().Select(Quote)) + "]",
                _ => throw new InvalidOperationException(def.Key),
            };
            yaml.AppendLine($"  {def.Key}: {value}");
        }
        return yaml.ToString();
    }

    bool SaveYaml(string path)
    {
        if (path == null)
        {
            if (!File.Exists(Path.Combine(_apDir.Text, "ArchipelagoLauncher.exe")))
            {
                MessageBox.Show(this, "Set the Archipelago folder on page 1, or use Save As.", "ME2 AP Setup");
                return false;
            }
            var players = Path.Combine(_apDir.Text, "Players");
            Directory.CreateDirectory(players);
            path = Path.Combine(players, SafeName() + ".yaml");
            if (File.Exists(path) && MessageBox.Show(this, $"{path} exists. Replace it?", "ME2 AP Setup", MessageBoxButtons.YesNo) != DialogResult.Yes) return false;
        }
        File.WriteAllText(path, BuildYaml(), new UTF8Encoding(false));
        MessageBox.Show(this, $"Saved {path}", "ME2 AP Setup");
        return true;
    }

    // used by the --write-yaml check (tools/setup/README.md): build the default YAML without showing the window
    public string DefaultYaml(string slot, string preset)
    {
        _slot.Text = slot;
        _preset.SelectedItem = preset;
        ApplyPreset();
        return BuildYaml();
    }
}

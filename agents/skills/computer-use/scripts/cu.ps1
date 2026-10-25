<#
.SYNOPSIS
  Windows computer-use helper: screenshot, window control, mouse, keyboard.

.DESCRIPTION
  Zero-dependency (PowerShell + user32/gdi32 P/Invoke).
  All coordinates are PHYSICAL pixels (script calls SetProcessDPIAware).

.EXAMPLE
  cu.ps1 info
  cu.ps1 shot -Out C:\tmp\s.png
  cu.ps1 windows -Filter QMT
  cu.ps1 activate -Title QMT
  cu.ps1 click -X 800 -Y 400
  cu.ps1 type -Text "hello"
  cu.ps1 hotkey -Keys "CTRL+S"
  cu.ps1 selftest
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet('info', 'shot', 'windows', 'activate', 'move', 'click', 'drag', 'scroll', 'type', 'key', 'hotkey', 'selftest')]
    [string]$Action,

    [int]$X, [int]$Y, [int]$X1, [int]$Y1, [int]$X2, [int]$Y2,
    [int]$W, [int]$H, [int]$Delta, [int]$Times = 1,
    [string]$Out, [string]$Text, [string]$Name, [string]$Keys,
    [string]$Title, [int64]$Hwnd, [string]$Filter,
    [ValidateSet('left', 'right', 'middle')][string]$Button = 'left',
    [switch]$Double, [switch]$All
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

if (-not ('CU' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class CU
{
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern int GetSystemMetrics(int i);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern IntPtr GetDC(IntPtr h);
    [DllImport("gdi32.dll")] public static extern int GetDeviceCaps(IntPtr dc, int index);
    [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] inputs, int size);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);

    public delegate bool EnumProc(IntPtr h, IntPtr l);

    [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X; public int Y; }
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT { public int dx, dy; public uint mouseData, dwFlags, time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort wVk, wScan; public uint dwFlags, time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Explicit)] public struct InputUnion { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; }
    [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public InputUnion U; }

    const uint INPUT_MOUSE = 0, INPUT_KEYBOARD = 1;
    const uint ME_LEFTDOWN = 0x0002, ME_LEFTUP = 0x0004, ME_RIGHTDOWN = 0x0008, ME_RIGHTUP = 0x0010;
    const uint ME_MIDDLEDOWN = 0x0020, ME_MIDDLEUP = 0x0040, ME_WHEEL = 0x0800;
    const uint KE_KEYUP = 0x0002, KE_UNICODE = 0x0004;

    public static void Init() { SetProcessDPIAware(); }

    public static int ScalePercent()
    {
        IntPtr dc = GetDC(IntPtr.Zero);
        int dpi = GetDeviceCaps(dc, 88); // LOGPIXELSX
        return dpi * 100 / 96;
    }

    static INPUT Mouse(uint flags, uint data)
    {
        INPUT i = new INPUT();
        i.type = INPUT_MOUSE;
        i.U.mi.dwFlags = flags;
        i.U.mi.mouseData = data;
        return i;
    }

    static void Send(INPUT[] arr) { SendInput((uint)arr.Length, arr, Marshal.SizeOf(typeof(INPUT))); }

    public static void MouseDown(string button) { Send(new INPUT[] { Mouse(DownFlag(button), 0) }); }
    public static void MouseUp(string button) { Send(new INPUT[] { Mouse(UpFlag(button), 0) }); }

    static uint DownFlag(string b)
    {
        if (b == "right") return ME_RIGHTDOWN;
        if (b == "middle") return ME_MIDDLEDOWN;
        return ME_LEFTDOWN;
    }

    static uint UpFlag(string b)
    {
        if (b == "right") return ME_RIGHTUP;
        if (b == "middle") return ME_MIDDLEUP;
        return ME_LEFTUP;
    }

    public static void Click(string button, bool dbl)
    {
        int n = dbl ? 2 : 1;
        for (int k = 0; k < n; k++)
        {
            MouseDown(button);
            System.Threading.Thread.Sleep(30);
            MouseUp(button);
            if (dbl) System.Threading.Thread.Sleep(80);
        }
    }

    public static void Wheel(int delta)
    {
        INPUT i = Mouse(ME_WHEEL, unchecked((uint)delta));
        Send(new INPUT[] { i });
    }

    public static void KeyDown(ushort vk) { KeyRaw(vk, 0, false); }
    public static void KeyUp(ushort vk) { KeyRaw(vk, 0, true); }

    static void KeyRaw(ushort vk, ushort scan, bool up)
    {
        INPUT i = new INPUT();
        i.type = INPUT_KEYBOARD;
        i.U.ki.wVk = vk;
        i.U.ki.wScan = scan;
        i.U.ki.dwFlags = up ? KE_KEYUP : 0;
        Send(new INPUT[] { i });
    }

    public static void TypeChar(char c)
    {
        INPUT d = new INPUT(); d.type = INPUT_KEYBOARD; d.U.ki.wVk = 0; d.U.ki.wScan = c; d.U.ki.dwFlags = KE_UNICODE;
        INPUT u = new INPUT(); u.type = INPUT_KEYBOARD; u.U.ki.wVk = 0; u.U.ki.wScan = c; u.U.ki.dwFlags = KE_UNICODE | KE_KEYUP;
        Send(new INPUT[] { d, u });
        System.Threading.Thread.Sleep(8);
    }

    public static List<IntPtr> Windows()
    {
        List<IntPtr> list = new List<IntPtr>();
        EnumWindows(delegate (IntPtr h, IntPtr l) { list.Add(h); return true; }, IntPtr.Zero);
        return list;
    }

    public static string TitleOf(IntPtr h)
    {
        StringBuilder sb = new StringBuilder(1024);
        GetWindowTextW(h, sb, sb.Capacity);
        return sb.ToString();
    }

    public static string ClassOf(IntPtr h)
    {
        StringBuilder sb = new StringBuilder(256);
        GetClassNameW(h, sb, sb.Capacity);
        return sb.ToString();
    }

    public static uint PidOf(IntPtr h)
    {
        uint pid; GetWindowThreadProcessId(h, out pid); return pid;
    }

    public static int[] Rect(IntPtr h)
    {
        RECT r; GetWindowRect(h, out r);
        return new int[] { r.Left, r.Top, r.Right - r.Left, r.Bottom - r.Top };
    }

    public static int[] Cursor() { POINT p; GetCursorPos(out p); return new int[] { p.X, p.Y }; }
}
'@
}

[CU]::Init()
$cursor = [CU]::Cursor()
$scale = [CU]::ScalePercent()

function Write-Json($obj) { $obj | ConvertTo-Json -Compress -Depth 5 }

function Wait-Target([int]$ms = 120) {
    if ($ms -gt 0) { Start-Sleep -Milliseconds $ms }
}

function Get-AllWindows {
    $rows = @()
    foreach ($h in [CU]::Windows()) {
        if (-not [CU]::IsWindowVisible($h)) { continue }
        $t = [CU]::TitleOf($h)
        if ([string]::IsNullOrWhiteSpace($t)) { continue }
        $r = [CU]::Rect($h)
        $rows += [pscustomobject][ordered]@{
            hwnd    = [int64]$h
            title   = $t
            class   = [CU]::ClassOf($h)
            pid     = [CU]::PidOf($h)
            x       = $r[0]; y = $r[1]; w = $r[2]; h = $r[3]
            iconic  = [CU]::IsIconic($h)
        }
    }
    return $rows
}

function Resolve-Window {
    if ($PSBoundParameters.ContainsKey('Hwnd') -and $Hwnd -gt 0) {
        return [pscustomobject]@{ hwnd = [int64]$Hwnd; title = [CU]::TitleOf([IntPtr]$Hwnd) }
    }
    if (-not $Title) { throw "need -Hwnd or -Title" }
    $match = Get-AllWindows | Where-Object { $_.title -like "*$Title*" }
    if (-not $match) { throw "no window matching '$Title'" }
    return ($match | Select-Object -Last 1)
}

try {
    switch ($Action) {

        'info' {
            $monitors = @()
            Add-Type -AssemblyName System.Windows.Forms
            foreach ($s in [System.Windows.Forms.Screen]::AllScreens) {
                $monitors += [pscustomobject]@{ name = $s.DeviceName; primary = $s.Primary; x = $s.Bounds.X; y = $s.Bounds.Y; w = $s.Bounds.Width; h = $s.Bounds.Height }
            }
            $vx = [CU]::GetSystemMetrics(76); $vy = [CU]::GetSystemMetrics(77)
            $vw = [CU]::GetSystemMetrics(78); $vh = [CU]::GetSystemMetrics(79)
            Write-Json ([ordered]@{
                    dpi_scale_percent = $scale
                    virtual           = [ordered]@{ x = $vx; y = $vy; w = $vw; h = $vh }
                    cursor            = [ordered]@{ x = $cursor[0]; y = $cursor[1] }
                    monitors          = $monitors
                })
        }

        'shot' {
            Add-Type -AssemblyName System.Windows.Forms
            $winHwnd = [IntPtr]::Zero
            if ($PSBoundParameters.ContainsKey('Hwnd') -and $Hwnd -gt 0) {
                $winHwnd = [IntPtr]$Hwnd
                $r = [CU]::Rect($winHwnd)
                $sx = $r[0]; $sy = $r[1]; $sw = $r[2]; $sh = $r[3]
            }
            elseif ($PSBoundParameters.ContainsKey('X') -and $PSBoundParameters.ContainsKey('Y') -and $PSBoundParameters.ContainsKey('W') -and $PSBoundParameters.ContainsKey('H')) {
                $sx = $X; $sy = $Y; $sw = $W; $sh = $H
            }
            else {
                $sx = [CU]::GetSystemMetrics(76); $sy = [CU]::GetSystemMetrics(77)
                $sw = [CU]::GetSystemMetrics(78); $sh = [CU]::GetSystemMetrics(79)
            }
            if ($sw -le 0 -or $sh -le 0) { throw "invalid capture region ${sw}x${sh}" }
            if (-not $Out) {
                $dir = Join-Path $env:TEMP 'cu'
                New-Item -ItemType Directory -Force -Path $dir | Out-Null
                $Out = Join-Path $dir ("shot-{0}.png" -f (Get-Date -Format 'HHmmss-fff'))
            }
            $bmp = New-Object System.Drawing.Bitmap $sw, $sh
            $g = [System.Drawing.Graphics]::FromImage($bmp)
            $mode = 'screen'
            if ($winHwnd -ne [IntPtr]::Zero) {
                $hdc = $g.GetHdc()
                try { $ok = [CU]::PrintWindow($winHwnd, $hdc, 2) } finally { $g.ReleaseHdc($hdc) }
                if ($ok) { $mode = 'printwindow' }
            }
            if ($mode -eq 'screen') { $g.CopyFromScreen($sx, $sy, 0, 0, $bmp.Size) }
            $bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
            $g.Dispose(); $bmp.Dispose()
            Write-Json ([ordered]@{ path = (Resolve-Path $Out).Path; x = $sx; y = $sy; w = $sw; h = $sh; mode = $mode })
        }

        'windows' {
            $rows = Get-AllWindows
            if ($Filter) { $rows = $rows | Where-Object { $_.title -like "*$Filter*" -or $_.class -like "*$Filter*" } }
            if ($All) { Write-Json @($rows) } else { Write-Json @($rows | Select-Object -First 25) }
        }

        'activate' {
            $w = Resolve-Window
            $h = [IntPtr]$w.hwnd
            if ([CU]::IsIconic($h)) { [CU]::ShowWindow($h, 9) | Out-Null }
            [CU]::BringWindowToTop($h) | Out-Null
            $ok = [CU]::SetForegroundWindow($h)
            Wait-Target 250
            $r = [CU]::Rect($h)
            Write-Json ([ordered]@{ hwnd = $w.hwnd; title = [CU]::TitleOf($h); activated = $ok; x = $r[0]; y = $r[1]; w = $r[2]; h = $r[3] })
        }

        'move' {
            if (-not ($PSBoundParameters.ContainsKey('X') -and $PSBoundParameters.ContainsKey('Y'))) { throw "need -X -Y" }
            [CU]::SetCursorPos($X, $Y) | Out-Null
            Wait-Target 80
            $c = [CU]::Cursor()
            Write-Json ([ordered]@{ x = $c[0]; y = $c[1] })
        }

        'click' {
            if ($PSBoundParameters.ContainsKey('X') -and $PSBoundParameters.ContainsKey('Y')) {
                [CU]::SetCursorPos($X, $Y) | Out-Null
                Wait-Target 60
            }
            $c = [CU]::Cursor()
            for ($i = 0; $i -lt $Times; $i++) { [CU]::Click($Button, [bool]$Double); Wait-Target 120 }
            Write-Json ([ordered]@{ clicked = $Button; double = [bool]$Double; times = $Times; x = $c[0]; y = $c[1] })
        }

        'drag' {
            if (-not ($PSBoundParameters.ContainsKey('X1') -and $PSBoundParameters.ContainsKey('Y1') -and
                    $PSBoundParameters.ContainsKey('X2') -and $PSBoundParameters.ContainsKey('Y2'))) {
                throw "need -X1 -Y1 -X2 -Y2"
            }
            [CU]::SetCursorPos($X1, $Y1) | Out-Null
            Wait-Target 120
            [CU]::MouseDown($Button)
            Wait-Target 120
            $steps = 12
            for ($i = 1; $i -le $steps; $i++) {
                $mx = [int]($X1 + ($X2 - $X1) * $i / $steps)
                $my = [int]($Y1 + ($Y2 - $Y1) * $i / $steps)
                [CU]::SetCursorPos($mx, $my) | Out-Null
                Start-Sleep -Milliseconds 25
            }
            Wait-Target 120
            [CU]::MouseUp($Button)
            $c = [CU]::Cursor()
            Write-Json ([ordered]@{ from = "$X1,$Y1"; to = "$X2,$Y2"; released_at = "$($c[0]),$($c[1])" })
        }

        'scroll' {
            if (-not $PSBoundParameters.ContainsKey('Delta')) { throw "need -Delta (positive=up, negative=down)" }
            if ($PSBoundParameters.ContainsKey('X') -and $PSBoundParameters.ContainsKey('Y')) {
                [CU]::SetCursorPos($X, $Y) | Out-Null
                Wait-Target 60
            }
            for ($i = 0; $i -lt $Times; $i++) { [CU]::Wheel($Delta); Wait-Target 60 }
            Write-Json ([ordered]@{ delta = $Delta; times = $Times })
        }

        'type' {
            if ($null -eq $Text) { throw "need -Text" }
            foreach ($ch in $Text.ToCharArray()) {
                if ($ch -eq "`n" -or $ch -eq "`r") { [CU]::KeyDown(13); [CU]::KeyUp(13); Start-Sleep -Milliseconds 20 }
                else { [CU]::TypeChar($ch) }
            }
            Write-Json ([ordered]@{ typed_chars = $Text.Length })
        }

        'key' {
            if (-not $Name) { throw "need -Name (ENTER/TAB/ESC/F1..F12/A..Z/0..9/ARROWS...)" }
            $map = @{
                ENTER = 13; TAB = 9; ESC = 27; ESCAPE = 27; SPACE = 32; BACKSPACE = 8; BACK = 8
                DELETE = 46; DEL = 46; INSERT = 45; HOME = 36; END = 35; PAGEUP = 33; PAGEDOWN = 34
                UP = 38; DOWN = 40; LEFT = 37; RIGHT = 39; WIN = 91; APPS = 93; PRINTSCREEN = 44
            }
            $n = $Name.ToUpper()
            if ($map.ContainsKey($n)) { $vk = [uint16]$map[$n] }
            elseif ($n -match '^F([1-9]|1[0-2])$') { $vk = [uint16](111 + [int]$n.Substring(1)) }
            elseif ($n.Length -eq 1 -and $n -match '[A-Z0-9]') { $vk = [uint16][char]$n }
            else { throw "unknown key '$Name'" }
            for ($i = 0; $i -lt $Times; $i++) {
                [CU]::KeyDown($vk); Wait-Target 20; [CU]::KeyUp($vk); Wait-Target 40
            }
            Write-Json ([ordered]@{ key = $n; times = $Times })
        }

        'hotkey' {
            if (-not $Keys) { throw "need -Keys e.g. CTRL+S" }
            $tokens = $Keys.ToUpper() -split '\+'
            $modMap = @{ CTRL = 17; CONTROL = 17; ALT = 18; SHIFT = 16; WIN = 91 }
            $keys = @()
            foreach ($t in $tokens) {
                if ($modMap.ContainsKey($t)) { $keys += [uint16]$modMap[$t] }
                elseif ($t -match '^F([1-9]|1[0-2])$') { $keys += [uint16](111 + [int]$t.Substring(1)) }
                elseif ($t.Length -eq 1) { $keys += [uint16][char]$t }
                else {
                    $special = @{ ENTER = 13; TAB = 9; ESC = 27; SPACE = 32; DELETE = 46; HOME = 36; END = 35; UP = 38; DOWN = 40; LEFT = 37; RIGHT = 39 }
                    if ($special.ContainsKey($t)) { $keys += [uint16]$special[$t] } else { throw "unknown hotkey token '$t'" }
                }
            }
            foreach ($k in $keys) { [CU]::KeyDown($k); Wait-Target 25 }
            [array]::Reverse($keys)
            foreach ($k in $keys) { [CU]::KeyUp($k); Wait-Target 25 }
            Write-Json ([ordered]@{ hotkey = $Keys })
        }

        'selftest' {
            $dir = Join-Path $env:TEMP ('cu-selftest-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
            $ready = Join-Path $dir 'ready.json'
            $log = Join-Path $dir 'clicks.log'
            $typed = Join-Path $dir 'typed.txt'
            $target = Join-Path $dir 'target.ps1'

            $targetCode = @'
param($ReadyPath, $ClickLog, $TypedPath)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type -TypeDefinition 'using System.Runtime.InteropServices; public class D { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }'
[D]::SetProcessDPIAware() | Out-Null

$form = New-Object System.Windows.Forms.Form
$form.Text = 'CU SELFTEST TARGET'
$form.StartPosition = 'Manual'
$form.Left = 300; $form.Top = 200
$form.Width = 620; $form.Height = 420
$form.TopMost = $false

$tb = New-Object System.Windows.Forms.TextBox
$tb.Left = 30; $tb.Top = 300; $tb.Width = 520; $tb.Height = 30
$tb.Add_TextChanged({ $tb.Text | Out-File -Encoding utf8 $TypedPath })
$form.Controls.Add($tb)

$form.Add_MouseDown({
    param($s, $e)
    $pt = $form.PointToScreen($e.Location)
    "$($pt.X),$($pt.Y)" | Out-File -Append -Encoding utf8 $ClickLog
})

$form.Add_Shown({
    $r = $form.Bounds
    @{ hwnd = [int64]$form.Handle; x = $r.X; y = $r.Y; w = $r.Width; h = $r.Height } | ConvertTo-Json -Compress | Out-File -Encoding utf8 $ReadyPath
    $tb.Focus() | Out-Null
})

[System.Windows.Forms.Application]::Run($form)
'@
            $targetCode | Out-File -Encoding utf8 $target

            $proc = Start-Process pwsh -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $target, '-ReadyPath', $ready, '-ClickLog', $log, '-TypedPath', $typed) -PassThru
            $deadline = (Get-Date).AddSeconds(20)
            while (-not (Test-Path $ready) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 200 }
            if (-not (Test-Path $ready)) { throw "selftest target did not start" }
            Start-Sleep -Milliseconds 400
            $info = Get-Content $ready -Raw | ConvertFrom-Json

            $results = [ordered]@{}

            # 1) window enumeration finds it
            $results.window_found = [bool](Get-AllWindows | Where-Object { $_.hwnd -eq $info.hwnd })

            # 2) activate
            $h = [IntPtr]$info.hwnd
            [CU]::BringWindowToTop($h) | Out-Null
            $results.activated = [CU]::SetForegroundWindow($h)
            Start-Sleep -Milliseconds 300

            # 3) click coordinate mapping: click inside form, compare logged screen point
            $cx = [int]($info.x + 200); $cy = [int]($info.y + 150)
            [CU]::SetCursorPos($cx, $cy) | Out-Null
            Start-Sleep -Milliseconds 100
            [CU]::Click('left', $false)
            Start-Sleep -Milliseconds 400
            if (Test-Path $log) {
                $hit = (Get-Content $log -Raw).Trim().Split("`n")[-1].Trim()
                $hp = $hit -split ','
                $results.click_sent = "$cx,$cy"
                $results.click_logged = $hit
                $results.click_dx = [math]::Abs([int]$hp[0] - $cx)
                $results.click_dy = [math]::Abs([int]$hp[1] - $cy)
                $results.click_ok = ($results.click_dx -le 2 -and $results.click_dy -le 2)
            }
            else { $results.click_ok = $false }

            # 4) typing: click the textbox area then type
            $tx = [int]($info.x + 30 + 100); $ty = [int]($info.y + 300 + 12)
            [CU]::SetCursorPos($tx, $ty) | Out-Null
            Start-Sleep -Milliseconds 100
            [CU]::Click('left', $false)
            Start-Sleep -Milliseconds 300
            foreach ($ch in 'cu-ok'.ToCharArray()) { [CU]::TypeChar($ch) }
            Start-Sleep -Milliseconds 600
            if (Test-Path $typed) {
                $results.typed = (Get-Content $typed -Raw).Trim()
                $results.type_ok = ($results.typed -eq 'cu-ok')
            }
            else { $results.type_ok = $false }

            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 200
            Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue

            $results.pass = ($results.window_found -and $results.activated -and $results.click_ok -and $results.type_ok)
            Write-Json $results
        }
    }
}
catch {
    Write-Json ([ordered]@{ error = $_.Exception.Message })
    exit 1
}

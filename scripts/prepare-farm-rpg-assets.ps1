[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceRoot = Join-Path $repoRoot "assets\Farm RPG - Tiny Asset Pack - (All in One) - new"
$targetRoot = Join-Path $repoRoot "apps\web\public\world\farm-rpg"
$manifestPath = Join-Path $repoRoot "assets\manifest.json"

if (-not (Test-Path -LiteralPath $sourceRoot)) {
    throw "Farm RPG source pack not found at $sourceRoot"
}

New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null
Add-Type -AssemblyName System.Drawing

$selected = [System.Collections.Generic.List[object]]::new()

function Register-Asset {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Runtime,
        [Parameter(Mandatory = $true)][string]$Purpose
    )

    $runtimePath = Join-Path $targetRoot $Runtime
    $hash = (Get-FileHash -LiteralPath $runtimePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $selected.Add(
        [ordered]@{
            source = $Source.Replace("\", "/")
            runtime = "apps/web/public/world/farm-rpg/$($Runtime.Replace('\', '/'))"
            purpose = $Purpose
            sha256 = $hash
        }
    )
}

function Copy-SelectedAsset {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Runtime,
        [Parameter(Mandatory = $true)][string]$Purpose
    )

    $sourcePath = Join-Path $sourceRoot $Source
    $runtimePath = Join-Path $targetRoot $Runtime
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $runtimePath) | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $runtimePath -Force
    Register-Asset -Source $Source -Runtime $Runtime -Purpose $Purpose
}

function Export-Crop {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Runtime,
        [Parameter(Mandatory = $true)][string]$Purpose,
        [Parameter(Mandatory = $true)][int]$X,
        [Parameter(Mandatory = $true)][int]$Y,
        [Parameter(Mandatory = $true)][int]$Width,
        [Parameter(Mandatory = $true)][int]$Height
    )

    $sourcePath = Join-Path $sourceRoot $Source
    $runtimePath = Join-Path $targetRoot $Runtime
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $runtimePath) | Out-Null

    $sourceImage = [System.Drawing.Bitmap]::FromFile($sourcePath)
    try {
        $rectangle = [System.Drawing.Rectangle]::new($X, $Y, $Width, $Height)
        $cropped = $sourceImage.Clone(
            $rectangle,
            [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
        )
        try {
            $cropped.Save($runtimePath, [System.Drawing.Imaging.ImageFormat]::Png)
        }
        finally {
            $cropped.Dispose()
        }
    }
    finally {
        $sourceImage.Dispose()
    }

    Register-Asset -Source "$Source crop($X,$Y,$Width,$Height)" -Runtime $Runtime -Purpose $Purpose
}

function Export-Composite {
    param(
        [Parameter(Mandatory = $true)][string[]]$Sources,
        [Parameter(Mandatory = $true)][string]$Runtime,
        [Parameter(Mandatory = $true)][string]$Purpose
    )

    $runtimePath = Join-Path $targetRoot $Runtime
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $runtimePath) | Out-Null
    $layers = @(
        $Sources | ForEach-Object {
            [System.Drawing.Bitmap]::FromFile((Join-Path $sourceRoot $_))
        }
    )

    try {
        $width = $layers[0].Width
        $height = $layers[0].Height
        $canvas = [System.Drawing.Bitmap]::new(
            $width,
            $height,
            [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
        )
        try {
            $graphics = [System.Drawing.Graphics]::FromImage($canvas)
            try {
                $graphics.Clear([System.Drawing.Color]::Transparent)
                $graphics.CompositingMode = [System.Drawing.Drawing2D.CompositingMode]::SourceOver
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
                foreach ($layer in $layers) {
                    $graphics.DrawImageUnscaled($layer, 0, 0)
                }
            }
            finally {
                $graphics.Dispose()
            }
            $canvas.Save($runtimePath, [System.Drawing.Imaging.ImageFormat]::Png)
        }
        finally {
            $canvas.Dispose()
        }
    }
    finally {
        foreach ($layer in $layers) {
            $layer.Dispose()
        }
    }

    Register-Asset -Source ($Sources -join " + ") -Runtime $Runtime -Purpose $Purpose
}

# Terrain and water.
Copy-SelectedAsset "Tileset\Tileset Grass Spring.png" "terrain-spring.png" "Spring terrain and dirt-path source tiles"
Copy-SelectedAsset "Tileset\Tileset Grass Water Spring.png" "terrain-water-spring.png" "Spring shoreline source tiles"
Copy-SelectedAsset "Tileset\Water tile.png" "water.png" "Harbor water base tile"
Copy-SelectedAsset "Tileset\Path tiles.png" "paths.png" "Civic stone and timber path source tiles"

# Complete buildings and assembled crops.
Export-Crop "Objects\Exterior\Houses\NPCS houses\School.png" "building-guildhouse.png" "Guildhouse" 0 0 224 160
Export-Crop "Objects\Exterior\Houses\NPCS houses\temple.png" "building-chapel.png" "Chapel" 0 0 112 208
Export-Crop "Objects\Exterior\Houses\NPCS houses\Base houses.png" "building-inn.png" "The Gull and Anchor" 0 16 192 160
Copy-SelectedAsset "Objects\Exterior\Houses\7.png" "building-constable.png" "Constable post"
Copy-SelectedAsset "Objects\Exterior\Houses\8.png" "building-midwife.png" "Midwife cottage"

# Village props cropped into ready-to-render sprites.
Export-Crop "Objects\Exterior\Water fountain.png" "prop-fountain.png" "Town-square fountain" 0 0 48 64
Export-Crop "Objects\Exterior\Well .png" "prop-well.png" "Village well" 0 0 32 48
Export-Crop "Objects\Exterior\Exterior.png" "prop-notice-board.png" "Public notice board" 144 0 48 48
Export-Crop "Objects\Exterior\Exterior.png" "prop-bench.png" "Square bench" 96 32 32 16
Export-Crop "Objects\Exterior\Exterior.png" "prop-signpost.png" "Direction signpost" 176 0 32 48
Export-Crop "Objects\Exterior\Exterior.png" "prop-flowers.png" "Spring flower patch" 0 112 96 32
Export-Crop "Objects\Exterior\Exterior.png" "prop-barrels.png" "Harbor barrel stack" 128 96 64 48
Export-Crop "Objects\Exterior\Exterior.png" "prop-graves.png" "Chapel grave markers" 48 144 32 32
# The generic Exterior sheet only contains detached awnings. Use the complete
# 48x48 vendor booths from the matching Beach tent sheet so the counters,
# produce, posts, and canopy are exported as one runtime sprite.
Export-Crop "Objects\Exterior\Beach\Tent.png" "market-stall-blue.png" "Complete blue produce stall" 0 48 48 48
Export-Crop "Objects\Exterior\Beach\Tent.png" "market-stall-red.png" "Complete red produce stall" 96 48 48 48
Export-Crop "Objects\Exterior\Beach\Tent.png" "market-stall-cream.png" "Complete cream produce stall" 48 48 48 48
Export-Crop "Objects\Exterior\Fence and Bridge\Bridge.png" "prop-bridge.png" "Harbor boardwalk bridge" 16 0 64 32
Export-Crop "Objects\Exterior\Beach\Wood Boat.png" "prop-boat.png" "Harbor boat" 0 0 176 112
# The common-tree atlas stores its complete large-tree row in 32x48 cells
# beginning at y=48. The previous 48x64 crop included pieces of both the small
# tree row above and the neighboring canopy.
Export-Crop "Objects\Tree\Common\Shadow\Maple Tree.png" "tree-green.png" "Green boundary tree" 0 48 32 48
Export-Crop "Objects\Tree\Common\Shadow\Maple Tree.png" "tree-lime.png" "Light-green village tree" 32 48 32 48
Export-Crop "Objects\Tree\Common\Shadow\Maple Tree.png" "tree-teal.png" "Teal depth tree" 128 48 32 48

# Premade player and resident sheets.
$characters = [ordered]@{
    "player-alex" = "Character\Character\Pre-made\Alex"
    "marta-lyria" = "Character\Character\Pre-made\Lyria"
    "pip-josh" = "Character\Character\Pre-made\Josh"
    "talia-tori" = "Character\Character\Pre-made\Tori"
    "rhea-manu" = "Character\Character\Pre-made\Manu"
}
foreach ($entry in $characters.GetEnumerator()) {
    Copy-SelectedAsset "$($entry.Value)\Idle.png" "characters\$($entry.Key)-idle.png" "$($entry.Key) idle animation"
    Copy-SelectedAsset "$($entry.Value)\Walk.png" "characters\$($entry.Key)-walk.png" "$($entry.Key) walk animation"
}
Copy-SelectedAsset "Character\Character\Others\NPC'S\Blacksmith\Idle.png" "characters\bram-blacksmith-idle.png" "Bram idle animation"
Copy-SelectedAsset "Character\Character\Others\NPC'S\Blacksmith\Walk.png" "characters\bram-blacksmith-walk.png" "Bram walk animation"
Copy-SelectedAsset "Character\Character\Others\NPC'S\Pirate\Idle.png" "characters\nessa-pirate-idle.png" "Nessa idle animation"
Copy-SelectedAsset "Character\Character\Others\NPC'S\Pirate\Walk.png" "characters\nessa-pirate-walk.png" "Nessa walk animation"
Copy-SelectedAsset "Character\Character\Others\NPC'S\Banker\Idle.png" "characters\elias-banker-idle.png" "Elias idle animation"
Copy-SelectedAsset "Character\Character\Others\NPC'S\Banker\Walk.png" "characters\elias-banker-walk.png" "Elias walk animation"

$orinIdleLayers = @(
    "Character\Character\PNG\1. Idle\Skins\1.png",
    "Character\Character\PNG\1. Idle\Clothers\Farm\Blue.png",
    "Character\Character\PNG\1. Idle\Eyes\Male\Brown.png",
    "Character\Character\PNG\1. Idle\Hair's\Sebastian\Brown.png"
)
$orinWalkLayers = @(
    "Character\Character\PNG\2. Walk\Skins\1.png",
    "Character\Character\PNG\2. Walk\Clothers\Farm\Blue.png",
    "Character\Character\PNG\2. Walk\Eyes\Male\Brown.png",
    "Character\Character\PNG\2. Walk\Hair's\Sebastian\Brown.png"
)
Export-Composite $orinIdleLayers "characters\orin-idle.png" "Orin modular idle animation"
Export-Composite $orinWalkLayers "characters\orin-walk.png" "Orin modular walk animation"

# Premade portraits plus a modular Orin portrait.
$portraitNumbers = [ordered]@{
    "marta" = "8"
    "bram" = "7"
    "pip" = "3"
    "talia" = "2"
    "rhea" = "10"
    "nessa" = "6"
    "elias" = "1"
}
foreach ($entry in $portraitNumbers.GetEnumerator()) {
    Copy-SelectedAsset "Character\Portrait\Premade\$($entry.Value).png" "portraits\$($entry.Key).png" "$($entry.Key) conversation portrait"
}
$orinPortraitLayers = @(
    "Character\Portrait\PNG\Skins\Male\1.png",
    "Character\Portrait\PNG\Clothers\Male\Blue.png",
    "Character\Portrait\PNG\Eyes\Brown.png",
    "Character\Portrait\PNG\Hair\Sebastian\Brown.png"
)
Export-Composite $orinPortraitLayers "portraits\orin.png" "Orin modular conversation portrait"

# UI artwork retained as integrated framing, not redistributed as a source pack.
Copy-SelectedAsset "UI\dialogue box.png" "ui-dialogue.png" "Conversation frame texture"
Copy-SelectedAsset "UI\HUD.png" "ui-hud.png" "Objective and clock frame texture"
Copy-SelectedAsset "UI\weather icons.png" "ui-weather.png" "Weather icon source sheet"

$manifest = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    pack = "Farm RPG - Tiny Asset Pack - (All in One)"
    creator = "Maeve Devs (formerly EmanuelleDev)"
    source_url = "https://maevedevs.itch.io/farm-rpg"
    local_license_file = "assets/Farm RPG - Tiny Asset Pack - (All in One) - new/Lincese   Info.txt"
    license_summary = @(
        "Commercial and non-commercial project use permitted.",
        "Modification permitted.",
        "Resale or redistribution, including modified asset packs, prohibited.",
        "Credit required by the bundled license.",
        "Crypto/NFT use and AI training prohibited by the current product license."
    )
    files = $selected
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Output "Prepared $($selected.Count) Farm RPG runtime assets in $targetRoot"

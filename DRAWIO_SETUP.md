# Draw.io Desktop Setup for V13 Development

## Quick Installation Guide

### Download Draw.io Desktop v28.2.8

**Official Release**: https://github.com/jgraph/drawio-desktop/releases/tag/v28.2.8

### For Windows (Your System)

**Recommended: Windows Installer**
```
drawio-x64-28.2.8.exe (Installer)
- Size: ~150 MB
- Installs to: C:\Program Files\draw.io
- Creates desktop shortcut
- Integrates with Windows
```

**Alternative: Portable Version**
```
drawio-x64-28.2.8-no-installer.exe
- No installation required
- Run directly from any folder
- Good for USB/portable use
```

### Installation Steps

1. **Download**
   - Go to: https://github.com/jgraph/drawio-desktop/releases/tag/v28.2.8
   - Click: `drawio-x64-28.2.8.exe`
   - Save to: Downloads folder

2. **Install**
   ```powershell
   # Run the installer
   cd $env:USERPROFILE\Downloads
   .\drawio-x64-28.2.8.exe
   ```
   - Follow installation wizard
   - Accept default settings
   - Create desktop shortcut: ✅ Yes

3. **Verify Installation**
   ```powershell
   # Check if installed
   Test-Path "C:\Program Files\draw.io\draw.io.exe"
   # Should return: True
   ```

4. **Launch Draw.io**
   - Double-click desktop shortcut, OR
   - Start Menu → draw.io, OR
   ```powershell
   & "C:\Program Files\draw.io\draw.io.exe"
   ```

## First-Time Setup

### 1. Configure for V13 Development

**On First Launch:**
1. Choose: **"Decide later"** for cloud storage (we'll use local files)
2. Set default save location:
   - File → Preferences → Default Location
   - Set to: `C:\Users\BRHN\Videos\bohrn 2025\trade\V13 gloabal\V13\diagrams`

### 2. Load V13 Template

1. Open Draw.io Desktop
2. File → Open
3. Navigate to: `diagrams/templates/module_template.drawio`
4. Save As → Your new diagram name

### 3. Configure Auto-Save

1. File → Preferences
2. Enable: **Auto-save** (every 2 minutes)
3. Enable: **Backup** (keep 3 versions)

## Integration with V13 Workflow

### Workflow Setup

**Your Development Folder:**
```
C:\Users\BRHN\Videos\bohrn 2025\trade\V13 gloabal\V13\
├── diagrams/              ← Draw.io files here
│   ├── architecture/
│   ├── workflows/
│   ├── modules/
│   ├── doctrines/
│   ├── risk/
│   └── templates/
├── core/                  ← Generated Python code here
├── docs/                  ← Exported SVG diagrams here
└── WORKFLOW_GUIDE.md      ← Your workflow reference
```

### Quick Access Setup

**Create PowerShell Alias:**
```powershell
# Add to your PowerShell profile
notepad $PROFILE

# Add this line:
function drawio { & "C:\Program Files\draw.io\draw.io.exe" $args }

# Save and reload
. $PROFILE

# Now you can open diagrams quickly:
drawio diagrams/workflows/my_flow.drawio
```

**Create Batch File for Quick Launch:**
```batch
# Create: open_drawio.bat in V13 root
@echo off
cd /d "C:\Users\BRHN\Videos\bohrn 2025\trade\V13 gloabal\V13\diagrams"
start "" "C:\Program Files\draw.io\draw.io.exe"
```

## Using Draw.io with BlackBox AI

### Step-by-Step Example

**1. Create Diagram in Draw.io Desktop**
```
File → New
Use template: diagrams/templates/module_template.drawio
Design your flow
Save as: diagrams/modules/V13_NewFeature.drawio
```

**2. Export for AI Processing**
```
File → Export as → XML (.drawio)
✅ Already saved as .drawio - ready for AI!
```

**3. Generate Code with BlackBox AI**
```
In this chat:
"Read diagrams/modules/V13_NewFeature.drawio and generate 
the Python module with proper V13 integration"
```

**4. Export for Documentation**
```
File → Export as → SVG
Save to: docs/diagrams/V13_NewFeature.svg
(For including in documentation)
```

## Draw.io Desktop Features for V13

### Useful Features

**1. Layers** (for complex diagrams)
- View → Layers
- Create layers: Data Flow, Error Handling, Logging
- Toggle visibility while working

**2. Shape Libraries**
- More Shapes → Software → UML
- More Shapes → Flowchart
- More Shapes → AWS (for cloud integrations)

**3. Custom Shapes for V13**
- Create custom shapes for V13 modules
- Save as library: File → New Library
- Reuse across diagrams

**4. Collaboration**
- File → Export as → PNG/SVG (for sharing)
- File → Export as → PDF (for presentations)
- File → Export as → XML (for version control)

### Keyboard Shortcuts

```
Ctrl + S          Save
Ctrl + D          Duplicate
Ctrl + C/V        Copy/Paste
Ctrl + Z/Y        Undo/Redo
Ctrl + G          Group
Ctrl + Shift + G  Ungroup
Ctrl + Mouse      Multi-select
Alt + Drag        Duplicate while dragging
```

## V13-Specific Diagram Conventions

### Color Coding (Recommended)

```
Blue (#dae8fc)    - Data Processing
Red (#f8cecc)     - Risk/Validation/Errors
Green (#d5e8d4)   - Execution/Success
Yellow (#fff2cc)  - Inputs/Configuration
Purple (#e1d5e7)  - Outputs/Results
Gray (#f5f5f5)    - Logging/Monitoring
```

### Shape Usage

```
Rectangle         - Modules/Components
Diamond           - Decision Points
Rounded Rectangle - Start/End
Parallelogram     - Input/Output
Cylinder          - Database/Storage
Cloud             - External API
```

### Labeling Convention

```
✅ Good: "Calculate Position Size (float) → Risk Check"
❌ Bad: "calc → check"

✅ Good: "V13_RiskSentinel.validate_order(order: dict) → bool"
❌ Bad: "validate"
```

## Example: Create Your First V13 Diagram

### Scenario: Document Signal Processing Flow

**1. Open Draw.io Desktop**
```powershell
drawio
```

**2. Create New Diagram**
- File → New
- Choose: Blank Diagram
- Name: `signal_processing_flow`

**3. Design the Flow**
```
[Signal Received]
    ↓
[V13_SignalValidator]
    ↓
[Valid?] ◇ → [No] → [Log & Reject]
    ↓ [Yes]
[V13_RiskSentinel]
    ↓
[Risk OK?] ◇ → [No] → [Log & Reject]
    ↓ [Yes]
[V13_CommanderFlex]
    ↓
[Execute Order]
    ↓
[V13_SessionLogger]
```

**4. Save**
- File → Save As
- Location: `diagrams/workflows/signal_processing_flow.drawio`

**5. Generate Code**
```
In BlackBox AI:
"Read diagrams/workflows/signal_processing_flow.drawio and 
show me the current implementation in V13 code, then suggest 
improvements based on the diagram"
```

**6. Export for Docs**
- File → Export as → SVG
- Save to: `docs/diagrams/signal_processing_flow.svg`

## Troubleshooting

### Draw.io Won't Open .drawio Files

**Solution:**
```powershell
# Set file association
cmd /c assoc .drawio=drawio.file
cmd /c ftype drawio.file="C:\Program Files\draw.io\draw.io.exe" "%1"
```

### Can't Find Saved Diagrams

**Check Default Location:**
```powershell
# Your diagrams should be here:
cd "C:\Users\BRHN\Videos\bohrn 2025\trade\V13 gloabal\V13\diagrams"
dir *.drawio /s
```

### BlackBox AI Can't Read Diagram

**Verify File Format:**
- Must be saved as `.drawio` (XML format)
- Not `.png`, `.svg`, or `.pdf`
- File should be in `diagrams/` folder

## Advanced Tips

### Version Control for Diagrams

**Git Integration:**
```powershell
# Add diagrams to git
git add diagrams/
git commit -m "Add signal processing flow diagram"

# Track changes
git diff diagrams/workflows/signal_processing_flow.drawio
```

### Batch Export

**Export All Diagrams:**
```powershell
# PowerShell script to export all .drawio to .svg
$drawioPath = "C:\Program Files\draw.io\draw.io.exe"
$diagramsPath = "diagrams"
$docsPath = "docs/diagrams"

Get-ChildItem -Path $diagramsPath -Filter *.drawio -Recurse | ForEach-Object {
    $outputPath = Join-Path $docsPath ($_.BaseName + ".svg")
    & $drawioPath --export --format svg --output $outputPath $_.FullName
}
```

### Custom Templates

**Create V13 Module Template:**
1. Design your standard module layout
2. File → Save As Template
3. Name: `V13_Module_Template`
4. Use: File → New → From Template

## Resources

### Official Documentation
- **Draw.io Desktop**: https://github.com/jgraph/drawio-desktop
- **User Manual**: https://www.diagrams.net/doc/
- **Video Tutorials**: https://www.youtube.com/c/drawio

### V13 Integration
- **Workflow Guide**: `WORKFLOW_GUIDE.md`
- **Diagram Guide**: `diagrams/README.md`
- **System Blueprint**: `MASTER_BLUEPRINT_V13.md`

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ V13 + Draw.io Desktop Quick Reference                  │
├─────────────────────────────────────────────────────────┤
│ 1. Design in Draw.io Desktop                           │
│    → Save as .drawio in diagrams/ folder               │
│                                                         │
│ 2. Generate Code                                        │
│    → "BlackBox, read diagrams/[file].drawio"           │
│                                                         │
│ 3. Test in V13                                          │
│    → python core/V13_NewModule.py                      │
│                                                         │
│ 4. Export for Docs                                      │
│    → File → Export as → SVG                            │
│                                                         │
│ 5. Update Blueprint                                     │
│    → Add to MASTER_BLUEPRINT_V13.md                    │
└─────────────────────────────────────────────────────────┘
```

## Next Steps

1. **Install Draw.io Desktop v28.2.8**
   - Download from GitHub release page
   - Run installer
   - Create desktop shortcut

2. **Configure for V13**
   - Set default save location to `diagrams/`
   - Enable auto-save
   - Load module template

3. **Create First Diagram**
   - Document existing V13 module
   - Or design new feature
   - Save and generate code with BlackBox AI

4. **Establish Workflow**
   - Use for all new features
   - Update diagrams when code changes
   - Keep visual and code in sync

---

**You're now ready to use Draw.io Desktop for visual V13 development!**

The combination of Draw.io Desktop + BlackBox AI + V13 gives you professional-grade visual development with AI-powered implementation speed.

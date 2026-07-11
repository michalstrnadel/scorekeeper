# README GIF — render with: vhs demo/demo.tape   (from the repo root)
Output docs/assets/demo.gif

Set FontSize 16
Set Width 1120
Set Height 500
Set Padding 16
Set Theme "Catppuccin Mocha"
Set TypingSpeed 30ms

# warm the uv env off-screen so the GIF opens straight on the demo
Hide
Type "uv run --project core python -c 'import scorekeeper' && clear"
Enter
Sleep 8s
Show

Type "uv run --project core python demo/drift_demo.py"
Sleep 400ms
Enter
Sleep 16s
Sleep 3s

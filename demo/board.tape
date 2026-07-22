# README board GIF — render with: vhs demo/board.tape   (from the repo root)
Output docs/assets/board.gif

Set FontSize 16
Set Width 1120
Set Height 520
Set Padding 16
Set Theme "Catppuccin Mocha"
Set TypingSpeed 30ms

# warm the uv env off-screen so the GIF opens straight on the board
Hide
Type "uv run --project core python -c 'import scorekeeper' && clear"
Enter
Sleep 8s
Show

Type "uv run --project core python demo/board_demo.py"
Sleep 400ms
Enter
Sleep 14s

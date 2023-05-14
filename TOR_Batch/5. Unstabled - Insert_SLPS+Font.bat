pushd ".."
python "Tales_Exe.py" -g TOR insert -ft "Elf"
popd
pushd "../Font_TOR"
armips TOR_SLPS_fixes.asm
popd
pause
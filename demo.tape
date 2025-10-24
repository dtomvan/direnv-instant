# run as: PATH="$PWD/target/debug:$PATH" vhs demo.tape

Output demo.mp4
Require direnv
Require direnv-instant
Require ls
Require mktemp
Require tmux

Set Shell "bash"
Set FontSize 32
Set Width 1920
Set Height 1080

# Begin Setup
Hide

# Create a simple counting example envrc with tmux
Type@1ms 'cd `mktemp -d`' Enter Sleep 10ms
Type@1ms "echo $'for i in $(seq 20); do\n\techo $i\n\tsleep 1\ndone\n\nSUCCESS=1' >> .envrc" Enter Sleep 10ms

# Some files to look at
Type@1ms 'touch foo bar' Enter Sleep 10ms

# Open tmux
Type@1ms "tmux" Enter Sleep 5s

# If .bashrc has direnv-instant setup already, undo it
Type@1ms 'unset DIRENV_DIFF DIRENV_DIR DIRENV_FILE DIRENV_WATCHES' Enter Sleep 10ms
Type@1ms 'PROMPT_COMMAND=' Enter Sleep 10ms

# Unfancy the prompt
Type@1ms 'PS1="$ "' Enter Sleep 10ms

# Output cleanup
Type@1ms "direnv deny" Enter Sleep 100ms
Type@1ms "clear" Enter Sleep 100ms

# End Setup
Show

Type "cat .envrc" Enter Sleep 10s

Type 'eval "$(direnv-instant hook bash)"' Sleep 500ms Enter Sleep 1s
Type 'direnv allow' Sleep 500ms Enter Sleep 1s

Type '# I can still work in this shell session' Enter
Type 'ls' Enter Sleep 1s
Type '# after a set delay, a window is opened with direnv counting its heart out' Enter Sleep 20s

Enter

Type "echo $SUCCESS" Enter Sleep 2s
Type "# et voila, we're in the direnv!" Enter

Sleep 5s

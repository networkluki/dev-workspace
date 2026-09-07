# fish completion for the "choice" command
#
# Install (choose one):
#   1. Per user (recommended):
#        cp completions/choice.fish ~/.config/fish/completions/choice.fish
#   2. System-wide:
#        sudo cp completions/choice.fish /usr/share/fish/vendor_completions.d/choice.fish
#
# If the executable is named differently (e.g. choice.py), copy the file to a
# matching name (choice.py.fish) or duplicate the `complete -c choice` lines
# with `-c choice.py`.

# Emit the individual characters of the -c/--choices value on the command line,
# defaulting to the Windows-style "YN" set, as candidates for -d/--default.
function __choice_default_chars
    set -l tokens (commandline -opc)
    set -l choices YN
    set -l n (count $tokens)
    for i in (seq 1 $n)
        switch $tokens[$i]
            case -c --choices
                set -l j (math $i + 1)
                if test $j -le $n
                    set choices $tokens[$j]
                end
            case '--choices=*'
                set choices (string replace -- '--choices=' '' $tokens[$i])
        end
    end
    string split '' -- $choices
end

# Disable default file completion for this command.
complete -c choice -f

complete -c choice -s c -l choices       -r -d 'Characters allowed as choices (default YN)'
complete -c choice -s n -l no-prompt        -d 'Hide the list of choices'
complete -c choice -s s -l case-sensitive   -d 'Case-sensitive matching'
complete -c choice -s t -l timeout       -r -d 'Seconds before the default is chosen (0-9999)'
complete -c choice -s d -l default        -r -d 'Default choice used when the timeout expires' -a '(__choice_default_chars)'
complete -c choice -s m -l message       -r -d 'Message shown before the prompt'
complete -c choice -s h -l help             -d 'Show help and exit'
complete -c choice -s V -l version          -d 'Show version and exit'

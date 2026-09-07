# bash completion for the "choice" command
#
# Install (choose one):
#   1. System-wide (preferred, requires the bash-completion package):
#        sudo cp completions/choice.bash \
#             /usr/share/bash-completion/completions/choice
#   2. Per user:
#        cp completions/choice.bash ~/.local/share/bash-completion/completions/choice
#   3. Ad hoc for the current shell:
#        source completions/choice.bash
#
# The command name completed here is "choice"; if you install the script under a
# different executable name, register it too, e.g.:
#   complete -F _choice choice.py

_choice()
{
    local cur prev words cword
    # Prefer the bash-completion helper when available (handles quoting and
    # word splitting robustly); fall back to a minimal manual setup otherwise.
    if declare -F _init_completion >/dev/null 2>&1; then
        _init_completion || return
    else
        cur=${COMP_WORDS[COMP_CWORD]}
        prev=${COMP_WORDS[COMP_CWORD-1]}
        words=("${COMP_WORDS[@]}")
        cword=$COMP_CWORD
    fi

    local options="-c --choices -n --no-prompt -s --case-sensitive \
-t --timeout -d --default -m --message -h --help -V --version"

    # Complete the argument for options that take a value.
    case "$prev" in
        -d|--default)
            # Suggest the individual characters from the -c/--choices value on
            # the command line, defaulting to the Windows-style "YN" set.
            local choices="YN" i
            for ((i = 1; i < cword; i++)); do
                case "${words[i]}" in
                    -c|--choices)
                        choices=${words[i+1]}
                        ;;
                    --choices=*)
                        choices=${words[i]#--choices=}
                        ;;
                esac
            done
            local chars=() c
            for ((i = 0; i < ${#choices}; i++)); do
                c=${choices:i:1}
                chars+=("$c")
            done
            COMPREPLY=($(compgen -W "${chars[*]}" -- "$cur"))
            return 0
            ;;
        -t|--timeout)
            # Numeric argument (0-9999); no fixed word list to offer.
            COMPREPLY=()
            return 0
            ;;
        -c|--choices|-m|--message)
            # Free-form text; nothing sensible to complete.
            COMPREPLY=()
            return 0
            ;;
    esac

    # Otherwise, complete option names.
    if [[ "$cur" == -* || -z "$cur" ]]; then
        COMPREPLY=($(compgen -W "$options" -- "$cur"))
        return 0
    fi

    COMPREPLY=()
    return 0
}

complete -F _choice choice

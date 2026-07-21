set -x PATH $HOME/.local/bin $PATH
set -x PATH /app/.venv/bin $PATH
set -x PATH $HOME/local/packages/*/bin $PATH
set -x EDITOR vim
set -x VISUAL vim
set -x SHELL /usr/bin/fish
set -g fish_greeting

type -q fzf_key_bindings; and fzf_key_bindings
which helm >/dev/null 2>/dev/null ;and helm completion fish | source

if test -f ~/.env
    while read -l line
        set key_value (string split -m 1 "=" -- $line)
        set key $key_value[1]
        set value $key_value[2]
        set -x $key $value
    end < ~/.env
end

alias g git
alias k kubectl

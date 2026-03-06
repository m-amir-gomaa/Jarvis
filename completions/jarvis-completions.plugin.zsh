# jarvis-completions.plugin.zsh
# Plugin loader for Jarvis Zsh completions.
#
# This file is sourced AFTER oh-my-zsh (which already ran compinit).
# We therefore cannot rely on the #compdef magic tag being picked up.
# Instead we explicitly autoload and register the completion function.

# Ensure _jarvis is on the fpath (belt-and-suspenders)
fpath=("${0:A:h}" $fpath)

# Explicitly autoload the completion function
autoload -U _jarvis

# Register it with the completion system post-compinit
compdef _jarvis jarvis

# jarvis-completions.plugin.zsh
# This file is the plugin loader for Zsh autocompletion.
# It adds the directory containing _jarvis to fpath so compinit can find it.

# The _jarvis file is in the same directory as this plugin loader.
fpath=("${0:A:h}" $fpath)

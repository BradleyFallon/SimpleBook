# SimpleBook aliases
alias regtest="${SIMPLEBOOK_ROOT}/scripts/regtest.py"
alias simplebook="${SIMPLEBOOK_ROOT}/scripts/simplebook.py"
alias gen-docs="${SIMPLEBOOK_ROOT}/scripts/gen-docs.py"
alias sample-paragraphs="${SIMPLEBOOK_ROOT}/scripts/sample-paragraphs.py"
alias debug-epub="${SIMPLEBOOK_ROOT}/scripts/debug-epub.py"
alias unpack-epub="${SIMPLEBOOK_ROOT}/scripts/unpack-epub.py"
alias unpack-all-epubs="${SIMPLEBOOK_ROOT}/scripts/unpack-all-epubs.py"
alias report-body-coverage="${SIMPLEBOOK_ROOT}/scripts/report-body-coverage.py"
alias gen-normalization-docs="${SIMPLEBOOK_ROOT}/scripts/gen-normalization-docs.py"

# Optional short alias
alias reg=regtest
alias sb=simplebook
alias gendocs=gen-docs
alias spara=sample-paragraphs
alias uall=unpack-all-epubs
alias rbc=report-body-coverage
alias gnd=gen-normalization-docs

# --- autocomplete (bash/zsh) ---
_simplebook_keys() {
  if [ -z "${SIMPLEBOOK_ROOT-}" ]; then
    return 0
  fi
  "${SIMPLEBOOK_ROOT}/scripts/regtest.py" --list 2>/dev/null
}

_simplebook_epub_paths() {
  if [ -z "${SIMPLEBOOK_ROOT-}" ]; then
    return 0
  fi
  local epub_dir
  epub_dir="${SIMPLEBOOK_ROOT}/tests/epubs"
  if [ ! -d "${epub_dir}" ]; then
    return 0
  fi
  for path in "${epub_dir}"/*.epub; do
    if [ -f "${path}" ]; then
      echo "tests/epubs/$(basename "${path}")"
    fi
  done
}

# Bash completions
_regtest_complete() {
  local cur
  cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=( $(compgen -W "$(_simplebook_keys)" -- "$cur") )
}

_debug_epub_complete() {
  local cur
  cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=( $(compgen -W "$(_simplebook_keys)" -- "$cur") )
}

_unpack_epub_complete() {
  local cur
  cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=( $(compgen -W "$(_simplebook_keys)" -- "$cur") )
}

_simplebook_complete() {
  local cur
  cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=( $(compgen -W "$(_simplebook_epub_paths)" -- "$cur") )
}

if [ -n "${BASH_VERSION-}" ]; then
  complete -F _regtest_complete regtest
  complete -F _simplebook_complete simplebook
  complete -F _simplebook_complete gen-docs
  complete -F _simplebook_complete sample-paragraphs
  complete -F _debug_epub_complete debug-epub
  complete -F _unpack_epub_complete unpack-epub
  complete -F _simplebook_complete unpack-all-epubs
  complete -F _simplebook_complete report-body-coverage
  complete -F _simplebook_complete gen-normalization-docs
  complete -F _regtest_complete reg
  complete -F _simplebook_complete sb
  complete -F _simplebook_complete gendocs
  complete -F _simplebook_complete spara
  complete -F _simplebook_complete uall
  complete -F _simplebook_complete rbc
  complete -F _simplebook_complete gnd
elif [ -n "${ZSH_VERSION-}" ]; then
  setopt completealiases 2>/dev/null || true
  autoload -Uz compinit && compinit
  _simplebook_compadd() {
    local -a keys
    keys=( ${(f)"$(_simplebook_keys)"} )
    compadd -- $keys
  }
  _regtest_zsh() { _simplebook_compadd; }
  _debug_epub_zsh() { _simplebook_compadd; }
  _unpack_epub_zsh() { _simplebook_compadd; }
  _simplebook_zsh() {
    local -a epubs
    epubs=( ${(f)"$(_simplebook_epub_paths)"} )
    compadd -- $epubs
  }
  compdef _regtest_zsh regtest
  compdef _simplebook_zsh simplebook
  compdef _simplebook_zsh gen-docs
  compdef _simplebook_zsh sample-paragraphs
  compdef _debug_epub_zsh debug-epub
  compdef _unpack_epub_zsh unpack-epub
  compdef _simplebook_zsh unpack-all-epubs
  compdef _simplebook_zsh report-body-coverage
  compdef _simplebook_zsh gen-normalization-docs
  compdef _regtest_zsh reg
  compdef _simplebook_zsh sb
  compdef _simplebook_zsh gendocs
  compdef _simplebook_zsh spara
  compdef _simplebook_zsh uall
  compdef _simplebook_zsh rbc
  compdef _simplebook_zsh gnd
fi

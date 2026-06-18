#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

status=0
ran_any=0

note() { printf '%s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; status=1; }
skip() { printf 'SKIP: %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

tracked_files() {
  git ls-files -z ':!:frontend/tsconfig.tsbuildinfo' ':!:tools/encryptly/**' ':!:docs/images/**'
}

tracked_matching() {
  git ls-files -z "$@" \
    ':!:frontend/tsconfig.tsbuildinfo' \
    ':!:tools/encryptly/**' \
    ':!:docs/images/**'
}

run_formatter() {
  local name="$1"
  shift
  note "==> $name"
  ran_any=1
  if ! "$@"; then
    fail "$name reported formatting differences or errors"
  fi
}

check_editorconfig_basics() {
  note '==> editorconfig basics (LF, trailing whitespace, final newline)'
  ran_any=1
  local file output
  while IFS= read -r -d '' file; do
    if [[ ! -f "$file" ]]; then
      continue
    fi
    if file "$file" | grep -Eq 'charset=binary|executable'; then
      continue
    fi
    if LC_ALL=C grep -Iq . "$file"; then
      if LC_ALL=C grep -n $'\r' "$file" >/dev/null; then
        fail "$file contains CRLF line endings"
      fi
      output="$(LC_ALL=C grep -nE '[[:blank:]]$' "$file" || true)"
      if [[ -n "$output" && "$file" != *.md ]]; then
        fail "$file contains trailing whitespace"
        printf '%s\n' "$output" >&2
      fi
      if [[ -s "$file" ]]; then
        local last_byte
        last_byte="$(tail -c 1 "$file" | od -An -t x1 | tr -d ' \n')"
        if [[ "$last_byte" != "0a" ]]; then
          fail "$file is missing a final newline"
        fi
      fi
    fi
  done < <(tracked_files)
}

check_gofmt() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.go')
  ((${#files[@]})) || return 0
  if have gofmt; then
    note '==> gofmt'
    ran_any=1
    local output
    output="$(gofmt -l "${files[@]}")"
    if [[ -n "$output" ]]; then
      printf '%s\n' "$output" >&2
      fail 'gofmt found unformatted Go files'
    fi
  else
    skip 'gofmt not found; Go formatting not checked'
  fi
}

check_rustfmt() {
  compgen -G 'backend/*.toml' >/dev/null || return 0
  if have cargo && cargo fmt --version >/dev/null 2>&1; then
    run_formatter 'cargo fmt --check' bash -c 'cd backend && cargo fmt -- --check'
  elif have rustfmt; then
    local files=()
    while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.rs')
    ((${#files[@]})) || return 0
    run_formatter 'rustfmt --check' rustfmt --check "${files[@]}"
  else
    skip 'rustfmt/cargo-fmt not found; Rust formatting not checked'
  fi
}

check_prettier() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.ts' '*.tsx' '*.js' '*.jsx' '*.json' '*.css' '*.html' '*.md' '*.yaml' '*.yml')
  ((${#files[@]})) || return 0
  if [[ -x frontend/node_modules/.bin/prettier ]]; then
    run_formatter 'prettier --check' frontend/node_modules/.bin/prettier --check "${files[@]}"
  elif have prettier; then
    run_formatter 'prettier --check' prettier --check "${files[@]}"
  elif have npx; then
    run_formatter 'npx prettier --check' npx --yes prettier --check "${files[@]}"
  else
    skip 'prettier/npx not found; frontend, JSON, CSS, HTML, Markdown, and YAML formatting not checked'
  fi
}

check_clang_format() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.c' '*.h' '*.cpp' '*.hpp' '*.cc' '*.cxx' '*.hxx' '*.java')
  ((${#files[@]})) || return 0
  if have clang-format; then
    run_formatter 'clang-format --dry-run' clang-format --dry-run --Werror "${files[@]}"
  else
    skip 'clang-format not found; C/C++/Java formatting not checked'
  fi
}

check_python() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.py')
  ((${#files[@]})) || return 0
  if have black; then
    run_formatter 'black --check' black --check "${files[@]}"
  else
    skip 'black not found; Python formatting not checked'
  fi
}

check_shell() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.sh')
  ((${#files[@]})) || return 0
  if have shfmt; then
    run_formatter 'shfmt -d' shfmt -d "${files[@]}"
  else
    skip 'shfmt not found; shell formatting not checked'
  fi
}

check_lua() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.lua')
  ((${#files[@]})) || return 0
  if have stylua; then
    run_formatter 'stylua --check' stylua --check "${files[@]}"
  else
    skip 'stylua not found; Lua formatting not checked'
  fi
}

check_terraform() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.tf')
  ((${#files[@]})) || return 0
  if have terraform; then
    run_formatter 'terraform fmt -check' terraform fmt -check -recursive .
  else
    skip 'terraform not found; Terraform formatting not checked'
  fi
}

check_ruby() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.rb')
  ((${#files[@]})) || return 0
  if have rubocop; then
    run_formatter 'rubocop --format simple' rubocop --format simple "${files[@]}"
  else
    skip 'rubocop not found; Ruby formatting not checked'
  fi
}

check_perl() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.pl')
  ((${#files[@]})) || return 0
  if have perltidy; then
    note '==> perltidy check'
    ran_any=1
    local file tmp
    for file in "${files[@]}"; do
      tmp="$(mktemp)"
      if ! perltidy -st "$file" >"$tmp" || ! cmp -s "$file" "$tmp"; then
        fail "perltidy found unformatted Perl file: $file"
      fi
      rm -f "$tmp"
    done
  else
    skip 'perltidy not found; Perl formatting not checked'
  fi
}

check_haskell() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.hs')
  ((${#files[@]})) || return 0
  if have ormolu; then
    run_formatter 'ormolu --mode check' ormolu --mode check "${files[@]}"
  elif have fourmolu; then
    run_formatter 'fourmolu --mode check' fourmolu --mode check "${files[@]}"
  else
    skip 'ormolu/fourmolu not found; Haskell formatting not checked'
  fi
}

check_sql() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*.sql')
  ((${#files[@]})) || return 0
  if have sqlfluff; then
    run_formatter 'sqlfluff format --check' sqlfluff format --check "${files[@]}"
  else
    skip 'sqlfluff not found; SQL formatting not checked'
  fi
}

check_cmake() {
  local files=()
  while IFS= read -r -d '' file; do files+=("$file"); done < <(tracked_matching '*CMakeLists.txt' '*.cmake')
  ((${#files[@]})) || return 0
  if have cmake-format; then
    run_formatter 'cmake-format --check' cmake-format --check "${files[@]}"
  else
    skip 'cmake-format not found; CMake formatting not checked'
  fi
}

check_editorconfig_basics
check_gofmt
check_rustfmt
check_prettier
check_clang_format
check_python
check_shell
check_lua
check_terraform
check_ruby
check_perl
check_haskell
check_sql
check_cmake

if (( ran_any == 0 )); then
  fail 'no formatting checks were run'
fi

if (( status == 0 )); then
  note 'Formatting checks passed.'
else
  note 'Formatting checks failed.' >&2
fi

exit "$status"

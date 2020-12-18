# utility functions, meant to be sourced and used in cli

function build() {
    rm -r build 2>/dev/null  || true
    pip wheel .  -w build/ --no-deps "$@" || return 1
}

function rebuild() {
    start="$PWD"
    cd ..
    if ! build "$@"; then cd "$start" && return 1; fi
    cd build
}


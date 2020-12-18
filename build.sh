# utility functions, meant to be sourced and used in cli

function build() {
    rm -r build  || true
    pip wheel .  -w build/ --no-deps "$@"
}

function rebuild() {
    cd ..
    build "$@"
    cd build
}


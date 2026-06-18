# Contributing to Tent of Trials

Thank you for helping improve Tent of Trials. This guide explains the expected local setup, build workflow, code style, and pull request process for contributors.

## 1. Clone the repository

Fork the repository on GitHub, then clone your fork locally:

```bash
git clone https://github.com/<your-user>/zeroeye.git
cd zeroeye
```

Add the upstream repository so you can keep your branch current:

```bash
git remote add upstream https://github.com/cuentaprueba244w-dotcom/zeroeye.git
git fetch upstream
```

Before starting work, create a focused branch from the default branch:

```bash
git checkout main
git pull --ff-only upstream main
git checkout -b fix/short-description
```

## 2. Install dependencies

This repository contains several modules implemented in different languages. Install the dependencies for the module you plan to touch.

### Repository tooling

```bash
sudo apt update
sudo apt install -y python3
```

### Backend: Rust

```bash
sudo apt install -y build-essential pkg-config curl protobuf-compiler libssl-dev
curl https://sh.rustup.rs -sSf | sh -s -- -y
source "$HOME/.cargo/env"
cd backend
cargo fetch
cd ..
```

### Frontend: TypeScript / React

```bash
sudo apt install -y curl ca-certificates gnupg
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
cd frontend
npm install
cd ..
```

### Market: Go

The market module expects a recent Go toolchain. Check `market/go.mod` for the required Go version.

```bash
cd market
go mod download
cd ..
```

### C, C++, Java, Ruby, Lua, and Haskell modules

Install the language/toolchain for the module you are changing. The `README.md` contains module-specific package examples for:

- `frailbox` / C
- `engine` / C++
- `compliance` / Java
- `v2-market-stream` / Ruby
- `nfc-scanner` / Lua
- `openapi-haskell` / Haskell
- `openapi-tools` / Lua

## 3. Build and test

Use the root build script before submitting a pull request:

```bash
python3 build.py
```

Build a subset of modules when iterating locally:

```bash
python3 build.py -m backend
python3 build.py -m frontend,market
python3 build.py --clean
python3 build.py --release
```

Run module-level checks relevant to your change before the full build. Examples:

```bash
cd backend && cargo test
cd frontend && npm test
cd market && go test ./...
```

The build script writes diagnostic artifacts into `diagnostic/`. Bounty PRs require the generated `diagnostic/build-*.logd` artifact and matching JSON metadata when present. If the encrypted log is split into `diagnostic/build-*-part*.logd` chunks, include those chunks and note the reassembly command from the build output in your PR.

Do not paste diagnostic passwords, secrets, tokens, or environment credentials into public comments.

## 4. Code style

Use the repository `.editorconfig` for whitespace, line endings, and final newline expectations. Configure your editor to read `.editorconfig` automatically.

Keep changes focused:

- Avoid unrelated formatting churn.
- Do not mix refactors with feature or test fixes unless required.
- Prefer small, reviewable commits.
- Do not commit local secrets, `.env` files, private keys, or generated build artifacts except the required diagnostic build log for bounty submissions.

## 5. Pull request workflow

1. Fork the repository.
2. Create a topic branch from the latest `main`.
3. Make the smallest scoped change that satisfies the issue acceptance criteria.
4. Run relevant module tests and `python3 build.py`.
5. Commit the code changes and required diagnostic artifacts.
6. Push your branch to your fork.
7. Open a pull request against the repository `main` branch.

Use the repository pull request template: [.github/pull_request_template.md](.github/pull_request_template.md).

Your PR should include:

- a concise summary;
- a list of changed files or behaviors;
- exact commands you ran and their results;
- a reference to the issue, for example `Fixes #123`;
- notes about any local toolchain limitation that affects the full build;
- the generated diagnostic artifact names required by the issue.

## 6. Review expectations

Maintainers may ask for changes. Respond by pushing follow-up commits to the same branch unless a maintainer asks for a new PR.

If your PR is for a bounty, wait for maintainer confirmation before assuming acceptance or payment. An open PR is a submission, not a guaranteed payout.

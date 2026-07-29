# Contributing to QuakeGuard 🌋

First off, thank you for considering contributing to QuakeGuard! It's people like you that make open-source a great community.

This document outlines the processes and conventions we follow.

## 🏗️ Architecture Awareness
QuakeGuard is a distributed Microservices architecture. When contributing, please ensure your changes respect the boundaries of the three main layers:
1.  **IoT Edge (`firmware/`)**: ESP32-C3 C++ codebase. Focus on memory efficiency (no dynamic allocations in DSP loops) and correct I2C timings.
2.  **Backend (`backend/`)**: Python FastAPI + Redis + PostgreSQL. Async rules apply. Ensure database operations do not block the event loop.
3.  **Mobile (`mobile/`)**: React Native (Expo). Keep state localized unless it requires Zustand. 

## 🌿 Branching Strategy
We use a Trunk-Based Development workflow. All Pull Requests should be made directly against the `main` branch.

**Branch Naming Convention:**
*   `feature/your-feature-name` (e.g., `feature/llm-reports`)
*   `bugfix/issue-description` (e.g., `bugfix/redis-lock-timeout`)
*   `docs/documentation-update`

## 💬 Commit Messages & PR Titles
We strictly enforce **Semantic Versioning** and conventional commits. Our CI pipeline (`pr-lint.yml`) will block Pull Requests that do not follow this format in the PR title.

**Format:** `type(scope): subject`

**Types:**
*   `feat`: A new feature.
*   `fix`: A bug fix.
*   `docs`: Documentation only changes.
*   `refactor`: Code change that neither fixes a bug nor adds a feature.
*   `test`: Adding missing tests or correcting existing ones.
*   `chore`: Changes to the build process or auxiliary tools.

**Examples:**
*   `feat(mobile): add haptic feedback to offline mode toggle`
*   `fix(backend): resolve Redis connection pool exhaustion`
*   `docs(architecture): update Typst whitepaper for v1.1.0`

## ✅ Pull Request Process
1.  Fork the repo (or branch off `main` if you are a core collaborator).
2.  Ensure your code passes all existing tests. If adding a feature, add corresponding tests (especially for the backend `tests/stress_test.py`).
3.  Ensure your code passes the CI workflows (`backend-ci`, `frontend-ci`, `iot-ci`).
4.  Update the documentation (`docs/` or `README.md`) if necessary.
5.  Open a PR targeting the `main` branch using our provided template.

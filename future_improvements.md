# Future Improvements Roadmap

This document outlines a comprehensive list of potential improvements for the Wicked Zerg Challenger project, categorized by impact and type.

## 1. Reliability & Robustness (High Priority)
*   **Standardize Error Handling**: Continue Phase 3 work.
    *   [ ] **Combat Manager**: Replace `print` debugs and silent `except: pass` blocks with `logger`.
    *   [ ] **Rogue Tactics Manager**: Unmask hidden errors in drop logic.
    *   [ ] **Intel Manager**: Ensure threat detection failures are logged.
*   **Async/Sync consistency**: Review `bot.do()` usages. Some are awaited, some are not. Standardize on `self.bot.do_actions()` or ensure consistent `await` usage where applicable.

## 2. Architecture & Maintainability
*   **Configuration Management**:
    *   [ ] **Extract Constants**: Move magic numbers (upgrade weights, unit ratios, timings) from code to a dedicated `config.py` or `constants.py`.
    *   [ ] **Dynamic Config**: Allow loading strategy parameters from a JSON/YAML file for easier tweaking without code changes.
*   **Type Hinting**:
    *   [ ] **Strict Typing**: Add `mypy` strict mode support. Many method signatures lack full type annotations.
*   **Event-Driven Communication**:
    *   [ ] **Decoupling**: Currently `BotStepIntegrator` manually calls every manager. Consider an Event Bus pattern (e.g., `on_enemy_detected`, `on_unit_created`) to decouple managers.

## 3. Testing & Quality Assurance
*   **Unit Tests**:
    *   [ ] **Test Suite**: Create a `tests/` directory with `pytest`.
    *   [ ] **Mock Bot**: Improve `fake_bot` to allow testing managers in isolation without launching SC2.
*   **CI/CD Hooks**:
    *   [ ] **Pre-commit hooks**: Setup `black` (formatter) and `ruff` (linter) to enforce style automatically.

## 4. Feature Enhancements
*   **Advanced Combat**:
    *   [ ] **Unit Micro**: Add specialized micro for Vipers (Abduct/Consume) and Infestors (Fungal Growth).
    *   [ ] **Flanking**: Implement logic to attack from multiple angles simultaneously.
*   **Machine Learning Integration**:
    *   [ ] **Training Pipeline**: Fully integrate `local_training` modules. Currently they exist but integration paths are unclear.
    *   [ ] **Model Serving**: Create a clean interface to load trained RL models for strategy selection.

## 5. Performance
*   **Profiling**:
    *   [ ] **Performance Monitor**: Add a decorator to measure execution time of each manager's `on_step`. Log warnings if any manager takes >10ms.
*   **Optimization**:
    *   [ ] **Caching**: Use `functools.lru_cache` for expensive geometry calculations (e.g., expansion distances).

## 6. Documentation
*   **Wiki/Guide**: Create a `DEVELOPER.md` guide explaining the manager architecture for new contributors.
*   **Docstrings**: Ensure all public methods have Google-style docstrings.

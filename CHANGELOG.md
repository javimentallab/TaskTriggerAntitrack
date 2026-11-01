# Changelog

## 1.0.0 — 2026-11-01

First numbered version. Until now the project had no version number or tags.

### Added
- **Tasks that combine when and what**: fixed time or random time within a range (anti-tracking),
  with *Repeat every day*; typing into terminals or running a program / opening a file or URL.
- **Typing into terminals**: filter by window title or process name, keys before the text, number of
  Enters, and which windows to act on (all / only the first / only the focused one).
- **Running a program**: arguments, working folder and window mode (normal / minimised / hidden /
  elevated with UAC).
- **Sound and pop-up** when a task fires, each one optional.
- **Clock-style time picker**, large controls and a DPI-aware window.
- **Interface in 15 languages**, with `--lang xx` or the `TTA_LANG` environment variable to pick one.
- **Reliability**: single instance, `--min` to start minimised, atomic saving, invalid tasks disabled
  instead of stopping the app, unreadable `alarms.json` kept aside instead of being overwritten, and
  failures logged to `error.log`.
- **Trivy** security scan in CI.
- README in English and Spanish, with a screenshot on the front page.

# Contributing to bw-flasher

Thank you for your interest in contributing! This project exists to help device owners understand and repair their hardware through transparent documentation of firmware protocols.

## Before Contributing

**Please read and agree to:**
- [PRINCIPLES.md](PRINCIPLES.md) - Our core values
- [LEGAL_DISCLAIMER.md](LEGAL_DISCLAIMER.md) - Legal responsibilities
- This project's [CC-BY-NC-SA-4.0 License](LICENSE)

## Our Values

All contributions must align with our principles:
- ✅ Educational and research focus
- ✅ Prioritizing user safety
- ✅ Respecting the law
- ❌ No commercial exploitation
- ❌ No bypassing safety features for profit
- ❌ No encouraging illegal use

## How to Contribute

### Reporting Issues

**Security Vulnerabilities:**
If you discover a security vulnerability in manufacturer firmware:
1. DO NOT open a public issue
2. Contact the manufacturer directly for responsible disclosure
3. Wait for a reasonable time before public discussion

**Bugs and Feature Requests:**
Open a GitHub issue with:
- Clear description of the problem
- Steps to reproduce (if applicable)
- Expected vs. actual behavior
- Your environment (OS, Python version, hardware)

### Code Contributions

**We welcome:**
- Bug fixes
- Documentation improvements
- New protocol support (with proper authentication/security)
- Test coverage improvements
- GUI/UX enhancements
- Error handling improvements
- Cross-platform compatibility fixes

**We do NOT accept:**
- Code that explicitly bypasses safety features
- Removal of safety warnings or disclaimers
- Features designed primarily for commercial exploitation
- Code that violates manufacturer security without disclosure

### Pull Request Process

1. **Fork the repository** and create a feature branch
2. **Follow existing code style** (PEP 8 for Python)
3. **Add tests** for new functionality
4. **Update documentation** (README, CLAUDE.md if architecture changes)
5. **Run the test suite:** `poetry run pytest tests/ -v`
6. **Include disclaimer headers** in new files (see below)
7. **Sign your commits** to acknowledge the license
8. **Submit PR** with clear description of changes

### Commit Messages

Use clear, descriptive commit messages:
```
Good: "fix(leqi): Handle timeout on end command retry"
Good: "docs: Add troubleshooting section for macOS serial ports"
Bad: "fixed stuff"
Bad: "update"
```

### Code Style

- Follow PEP 8 Python style guide
- Use type hints where beneficial
- Keep functions focused and testable
- Add docstrings for complex functions
- Use meaningful variable names

### File Headers

All new Python files must include the license header:

```python
#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Flasher
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
```

## Adding New Protocol Support

If you've reverse engineered a new protocol:

1. **Verify it's not already documented** elsewhere
2. **Create a new flasher class** inheriting from `BaseFlasher`
3. **Implement all abstract methods:** `load_file()`, `run()`, `test_connection()`, `detect_firmware_type()`
4. **Add comprehensive tests** in `tests/`
5. **Document the protocol** in CLAUDE.md architecture section
6. **Include safety considerations** if protocol lacks authentication

## Testing

Before submitting:
```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific test file
poetry run pytest tests/test_firmware_detection.py -v

# Test in simulation mode
poetry run python -m bwflasher --simulation test_firmware.bin
```

## Documentation

Update documentation when changing:
- **README.md** - User-facing features, installation, usage
- **CLAUDE.md** - Architecture, development workflow, implementation details
- **Docstrings** - Complex functions and classes

## Community Guidelines

### Be Respectful
- Treat all contributors with respect
- Provide constructive feedback
- Assume good intentions
- Welcome newcomers

### Stay On Topic
- Keep discussions focused on the project
- Use GitHub Issues for bug reports
- Use Discussions for general questions
- Don't spam or advertise

### No Illegal Activity
- Don't share stolen firmware
- Don't discuss bypassing laws
- Don't encourage dangerous modifications
- Don't facilitate commercial exploitation

## What Happens to Your Contribution

By contributing, you agree that:
- Your contribution will be licensed under CC-BY-NC-SA-4.0
- Your contribution may be modified by maintainers
- You have the right to contribute (no employer restrictions)
- You're not contributing proprietary/confidential information

## Questions?

- Open a GitHub Discussion for general questions
- Check existing Issues and Pull Requests first
- Read the [CLAUDE.md](CLAUDE.md) for architecture details

## Recognition

Contributors will be acknowledged in:
- Git commit history
- Release notes (for significant contributions)
- Project appreciation in community discussions

Thank you for helping make firmware more transparent and accessible! 🔓

## Contributing

Contributions are welcome! SkillMeat is built with Python, FastAPI, Next.js, and React.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/skillmeat.git
cd skillmeat

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest -v --cov=skillmeat

# Start development servers
skillmeat web dev
```

### Code Quality

```bash
# Format code (required)
black skillmeat

# Type checking
mypy skillmeat --ignore-missing-imports

# Lint
flake8 skillmeat --select=E9,F63,F7,F82
```

### Contribution Guidelines

- Follow existing code patterns and conventions
- Add tests for new features
- Update documentation for user-facing changes
- Run code quality checks before submitting
- Write clear commit messages

For detailed guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

### Reporting Issues

Found a bug or have a feature request? Open an issue on [GitHub Issues](https://github.com/yourusername/skillmeat/issues).

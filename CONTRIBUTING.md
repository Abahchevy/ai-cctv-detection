# Contributing to Inspection AI

Thank you for your interest in contributing to Inspection AI! We welcome contributions from the community to help improve this PPE compliance monitoring system.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/inspection-ai.git
   cd inspection-ai
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   # or source .venv/bin/activate  # On Linux/Mac
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Development Workflow

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
   Use descriptive branch names:
   - `feature/` for new features
   - `fix/` for bug fixes
   - `docs/` for documentation
   - `refactor/` for code improvements

2. **Make your changes** and test them locally

3. **Commit with clear messages**:
   ```bash
   git commit -m "feat: add object detection optimization"
   ```
   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` for features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `refactor:` for code refactoring
   - `test:` for tests
   - `chore:` for dependencies/config

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request** on GitHub with:
   - Clear title and description
   - Reference any related issues (e.g., "Closes #123")
   - List of changes made

## Testing

Before submitting a PR, ensure your changes don't break existing functionality:
```bash
python test_detection.py
python test_webcam.py
```

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and concise

## Areas for Contribution

- **Detection improvements**: Better PPE classification models
- **Performance optimization**: Faster inference or streaming
- **New features**: Additional monitoring capabilities
- **Documentation**: Guides, examples, troubleshooting
- **Testing**: Unit tests, integration tests
- **UI/Dashboard**: Frontend for monitoring and alerts
- **Database**: Schema improvements, query optimization

## Reporting Issues

Found a bug? Please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs. actual behavior
- System information (OS, Python version, GPU if applicable)

## Questions?

Feel free to open a discussion or issue if you have questions about the project or need guidance.

Thank you for contributing! 🎉

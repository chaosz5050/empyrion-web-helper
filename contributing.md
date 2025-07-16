# FILE LOCATION: /CONTRIBUTING.md (root directory)

# Contributing to Empyrion Web Helper

Thank you for your interest in contributing to Empyrion Web Helper! This document provides guidelines and information for contributors.

## 🎯 Project Goals

Empyrion Web Helper aims to provide a professional, modular, and user-friendly web-based administration tool for Empyrion Galactic Survival dedicated servers. We focus on:

- **Linux-first development** (primarily tested on CachyOS/Arch Linux)
- **Modular architecture** for maintainability
- **Professional UI/UX** with dark theme
- **Real-time functionality** with WebSocket integration
- **Security** with encrypted credential storage

## 🏗️ Development Setup

### Prerequisites
- **Linux** (CachyOS, Ubuntu, Arch, etc.)
- **Python 3.8+** (preferably 3.11+)
- **Git**

### Setup Steps
1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/empyrion-web-helper.git
   cd empyrion-web-helper
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If it exists
   ```

4. **Set up configuration**
   ```bash
   cp config_template.txt empyrion_helper.conf
   # Edit empyrion_helper.conf with your test server details
   ```

5. **Run the application**
   ```bash
   python3 app.py
   ```

## 📋 Code Guidelines

### Architecture Principles
- **Modular Design**: Each feature should be self-contained in its own module
- **Single Responsibility**: Each module should have a clear, focused purpose
- **Configuration-Driven**: Behavior controlled through config files, not hardcoded values
- **Professional Logging**: Use the logging manager for all log output

### File Size Limits
- **Python Modules**: 200-400 lines (ideal), 600 lines (max), 800 lines (hard limit)
- **JavaScript Files**: 150-300 lines (ideal), 500 lines (max), 600 lines (hard limit)
- **HTML Templates**: 300-500 lines (ideal), 800 lines (max)

*When approaching limits, consider splitting into smaller, focused modules.*

### Coding Standards

#### Python
- Follow **PEP 8** style guidelines
- Use **type hints** where appropriate
- Include **comprehensive docstrings** for modules, classes, and functions
- Use the **logging manager** instead of print statements
- Handle exceptions gracefully with informative error messages

#### JavaScript
- Use **modern ES6+** syntax
- Follow **camelCase** naming convention
- Include **JSDoc comments** for functions
- Use **async/await** for API calls
- Maintain the modular manager pattern (e.g., `window.PlayersManager`)

#### HTML/CSS
- Use **semantic HTML5** elements
- Follow the established **dark theme** styling
- Ensure **responsive design** for mobile compatibility
- Use **CSS custom properties** (variables) for consistency

### File Headers
All files should include a location comment at the top:

```python
# FILE LOCATION: /path/to/file.py (root directory)
```

```javascript
// FILE LOCATION: /static/js/file.js
```

```html
<!-- FILE LOCATION: /templates/file.html -->
```

## 🔧 Development Workflow

### Branch Strategy
- **main**: Stable releases
- **develop**: Development integration branch
- **feature/feature-name**: New features
- **bugfix/issue-description**: Bug fixes
- **hotfix/critical-fix**: Critical production fixes

### Commit Messages
Use clear, descriptive commit messages:
```
feat: add entity search and filtering functionality
fix: resolve player status detection edge case
docs: update installation instructions for CachyOS
style: improve dark theme consistency across modals
refactor: split large messaging module into smaller components
```

### Pull Request Process
1. **Create a feature branch** from `develop`
2. **Make your changes** following the coding guidelines
3. **Test thoroughly** on Linux (preferably CachyOS/Arch)
4. **Update documentation** if needed
5. **Submit a pull request** to `develop` branch

### Testing
- **Manual testing** on a real Empyrion server (preferred)
- **Cross-browser testing** (Chrome, Firefox, Safari)
- **Mobile responsiveness** testing
- **Error handling** validation

## 🐛 Bug Reports

When reporting bugs, please include:

- **Environment details** (Linux distro, Python version, browser)
- **Empyrion server version** and configuration
- **Steps to reproduce** the issue
- **Expected vs. actual behavior**
- **Log files** (sanitized of sensitive information)
- **Screenshots** if relevant

## 💡 Feature Requests

For new features, please:

- **Check existing issues** to avoid duplicates
- **Describe the use case** clearly
- **Explain the benefits** for server administrators
- **Consider the scope** (should fit within the project's goals)
- **Suggest implementation approaches** if you have ideas

## 🎨 UI/UX Guidelines

### Design Principles
- **Dark theme first** - professional, easy on the eyes
- **Information density** - display relevant data efficiently
- **Progressive disclosure** - advanced features behind clear navigation
- **Responsive design** - works on desktop and mobile
- **Real-time updates** - live data without page refreshes

### Color Scheme
```css
--bg-primary: #1a1a1a
--bg-secondary: #2d2d2d
--bg-tertiary: #3d3d3d
--text-primary: #ffffff
--text-secondary: #cccccc
--accent-blue: #0066cc
--accent-green: #00cc66
--accent-red: #cc0000
--accent-orange: #ff9900
```

## 📚 Adding New Features

### Creating a New Module
1. **Plan the module structure** (keep under 600 lines)
2. **Create the Python module** with proper logging
3. **Add corresponding JavaScript manager** if needed
4. **Create HTML templates** following the established pattern
5. **Update navigation** and routing as needed
6. **Add appropriate CSS** styling
7. **Update documentation**

### Module Template
```python
# FILE LOCATION: /new_module.py (root directory)
#!/usr/bin/env python3
"""
New Module for Empyrion Web Helper
Brief description of module functionality
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class NewModuleManager:
    """Handles new module functionality"""
    
    def __init__(self, config_file: str = "empyrion_helper.conf"):
        self.config_file = config_file
        logger.info("NewModuleManager initialized")
    
    def example_method(self) -> bool:
        """Example method with proper typing and documentation"""
        try:
            # Implementation here
            logger.info("Example method executed successfully")
            return True
        except Exception as e:
            logger.error(f"Error in example method: {e}")
            return False
```

## 🔒 Security Considerations

- **Never commit** sensitive data (passwords, IPs, etc.)
- **Use the database** for credential storage (with encryption)
- **Validate all inputs** from web interface
- **Sanitize outputs** to prevent XSS
- **Use parameterized queries** for database operations
- **Keep dependencies updated** for security patches

## 📝 Documentation

### README Updates
- Keep installation instructions current
- Update feature lists when adding functionality
- Include screenshots for major UI changes
- Maintain the version number and changelog

### Code Documentation
- **Module docstrings** explaining purpose and usage
- **Function docstrings** with parameters and return values
- **Inline comments** for complex logic
- **Configuration examples** for new settings

## 🏷️ Versioning

We use semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes and small improvements

## 📄 License

This project is licensed under **CC BY-NC-SA 4.0**. By contributing, you agree that your contributions will be licensed under the same terms.

## 🤝 Community Guidelines

- **Be respectful** and professional in all interactions
- **Help newcomers** get started with the project
- **Share knowledge** and document solutions
- **Test thoroughly** before submitting changes
- **Collaborate openly** on design decisions

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and community chat
- **Wiki**: For detailed documentation (if available)

## 🙏 Recognition

Contributors are recognized in:
- **CHANGELOG.md** for their contributions
- **README.md** acknowledgments section
- **Git commit history** as the permanent record

---

**Thank you for contributing to Empyrion Web Helper!**

*Building better server management tools for the Empyrion community* 🚀

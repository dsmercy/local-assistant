Run the full test suite with coverage report.

```bash
pytest -x --cov=src --cov-report=term-missing && ruff check . && mypy src/
```

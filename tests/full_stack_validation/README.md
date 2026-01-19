# Full Stack Validation

Focused integration tests for the backend and AI services. These hit real endpoints and real databases.

## Run
```bash
cd tests/full_stack_validation
python run_tests.py
```

## Notes
- Configure with `.env.test` if needed.
- Use pytest markers like `-m security` or `-m performance` to narrow scope.

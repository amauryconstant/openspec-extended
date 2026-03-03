# Install Test Fixtures

This directory contains test fixtures for `install.sh` and `openspecx` tests.

## Contents

Currently, the install tests use the actual project resources rather than fixtures.
The helper functions in `tests/helpers/test-helpers.bash` provide utilities for:

- `setup_installed_openspecx()` - Creates a fake installed location
- `create_test_tarball()` - Creates a minimal tarball for testing

## Regenerating Fixtures

If you need to create fixture tarballs for offline testing:

```bash
# Create minimal test tarball
./tests/helpers/create-fixture-tarball.sh
```

## Note

The integration tests (`tests/integration/install-flow.bats`) test against the
actual resources in `resources/` directory. This ensures tests reflect real
behavior rather than potentially stale fixtures.

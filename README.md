# validate_dbc
Github Action for validating .dbc files using cantools


A GitHub Action that lints CAN `.dbc` files for **syntax and structural
defects** using [cantools](https://github.com/cantools/cantools). Inspired by DBC Utility's [DBC validation release checklist](https://dbcutility.com/blog/dbc-validation-release-checklist/), it runs the checks that can be done without a live CAN bus. This should at the very least provide a lint.

Findings are emitted as GitHub Actions annotations, so they show up inline on
the pull request. Errors fail the job, and warnings are reported but do not result in failure.

## What it checks

| Check | Severity |
|---|---|
| File does not parse in cantools (syntax / format error) | **error** |
| Signal overlap, out-of-bounds signal, or multiplexer error | **error** |
| Classical CAN message with payload length above 8 bytes | **error** |
| Duplicate signal name within a single message | **error** |
| Duplicate frame ids across messages (may be variant-specific) | warning |
| Standard id above 11 bits not marked extended | warning |
| CAN FD message with a non-standard payload length | warning |
| Physical min/max that cannot fit the signal's bit width and scale | warning |

**Out of scope** (needs a real bus, captured logs, or human review, so it is
deliberately *not* checked): log replay, physical-value plausibility, unit
correctness, enum-vs-firmware agreement, and release-note review.

## Usage

```yaml
name: DBC Lint
on:
  pull_request:
    paths: ['**.dbc']
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: polymathrobotics/validate_dbc@v0.1
        # No inputs needed: validates every .dbc in the repo by default.
```

Validate only a single directory:

```yaml
      - uses: polymathrobotics/validate_dbc@v0.1
        with:
          path: dbc_dir
```

Validate an explicit set of files:

```yaml
      - uses: polymathrobotics/validate_dbc@v0.1
        with:
          files: |
            path/to/example.dbc
```

## Inputs

| Input | Default | Description |
|---|---|---|
| `path` | `.` | Directory searched recursively for `.dbc` files when `files` is empty. |
| `files` | `''` | Explicit space/newline-separated list of `.dbc` files. Overrides `path`. |
| `python-version` | `3.10` | Python version used to run the validator. |
| `cantools-version` | `>=40,<41` | Version specifier appended to `cantools` for `pip install`. |

## Versioning

Pin to a version tag (`@v0.1`) to receive compatible updates, or to a full
commit SHA for maximum reproducibility.

## License

Apache-2.0 — see [LICENSE](LICENSE).

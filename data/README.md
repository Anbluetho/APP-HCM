# Data sources and configuration

This package stores versioned data and provides the generic loader:

- `hcm_tables/registry.json`: table metadata, file paths, source provenance, and
  separate availability and verification statuses.
- `hcm_tables/imported/`: 11 CSVs preserved byte-for-byte as received from the supplied ZIP.
- `hcm_tables/reviewed/`: canonical reviewed copies where the manual revealed a transcription label to normalize or an explicit condition to include.
- `hcm_tables/README.md`: provenance and unresolved discrepancies.
- `configuration/`: methodology and jurisdiction configuration.
- `data_loader.py`: CSV/JSON loading, record search, parameter lookup, and
  structural validation.
- `data_dictionary.md`: definitions of current interface inputs and imported
  table columns.

The supplied `HCM_K20.pdf` chapter was used as the primary source to review the ten tabular/reference datasets. The formula CSV remains `reference_only` and is not an executable calculation engine. The academic presentation and the original ZIP are secondary provenance. No Ecuador parameters have been incorporated.

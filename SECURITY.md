# Security policy
This is an educational portfolio project, not a hosted production service.

Do not open a public issue containing credentials or private data. For a suspected
vulnerability, use GitHub's private vulnerability reporting if enabled; otherwise
contact the repository owner through their public GitHub profile without posting
exploit details or secrets. No dedicated response-time commitment is offered.

Only public TLC files are downloaded by the built-in HTTP path. The --input option
accepts trusted local Parquet files. Treat input and SQL changes as code-review
boundaries. The lock is local, not a distributed authorization mechanism.
Dependencies are locked for reproducibility, not guaranteed vulnerability-free.

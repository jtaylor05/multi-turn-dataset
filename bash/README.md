# Helper Scripts

These scripts are convenience wrappers around Docker and analysis commands. The supported container launchers are `start-initial-generation`, `start-experimentation`, and `start-evaluation`; each mounts a host data directory at `/app/data`.

```sh
bash/start-initial-generation [host-data-directory]
bash/start-experimentation [host-data-directory]
bash/start-evaluation [host-data-directory]
```

The default host data directory is `./data`. If the corresponding `.env` file exists, the launcher passes it into the container. The interactive container is removed when its shell exits, while files under `/app/data` remain on the host.

`run-evaluations` analyzes scored JSONL files into `analysis_output/`.
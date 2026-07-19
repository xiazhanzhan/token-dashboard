# Third-party notices

Token Dashboard is distributed under the MIT License. It also uses and, in
release archives, may redistribute third-party software under its own terms.
The following list covers the primary direct and redistributed components used
by the initial public release. The lockfiles remain the authoritative inventory
for exact dependency versions.

| Component | License | Role |
| --- | --- | --- |
| Apache ECharts | Apache-2.0 | Dashboard charts |
| echarts-for-react | MIT | React integration for ECharts |
| React / React DOM | MIT | Frontend UI |
| Lucide | ISC | Interface icons |
| Vite | MIT | Frontend build tool |
| TypeScript | Apache-2.0 | Frontend language and compiler |
| FastAPI | MIT | HTTP API |
| Uvicorn | BSD-3-Clause | Local ASGI server |
| Pydantic | MIT | Data validation |
| certifi | MPL-2.0 | CA certificate bundle used by the Windows Agent |
| Python | PSF License | Embedded Windows Agent runtime |

Dependency versions and additional transitive components are recorded in
`frontend/package-lock.json` and the Python requirements files. A release
builder must preserve all notices included by redistributed runtimes and
libraries.

## Apache ECharts NOTICE

Apache ECharts
Copyright 2017-2026 The Apache Software Foundation

This product includes software developed at the Apache Software Foundation
(https://www.apache.org/).

Project links:

- Apache ECharts: https://echarts.apache.org/
- React: https://react.dev/
- FastAPI: https://fastapi.tiangolo.com/
- Uvicorn: https://www.uvicorn.org/
- Pydantic: https://docs.pydantic.dev/
- Python: https://www.python.org/

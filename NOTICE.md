Copyright (2026) Databricks, Inc.

This Software includes software developed at Databricks (https://www.databricks.com/) and its use is subject to the included LICENSE file.
By using this repository and the notebooks within, you consent to Databricks collection and use of usage and tracking information in accordance with our privacy policy at www.databricks/privacypolicy.

## Third-Party Software

This project depends on the open-source libraries listed in the **Open-source dependencies**
section of the [README](README.md), which records each library's license and source.

All third-party dependencies are permissively licensed (MIT, BSD-3-Clause, Apache-2.0, ISC)
with one exception:

- **psycopg** — PostgreSQL driver — **GNU Lesser General Public License v3.0 (LGPL-3.0)** —
  https://github.com/psycopg/psycopg

psycopg is used **unmodified** and is **dynamically linked** at runtime (imported via
SQLAlchemy); it is neither modified nor statically linked into this project's proprietary
code, and recipients are free to replace it with their own version of the library.

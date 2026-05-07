"""
Parameterized generator for GH510_gorm_7726.

Source PR:    https://github.com/go-gorm/gorm/pull/7726
Source Issue: N/A

Seed varies: renames 'actions' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH510_gorm_7726'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH510_gorm_7726'
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        files = self._base_workspace()
        # Apply seed-based renaming to prevent direct memorization
        suffixes = ["", "_alt", "_impl"]
        suffix = suffixes[seed % len(suffixes)]
        if suffix:
            for fpath in list(files.keys()):
                files[fpath] = files[fpath].replace('actions', 'actions' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH510_gorm_7726',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'go-gorm/gorm',
                "pr_number": 7726,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/go-gorm/gorm/pull/7726",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            '.github/workflows/tests.yml': 'name: tests\n\non:\n  push:\n    branches-ignore:\n      - \'gh-pages\'\n  pull_request:\n    branches-ignore:\n      - \'gh-pages\'\n\npermissions:\n  contents: read\n\njobs:\n  # Label of the container job\n  sqlite:\n    strategy:\n      matrix:\n        go: [\'1.25\', \'1.26\']\n        platform: [ubuntu-latest] # can not run in windows OS\n    runs-on: ${{ matrix.platform }}\n\n    steps:\n    - name: Set up Go 1.x\n      uses: actions/setup-go@v4\n      with:\n        go-version: ${{ matrix.go }}\n\n    - name: Check out code into the Go module directory\n      uses: actions/checkout@v4\n\n    - name: go mod package cache\n      uses: actions/cache@v4\n      with:\n        path: ~/go/pkg/mod\n        key: ${{ runner.os }}-go-${{ matrix.go }}-${{ hashFiles(\'tests/go.mod\') }}\n\n    - name: Tests\n      run: GITHUB_ACTION=true GORM_DIALECT=sqlite ./tests/tests_all.sh\n\n  mysql:\n    strategy:\n      matrix:\n        dbversion: [\'mysql:9\', \'mysql:8\', \'mysql:5.7\']\n        go: [\'1.25\', \'1.26\']\n        platform: [ubuntu-latest]\n    runs-on: ${{ matrix.platform }}\n\n    services:\n      mysql:\n        image: ${{ matrix.dbversion }}\n        env:\n          MYSQL_DATABASE: gorm\n          MYSQL_USER: gorm\n          MYSQL_PASSWORD: gorm\n          MYSQL_RANDOM_ROOT_PASSWORD: "yes"\n        ports:\n          - 9910:3306\n        options: >-\n          --health-cmd "mysqladmin ping -ugorm -pgorm"\n          --health-interval 10s\n          --health-start-period 10s\n          --health-timeout 5s\n          --health-retries 10\n\n    steps:\n    - name: Set up Go 1.x\n      uses: actions/setup-go@v4\n      with:\n        go-version: ${{ matrix.go }}\n\n    - name: Check out code into the Go module directory\n      uses: actions/checkout@v4\n\n    - name: go mod package cache\n      uses: actions/cache@v4\n      with:\n        path: ~/go/pkg/mod\n        key: ${{ runner.os }}-go-${{ matrix.go }}-${{ hashFiles(\'tests/go.mod\') }}\n\n    - name: Tests\n      run: GITHUB_ACTION=true GORM_DIALECT=mysql GORM_DSN="gorm:gorm@tcp(localhost:9910)/gorm?charset=utf8&parseTime=True" ./tests/tests_all.sh\n\n  mariadb:\n    strategy:\n      matrix:\n        dbversion: [ \'mariadb:latest\' ]\n        go: [\'1.25\', \'1.26\']\n        platform: [ ubuntu-latest ]\n    runs-on: ${{ matrix.platform }}\n\n    services:\n      mysql:\n        image: ${{ matrix.dbversion }}\n        env:\n          MYSQL_DATABASE: gorm\n          MYSQL_USER: gorm\n          MYSQL_PASSWORD: gorm\n          MYSQL_RANDOM_ROOT_PASSWORD: "yes"\n        ports:\n          - 9910:3306\n        options: >-\n          --health-cmd "mariadb-admin ping -ugorm -pgorm"\n          --health-interval 10s\n          --health-start-period 10s\n          --health-timeout 5s\n          --health-retries 10\n\n    steps:\n      - name: Set up Go 1.x\n        uses: actions/setup-go@v4\n        with:\n          go-version: ${{ matrix.go }}\n\n      - name: Check out code into the Go module directory\n        uses: actions/checkout@v4\n\n      - name: go mod package cache\n        uses: actions/cache@v4\n        with:\n          path: ~/go/pkg/mod\n          key: ${{ runner.os }}-go-${{ matrix.go }}-${{ hashFiles(\'tests/go.mod\') }}\n\n      - name: Tests\n        run: GITHUB_ACTION=true GORM_DIALECT=mysql GORM_DSN="gorm:gorm@tcp(localhost:9910)/gorm?charset=utf8&parseTime=True" ./tests/tests_all.sh\n\n  postgres:\n    strategy:\n      matrix:\n        dbversion: [\'postgres:latest\', \'postgres:15\', \'postgres:14\', \'postgres:13\']\n        go: [\'1.25\', \'1.26\']\n        platform: [ubuntu-latest] # can not run in macOS and Windows\n    runs-on: ${{ matrix.platform }}\n\n    services:\n      postgres:\n        image: ${{ matrix.dbversion }}\n        env:\n          POSTGRES_PASSWORD: gorm\n          POSTGRES_USER: gorm\n          POSTGRES_DB: gorm\n          TZ: Asia/Shanghai\n        ports:\n          - 9920:5432\n        # Set health checks to wait until postgres has started\n        options: >-\n          --health-cmd pg_isready\n          --health-interval 10s\n          --health-timeout 5s\n          --health-retries 5\n\n    steps:\n    - name: Set up Go 1.x\n      uses: actions/setup-go@v4\n      with:\n        go-version: ${{ matrix.go }}\n\n    - name: Check out code into the Go module directory\n      uses: actions/checkout@v4\n\n    - name: go mod package cache\n      uses: actions/cache@v4\n      with:\n        path: ~/go/pkg/mod\n        key: ${{ runner.os }}-go-${{ matrix.go }}-${{ hashFiles(\'tests/go.mod\') }}\n\n    - name: Tests\n      run: GITHUB_ACTION=true GORM_DIALECT=postgres GORM_DSN="user=gorm password=gorm dbname=gorm host=localhost port=9920 sslmode=disable TimeZone=Asia/Shanghai" ./tests/tests_all.sh\n\n  sqlserver:\n    strategy:\n      matrix:\n        go: [\'1.25\', \'1.26\']\n        platform: [ubuntu-latest] # can not run test in macOS and windows\n    runs-on: ${{ matrix.platform }}\n\n    services:\n      mssql:\n        image: mcr.microsoft.com/mssql/server:2022-latest\n        env:\n          TZ: Asia/Shanghai\n          ACCEPT_EULA: Y\n          MSSQL_SA_PASSWORD: LoremIpsum86\n        ports:\n          - 9930:1433\n        options: >-\n          --health-cmd="/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P ${MSSQL_SA_PASSWORD} -N -C -l 30 -Q \\"SELECT 1\\" || exit 1"\n          --health-start-period 10s\n          --health-interval 10s\n          --health-timeout 5s\n          --health-retries 10\n\n    steps:\n    - name: Set up Go 1.x\n      uses: actions/setup-go@v4\n      with:\n        go-version: ${{ matrix.go }}\n\n    - name: Check out code into the Go module directory\n      uses: actions/checkout@v4\n\n    - name: go mod package cache\n      uses: actions/cache@v4\n      with:\n        path: ~/go/pkg/mod\n        key: ${{ runner.os }}-go-${{ matrix.go }}-${{ hashFiles(\'tests/go.mod\') }}\n\n    - name: Tests\n      run: GITHUB_ACTION=true GORM_DIALECT=sqlserver GORM_DSN="sqlserver://sa:LoremIpsum86@localhost:9930?database=master" ./tests/tests_all.sh\n\n  tidb:\n    strategy:\n      matrix:\n        dbversion: [ \'v6.5.0\' ]\n        go: [\'1.25\', \'1.26\']\n        platform: [ ubuntu-latest ]\n    runs-on: ${{ matrix.platform }}\n\n    steps:\n      - name: Setup TiDB\n        uses: Icemap/tidb-action@main\n        with:\n          port: 9940\n          version: ${{matrix.dbversion}}\n\n      - name: Set up Go 1.x\n        uses: actions/setup-go@v4\n        with:\n          go-version: ${{ matrix.go }}\n\n      - name: Check out code into the Go module directory\n        uses: actions/checkout@v4\n\n\n      - name: go mod package cache\n        uses: actions/cache@v4\n        with:\n          path: ~/go/pkg/mod\n          key: ${{ runner.os }}-go-${{ matrix.go }}-${{ hashFiles(\'tests/go.mod\') }}\n\n      - name: Tests\n        run: GITHUB_ACTION=true GORM_DIALECT=tidb GORM_DSN="root:@tcp(localhost:9940)/test?charset=utf8&parseTime=True&loc=Local" ./tests/tests_all.sh\n\n  gaussdb:\n    strategy:\n      matrix:\n        dbversion: [\'opengauss/opengauss:7.0.0-RC1.B023\']\n        go: [\'1.25\', \'1.26\']\n        platform: [ubuntu-latest] # can not run in macOS and Windows\n    runs-on: ${{ matrix.platform }}\n\n    services:\n      gaussdb:\n        image: ${{ matrix.dbversion }}\n        env:\n          # GaussDB has password limitations\n          GS_PASSWORD: Gaussdb@123\n          TZ: Asia/Shanghai\n        ports:\n          - 9950:5432\n\n    steps:\n      - name: Set up Go 1.x\n        uses: actions/setup-go@v4\n        with:\n          go-version: ${{ matrix.go }}\n\n      - name: Check out code into the Go module directory\n        uses: actions/checkout@v4\n\n      - name: Waiting for GaussDB to be ready\n        run: |\n          container_name=$(docker ps --filter "ancestor=opengauss/opengauss:7.0.0-RC1.B023" --format "{{.Names}}")\n          if [ -z "$container_name" ]; then\n            echo "Error: failed to find a container created from the \'opengauss/opengauss:7.0.0-RC1.B023\' image."\n            exit 1\n          fi\n          max_retries=12\n          retry_count=0\n          if [ -t 0 ]; then\n            TTY_FLAG="-t"\n          else\n            TTY_FLAG=""\n          fi\n          while [ $retry_count -lt $max_retries ]; do\n            if docker exec -i "${container_name}" bash -c "su - omm -c \'gsql -U omm -c \\"select 1;\\"\'" \n            then\n              echo "Creating database gorm..."\n              sql_file=\'/tmp/create_database.sql\'\n              echo "CREATE DATABASE gorm DBCOMPATIBILITY \'PG\';" > ${sql_file}\n              docker cp "${sql_file}" "${container_name}":"${sql_file}"\n              docker exec -i ${TTY_FLAG} "${container_name}" bash -c "su - omm -c \'gsql -U omm -f ${sql_file}\'"\n              echo "Database initialization completed."\n              break\n            fi\n\n            echo "Waiting for database to be ready... (attempt $((retry_count + 1))/$max_retries)"\n            sleep 10\n            ((++retry_count))\n          done\n          exit 0\n\n      - name: go mod package cache\n        uses: actions/cache@v4\n        with:\n          path: ~/go/pkg/mod\n          key: ${{ runner.os }}-go-${{ matrix.go }}-${{ hashFiles(\'tests/go.mod\') }}\n\n      - name: Tests\n        run: GITHUB_ACTION=true GORM_DIALECT=gaussdb GORM_DSN="user=gaussdb password=Gaussdb@123 dbname=gorm host=localhost port=9950 sslmode=disable TimeZone=Asia/Shanghai" ./tests/tests_all.sh\n',
        }

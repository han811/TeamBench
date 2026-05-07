"""
Parameterized generator for GH41_fiber_4133.

Source PR:    https://github.com/gofiber/fiber/pull/4133
Source Issue: https://github.com/gofiber/fiber/issues/4132

Seed varies: renames 'addr' identifier with suffix across seeds.

Bug: pre-PR state of workspace files contains the bug the PR fixes.
Fix: agent must replicate the PR's changes guided by spec.md.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask


class Generator(TaskGenerator):
    task_id = 'GH41_fiber_4133'
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", 'GH41_fiber_4133'
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
                files[fpath] = files[fpath].replace('addr', 'addr' + suffix)
        # Deep parameterization — consistent cross-seed variation
        from generators.gh_deep_param import deep_rename_symbols, add_realistic_noise
        files = deep_rename_symbols(files, seed, strategy="mixed")
        files = add_realistic_noise(files, seed, noise_level=0.15)
        return GeneratedTask(
            task_id='GH41_fiber_4133',
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "repo": 'gofiber/fiber',
                "pr_number": 4133,
                "bug_fixed": True,
            },
            workspace_files=files,
            metadata={
                "difficulty": "medium",
                "category": "Real-World GitHub",
                "source_pr": "https://github.com/gofiber/fiber/pull/4133",
            },
        )

    def _base_workspace(self) -> dict[str, str]:
        """Return the pre-PR (buggy) workspace files."""
        return {
            'prefork.go': 'package fiber\n\nimport (\n\t"crypto/tls"\n\t"errors"\n\t"fmt"\n\t"net"\n\t"os"\n\t"os/exec"\n\t"runtime"\n\t"sync/atomic"\n\t"time"\n\n\t"github.com/valyala/fasthttp/reuseport"\n\n\t"github.com/gofiber/fiber/v3/log"\n)\n\nconst (\n\tenvPreforkChildKey = "FIBER_PREFORK_CHILD"\n\tenvPreforkChildVal = "1"\n\tsleepDuration      = 100 * time.Millisecond\n\twindowsOS          = "windows"\n)\n\nvar (\n\ttestPreforkMaster = false\n\ttestOnPrefork     = false\n)\n\n// IsChild determines if the current process is a child of Prefork\nfunc IsChild() bool {\n\treturn os.Getenv(envPreforkChildKey) == envPreforkChildVal\n}\n\n// prefork manages child processes to make use of the OS REUSEPORT or REUSEADDR feature\nfunc (app *App) prefork(addr string, tlsConfig *tls.Config, cfg *ListenConfig) error {\n\tif cfg == nil {\n\t\tcfg = &ListenConfig{}\n\t}\n\tvar ln net.Listener\n\tvar err error\n\n\t// 👶 child process 👶\n\tif IsChild() {\n\t\t// use 1 cpu core per child process\n\t\truntime.GOMAXPROCS(1)\n\t\t// Linux will use SO_REUSEPORT and Windows falls back to SO_REUSEADDR\n\t\t// Only tcp4 or tcp6 is supported when preforking, both are not supported\n\t\tif ln, err = reuseport.Listen(cfg.ListenerNetwork, addr); err != nil {\n\t\t\tif !cfg.DisableStartupMessage {\n\t\t\t\ttime.Sleep(sleepDuration) // avoid colliding with startup message\n\t\t\t}\n\t\t\treturn fmt.Errorf("prefork: %w", err)\n\t\t}\n\t\t// wrap a tls config around the listener if provided\n\t\tif tlsConfig != nil {\n\t\t\tln = tls.NewListener(ln, tlsConfig)\n\t\t}\n\n\t\t// kill current child proc when master exits\n\t\tgo watchMaster()\n\n\t\t// prepare the server for the start\n\t\tapp.startupProcess()\n\n\t\tif cfg.ListenerAddrFunc != nil {\n\t\t\tcfg.ListenerAddrFunc(ln.Addr())\n\t\t}\n\n\t\t// listen for incoming connections\n\t\treturn app.server.Serve(ln)\n\t}\n\n\t// 👮 master process 👮\n\ttype child struct {\n\t\terr error\n\t\tpid int\n\t}\n\t// create variables\n\tmaxProcs := runtime.GOMAXPROCS(0)\n\tchildren := make(map[int]*exec.Cmd)\n\tchannel := make(chan child, maxProcs)\n\n\t// kill child procs when master exits\n\tdefer func() {\n\t\tfor _, proc := range children {\n\t\t\tif err = proc.Process.Kill(); err != nil {\n\t\t\t\tif !errors.Is(err, os.ErrProcessDone) {\n\t\t\t\t\tlog.Errorf("prefork: failed to kill child: %v", err)\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}()\n\n\t// collect child pids\n\tvar childPIDs []int\n\n\t// launch child procs\n\tfor range maxProcs {\n\t\tcmd := exec.Command(os.Args[0], os.Args[1:]...) //nolint:gosec // It\'s fine to launch the same process again\n\t\tif testPreforkMaster {\n\t\t\t// When test prefork master,\n\t\t\t// just start the child process with a dummy cmd,\n\t\t\t// which will exit soon\n\t\t\tcmd = dummyCmd()\n\t\t}\n\t\tcmd.Stdout = os.Stdout\n\t\tcmd.Stderr = os.Stderr\n\n\t\t// add fiber prefork child flag into child proc env\n\t\tcmd.Env = append(os.Environ(),\n\t\t\tfmt.Sprintf("%s=%s", envPreforkChildKey, envPreforkChildVal),\n\t\t)\n\n\t\tif err = cmd.Start(); err != nil {\n\t\t\treturn fmt.Errorf("failed to start a child prefork process, error: %w", err)\n\t\t}\n\n\t\t// store child process\n\t\tpid := cmd.Process.Pid\n\t\tchildren[pid] = cmd\n\t\tchildPIDs = append(childPIDs, pid)\n\n\t\t// execute fork hook\n\t\tif app.hooks != nil {\n\t\t\tif testOnPrefork {\n\t\t\t\tapp.hooks.executeOnForkHooks(dummyPid)\n\t\t\t} else {\n\t\t\t\tapp.hooks.executeOnForkHooks(pid)\n\t\t\t}\n\t\t}\n\n\t\t// notify master if child crashes\n\t\tgo func() {\n\t\t\tchannel <- child{pid: pid, err: cmd.Wait()}\n\t\t}()\n\t}\n\n\t// Run onListen hooks\n\t// Hooks have to be run here as different as non-prefork mode due to they should run as child or master\n\tlistenData := app.prepareListenData(addr, tlsConfig != nil, cfg, childPIDs)\n\n\tapp.runOnListenHooks(listenData)\n\n\tapp.startupMessage(listenData, cfg)\n\n\tif cfg.EnablePrintRoutes {\n\t\tapp.printRoutesMessage()\n\t}\n\n\t// return error if child crashes\n\treturn (<-channel).err\n}\n\n// watchMaster watches child procs\nfunc watchMaster() {\n\tif runtime.GOOS == windowsOS {\n\t\t// finds parent process,\n\t\t// and waits for it to exit\n\t\tp, err := os.FindProcess(os.Getppid())\n\t\tif err == nil {\n\t\t\t_, _ = p.Wait() //nolint:errcheck // It is fine to ignore the error here\n\t\t}\n\t\tos.Exit(1) //nolint:revive // Calling os.Exit is fine here in the prefork\n\t}\n\t// if it is equal to 1 (init process ID),\n\t// it indicates that the master process has exited\n\tconst watchInterval = 500 * time.Millisecond\n\tfor range time.NewTicker(watchInterval).C {\n\t\tif os.Getppid() == 1 {\n\t\t\tos.Exit(1) //nolint:revive // Calling os.Exit is fine here in the prefork\n\t\t}\n\t}\n}\n\nvar (\n\tdummyPid      = 1\n\tdummyChildCmd atomic.Value\n)\n\n// dummyCmd is for internal prefork testing\nfunc dummyCmd() *exec.Cmd {\n\tcommand := "go"\n\tif storeCommand := dummyChildCmd.Load(); storeCommand != nil && storeCommand != "" {\n\t\tcommand = storeCommand.(string) //nolint:forcetypeassert,errcheck // We always store a string in here\n\t}\n\tif runtime.GOOS == windowsOS {\n\t\treturn exec.Command("cmd", "/C", command, "version")\n\t}\n\treturn exec.Command(command, "version")\n}\n',
        }

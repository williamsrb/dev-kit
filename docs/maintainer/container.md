# The headless CLI-agent container

The one place Docker earns its keep: a vendor CLI plus `agentctl` plus the core
skills, with the project bind-mounted. No GUI, no Docker socket.

It is useful for three things:

- CI, where a GUI is meaningless
- untrusted-repo work, where the isolation is the point
- a clean-room check that `bootstrap.sh` actually works on a fresh machine,
  which is hard to test on a box that already has everything

## What it is not

It is not profile isolation. See [design.md](design.md#profile-isolation-is-environment-variables-not-containers).

It deliberately does **not** mount `/var/run/docker.sock`. A mounted socket is
root-equivalent on the host, which would erase the isolation the container
exists for. That means the image cannot drive `docker compose` or
`enonic sandbox` — and if you need those, you want the host, not this.

## Building

```bash
docker build -f Dockerfile.agent -t devkit:core --build-arg PROFILE=core .
docker run --rm -it -v "$PWD:/work" -w /work devkit:core
```

The build runs the real `bootstrap.sh`, which is what makes it a useful test
rather than a parallel install path that drifts.

## Why this is the only container

The kit does not containerize the harness for profile isolation — see the
"Why not Docker" section of the [README](../../README.md). GUI-in-Docker was
assessed and rejected; this headless image is the one place Docker earns its
keep.

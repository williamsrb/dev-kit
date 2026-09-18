<!-- src:https://developer.enonic.com/docs/code/stable/tooling/ci-cd generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/tooling/ci-cd.md

# Setting up CI/CD pipelines

Reference configurations for building, testing, and deploying Enonic XP apps with common CI/CD providers.

## CI/CD images

Enonic publishes Docker images purpose-built for CI/CD pipelines. Each image bundles the latest minor of a given XP major version, the latest Enonic CLI, and essentials like Yarn and common Node tools. Tag format is `enonic/enonic-ci:.`.

See the [full tag list on Docker Hub](https://hub.docker.com/r/enonic/enonic-ci/tags) for available images. The examples below use `8` — pin to a concrete `.` tag in production.

## Deployment variables

The Enonic CLI reads deployment credentials from environment variables:

- `ENONIC_CLI_REMOTE_URL` — management port URL (e.g. `[https://host:4848](https://host:4848)`).

- `ENONIC_CLI_REMOTE_USER` — deployment user.

- `ENONIC_CLI_REMOTE_PASS` — password for the above user.

See the [Enonic CLI reference](https://developer.enonic.com/docs/enonic-cli/stable/xp#environment_variables) for the full list. The GitHub Actions example below uses dedicated actions with their own inputs rather than these variables.

## CI/CD providers

### GitHub Actions

GitHub Actions integrates via the `enonic/action-app-build` and `enonic/action-app-deploy` actions. Deployment uses a [Service Account Key](https://developer.enonic.com/docs/platform/xp8/security/service-accounts) rather than basic auth. Store the key file contents and the management URL as repository secrets; add client certificate and key secrets if mTLS is enabled.

Example workflow (`.github/workflows/enonic.yml`):

```yaml
name: Enonic CI deploy

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: enonic/action-app-build@v1
      - uses: enonic/action-app-deploy@v1
        with:
          url: ${{ secrets.XP_REMOTE_URL }}
          cred_file: ${{ secrets.XP_CRED_FILE }}
          client_cert: ${{ secrets.XP_CLIENT_CERT }}
          client_key: ${{ secrets.XP_CLIENT_KEY }}
```

### CircleCI

CircleCI runs the Enonic CI image and invokes the CLI for build and deploy. Configure the [deployment variables](#env-var) via [project environment variables](https://circleci.com/docs/guides/security/set-environment-variable/) or [contexts](https://circleci.com/docs/guides/security/contexts/).

Example config (`.circleci/config.yml`):

```yaml
version: 2.1
jobs:
  build:
    working_directory: ~/app
    docker:
      - image: enonic/enonic-ci:{release}
    steps:
      - checkout
      - run: /setup_sandbox.sh
      - run: enonic project build
      - run: enonic app install --file build/libs/*.jar
```

### Jenkins

Jenkins runs the Enonic CI image via the `docker` agent. Configure the [deployment variables](#env-var) as [credentials](https://jenkins.io/doc/book/pipeline/jenkinsfile/#handling-credentials).

Example `Jenkinsfile`:

```text
pipeline {
  agent {
    docker {
      image 'enonic/enonic-ci:{release}'
    }
  }
  environment {
    ENONIC_CLI_REMOTE_URL  = credentials('jenkins-enonic-url')
    ENONIC_CLI_REMOTE_USER = credentials('jenkins-enonic-user')
    ENONIC_CLI_REMOTE_PASS = credentials('jenkins-enonic-pass')
  }
  stages {
    stage('Build') {
      steps {
        sh '/setup_sandbox.sh'
        sh 'enonic project build'
      }
    }
    stage('Deploy') {
      steps {
        sh 'enonic app install --file build/libs/*.jar'
      }
    }
  }
}
```

## Conditional deployment

Most providers support conditional deployment to multiple environments — for example, feature branches to a test server, `master` to staging, and tagged releases to production (with manual approval).

The CircleCI workflow below uses three contexts (`testing-server`, `staging-server`, `production-server`), each holding its own set of [deployment variables](#env-var):

```yaml
version: 2.1

executors:
  xp-executor:
    docker:
      - image: enonic/enonic-ci:{release}
    working_directory: ~/app

jobs:
  build:
    executor: xp-executor
    steps:
      - checkout
      - run: /setup_sandbox.sh
      - run: enonic project build
      - persist_to_workspace:
          root: ~/app/build
          paths:
            - libs
  deploy:
    executor: xp-executor
    steps:
      - attach_workspace:
          at: ~/app/build
      - run: enonic app install --file build/libs/*.jar

workflows:
  xp-ci-cd:
    jobs:
      - build:
          filters:
            tags:
              only: /.*/
            branches:
              only: /.*/
      - deploy:
          name: deploy-testing
          context: testing-server
          requires: [build]
          filters:
            branches:
              only: /^feature-.*/
      - deploy:
          name: deploy-staging
          context: staging-server
          requires: [build]
          filters:
            tags:
              only: /.*/
            branches:
              only: master
      - deploy-prod-approval:
          type: approval
          requires: [build]
          filters:
            tags:
              only: /^v[0-9]+\.[0-9]+\.[0-9]+$/
            branches:
              ignore: /.*/
      - deploy:
          name: deploy-production
          context: production-server
          requires: [build, deploy-prod-approval]
          filters:
            tags:
              only: /^v[0-9]+\.[0-9]+\.[0-9]+$/
            branches:
              ignore: /.*/
```

Production deploys wait on manual approval of the `deploy-prod-approval` hold job in the CircleCI workflow UI.

## FAQ

### Build prompts to select sandbox

The CI image’s entrypoint has been overridden. Run `/setup_sandbox.sh` before `enonic project build` in the pipeline (as shown in the CircleCI and Jenkins examples above).

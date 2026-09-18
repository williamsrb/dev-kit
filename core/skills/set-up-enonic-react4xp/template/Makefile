APP := {PROJECT_SHORT_NAME}-xp-app
DCWD := /enonic-xp/source
PROTO_APP := {PROJECT_SHORT_NAME}-prototype
PROTO_DCWD := /usr/app/prototype
USER := $(shell /usr/bin/id -u)
UNAME_S := $(shell uname -s)

PROTOTYPE_COMPONENTS_DIR := prototype/src/components
ENONIC_COMPONENTS_DIR := xp/src/main/resources/react4xp/components/prototype

PROTOTYPE_PAGES_DIR := prototype/src/pages

PROTOTYPE_ASSETS_DIR := prototype/src/assets
ENONIC_ASSETS_DIR := xp/src/main/resources/react4xp/shared

PROTOTYPE_FONTS_DIR := prototype/public/fonts
ENONIC_FONTS_DIR := xp/src/main/resources/react4xp/shared/fonts

PROTOTYPE_UTILS_DIR := prototype/src/utils
ENONIC_UTILS_DIR := xp/src/main/resources/react4xp/utils/prototype

#Enonic
up:
	docker compose -f ./docker/dev/docker-compose.yml up --build -d

down:
	docker compose -f ./docker/dev/docker-compose.yml down

logs:
	docker logs -f $(APP)

access:
	docker exec -it $(APP) bash

copyComponents:
	rsync -av --exclude='.gitkeep' $(PROTOTYPE_COMPONENTS_DIR)/ $(ENONIC_COMPONENTS_DIR)/
	rsync -av --exclude='.gitkeep' $(PROTOTYPE_PAGES_DIR)/ $(ENONIC_COMPONENTS_DIR)/
	rsync -av --exclude='.gitkeep' $(PROTOTYPE_ASSETS_DIR)/ $(ENONIC_ASSETS_DIR)/
	rsync -av --exclude='.gitkeep' $(PROTOTYPE_FONTS_DIR)/ $(ENONIC_FONTS_DIR)/
	rsync -av --exclude='.gitkeep' $(PROTOTYPE_UTILS_DIR)/ $(ENONIC_UTILS_DIR)/
ifeq ($(UNAME_S),Darwin)
	find $(ENONIC_UTILS_DIR) -type f -exec LC_ALL=C sed -i '' 's|@/components|/react4xp/components/prototype|g' {} +
	find $(ENONIC_COMPONENTS_DIR) -type f -exec LC_ALL=C sed -i '' 's|@/components|/react4xp/components/prototype|g' {} +
	find $(ENONIC_COMPONENTS_DIR) -type f -exec LC_ALL=C sed -i '' 's|@/assets|/react4xp/shared|g' {} +
	find $(ENONIC_COMPONENTS_DIR) -type f -exec LC_ALL=C sed -i '' 's|@/utils|/react4xp/utils/prototype|g' {} +
	find $(ENONIC_ASSETS_DIR) -type f -exec LC_ALL=C sed -i '' "s|url('/fonts/|url('/react4xp/shared/fonts/|g" {} +
else
	find $(ENONIC_UTILS_DIR) -type f -exec sed -i 's|@/components|/react4xp/components/prototype|g' {} +
	find $(ENONIC_COMPONENTS_DIR) -type f -exec sed -i 's|@/components|/react4xp/components/prototype|g' {} +
	find $(ENONIC_COMPONENTS_DIR) -type f -exec sed -i 's|@/assets|/react4xp/shared|g' {} +
	find $(ENONIC_COMPONENTS_DIR) -type f -exec sed -i 's|@/utils|/react4xp/utils/prototype|g' {} +
	find $(ENONIC_ASSETS_DIR) -type f -exec sed -i "s|url('/fonts/|url('/react4xp/shared/fonts/|g" {} +
endif

clean:
	docker exec -it $(APP) sh -c "(cd $(DCWD) && ./gradlew clean)"

build:
	docker exec -it $(APP) sh -c "(cd $(DCWD) && rm -f package-lock.json && rm -rf node_modules/@acme && ./gradlew build)"

deploy:
	docker exec -it $(APP) sh -c "(cd $(DCWD) && ./gradlew deploy)"

grant:
	bash -c "sudo chmod -R a+rw . && sudo chown -R $(USER):$(USER) ."

full: copyComponents clean build deploy

# Prototype
protoUp:
	docker compose -f ./docker/prototype-local/docker-compose.yml up --build

protoDown:
	docker compose -f ./docker/prototype-local/docker-compose.yml down

protoInstall:
	docker exec -it $(PROTO_APP) sh -c "npm install"

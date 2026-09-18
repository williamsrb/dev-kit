# Permite que o container se conecte ao servidor X11 local
xhost +local:docker

docker run -d \
  --name cursor_trabalho \
  --net=host \
  --ipc=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
  -v /meus-perfis-cursor/perfil_trabalho/config:/home/devuser/.config/Cursor \
  -v /meus-perfis-cursor/perfil_trabalho/extensions:/home/devuser/.cursor/extensions \
  -v /caminho/para/projetos/trabalho:/home/devuser/projects \
  cursor-ide-image

